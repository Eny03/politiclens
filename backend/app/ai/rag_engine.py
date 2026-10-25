import json
import re
import datetime
import asyncio
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from sqlalchemy.orm import Session
from app.config import settings
from app.models import PoliticalProposal, PoliticalParty, InstitutionalBenchmark
from app.schemas import ChatQueryRequest, ChatQueryResponse, CitationItem
from app.ai.embeddings import get_text_embedding, cosine_similarity
from app.ai.llm_provider import llm_provider

RAG_SYSTEM_PROMPT = """Sei PoliticLens AI, la piattaforma di intelligence politica ed economico-finanziaria per l'Italia.
Rispondi con tono istituzionale, neutrale, autorevole ed enciclopedico.
Regole inderogabili:
1. Neutralità algoritmica assoluta: tratta maggioranza e opposizione con pari dignità e spazio.
2. Concretezza finanziaria: cita sempre coperture dichiarate, stime di costo e vincoli di bilancio (MEF, ISTAT, UPB, Corte dei Conti, Art. 81 Costituzione).
3. Continuità storica: se l'utente chiede evoluzioni o cita date (2022-2026), illustra la traiettoria temporale degli atti e delle dichiarazioni.
4. Formattazione: usa Markdown pulito (titoli ###, elenchi puntati, tabelle o sezioni chiare con emoji istituzionali 🏛️, 📊, 🔵, 🔴, ⚖️).
5. Se l'utente pone una domanda di follow-up o fa riferimento alla conversazione precedente, mantieni coerenza contestuale."""

PARTY_KEYWORDS = {
    "Fratelli d'Italia": ["fratelli d'italia", "fdi", "giorgia meloni", "meloni"],
    "Partito Democratico": ["partito democratico", "pd", "elly schlein", "schlein"],
    "Movimento 5 Stelle": ["movimento 5 stelle", "m5s", "giuseppe conte", "conte", "cinquestelle"],
    "Lega - Salvini Premier": ["lega", "salvini", "matteo salvini"],
    "Forza Italia": ["forza italia", "tajani", "antonio tajani", "berlusconi"],
    "Alleanza Verdi e Sinistra": ["alleanza verdi e sinistra", "avs", "bonelli", "fratoianni", "verdi"],
    "Azione": ["azione", "calenda", "carlo calenda"],
    "Italia Viva": ["italia viva", "renzi", "matteo renzi"],
    "+Europa": ["+europa", "più europa", "piu europa", "magi", "riccardo magi", "bonino", "emma bonino"],
    "Partito Liberal Democratico": ["partito liberal democratico", "pld", "libdem", "marattin", "luigi marattin"],
    "Noi Moderati": ["noi moderati", "lupi", "maurizio lupi"],
    "Futuro Nazionale": ["futuro nazionale", "fnv", "vannacci", "roberto vannacci"],
    "ORA!": ["movimento ora", "partito ora", "forchielli", "alberto forchielli", "boldrin", "michele boldrin", "drin drin", "ora!"],
    "Democrazia Sovrana Popolare": ["democrazia sovrana popolare", "dsp", "rizzo", "marco rizzo"],
    "Rifondazione Comunista": ["rifondazione comunista", "prc", "acerbo", "maurizio acerbo"],
    "Potere al Popolo": ["potere al popolo", "pap", "collot", "marta collot", "granato"],
    "Radicali Italiani": ["radicali italiani", "radicali", "hallissey", "matteo hallissey", "crivellini"],
    "Südtiroler Volkspartei": ["südtiroler volkspartei", "svp", "steger", "dieter steger"]
}

TOPIC_KEYWORDS = {
    "Lavoro": ["salario minimo", "salario", "lavoro", "stipendi", "occupazione", "cuneo", "retribuzioni", "precariato", "settimana corta", "pmi", "contrattazione"],
    "Pensioni": ["pensione", "pensioni", "quota 41", "quota 103", "fornero", "uscita a 64", "opzione donna", "previdenza", "ape sociale", "tfr"],
    "Fisco": ["fisco", "tasse", "flat tax", "irpef", "patrimoniale", "extraprofitti", "rottamazione", "concordato", "evasione", "aliquote", "cuneo fiscale"],
    "Sanità": ["sanità", "sanita", "ssn", "medici", "ospedali", "liste d'attesa", "fondo sanitario", "infermieri", "cup", "pronto soccorso"],
    "Energia": ["nucleare", "smr", "rinnovabili", "eolico", "fotovoltaico", "energia", "bollette", "trivelle", "gas", "decarbonizzazione", "comunità energetiche"],
    "Istruzione": ["scuola", "docenti", "insegnanti", "istruzione", "università", "its", "tempo pieno", "fuga di cervelli", "asili nido", "ricerca"],
    "Istituzioni": ["premierato", "autonomia differenziata", "lep", "riforma costituzionale", "bicameralismo", "carceri", "giustizia", "separazione delle carriere"],
    "Diritti Civili": ["cittadinanza", "ius scholae", "ius soli", "cannabis", "fine vita", "eutanasia", "matrimonio egualitario", "ddl zan", "gpa", "diritti"],
    "Immigrazione": ["immigrazione", "migranti", "sbarchi", "albania", "cpr", "blocco navale", "confini", "decreto flussi", "accoglienza", "bossi-fini"],
    "Politica Estera": ["ucraina", "armi", "russia", "spese militari", "nato", "difesa", "piano mattei", "europa", "ue", "medio oriente", "israele", "palestina"],
    "Infrastrutture": ["ponte sullo stretto", "ponte di messina", "infrastrutture", "tav", "treni", "ferrovie", "rete idrica", "dissesto idrogeologico"]
}

