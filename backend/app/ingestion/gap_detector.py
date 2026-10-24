import json
import re
import datetime
import urllib.parse
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.models import PoliticalParty, PoliticalProposal, IngestionLog, AuditLog
from app.ai.proposal_validator import sanitize_and_validate_proposal_statement, strip_media_source_suffix
from app.ingestion.sources_config import PARTY_ALIASES
from app.ingestion.universal_web_search import search_web_news, search_duckduckgo_open_web
from app.ingestion.text_extractor import compute_content_hash, clean_html
from app.ai.extractor import extract_proposals_from_text
from app.ai.embeddings import get_text_embedding
from app.ai.fact_checker import analyze_feasibility_and_factcheck
from app.ai.policy_merger import find_matching_existing_proposal, merge_or_update_policy_proposal
from app.ingestion.dossier_generator import generate_party_dossier

CORE_MACRO_TOPICS = [
    "Fisco",
    "Lavoro",
    "Sanità",
    "Pensioni",
    "Energia",
    "Istruzione",
    "Istituzioni",
    "Immigrazione",
    "Politica Estera",
    "Diritti Civili",
    "Infrastrutture"
]

PARTY_SEARCH_ANCHORS = {
    "Fratelli d'Italia": "Fratelli d'Italia Giorgia Meloni",
    "Partito Democratico": "Partito Democratico Elly Schlein",
    "Movimento 5 Stelle": "Movimento 5 Stelle Giuseppe Conte",
    "Lega - Salvini Premier": "Lega Matteo Salvini",
    "Forza Italia": "Forza Italia Antonio Tajani",
    "Alleanza Verdi e Sinistra": "Alleanza Verdi e Sinistra Bonelli Fratoianni",
    "Azione": "Azione Carlo Calenda",
    "Italia Viva": "Italia Viva Matteo Renzi",
    "+Europa": "+Europa Riccardo Magi Emma Bonino",
    "Partito Liberal Democratico": "Partito Liberal Democratico Luigi Marattin",
    "Noi Moderati": "Noi Moderati Maurizio Lupi",
    "Futuro Nazionale": "Futuro Nazionale Roberto Vannacci",
    "ORA!": "ORA! Alberto Forchielli Michele Boldrin",
    "Democrazia Sovrana Popolare": "Democrazia Sovrana Popolare Marco Rizzo",
    "Rifondazione Comunista": "Rifondazione Comunista Maurizio Acerbo",
    "Potere al Popolo": "Potere al Popolo Marta Collot",
    "Radicali Italiani": "Radicali Italiani Matteo Hallissey",
    "Südtiroler Volkspartei": "Südtiroler Volkspartei Dieter Steger",
    "Sud chiama Nord": "Sud chiama Nord Cateno De Luca",
    "Pace Terra Dignità": "Pace Terra Dignità Michele Santoro",
    "Partito Socialista Italiano": "Partito Socialista Italiano Enzo Maraio",
    "Alternativa Popolare": "Alternativa Popolare Stefano Bandecchi"
}

TOPIC_FOCUSED_KEYWORDS = {
    "Fisco": ["tasse", "IRPEF", "flat tax", "cuneo fiscale", "detrazioni"],
    "Lavoro": ["salario minimo", "stipendi", "occupazione", "contratti"],
    "Sanità": ["fondo sanitario", "liste attesa", "medici", "ospedali", "SSN"],
    "Pensioni": ["quota 41", "pensioni", "legge Fornero", "uscita anticipata"],
    "Energia": ["nucleare", "rinnovabili", "bollette", "transizione energetica"],
    "Istruzione": ["scuola", "università", "docenti", "tempo pieno"],
    "Istituzioni": ["premierato", "autonomia differenziata", "riforma giustizia", "separazione carriere"],
    "Immigrazione": ["immigrazione", "decreti sicurezza", "ius scholae", "CPR"],
    "Politica Estera": ["Ucraina", "spese militari", "difesa europea", "Nato", "Piano Mattei"],
    "Diritti Civili": ["fine vita", "matrimonio egualitario", "cittadinanza", "carceri"],
    "Infrastrutture": ["Ponte sullo Stretto", "ferrovie", "rete idrica", "trasporti"]
}