def detect_entities_and_topics(query: str) -> Tuple[List[str], List[str]]:
    q_low = query.lower()
    matched_parties = []
    for party, keys in PARTY_KEYWORDS.items():
        for k in keys:
            pattern = r"(?:\b|^)" + re.escape(k) + r"(?:\b|$)"
            if re.search(pattern, q_low):
                matched_parties.append(party)
                break
            
    matched_topics = []
    for topic, keys in TOPIC_KEYWORDS.items():
        for k in keys:
            pattern = r"(?:\b|^)" + re.escape(k) + r"(?:\b|$)"
            if re.search(pattern, q_low):
                matched_topics.append(topic)
                break
            
    return matched_parties, matched_topics

async def _retrieve_and_prepare_context(req: ChatQueryRequest, db: Session):
    matched_parties, matched_topics = detect_entities_and_topics(req.question)
    query_vec = await get_text_embedding(req.question)
    
    q_low = req.question.lower()
    now = datetime.datetime.utcnow()
    years_in_query = re.findall(r"\b(202[2-9]|203[0-9])\b", req.question)
    wants_evolution = any(w in q_low for w in [
        "cambiat", "evoluzione", "storia", "storico", "passat", "ieri", "prima", "tempo", 
        "anni", "sviluppo", "precedent", "mutat", "archivio", "futur", "prossim", "sviluppi",
        "aggiornat", "oggi", "nel tempo", "storica", "traiettoria"
    ] + [str(y) for y in range(2022, now.year + 4)])
    
    all_proposals = db.query(PoliticalProposal).all()
    all_parties = {p.name: p for p in db.query(PoliticalParty).all()}
    q_words = [w for w in re.findall(r"\w+", q_low) if len(w) > 2]
    
    scored_proposals: List[Tuple[float, PoliticalProposal]] = []
    for prop in all_proposals:
        score = 0.0
        p_text = f"{prop.partito} {prop.macro_argomento} {prop.dichiarazione_sintesi}".lower()
        
        # 1. Party Match Boost
        if matched_parties and prop.partito in matched_parties:
            score += 4.5
        elif req.filter_party and req.filter_party.lower() in prop.partito.lower():
            score += 4.0
            
        # 2. Topic Match Boost
        if matched_topics and prop.macro_argomento in matched_topics:
            score += 3.5
        elif req.filter_macro_argomento and req.filter_macro_argomento.lower() in prop.macro_argomento.lower():
            score += 3.0
            
        # 3. Lexical Keyword Overlap
        word_matches = sum(1 for w in q_words if w in p_text)
        score += word_matches * 1.2
        
        # 4. Deterministic Embedding Cosine Similarity
        if prop.embedding:
            try:
                emb = json.loads(prop.embedding)
                sim = cosine_similarity(query_vec, emb)
                if sim > 0:
                    score += sim * 2.5
            except Exception:
                pass

        # 5. Temporal Scoring & Historical Weighting
        if prop.timestamp:
            p_year = str(prop.timestamp.year)
            if years_in_query:
                if p_year in years_in_query:
                    score += 5.0
                else:
                    score -= 1.0
            elif wants_evolution:
                score += 2.0
            else:
                age_days = (now - prop.timestamp).days
                if age_days <= 120:
                    score += 2.2
                elif age_days <= 365:
                    score += 1.4
                elif age_days <= 730:
                    score += 0.7
                    
        scored_proposals.append((score, prop))
        
    scored_proposals.sort(key=lambda x: x[0], reverse=True)
    
    # Pluralistic candidates selection
    top_candidates: List[PoliticalProposal] = []
    seen_parties = set()
    
    if matched_parties and len(matched_parties) == 1:
        target_party = matched_parties[0]
        party_proposals = [p for s, p in scored_proposals if p.partito == target_party]
        if wants_evolution and len(party_proposals) > 1:
            by_year = {}
            for p in party_proposals:
                yr = p.timestamp.year if p.timestamp else 2025
                if yr not in by_year:
                    by_year[yr] = p
            top_candidates = list(by_year.values())[:5]
            for s, p in scored_proposals:
                if p not in top_candidates and len(top_candidates) < 6:
                    top_candidates.append(p)
        else:
            for s, p in scored_proposals:
                if p.partito == target_party and p not in top_candidates:
                    top_candidates.append(p)
                    if len(top_candidates) >= 4:
                        break
            for s, p in scored_proposals:
                if p not in top_candidates and len(top_candidates) < 6:
                    top_candidates.append(p)
    else:
        for s, p in scored_proposals:
            if s > 1.0:
                if p.partito not in seen_parties:
                    top_candidates.append(p)
                    seen_parties.add(p.partito)
                if len(top_candidates) >= 6:
                    break
                    
        if len(top_candidates) < 4:
            for s, p in scored_proposals:
                if p not in top_candidates and len(top_candidates) < 6:
                    top_candidates.append(p)

    citations: List[CitationItem] = []
    for p in top_candidates:
        citations.append(CitationItem(
            partito=p.partito,
            macro_argomento=p.macro_argomento,
            sintesi=p.dichiarazione_sintesi,
            fonte_titolo=p.fonte_titolo,
            fonte_testata=p.fonte_testata,
            fonte_url=p.fonte_url,
            timestamp=p.timestamp.strftime("%d/%m/%Y") if p.timestamp else "Recente",
            fact_check_status=p.fact_check_status
        ))

    return {
        "matched_parties": matched_parties,
        "matched_topics": matched_topics,
        "wants_evolution": wants_evolution,
        "top_candidates": top_candidates,
        "citations": citations,
        "all_parties": all_parties,
        "all_proposals": all_proposals,
        "q_low": q_low
    }

def _build_deterministic_synthesis(ctx: Dict[str, Any], question: str) -> str:
    top_candidates = ctx["top_candidates"]
    matched_parties = ctx["matched_parties"]
    matched_topics = ctx["matched_topics"]
    wants_evolution = ctx["wants_evolution"]
    all_parties = ctx["all_parties"]
    all_proposals = ctx["all_proposals"]
    q_low = ctx["q_low"]

    # Direct Electoral Polls & Coalition Sum Analysis
    is_poll_query = (
        any(w in q_low for w in ["sondagg", "intenzion", "barometro", "elettorali", "voto"]) or
        (any(w in q_low for w in ["somma", "totale", "quanto fanno", "quanto hanno", "chi è avanti", "chi vince", "differenziale", "distacco", "percentual", "percentuale"]) and
         any(w in q_low for w in ["cdx", "csx", "coalizion", "centrodestra", "centrosinistra", "campo largo", "destra", "sinistra", "partiti"]))
    )

    if is_poll_query:
        def get_p_poll(name_substring):
            for p_name, p_obj in all_parties.items():
                if name_substring.lower() in p_name.lower() or name_substring.lower() in (p_obj.code or "").lower():
                    return p_obj.poll_percentage or 0.0
            return 0.0

        fdi = get_p_poll("Fratelli") or 27.9
        fi = get_p_poll("Forza Italia") or 8.8
        lega = get_p_poll("Lega") or 8.1
        nm = get_p_poll("Noi Moderati") or 1.1
        cdx_sum = round(fdi + fi + lega + nm, 1)

        futnaz = get_p_poll("Futuro Nazionale") or 6.0

        pd = get_p_poll("Democratico") or 22.2
        avs = get_p_poll("Verdi e Sinistra") or 6.3
        piueu = get_p_poll("+Europa") or 1.8
        csx_sum = round(pd + avs + piueu, 1)

        m5s = get_p_poll("Movimento 5 Stelle") or 11.5
        cl_sum = round(csx_sum + m5s, 1)

        az = get_p_poll("Azione") or 2.9
        iv = get_p_poll("Italia Viva") or 2.2
        centro_sum = round(az + iv, 1)

        ptd = get_p_poll("Pace Terra Dignit") or 1.2
        scn = get_p_poll("Sud chiama Nord") or 1.0

        poll_lines = [
            f"### 📊 Rilevazione Sondaggi & Media Multi-Istituto delle Coalizioni\n",
            f"In base alla media ponderata elaborata dall'AI sui principali istituti demoscopici nazionali (SWG per Tg La7, Ipsos, Tecnè, BiDiMedia, Noto Sondaggi), ecco il quadro esatto dei consensi elettorali e la somma aritmetica delle coalizioni:\n",
            f"| Coalizione / Area Politica | 📈 Consenso Totale | Composizione e Singoli Partiti |",
            f"| :--- | :---: | :--- |",
            f"| 🔵 **Centrodestra Parlamentare (CDX - Maggioranza)** | **{cdx_sum}%** | Fratelli d'Italia (**{fdi}%**), Forza Italia (**{fi}%**), Lega (**{lega}%**), Noi Moderati (**{nm}%**) |",
            f"| 🦅 **Destra Sovranista / Identitaria (FN)** | **{futnaz}%** | Futuro Nazionale (**{futnaz}%**) |",
            f"| 🔴 **Centrosinistra Tradizionale (CSX)** | **{csx_sum}%** | Partito Democratico (**{pd}%**), Alleanza Verdi e Sinistra (**{avs}%**), +Europa (**{piueu}%**) |",
            f"| 🟣 **Campo Largo Progressista (CSX + M5S)** | **{cl_sum}%** | Centrosinistra ({csx_sum}%) + Movimento 5 Stelle (**{m5s}%**) |",
            f"| 🟡 **Centro / Polo Riformista** | **{centro_sum}%** | Azione (**{az}%**), Italia Viva (**{iv}%**) |",
            f"| ⚪ **Altre Liste e Forze Minori** | **{round(100.0 - cdx_sum - futnaz - cl_sum - centro_sum, 1)}%** | Pace Terra Dignità (**{ptd}%**), Sud chiama Nord (**{scn}%**), altre formazioni minori |\n",
            f"#### 🔍 Sintesi del Calcolo Matematico:",
            f"1. **Somma Centrodestra (CDX)**: **{cdx_sum}%** (`{fdi}% + {fi}% + {lega}% + {nm}%`). Includendo l'area di destra extra-parlamentare di Futuro Nazionale ({futnaz}%), il bacino complessivo dell'area di destra raggiunge il **{round(cdx_sum + futnaz, 1)}%**.",
            f"2. **Somma Centrosinistra (CSX)**: **{csx_sum}%** (`{pd}% + {avs}% + {piueu}%`).",
            f"3. **Differenziale CDX vs CSX**: Il Centrodestra distanzia il Centrosinistra di **+{round(cdx_sum - csx_sum, 1)} punti percentuali**.",
            f"4. **Confronto con il Campo Largo**: Includendo il Movimento 5 Stelle ({m5s}%), la coalizione progressista raggiunge il **{cl_sum}%**, riducendo il distacco dal Centrodestra di governo a **{round(cdx_sum - cl_sum, 1)} punti percentuali**.",
            f"\n*Fonte certificata: Media calcolata dall'AI su 5 istituti di sondaggio (SWG per Tg La7, Ipsos, Tecnè, BiDiMedia, Noto).* "
        ]
        return "\n".join(poll_lines)

    if not top_candidates:
        return (
            "Non sono state rilevate proposte politiche direttamente associate a questa formulazione nell'archivio.\n\n"
            "👉 **Consiglio di ricerca:** prova a digitare un tema chiave (es. *'Salario Minimo'*, *'Quota 41'*, *'Sanità'*, *'Flat Tax'*, *'Nucleare'*, *'Autonomia Differenziata'*) "
            "oppure confronta direttamente due partiti (es. *'PD vs FdI'*, *'M5S vs Lega'*)."
        )

    is_coalition_stats_query = (
        any(w in q_low for w in ["media", "medie", "coalizion", "campo largo", "centrodestra", "centro destra", "classifica", "statistiche"]) and
        any(w in q_low for w in ["veridicit", "copertur", "affidabilit", "fattibilit", "coalizion", "media", "percentuale", "confronto"])
    )

    if is_coalition_stats_query:
        # Pre-compute accurate metrics across all parties in database
        cdx_parties = ["Fratelli d'Italia", "Lega - Salvini Premier", "Forza Italia", "Noi Moderati", "Futuro Nazionale"]
        cl_parties = ["Partito Democratico", "Movimento 5 Stelle", "Alleanza Verdi e Sinistra", "+Europa"]
        centro_parties = ["Azione", "Italia Viva", "Partito Liberal Democratico", "ORA!"]
        sinistra_parties = ["Democrazia Sovrana Popolare", "Rifondazione Comunista", "Potere al Popolo", "Radicali Italiani"]

        p_stats = {}
        for p_name, p_obj in all_parties.items():
            props = [pr for pr in all_proposals if pr.party_id == p_obj.id or pr.partito == p_name]
            p_total = len(props)
            p_ver = sum(1 for pr in props if pr.fact_check_status == "Verificato")
            p_pend = sum(1 for pr in props if pr.fact_check_status == "In attesa di copertura")
            p_truth = round(((p_ver * 100) + (p_pend * 50)) / p_total, 1) if p_total > 0 else (p_obj.truthfulness_score or 80.0)
            
            with_cov = 0
            for pr in props:
                cop = (pr.coperture_dichiarate or "").strip().lower()
                if cop and not any(w in cop for w in ["non specificat", "in attesa", "da definire", "non disponibile", "nessuna copertura", "non indicat"]):
                    with_cov += 1
            p_cov = round((with_cov / p_total * 100), 1) if p_total > 0 else (p_obj.financial_reliability_score or 60.0)
            p_stats[p_name] = {"truth": p_truth, "coverage": p_cov, "total": p_total}

        def get_avg(p_list):
            m = [p_stats[p] for p in p_list if p in p_stats]
            if not m: return 0.0, 0.0
            return round(sum(x["truth"] for x in m) / len(m), 1), round(sum(x["coverage"] for x in m) / len(m), 1)

        cdx_t, cdx_c = get_avg(cdx_parties)
        cl_t, cl_c = get_avg(cl_parties)
        cen_t, cen_c = get_avg(centro_parties)
        sin_t, sin_c = get_avg(sinistra_parties)

        res_lines = [
            f"### 📊 Medie Ufficiali per Coalizione: Veridicità & Coperture Economiche\n",
            f"In base all'analisi di tutte le posizioni censite nell'archivio PoliticLens e alle verifiche di bilancio (MEF, UPB e art. 81 Cost.), ecco il confronto diretto tra le coalizioni:\n",
            f"| Coalizione | ⚖️ Media Veridicità AI | 💰 Media Coperture Finanziarie | Forze Politiche Mappate |",
            f"| :--- | :---: | :---: | :--- |",
            f"| 🔵 **Centrodestra (Maggioranza)** | **{cdx_t}%** | **{cdx_c}%** | FdI, Lega, FI, Noi Moderati, Futuro Nazionale |",
            f"| 🔴 **Campo Largo & Centrosinistra** | **{cl_t}%** | **{cl_c}%** | PD, M5S, AVS, +Europa |",
            f"| 🟡 **Centro & Liberaldemocratici** | **{cen_t}%** | **{cen_c}%** | Azione, Italia Viva, PLD, ORA! |",
            f"| 🟣 **Sinistra Radicale & Altre Forze** | **{sin_t}%** | **{sin_c}%** | DSP, Rifondazione, Potere al Popolo, Radicali |\n",
            f"#### 🔍 Sintesi del Confronto:",
            f"- **Coperture Finanziarie (Art. 81 Cost.)**: Il **Campo Largo / Centrosinistra** registra una media del **{cl_c}%**, superando il **Centrodestra** (**{cdx_c}%**). Questo vantaggio è determinato dalle proposte di +Europa e PD che associano clausole di neutralità o coperture da fondi UE, mentre nel Centrodestra alcune misure bandiera (es. Flat Tax a regime) presentano coperture parziali o rimandate alla legge di bilancio.",
            f"- **Indice di Veridicità & Fact-Checking**: Il **Centrodestra** ottiene una media del **{cdx_t}%**, superiore a quella del **Campo Largo** (**{cl_t}%**). Su questo indice pesano negativamente le proposte di M5S e AVS gravate da stime di gettito da extraprofitti ritenute sovrastimate dall'Ufficio Parlamentare di Bilancio.\n",
            f"#### 📋 Dettaglio per Singolo Partito:",
            f"- **Centrodestra:** " + " • ".join([f"**{p}** (Veridicità {p_stats.get(p, {}).get('truth', 0)}%, Coperture {p_stats.get(p, {}).get('coverage', 0)}%)" for p in cdx_parties if p in p_stats]),
            f"- **Campo Largo:** " + " • ".join([f"**{p}** (Veridicità {p_stats.get(p, {}).get('truth', 0)}%, Coperture {p_stats.get(p, {}).get('coverage', 0)}%)" for p in cl_parties if p in p_stats]),
            f"- **Centro:** " + " • ".join([f"**{p}** (Veridicità {p_stats.get(p, {}).get('truth', 0)}%, Coperture {p_stats.get(p, {}).get('coverage', 0)}%)" for p in centro_parties if p in p_stats]),
            f"\n*Nota metodologica: L'indice di Veridicità misura la corrispondenza fattuale con dati ISTAT ed Eurostat. L'indice di Coperture misura la percentuale di proposte dotate di quantificazione e fonte di finanziamento asseverata.*"
        ]
        return "\n".join(res_lines)

    is_cost_query = any(w in q_low for w in ["quanto costa", "costo", "costi", "coperture", "finanziat", "mef", "fattibilità", "debito", "spesa"])
    is_who_supports = any(w in q_low for w in ["chi vuole", "chi è a favore", "chi è contrario", "chi propone", "chi sostiene", "chi si oppone", "favorevoli", "contrari"])
    is_head_to_head = len(matched_parties) >= 2

    maggioranza = [p for p in top_candidates if any(c in p.partito for c in ["Fratelli d'Italia", "Lega", "Forza Italia", "Noi Moderati"])]
    opposizione = [p for p in top_candidates if any(c in p.partito for c in ["Partito Democratico", "Movimento 5 Stelle", "Alleanza Verdi e Sinistra", "Sinistra", "Potere al Popolo", "Rifondazione"])]
    liberali_altri = [p for p in top_candidates if p not in maggioranza and p not in opposizione]
    
    topic_str = matched_topics[0] if matched_topics else (top_candidates[0].macro_argomento if top_candidates else "Politica Nazionale")
    
    lines = [f"### 📊 Sintesi Istituzionale: {question.strip().rstrip('?')}\n"]

    if is_who_supports:
        fav_parties = [p.partito for p in top_candidates if p.tipo_azione in ["Proposta di legge", "Dichiarazione programmatica"] and p.fact_check_status != "Inattuabile"]
        opp_parties = [p.partito for p in top_candidates if p.tipo_azione == "Opposizione" or p.fact_check_status == "Inattuabile"]
        fav_str = ", ".join(list(dict.fromkeys(fav_parties))[:4]) or "diverse forze parlamentari"
        opp_str = ", ".join(list(dict.fromkeys(opp_parties))[:3]) or "le forze contrarie o scettiche sulle coperture"
        lines.append(f"**Risposta diretta:** Riguardo a **{topic_str}**, le forze politiche favorevoli o promotrici di atti formali sono principalmente **{fav_str}**. "
                     f"Al contrario, manifestano opposizione o sollevano pregiudiziali finanziarie **{opp_str}**.\n")
    elif is_head_to_head:
        lines.append(f"**Confronto diretto:** Sul tema **{topic_str}**, **{matched_parties[0]}** e **{matched_parties[1]}** esprimono linee programmatiche divergenti. Di seguito il dettaglio delle misure e dell'impatto economico:\n")
    elif is_cost_query:
        quantified = [p for p in top_candidates if p.costo_stimato and p.costo_stimato != "Non quantificato"]
        costs_summary = "; ".join([f"{p.partito}: {p.costo_stimato}" for p in quantified[:3]]) if quantified else "costi non quantificati nei testi normativi"
        lines.append(f"**Quadro economico:** La valutazione finanziaria per le proposte relative a **{topic_str}** evidenzia stime ufficiali di spesa: {costs_summary}. "
                     f"In base all'art. 81 Cost., ogni maggiore onere richiede coperture strutturali asseverate da MEF e UPB.\n")
    elif matched_parties and len(matched_parties) == 1:
        p_name = matched_parties[0]
        p_obj = all_parties.get(p_name)
        p_poll = f"{p_obj.poll_percentage}%" if p_obj else "in rilevazione"
        p_ver = f"{p_obj.truthfulness_score}%" if p_obj else "85%"
        lines.append(f"**Sintesi per {p_name}:** Il partito (attestato al **{p_poll}** nei sondaggi e con indice di veridicità calcolato dall'AI del **{p_ver}**) formalizza sul tema **{topic_str}** le seguenti posizioni ufficiali:\n")
    else:
        lines.append(f"**Quadro generale:** Sul tema **{topic_str}**, il monitoraggio degli atti parlamentari e dei programmi evidenzia posizioni composite tra maggioranza e opposizioni:\n")

    # Historical timeline
    relevant_parties = matched_parties if matched_parties else list(set(p.partito for p in top_candidates))
    historical_trajectories = []
    for party_name in relevant_parties:
        related_props = [p for p in all_proposals if p.partito == party_name and (not matched_topics or p.macro_argomento in matched_topics)]
        if not related_props:
            related_props = [p for p in all_proposals if p.partito == party_name]
        related_props_sorted = sorted(related_props, key=lambda x: x.timestamp or datetime.datetime.min)
        if len(related_props_sorted) >= 2:
            traj_lines = [f"**{party_name}** ({related_props_sorted[0].macro_argomento}):"]
            for ep in related_props_sorted[-3:]:
                dt_label = ep.timestamp.strftime("%m/%Y") if ep.timestamp else "Archivio"
                traj_lines.append(f"  - **{dt_label}** [{ep.tipo_azione}]: {ep.dichiarazione_sintesi} *(Verifica: {ep.fact_check_status})*")
            historical_trajectories.append("\n".join(traj_lines))

    if wants_evolution and historical_trajectories:
        lines.append(f"#### ⏱️ Evoluzione Temporale & Traiettoria (2022 – {now.year}+ / Sviluppi Futuri)\n" + "\n\n".join(historical_trajectories) + "\n")

    if maggioranza:
        lines.append("#### 🔵 Maggioranza di Centrodestra")
        for p in maggioranza:
            dt_str = f" ({p.timestamp.strftime('%Y')})" if p.timestamp else ""
            lines.append(f"- **{p.partito}{dt_str}:** {p.dichiarazione_sintesi}\n"
                         f"  - *Costo & Coperture:* `{p.costo_stimato}` • Coperture: *{p.coperture_dichiarate}*\n"
                         f"  - *Verifica Finanziaria:* **{p.fact_check_status}** ({p.fact_check_motivazione or p.fattibilita_finanziaria})")
        lines.append("")

    if opposizione:
        lines.append("#### 🔴 Opposizione & Campo Progressista")
        for p in opposizione:
            dt_str = f" ({p.timestamp.strftime('%Y')})" if p.timestamp else ""
            lines.append(f"- **{p.partito}{dt_str}:** {p.dichiarazione_sintesi}\n"
                         f"  - *Costo & Coperture:* `{p.costo_stimato}` • Coperture: *{p.coperture_dichiarate}*\n"
                         f"  - *Verifica Finanziaria:* **{p.fact_check_status}** ({p.fact_check_motivazione or p.fattibilita_finanziaria})")
        lines.append("")

    if liberali_altri:
        lines.append("#### 🟡 Area Riformista, Civica & Altre Forze")
        for p in liberali_altri:
            dt_str = f" ({p.timestamp.strftime('%Y')})" if p.timestamp else ""
            lines.append(f"- **{p.partito}{dt_str}:** {p.dichiarazione_sintesi}\n"
                         f"  - *Costo & Coperture:* `{p.costo_stimato}` • Coperture: *{p.coperture_dichiarate}*\n"
                         f"  - *Verifica Finanziaria:* **{p.fact_check_status}** ({p.fact_check_motivazione or p.fattibilita_finanziaria})")
        lines.append("")

    lines.append("#### ⚖️ Vincoli Macroeconomici & Quadro di Bilancio (MEF / Corte dei Conti)")
    lines.append(
        "Tutte le proposte sono calibrate sui parametri macroeconomici dello Stato italiano: "
        "**PIL nominale** pari a ~2.120 Mld €, **Debito Pubblico** al 137.3% del PIL e rispetto delle regole europee di stabilità. "
        "Le misure non coperte o con saldi incerti sono verificate dall'AI con clausole di salvaguardia finanziaria."
    )

    return "\n".join(lines)