TOPIC_SEARCH_TERMS = {
    "Fisco": "fisco tasse flat tax irpef detrazioni cuneo",
    "Lavoro": "lavoro salario minimo stipendi occupazione contratti",
    "Sanità": "sanità ospedali fondo sanitario liste attesa medici ssn",
    "Pensioni": "pensioni quota 41 fornero previdenza uscita anticipata",
    "Energia": "energia nucleare rinnovabili bollette transizione ecologica fotovoltaico",
    "Istruzione": "scuola università docenti istruzione ricerca tempo pieno",
    "Istituzioni": "premierato autonomia differenziata riforme giustizia costituzione",
    "Immigrazione": "immigrazione migranti frontiere rimpatri cpr asilo",
    "Politica Estera": "ucraina esteri difesa spese militari unione europea nato",
    "Diritti Civili": "diritti civili fine vita cittadinanza carceri ius scholae",
    "Infrastrutture": "infrastrutture opere pubbliche ferrovie trasporti ponti rete idrica"
}

def detect_information_gaps(db: Session, max_gaps: int = 6) -> List[Dict[str, Any]]:
    """
    Scans the database to identify political information voids:
    1. Finds parties and macro-topics with 0 proposals (total void).
    2. Prioritizes under-represented parties to eliminate information starvation.
    3. Dynamically rotates priorities across 10-minute cycles so all 18 parties and 11 topics are scanned.
    """
    parties = db.query(PoliticalParty).all()
    all_proposals = db.query(PoliticalProposal).all()
    
    matrix: Dict[str, Dict[str, List[PoliticalProposal]]] = {}
    party_total_counts: Dict[str, int] = {}
    
    for p in parties:
        matrix[p.name] = {t: [] for t in CORE_MACRO_TOPICS}
        party_total_counts[p.name] = 0
        
    for prop in all_proposals:
        p_name = prop.partito
        if p_name in matrix:
            t = prop.macro_argomento
            if t in matrix[p_name]:
                matrix[p_name][t].append(prop)
            else:
                mapped = False
                for core_t in CORE_MACRO_TOPICS:
                    if core_t.lower() in t.lower() or t.lower() in core_t.lower():
                        matrix[p_name][core_t].append(prop)
                        mapped = True
                        break
                if not mapped and (t.lower() in ["esteri", "difesa", "affari esteri"]):
                    matrix[p_name]["Politica Estera"].append(prop)
            party_total_counts[p_name] = party_total_counts.get(p_name, 0) + 1

    gap_candidates = []
    now = datetime.datetime.utcnow()
    cycle_seed = (now.hour * 6 + now.minute // 10)
    
    for party in parties:
        p_name = party.name
        total_p = party_total_counts.get(p_name, 0)
        
        for topic in CORE_MACRO_TOPICS:
            props = matrix[p_name].get(topic, [])
            gap_score = 0
            reason = ""
            
            if len(props) == 0:
                gap_score = 100
                reason = f"Lacuna totale: nessuna proposta censita in materia di {topic}"
            elif len(props) == 1:
                gap_score = 35
                reason = f"Copertura minima: una sola posizione censita in materia di {topic}"
            else:
                latest_ts = max((p.timestamp for p in props if p.timestamp), default=datetime.datetime(2022, 1, 1))
                days_old = (now - latest_ts).days
                if days_old > 365:
                    gap_score = 25
                    reason = f"Posizione da aggiornare: ultimo riscontro risalente a oltre un anno fa ({latest_ts.year})"
                    
            if gap_score > 0:
                # 1. Scarcity bonus: severely under-represented parties (< 10 proposals) are boosted massively
                scarcity_bonus = max(0, 20 - total_p) * 25
                
                # 2. Dynamic cyclic rotation bonus: rotates priority among tied parties every 10-minute cycle
                party_hash = sum(ord(ch) for ch in p_name)
                rot_bonus = ((party_hash + cycle_seed) % 18) * 3
                
                total_gap_score = gap_score + scarcity_bonus + rot_bonus
                
                anchor = PARTY_SEARCH_ANCHORS.get(p_name, p_name)
                focused_terms = TOPIC_FOCUSED_KEYWORDS.get(topic, [topic])
                k1 = focused_terms[0]
                k2 = focused_terms[1] if len(focused_terms) > 1 else topic
                
                # Use disambiguated search name for parties whose name is a common word (e.g. ORA!)
                search_name = "Movimento ORA!" if p_name == "ORA!" else p_name

                # Crisp, high-yield search queries tailored for search engines
                queries = [
                    f'"{search_name}" {topic} proposta',
                    f'"{anchor}" {k1} ddl',
                    f'"{search_name}" {topic} disegno di legge',
                    f'"{search_name}" programma {k2}'
                ]
                if party.official_website:
                    domain = urllib.parse.urlparse(party.official_website).netloc.replace("www.", "")
                    if domain:
                        queries.append(f"site:{domain} {topic}")
                
                gap_candidates.append({
                    "party_name": p_name,
                    "party_code": party.code,
                    "topic": topic,
                    "gap_score": total_gap_score,
                    "existing_count": len(props),
                    "party_total": total_p,
                    "reason": reason,
                    "queries": queries
                })

    # Sort strictly by gap_score descending (which embeds scarcity and cycle rotation)
    gap_candidates.sort(key=lambda x: x["gap_score"], reverse=True)
    
    # Pluralistic selection: max 1 gap per party per cycle to diversify knowledge across 6 forces
    selected_gaps = []
    seen_parties = set()
    for candidate in gap_candidates:
        p = candidate["party_name"]
        if p not in seen_parties:
            selected_gaps.append(candidate)
            seen_parties.add(p)
            if len(selected_gaps) >= max_gaps:
                break
                
    if len(selected_gaps) < max_gaps:
        for candidate in gap_candidates:
            if candidate not in selected_gaps:
                selected_gaps.append(candidate)
                if len(selected_gaps) >= max_gaps:
                    break

    return selected_gaps

def _extract_gap_policy_commitment(text: str, party_name: str, topic: str, title: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Analyzes article text and title specifically for the targeted party and topic to extract
    concrete programmatic commitments and public policy proposals.
    Requires explicit party attribution to avoid attributing union/media noise.
    """
    party_aliases = [a.lower() for a in PARTY_ALIASES.get(party_name, [party_name.lower()])]
    full_corpus = f"{title or ''} {text}".lower()
    
    # 0. Party Attribution Gate: party must be explicitly mentioned in the text or headline
    has_party = any(re.search(r"\b" + re.escape(a) + r"\b", full_corpus) for a in party_aliases)
    if not has_party:
        return None

    clean_title = strip_media_source_suffix(title) if title else ""
    topic_keywords = TOPIC_FOCUSED_KEYWORDS.get(topic, [topic])
    topic_keywords_all = topic_keywords + [topic.lower()]
    
    # 1. Check headline / title for explicit proposal quotes or statements
    if clean_title:
        t_low = clean_title.lower()
        if any(kw.lower() in t_low for kw in topic_keywords_all):
            quote_m = re.search(r"[:'\"«]\s*([^'\"»]{18,150})", clean_title)
            if quote_m:
                # Ensure the party was mentioned BEFORE the quote in the headline!
                prefix_headline = t_low[:quote_m.start()]
                if any(re.search(r"\b" + re.escape(a) + r"\b", prefix_headline) for a in party_aliases):
                    q_text = quote_m.group(1).strip()
                    valid_q = sanitize_and_validate_proposal_statement(q_text)
                    if valid_q:
                        act = "Proposta di legge" if any(w in t_low for w in ["ddl", "disegno di legge", "legge", "emendamento"]) else "Dichiarazione programmatica"
                        if any(w in t_low for w in ["no a", "stop a", "contro", "boccia", "respinge"]):
                            act = "Opposizione"
                        return {
                            "sintesi": f"{valid_q[0].upper() + valid_q[1:]}",
                            "tipo_azione": act,
                            "costo": "Non quantificato",
                            "coperture": "Fondi ordinari di bilancio e riordino della spesa"
                        }

    # 2. Check body sentences for policy commitments
    sentences = re.split(r"(?<=[.!?])\s+", text)
    
    commitment_patterns = [
        r"(?:propon(?:e|e di|iamo|e che)|chied(?:e|e di|iamo)|presenta (?:un |la |il )?(?:ddl|disegno di legge|proposta|mozione|piano|riforma)|nostro programma prevede|nostra proposta (?:è|sarà)|intende (?:introdurre|istituire|tagliare|aumentare|cancellare|riformare|ridurre)|priorit[àa] (?:è|sarà|rimane)|sostien(?:e|iamo)|punta (?:su|a)|vuole (?:introdurre|tagliare|riformare|investire)|lancia (?:la proposta|il piano|la misura per))\s+([^.!?]{18,220})",
        r"(?:annuncia (?:il|la|un|una) (?:ddl|proposta|piano|legge)|ha depositato (?:un|il) disegno di legge per|deposita la proposta per)\s+([^.!?]{18,220})",
        r"(?:nel programma di [^:]+:\s*|linea di [^:]+:\s*)([^.!?]{18,220})",
        r"(?:ferma opposizione (?:a|al|alla|allo|ai|agli|alle)|chiede lo stop (?:a|al|alla|allo|ai|agli|alle|del|della|di)|promuove il referendum (?:per|contro|abrogativo))\s+([^.!?]{18,220})",
        r"(?:battaglia|obiettivo|impegno).*sul(?:la|lo|l')?\s+([a-zA-Z0-9\s,]{15,180})",
        r"(?:per riformare|per rilanciare|per sostenere|per tagliare|per finanziare)\s+([^.!?]{18,180})"
    ]
    
    for idx, sentence in enumerate(sentences):
        s_low = sentence.lower()
        if not any(kw.lower() in s_low for kw in topic_keywords_all):
            continue

        # Context window: check that party is mentioned in sentence or adjacent sentence
        context = s_low
        if idx > 0:
            context = sentences[idx - 1].lower() + " " + context
        if idx + 1 < len(sentences):
            context = context + " " + sentences[idx + 1].lower()
        if not any(re.search(r"\b" + re.escape(a) + r"\b", context) for a in party_aliases):
            continue

        for pat in commitment_patterns:
            match = re.search(pat, sentence, re.I)
            if match:
                raw_prop = match.group(1).strip()
                raw_prop = re.sub(r"\s+", " ", raw_prop)
                raw_prop = re.sub(r"^(?:che\s+|di\s+|per\s+|a\s+|e\s+)", "", raw_prop, flags=re.I).strip()
                raw_prop = re.sub(r"[,;:\-–—\s]+$", "", raw_prop).strip()
                if len(raw_prop) >= 18 and not any(noise in raw_prop.lower() for noise in ["arrestato", "indagato", "sfida", "congresso", "lite", "bufera", "scandalo", "insulti"]):
                    # Strict validation: verify proposal statement is not an abstract slogan
                    valid_prop = sanitize_and_validate_proposal_statement(raw_prop)
                    if not valid_prop:
                        # If raw_prop was a rhetorical phrase, check if title mentions a specific legislative bill
                        if clean_title and re.search(r"\b(ddl|disegno di legge|proposta di legge|legge|emendamento)\b", clean_title, re.I):
                            title_clean = re.sub(r"^.*?:\s*", "", clean_title).strip()
                            valid_prop = sanitize_and_validate_proposal_statement(title_clean)
                    if not valid_prop:
                        continue

                    if any(w in s_low for w in ["ferma opposizione", "chiede lo stop", "referendum abrogativo", "contrari"]):
                        act = "Opposizione"
                    elif any(w in s_low for w in ["ddl", "disegno di legge", "legge", "emendamento"]):
                        act = "Proposta di legge"
                    else:
                        act = "Dichiarazione programmatica"
                    
                    cost_m = re.search(r"(\d+(?:[.,]\d+)?\s*(?:miliardi|milioni|mld|mln|€|euro))", sentence, re.I)
                    cost = cost_m.group(1) if cost_m else "Non quantificato"
                    
                    cov = "Fondi ordinari di bilancio e riordino delle spese"
                    cov_m = re.search(r"(?:coperture|finanziat[oa]|risorse da|tramite)\s*([^.;]{10,80})", sentence, re.I)
                    if cov_m:
                        cov = cov_m.group(1).strip()
                        
                    return {
                        "sintesi": f"{valid_prop[0].upper() + valid_prop[1:]}",
                        "tipo_azione": act,
                        "costo": cost,
                        "coperture": cov
                    }

    return None

async def autonomous_targeted_gap_search(db: Session, max_gaps: int = 6) -> Dict[str, Any]:
    """
    Autonomously searches the web for the detected political gaps,
    extracts policy proposals, merges them into permanent memory,
    and updates the respective party's AI dossier.
    """
    gaps = detect_information_gaps(db, max_gaps=max_gaps)
    if not gaps:
        return {"status": "NO_GAPS", "message": "Nessuna lacuna rilevata, copertura bilanciata.", "added": 0}
        
    total_added_or_updated = 0
    searched_targets = []
    
    for gap in gaps:
        p_name = gap["party_name"]
        topic = gap["topic"]
        searched_targets.append(f"{p_name} ({topic})")
        
        # 1. Fetch targeted news
        articles = []
        for q in gap["queries"][:2]:
            found = search_web_news(q, max_results=5)
            articles.extend(found)
            if len(articles) >= 5:
                break
                
        if len(articles) < 3 and len(gap["queries"]) > 1:
            ddg_items = search_duckduckgo_open_web(gap["queries"][0], max_results=4)
            articles.extend(ddg_items)

        party_obj = db.query(PoliticalParty).filter(PoliticalParty.name == p_name).first()
        party_id = party_obj.id if party_obj else None

        proposals_added_for_topic = 0

        for art in articles:
            if proposals_added_for_topic >= 3:
                break
            raw_text = art["raw_text"]
            content_hash = compute_content_hash(raw_text)
            
            # Try standard extraction
            extracted = await extract_proposals_from_text(
                text=raw_text,
                url=art["url"],
                title=art["title"],
                published_at=art["published_at"]
            )
            
            # If standard extractor missed, use targeted gap commitment heuristic
            if not extracted:
                comm = _extract_gap_policy_commitment(raw_text, p_name, topic, title=art.get("title"))
                if comm:
                    from app.ai.fiscal_calculator import calculate_fiscal_impact_and_coverage
                    f_calc = calculate_fiscal_impact_and_coverage(
                        partito=p_name,
                        macro_argomento=topic,
                        sintesi=comm["sintesi"],
                        costo_stimato=comm["costo"],
                        coperture_dichiarate=comm["coperture"]
                    )
                    comm["costo"] = f_calc["costo_stimato"]
                    comm["coperture"] = f_calc["coperture_dichiarate"]
                    feasibility = f_calc["fattibilita_finanziaria"]
                    status = f_calc["fact_check_status"]
                    motivazione = f_calc["fact_check_motivazione"]
                    fonte_verif = f_calc["fact_check_fonte"]
                    
                    text_to_embed = f"{p_name} {topic} {comm['sintesi']}"
                    emb_list = await get_text_embedding(text_to_embed)
                    emb_json = json.dumps(emb_list) if emb_list else None
                    item_hash = compute_content_hash(f"{p_name}_{topic}_{comm['sintesi']}")

                    matching_comm = find_matching_existing_proposal(
                        db=db,
                        party_id=party_id,
                        partito=p_name,
                        macro_argomento=topic,
                        dichiarazione_sintesi=comm["sintesi"],
                        emb_list=emb_list
                    )
                    if matching_comm:
                        old_s = matching_comm.dichiarazione_sintesi
                        matching_comm.dichiarazione_sintesi = comm["sintesi"]
                        matching_comm.costo_stimato = comm["costo"]
                        matching_comm.coperture_dichiarate = comm["coperture"]
                        matching_comm.fattibilita_finanziaria = feasibility
                        matching_comm.fact_check_status = status
                        matching_comm.timestamp = art.get("published_at", datetime.datetime.utcnow())
                        db.add(AuditLog(
                            event_type="modifica",
                            entity_type="programma",
                            entity_id=str(matching_comm.id),
                            entity_name=f"{p_name}: {topic}",
                            old_value=old_s[:90] + "..." if len(old_s) > 90 else old_s,
                            new_value=comm["sintesi"][:90] + "..." if len(comm["sintesi"]) > 90 else comm["sintesi"],
                            agent_responsible="PolicyMergerAgent",
                            details=f"Modifica proposta per {p_name} ({topic}) da riscontro web: '{comm['sintesi']}'.",
                            timestamp=datetime.datetime.utcnow()
                        ))
                        total_added_or_updated += 1
                        proposals_added_for_topic += 1
                        continue

                    record = PoliticalProposal(
                        party_id=party_id,
                        partito=p_name,
                        macro_argomento=topic,
                        dichiarazione_sintesi=comm["sintesi"],
                        tipo_azione=comm["tipo_azione"],
                        costo_stimato=comm["costo"],
                        coperture_dichiarate=comm["coperture"],
                        fattibilita_finanziaria=feasibility,
                        fact_check_status=status,
                        fact_check_motivazione=motivazione,
                        fact_check_fonte=fonte_verif,
                        fonte_url=art["url"],
                        fonte_titolo=art["title"] or f"Presa di posizione {p_name} su {topic}",
                        fonte_testata=art.get("source_name", "Ricerca Mirata Web"),
                        raw_text=raw_text,
                        content_hash=item_hash,
                        embedding=emb_json,
                        timestamp=art.get("published_at", datetime.datetime.utcnow())
                    )
                    db.add(record)
                    db.flush()
                    db.add(AuditLog(
                        event_type="aggiunta",
                        entity_type="programma",
                        entity_id=str(record.id),
                        entity_name=f"{p_name}: {topic}",
                        old_value=None,
                        new_value=record.dichiarazione_sintesi[:90] + "..." if len(record.dichiarazione_sintesi) > 90 else record.dichiarazione_sintesi,
                        agent_responsible="PolicyDistillerAgent",
                        details=f"Aggiunta proposta per {p_name} ({topic}) tramite ricerca mirata: '{record.dichiarazione_sintesi}'.",
                        timestamp=datetime.datetime.utcnow()
                    ))
                    total_added_or_updated += 1
                    proposals_added_for_topic += 1
                    continue

            for item in extracted:
                if item.partito.lower() in p_name.lower() or p_name.lower() in item.partito.lower():
                    text_to_embed = f"{item.partito} {item.macro_argomento} {item.dichiarazione_sintesi}"
                    emb_list = await get_text_embedding(text_to_embed)
                    emb_json = json.dumps(emb_list) if emb_list else None
                    item_hash = compute_content_hash(f"{item.partito}_{item.macro_argomento}_{item.dichiarazione_sintesi}")

                    matching_existing = find_matching_existing_proposal(
                        db=db,
                        party_id=party_id,
                        partito=item.partito,
                        macro_argomento=item.macro_argomento,
                        dichiarazione_sintesi=item.dichiarazione_sintesi,
                        emb_list=emb_list
                    )

                    if matching_existing:
                        old_s = matching_existing.dichiarazione_sintesi
                        merge_or_update_policy_proposal(
                            db=db,
                            existing=matching_existing,
                            item=item,
                            url=art["url"],
                            title=art["title"],
                            source_name=art["source_name"],
                            published_at=art["published_at"],
                            raw_text=raw_text,
                            content_hash=item_hash,
                            emb_json=emb_json
                        )
                        db.add(AuditLog(
                            event_type="modifica",
                            entity_type="programma",
                            entity_id=str(matching_existing.id),
                            entity_name=f"{item.partito}: {item.macro_argomento}",
                            old_value=old_s[:90] + "..." if len(old_s) > 90 else old_s,
                            new_value=item.dichiarazione_sintesi[:90] + "..." if len(item.dichiarazione_sintesi) > 90 else item.dichiarazione_sintesi,
                            agent_responsible="PolicyMergerAgent",
                            details=f"Modifica proposta per {item.partito} ({item.macro_argomento}): '{item.dichiarazione_sintesi}'.",
                            timestamp=datetime.datetime.utcnow()
                        ))
                        total_added_or_updated += 1
                        gap_filled_for_this_topic = True
                    else:
                        dt = datetime.datetime.fromisoformat(item.timestamp) if item.timestamp else art["published_at"]
                        new_prop = PoliticalProposal(
                            party_id=party_id,
                            partito=item.partito,
                            macro_argomento=item.macro_argomento,
                            dichiarazione_sintesi=item.dichiarazione_sintesi,
                            tipo_azione=item.tipo_azione,
                            costo_stimato=item.impatto_economico.costo_stimato,
                            coperture_dichiarate=item.impatto_economico.coperture_dichiarate,
                            fattibilita_finanziaria=item.impatto_economico.fattibilita_finanziaria,
                            fact_check_status=item.fact_check.status,
                            fact_check_motivazione=item.fact_check.motivazione_oggettiva,
                            fact_check_fonte=item.fact_check.fonte_verifica,
                            fonte_url=item.fonte_url or art["url"],
                            fonte_titolo=art["title"],
                            fonte_testata=art["source_name"],
                            raw_text=raw_text,
                            content_hash=item_hash,
                            embedding=emb_json,
                            timestamp=dt
                        )
                        db.add(new_prop)
                        db.flush()
                        db.add(AuditLog(
                            event_type="aggiunta",
                            entity_type="programma",
                            entity_id=str(new_prop.id),
                            entity_name=f"{item.partito}: {item.macro_argomento}",
                            old_value=None,
                            new_value=new_prop.dichiarazione_sintesi[:90] + "..." if len(new_prop.dichiarazione_sintesi) > 90 else new_prop.dichiarazione_sintesi,
                            agent_responsible="PolicyDistillerAgent",
                            details=f"Aggiunta proposta per {item.partito} ({item.macro_argomento}): '{new_prop.dichiarazione_sintesi}'.",
                            timestamp=datetime.datetime.utcnow()
                        ))
                        total_added_or_updated += 1
                        proposals_added_for_topic += 1

        # Update dossier for this party if a new proposal was recorded
        if party_obj:
            try:
                dossier_data = generate_party_dossier(party_obj, db)
                party_obj.dossier_ai = json.dumps(dossier_data, ensure_ascii=False)
            except Exception as e:
                print(f"[GapDetector] Dossier update error for {party_obj.name}: {e}")

    db.commit()
    msg = f"Ricerca mirata su {len(searched_targets)} lacune ({', '.join(searched_targets)}): integrate/aggiornate {total_added_or_updated} posizioni formalizzate."
    return {
        "status": "GAPS_SEARCHED",
        "searched_targets": searched_targets,
        "proposals_added_or_updated": total_added_or_updated,
        "message": msg
    }