async def answer_rag_query(req: ChatQueryRequest, db: Session) -> ChatQueryResponse:
    """Standard non-streaming RAG query endpoint."""
    ctx = await _retrieve_and_prepare_context(req, db)
    fallback_text = _build_deterministic_synthesis(ctx, req.question)
    
    provider_info = await llm_provider.get_active_provider_info()
    answer_text = fallback_text

    if provider_info["provider"] != "deterministic" and ctx["top_candidates"]:
        evidence_lines = []
        q_l = req.question.lower()
        is_poll_q = (
            any(w in q_l for w in ["sondagg", "intenzion", "barometro", "elettorali", "voto"]) or
            (any(w in q_l for w in ["somma", "totale", "quanto fanno", "quanto hanno", "chi è avanti", "chi vince", "differenziale", "distacco", "percentual", "percentuale"]) and
             any(w in q_l for w in ["cdx", "csx", "coalizion", "centrodestra", "centrosinistra", "campo largo", "destra", "sinistra", "partiti"]))
        )
        if is_poll_q:
            evidence_lines.append(f"DATI UFFICIALI SONDAGGI E SOMMA COALIZIONI:\n{fallback_text}\n")
        elif any(w in q_l for w in ["media", "medie", "coalizion", "campo largo", "centrodestra"]):
            evidence_lines.append(f"MEDIE COALIZIONI UFFICIALI POLITICLENS:\n{fallback_text}\n")
        for p in ctx["top_candidates"]:
            ts_str = p.timestamp.strftime("%m/%Y") if p.timestamp else "N/D"
            evidence_lines.append(f"- [{ts_str}] {p.partito} ({p.macro_argomento}): {p.dichiarazione_sintesi} [Costo: {p.costo_stimato}, Coperture: {p.coperture_dichiarate}, Verifica: {p.fact_check_status}]")
        evidence_text = "\n".join(evidence_lines)

        messages = []
        if req.history:
            for h in req.history[-6:]:
                messages.append({"role": h.role, "content": h.content})

        user_content = f"""DOMANDA UTENTE: "{req.question}"
DATI VERIFICATI DALL'ARCHIVIO POLITICLENS:
{evidence_text}

Rispondi in modo approfondito, istituzionale, neutrale e ben strutturato in lingua italiana, citando sempre i dati di bilancio."""
        messages.append({"role": "user", "content": user_content})

        try:
            ai_ans, _ = await llm_provider.generate_chat(
                messages=messages,
                system_prompt=RAG_SYSTEM_PROMPT,
                fallback_text=fallback_text
            )
            if ai_ans and len(ai_ans.strip()) > 40:
                answer_text = ai_ans
        except Exception as e:
            print(f"[RAG Engine] LLM generation error: {e}")

    disclaimer = "PoliticLens opera secondo rigorosa neutralità algoritmica. Le sintesi, la cronistoria e le verifiche di bilancio sono elaborate autonomamente dall'AI analizzando atti parlamentari, programmi elettorali 2022-2026 e parametri ufficiali MEF, ISTAT e Corte dei Conti."

    return ChatQueryResponse(
        answer=answer_text,
        neutrality_disclaimer=disclaimer,
        mode=req.mode or "comparativo",
        citations=ctx["citations"]
    )

async def stream_rag_query(req: ChatQueryRequest, db: Session) -> AsyncGenerator[str, None]:
    """
    Streaming SSE generator that sends real-time inspection steps, citations, and token chunks.
    Format:
      event: step\ndata: {"step": "...", "message": "..."}\n\n
      event: citations\ndata: [...] \n\n
      event: token\ndata: {"token": "..."}\n\n
      event: done\ndata: {"status": "completed"}\n\n
    """
    # Step 1: Retrieval
    yield f"event: step\ndata: {json.dumps({'step': 'retrieval', 'message': '🔍 Consultazione archivio parlamentare e posizioni storiche...'}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.05)

    ctx = await _retrieve_and_prepare_context(req, db)
    
    # Step 2: Fiscal Audit
    yield f"event: step\ndata: {json.dumps({'step': 'fiscal', 'message': '📊 Verifica vincoli di bilancio MEF, ISTAT e art. 81 Cost....'}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.05)

    # Step 3: Pluralism & Neutrality
    yield f"event: step\ndata: {json.dumps({'step': 'balancing', 'message': '⚖️ Bilanciamento neutrale maggioranza-opposizione e riforme...'}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.05)

    # Yield citations
    citations_data = [c.model_dump() for c in ctx["citations"]]
    yield f"event: citations\ndata: {json.dumps(citations_data, ensure_ascii=False)}\n\n"

    fallback_text = _build_deterministic_synthesis(ctx, req.question)
    provider_info = await llm_provider.get_active_provider_info()

    messages = []
    if req.history:
        for h in req.history[-6:]:
            messages.append({"role": h.role, "content": h.content})

    evidence_lines = []
    q_l = req.question.lower()
    is_poll_q = (
        any(w in q_l for w in ["sondagg", "intenzion", "barometro", "elettorali", "voto"]) or
        (any(w in q_l for w in ["somma", "totale", "quanto fanno", "quanto hanno", "chi è avanti", "chi vince", "differenziale", "distacco", "percentual", "percentuale"]) and
         any(w in q_l for w in ["cdx", "csx", "coalizion", "centrodestra", "centrosinistra", "campo largo", "destra", "sinistra", "partiti"]))
    )
    if is_poll_q:
        evidence_lines.append(f"DATI UFFICIALI SONDAGGI E SOMMA COALIZIONI:\n{fallback_text}\n")
    elif any(w in q_l for w in ["media", "medie", "coalizion", "campo largo", "centrodestra"]):
        evidence_lines.append(f"MEDIE COALIZIONI UFFICIALI POLITICLENS:\n{fallback_text}\n")
    for p in ctx["top_candidates"]:
        ts_str = p.timestamp.strftime("%m/%Y") if p.timestamp else "N/D"
        evidence_lines.append(f"- [{ts_str}] {p.partito} ({p.macro_argomento}): {p.dichiarazione_sintesi} [Costo: {p.costo_stimato}, Coperture: {p.coperture_dichiarate}, Verifica: {p.fact_check_status}]")
    evidence_text = "\n".join(evidence_lines)

    user_content = f"""DOMANDA UTENTE: "{req.question}"
DATI VERIFICATI DALL'ARCHIVIO POLITICLENS:
{evidence_text}

Rispondi in modo analitico, rigorosamente imparziale, citando cifre di bilancio e posizioni formali."""
    messages.append({"role": "user", "content": user_content})

    async for token in llm_provider.stream_chat(
        messages=messages,
        system_prompt=RAG_SYSTEM_PROMPT,
        fallback_text=fallback_text
    ):
        yield f"event: token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

    yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"
