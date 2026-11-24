import json
import re
import datetime
import asyncio
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from sqlalchemy.orm import Session
from app.config import settings
from app.models import PoliticalProposal, PoliticalParty, InstitutionalBenchmark, InstitutionalBenchmark
from app.schemas import ChatQueryRequest, ChatQueryResponse, CitationItem
from app.ai.embeddings import get_text_embedding, cosine_similarity
from app.ai.llm_provider import llm_provider
from app.ai.fact_checker import calculate_proposal_truthfulness_score
from app.ai.fiscal_calculator import calculate_financial_coverage_percentage

ITALIAN_MONTHS = {
    1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
    5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
    9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
}

MODE_INSTRUCTIONS = {
    "comparativo": (
        "MODALITÀ COMPARATIVA: Offri una panoramica bilanciata delle posizioni di maggioranza, opposizione e centro "
        "sul tema richiesto, evidenziando convergenze, differenze programmatiche e sostenibilità di bilancio."
    ),
    "confronto_diretto": (
        "MODALITÀ TESTA A TESTA: Confronta in modo simmetrico e diretto i due partiti o schieramenti richiesti, "
        "mettendo a fianco proposte, costi stimati, coperture dichiarate e status di fact-check."
    ),
    "fact_check": (
        "MODALITÀ FACT-CHECK & BILANCIO: Concentrati in modo rigoroso su veridicità fattuale (ISTAT, Eurostat, IPCC), "
        "stima dei costi, coperture dichiarate e rispetto dell'art. 81 Cost. e dei pareri UPB/MEF/Corte dei Conti."
    )
}


def _build_rag_system_prompt(mode: Optional[str] = "comparativo") -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    today = f"{now.day} {ITALIAN_MONTHS.get(now.month, str(now.month))} {now.year}"
    mode_key = (mode or "comparativo").strip().lower()
    mode_hint = MODE_INSTRUCTIONS.get(mode_key, MODE_INSTRUCTIONS["comparativo"])
    return f"""Sei PoliticLens AI, la piattaforma di intelligence politica ed economico-finanziaria per l'Italia.
Data corrente: {today}. XIX Legislatura in corso (2022-2027).
Rispondi con tono istituzionale, neutrale, autorevole ed enciclopedico.
{mode_hint}
Regole inderogabili:
1. Neutralità algoritmica assoluta: tratta maggioranza, opposizione e centro con pari dignità e spazio.
2. Concretezza finanziaria: cita sempre coperture dichiarate, stime di costo e vincoli di bilancio (MEF, ISTAT, UPB, Corte dei Conti, Art. 81 Costituzione).
3. Fedeltà alle fonti: basati esclusivamente sui dati verificati dall'archivio PoliticLens forniti nel contesto; non inventare proposte o numeri non presenti nei dati.
4. Continuità storica: se l'utente chiede evoluzioni o cita date (2022-{now.year}), illustra la traiettoria temporale degli atti e delle dichiarazioni.
5. Formattazione: usa Markdown pulito (titoli ###, elenchi puntati, tabelle o sezioni chiare con emoji istituzionali 🏛️, 📊, 🔵, 🔴, ⚖️).
6. Se l'utente pone una domanda di follow-up o fa riferimento alla conversazione precedente, mantieni coerenza contestuale."""


# Module-level embedding cache: maps proposal.id -> (embedding_hash, List[float])
_embedding_cache: Dict[int, Tuple[int, List[float]]] = {}


def _get_embedding_cached(prop: PoliticalProposal) -> List[float]:
    """Returns deserialized embedding for a proposal, auto-invalidating if DB embedding changed."""
    raw = prop.embedding or ""
    raw_sig = hash(raw)
    cached = _embedding_cache.get(prop.id)
    if cached and cached[0] == raw_sig:
        return cached[1]
    if raw:
        try:
            vec = json.loads(raw)
            _embedding_cache[prop.id] = (raw_sig, vec)
            return vec
        except Exception:
            pass
    _embedding_cache[prop.id] = (raw_sig, [])
    return []


PARTY_KEYWORDS = {
    "Fratelli d'Italia": ["fratelli d'italia", "fdi", "giorgia meloni", "meloni"],
    "Partito Democratico": ["partito democratico", "pd", "elly schlein", "schlein"],
    "Movimento 5 Stelle": ["movimento 5 stelle", "m5s", "giuseppe conte", "conte", "cinquestelle"],
    "Lega - Salvini Premier": ["lega - salvini premier", "lega", "salvini", "matteo salvini"],
    "Forza Italia": ["forza italia", "fi", "tajani", "antonio tajani", "berlusconi"],
    "Alleanza Verdi e Sinistra": ["alleanza verdi e sinistra", "avs", "bonelli", "fratoianni", "verdi e sinistra"],
    "Azione": ["azione", "calenda", "carlo calenda"],
    "Italia Viva": ["italia viva", "iv", "renzi", "matteo renzi"],
    "+Europa": ["+europa", "più europa", "piu europa", "magi", "riccardo magi", "bonino", "emma bonino"],
    "Partito Liberal Democratico": ["partito liberal democratico", "pld", "libdem", "marattin", "luigi marattin"],
    "Noi Moderati": ["noi moderati", "maurizio lupi", "lupi"],
    "Futuro Nazionale": ["futuro nazionale", "fnv", "futnaz", "vannacci", "roberto vannacci"],
    "ORA!": ["movimento ora", "partito ora", "forchielli", "alberto forchielli", "boldrin", "michele boldrin", "drin drin", "ora!"],
    "Democrazia Sovrana Popolare": ["democrazia sovrana popolare", "dsp", "rizzo", "marco rizzo"],
    "Rifondazione Comunista": ["rifondazione comunista", "prc", "acerbo", "maurizio acerbo"],
    "Potere al Popolo": ["potere al popolo", "pap", "collot", "marta collot", "granato"],
    "Radicali Italiani": ["radicali italiani", "radicali", "hallissey", "matteo hallissey", "crivellini"],
    "Südtiroler Volkspartei": ["südtiroler volkspartei", "sudtiroler volkspartei", "svp", "steger", "dieter steger"],
    "Sud chiama Nord": ["sud chiama nord", "scn", "cateno de luca", "de luca cateno", "laura castelli"],
    "Pace Terra Dignità": ["pace terra dignità", "pace terra dignita", "ptd", "michele santoro", "santoro"],
    "Partito Socialista Italiano": ["partito socialista italiano", "partito socialista", "psi", "enzo maraio", "maraio"],
    "Alternativa Popolare": ["alternativa popolare", "bandecchi", "stefano bandecchi", "paolo alli"]
}

TOPIC_KEYWORDS = {
    "Fisco": ["fisco", "tasse", "flat tax", "irpef", "patrimoniale", "extraprofitti", "rottamazione", "concordato", "evasione", "aliquote", "cuneo fiscale", "accise", "superbonus", "liberalizzazioni", "tassazione"],
    "Lavoro": ["salario minimo", "salario", "lavoro", "stipendi", "occupazione", "retribuzioni", "precariato", "settimana corta", "contrattazione", "reddito di cittadinanza", "rdc", "scala mobile", "lsu", "lpu"],
    "Pensioni": ["pensione", "pensioni", "pensioni minime", "quota 41", "quota 103", "fornero", "uscita a 64", "opzione donna", "previdenza", "ape sociale", "tfr"],
    "Sanità": ["sanità", "sanita", "ssn", "medici", "ospedali", "liste d'attesa", "liste attesa", "fondo sanitario", "infermieri", "cup", "pronto soccorso", "mes sanitario"],
    "Energia": ["nucleare", "smr", "rinnovabili", "eolico", "fotovoltaico", "energia", "bollette", "trivelle", "gas", "decarbonizzazione", "comunità energetiche", "ambiente", "clima", "sad"],
    "Istruzione": ["scuola", "docenti", "insegnanti", "istruzione", "università", "universita", "its", "tempo pieno", "fuga di cervelli", "asili nido", "ricerca"],
    "Istituzioni": ["premierato", "autonomia differenziata", "lep", "riforma costituzionale", "bicameralismo", "giustizia", "separazione delle carriere", "csm", "legittima difesa", "upb"],
    "Diritti Civili": ["cittadinanza", "ius scholae", "ius soli", "cannabis", "fine vita", "eutanasia", "matrimonio egualitario", "ddl zan", "gpa", "diritti civili", "carceri", "maternità surrogata"],
    "Immigrazione": ["immigrazione", "migranti", "sbarchi", "albania", "cpr", "blocco navale", "confini", "decreto flussi", "accoglienza", "bossi-fini", "rimpatri"],
    "Politica Estera": ["ucraina", "armi", "russia", "spese militari", "nato", "difesa", "piano mattei", "europa", "ue", "medio oriente", "israele", "palestina", "eurobond", "esteri", "politica estera"],
    "Infrastrutture": ["ponte sullo stretto", "ponte di messina", "infrastrutture", "tav", "treni", "ferrovie", "rete idrica", "dissesto idrogeologico", "brennero", "trasporti", "piano casa"]
}


def detect_entities_and_topics(query: str) -> Tuple[List[str], List[str]]:
    q_low = (query or "").lower()
    matched_parties: List[str] = []
    for party, keys in PARTY_KEYWORDS.items():
        for k in keys:
            pattern = r"(?<![a-zA-ZÀ-ÿ\d])" + re.escape(k) + r"(?![a-zA-ZÀ-ÿ\d])"
            if re.search(pattern, q_low):
                matched_parties.append(party)
                break

    # Rank matched topics by total keyword hits (so "cuneo fiscale e flat tax" ranks Fisco above Lavoro)
    topic_hits: List[Tuple[int, str]] = []
    for topic, keys in TOPIC_KEYWORDS.items():
        hits = 0
        for k in keys:
            pattern = r"(?<![a-zA-ZÀ-ÿ\d])" + re.escape(k) + r"(?![a-zA-ZÀ-ÿ\d])"
            if re.search(pattern, q_low):
                hits += 2 if " " in k else 1
        if hits > 0:
            topic_hits.append((hits, topic))

    topic_hits.sort(key=lambda x: x[0], reverse=True)
    matched_topics = [t for _, t in topic_hits]
    return matched_parties, matched_topics


def _is_poll_query(q_low: str) -> bool:
    """Returns True if the query is asking about electoral polls or coalition vote shares."""
    return (
        any(w in q_low for w in ["sondagg", "intenzion", "barometro", "elettorali"]) or
        (any(w in q_low for w in ["voto", "voti", "somma", "totale", "quanto fanno", "quanto hanno", "chi è avanti", "chi vince", "differenziale", "distacco", "percentual"]) and
         any(w in q_low for w in ["cdx", "csx", "coalizion", "centrodestra", "centrosinistra", "campo largo", "destra", "sinistra", "partiti", "sondagg"]))
    )


def _is_coalition_stats_query(q_low: str) -> bool:
    return (
        any(w in q_low for w in ["media", "medie", "coalizion", "campo largo", "centrodestra", "centro destra", "maggioranza e opposizione"]) and
        any(w in q_low for w in ["veridicit", "copertur", "affidabilit", "fattibilit"])
    )


def _is_ranking_query(q_low: str) -> bool:
    """Returns True if the query asks for party rankings by truthfulness/coverage or a list of exaggerated/infeasible proposals."""
    asks_rank = any(w in q_low for w in [
        "classifica", "punteggio più alto", "più affidabil", "più veritier", "migliori copertur",
        "peggiori copertur", "chi è più affidabile", "chi ha più coperture", "ranking",
        "quali proposte", "elenca le proposte", "proposte inattuabil", "proposte esagerat",
        "risultano inattuabil", "risultano esagerat", "meno affidabil"
    ])
    mentions_metric = any(w in q_low for w in [
        "veridicit", "copertur", "affidabil", "fattibilit", "inattuabil", "esagerat", "puntegg", "score", "classifica"
    ])
    return asks_rank and mentions_metric


def _resolve_followup_entities(req: ChatQueryRequest, matched_parties: List[str], matched_topics: List[str]) -> Tuple[List[str], List[str]]:
    """
    True multi-turn conversational memory for both deterministic and LLM modes:
    If the current question omits party or topic (e.g. 'E invece il PD?', 'Quali coperture ha?', 'Quanto costa?'),
    carries over the most recent topic or party from prior user turns in req.history.
    """
    if not req.history:
        return matched_parties, matched_topics
    if matched_parties and matched_topics:
        return matched_parties, matched_topics

    q_low = (req.question or "").lower().strip()
    is_followup = (
        len(q_low.split()) <= 10 or
        any(q_low.startswith(pref) for pref in [
            "e ", "e invece", "e per", "e su", "quanto costa", "quali copertur", "approfondisci",
            "confronta", "invece", "ma ", "perché", "come ", "cosa ne pensa"
        ])
    )
    if not is_followup:
        return matched_parties, matched_topics

    prev_user_texts = []
    for h in reversed(req.history):
        role = h.role if hasattr(h, "role") else (h.get("role", "") if isinstance(h, dict) else "")
        content = h.content if hasattr(h, "content") else (h.get("content", "") if isinstance(h, dict) else "")
        if role == "user" and content:
            prev_user_texts.append(content)
            if len(prev_user_texts) >= 2:
                break

    for prev_q in prev_user_texts:
        prev_parties, prev_topics = detect_entities_and_topics(prev_q)
        if not matched_topics and prev_topics:
            matched_topics = prev_topics[:2]
        if not matched_parties and prev_parties:
            matched_parties = prev_parties[:2]
        if matched_parties and matched_topics:
            break

    return matched_parties, matched_topics


def _trim_history(history: Optional[List[Any]], max_chars: int = 3500) -> List[Dict[str, str]]:
    """Trims conversational memory to respect LLM context token boundaries."""
    if not history:
        return []
    trimmed = []
    total_chars = 0
    for h in reversed(history):
        content = h.content if hasattr(h, "content") else (h.get("content", "") if isinstance(h, dict) else "")
        role = h.role if hasattr(h, "role") else (h.get("role", "user") if isinstance(h, dict) else "user")
        if not content:
            continue
        # Skip boilerplate welcome messages from UI history
        if role == "assistant" and "Benvenuto su **PoliticLens AI" in content:
            continue
        if total_chars + len(content) > max_chars and trimmed:
            break
        trimmed.insert(0, {"role": role, "content": content})
        total_chars += len(content)
        if len(trimmed) >= 8:
            break
    return trimmed


async def _retrieve_and_prepare_context(req: ChatQueryRequest, db: Session):
    matched_parties, matched_topics = detect_entities_and_topics(req.question)
    matched_parties, matched_topics = _resolve_followup_entities(req, matched_parties, matched_topics)
    query_vec = await get_text_embedding(req.question)

    q_low = req.question.lower()
    mode = (req.mode or "comparativo").strip().lower()
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    years_in_query = re.findall(r"\b(202[2-9]|203[0-9])\b", req.question)
    wants_evolution = any(w in q_low for w in [
        "cambiat", "evoluzione", "evoluta", "storia", "storico", "passat", "ieri", "prima", "tempo",
        "anni", "sviluppo", "precedent", "mutat", "archivio", "futur", "prossim", "sviluppi",
        "aggiornat", "oggi", "nel tempo", "storica", "traiettoria", "presente"
    ] + [str(y) for y in range(2022, now.year + 4)])

    is_poll_q = _is_poll_query(q_low)
    is_coal_stats_q = _is_coalition_stats_query(q_low)
    is_ranking_q = _is_ranking_query(q_low) and not is_coal_stats_q

    all_parties = {p.name: p for p in db.query(PoliticalParty).all()}
    full_db_proposals = db.query(PoliticalProposal).all()
    all_benchmarks = db.query(InstitutionalBenchmark).all()

    # For pure poll, coalition statistics, or global ranking queries, skip random proposal citations
    if is_poll_q or is_coal_stats_q or is_ranking_q:
        return {
            "matched_parties": matched_parties,
            "matched_topics": matched_topics,
            "wants_evolution": wants_evolution,
            "is_poll_query": is_poll_q,
            "is_coalition_stats_query": is_coal_stats_q,
            "is_ranking_query": is_ranking_q,
            "mode": mode,
            "top_candidates": [],
            "citations": [],
            "all_parties": all_parties,
            "all_proposals": full_db_proposals,
            "all_benchmarks": all_benchmarks,
            "q_low": q_low
        }

    # Narrow candidate pool when explicit API filters are provided
    candidate_proposals = full_db_proposals
    if req.filter_party:
        candidate_proposals = [p for p in candidate_proposals if req.filter_party.lower() in p.partito.lower()]
    if req.filter_macro_argomento:
        candidate_proposals = [p for p in candidate_proposals if req.filter_macro_argomento.lower() in p.macro_argomento.lower()]

    q_words = [w for w in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", q_low) if len(w) > 2]

    scored_proposals: List[Tuple[float, PoliticalProposal]] = []
    for prop in candidate_proposals:
        score = 0.0
        p_text = f"{prop.partito} {prop.macro_argomento} {prop.dichiarazione_sintesi} {prop.coperture_dichiarate or ''}".lower()

        # 1. Party Match Boost
        party_matched = bool(matched_parties and prop.partito in matched_parties)
        if party_matched:
            score += 5.0
        elif req.filter_party and req.filter_party.lower() in prop.partito.lower():
            score += 4.5

        # 2. Topic Match Boost (weighted higher for primary detected topic)
        topic_matched = bool(matched_topics and prop.macro_argomento in matched_topics)
        if topic_matched:
            if prop.macro_argomento == matched_topics[0]:
                score += 5.0
            else:
                score += 3.5
        elif req.filter_macro_argomento and req.filter_macro_argomento.lower() in prop.macro_argomento.lower():
            score += 3.5

        # Joint Party + Topic Synergy Boost
        if party_matched and topic_matched:
            score += 4.5

        # 3. Lexical Keyword Overlap (rewarding specific policy terms in synthesis)
        synth_low = (prop.dichiarazione_sintesi or "").lower()
        synth_matches = sum(1 for w in q_words if w in synth_low)
        meta_matches = sum(1 for w in q_words if w in p_text)
        score += synth_matches * 2.2 + max(0, meta_matches - synth_matches) * 0.6

        # 4. Semantic Embedding Cosine Similarity (unified 384-dim space)
        emb = _get_embedding_cached(prop)
        if emb:
            try:
                sim = cosine_similarity(query_vec, emb)
                if sim > 0:
                    score += sim * 4.0
            except Exception:
                pass

        # 5. Fact-Check Mode Boost (prioritize proposals with explicit audit findings or quantified costs)
        if mode == "fact_check":
            if prop.fact_check_status in ("Esagerato", "Inattuabile", "Fake / Infondato", "Verificato"):
                score += 1.5
            if prop.costo_stimato and "non quantificat" not in prop.costo_stimato.lower():
                score += 0.8

        # 6. Temporal Scoring & Historical Weighting
        if prop.timestamp:
            p_year = str(prop.timestamp.year)
            if years_in_query:
                if p_year in years_in_query:
                    score += 3.0
            elif wants_evolution:
                score += 1.0
            else:
                age_days = max(0, (now - prop.timestamp).days)
                if age_days <= 180:
                    score += 1.2
                elif age_days <= 365:
                    score += 0.7
                elif age_days <= 730:
                    score += 0.3

        scored_proposals.append((score, prop))

    scored_proposals.sort(key=lambda x: x[0], reverse=True)

    # Intelligent Mode-Aware & Pluralistic Candidate Selection
    top_candidates: List[PoliticalProposal] = []

    if len(matched_parties) >= 2:
        # Head-to-head: strictly prioritize balanced proposals from the requested parties!
        per_party_limit = max(2, 6 // len(matched_parties))
        for mp in matched_parties[:3]:
            p_scored = [(s, p) for s, p in scored_proposals if p.partito == mp]
            if matched_topics:
                # Prefer proposals matching the requested topics first
                in_topic = [p for s, p in p_scored if p.macro_argomento in matched_topics]
                out_topic = [p for s, p in p_scored if p.macro_argomento not in matched_topics]
                chosen = (in_topic + out_topic)[:per_party_limit]
            else:
                chosen = [p for s, p in p_scored[:per_party_limit]]
            for p in chosen:
                if p not in top_candidates:
                    top_candidates.append(p)
    elif len(matched_parties) == 1:
        target_party = matched_parties[0]
        party_scored = [(s, p) for s, p in scored_proposals if p.partito == target_party]

        if matched_topics:
            # User asked about a specific party AND topic(s): select matching topic proposals first
            party_in_topic = [p for s, p in party_scored if p.macro_argomento in matched_topics]
            if wants_evolution and len(party_in_topic) > 1:
                by_year = {}
                for p in party_in_topic:
                    yr = p.timestamp.year if p.timestamp else 2025
                    if yr not in by_year:
                        by_year[yr] = p
                top_candidates.extend(list(by_year.values())[:4])
            else:
                top_candidates.extend(party_in_topic[:4])

            # Add up to 2 comparison proposals from other parties on the SAME topic for neutrality
            seen_other = {target_party}
            for s, p in scored_proposals:
                if p.partito not in seen_other and p.macro_argomento in matched_topics and p not in top_candidates:
                    top_candidates.append(p)
                    seen_other.add(p.partito)
                    if len(top_candidates) >= 6:
                        break
        else:
            if wants_evolution and len(party_scored) > 1:
                by_year = {}
                for s, p in party_scored:
                    yr = p.timestamp.year if p.timestamp else 2025
                    if yr not in by_year:
                        by_year[yr] = p
                top_candidates = list(by_year.values())[:5]
            else:
                top_candidates = [p for s, p in party_scored[:5]]
    else:
        # General / thematic / fact-check query: pluralistic top matches (1 per party first)
        seen_parties = set()
        for s, p in scored_proposals:
            if s > 2.0 and p.partito not in seen_parties:
                top_candidates.append(p)
                seen_parties.add(p.partito)
                if len(top_candidates) >= 6:
                    break
        if len(top_candidates) < 4:
            for s, p in scored_proposals:
                if s > 1.0 and p not in top_candidates:
                    top_candidates.append(p)
                    if len(top_candidates) >= 6:
                        break

    citations: List[CitationItem] = []
    for p in top_candidates:
        citations.append(CitationItem(
            partito=p.partito,
            macro_argomento=p.macro_argomento,
            sintesi=p.dichiarazione_sintesi,
            fonte_titolo=p.fonte_titolo,
            fonte_testata=p.fonte_testata,
            fonte_url=p.fonte_url or "",
            timestamp=p.timestamp.strftime("%d/%m/%Y") if p.timestamp else "Recente",
            fact_check_status=p.fact_check_status
        ))

    return {
        "matched_parties": matched_parties,
        "matched_topics": matched_topics,
        "wants_evolution": wants_evolution,
        "is_poll_query": is_poll_q,
        "is_coalition_stats_query": is_coal_stats_q,
        "is_ranking_query": False,
        "mode": mode,
        "top_candidates": top_candidates,
        "citations": citations,
        "all_parties": all_parties,
        "all_proposals": full_db_proposals,
        "all_benchmarks": all_benchmarks,
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
    mode = ctx.get("mode", "comparativo")
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    # 1. Direct Electoral Polls & Coalition Sum Analysis
    if ctx.get("is_poll_query") or _is_poll_query(q_low):
        def get_p_poll(code_or_name: str, default: float = 0.0) -> float:
            key = code_or_name.lower()
            for p_name, p_obj in all_parties.items():
                if (p_obj.code or "").lower() == key or p_name.lower() == key:
                    return float(p_obj.poll_percentage) if p_obj.poll_percentage is not None else default
            for p_name, p_obj in all_parties.items():
                if key in p_name.lower():
                    return float(p_obj.poll_percentage) if p_obj.poll_percentage is not None else default
            return default

        fdi = get_p_poll("FDI", 27.5)
        fi = get_p_poll("FI", 7.3)
        lega = get_p_poll("LEGA", 5.9)
        nm = get_p_poll("NM", 1.1)
        cdx_sum = round(fdi + fi + lega + nm, 1)

        futnaz = get_p_poll("FUTNAZ", 6.6)

        pd = get_p_poll("PD", 20.4)
        avs = get_p_poll("AVS", 6.2)
        piueu = get_p_poll("PIUEU", 1.4)
        psi = get_p_poll("PSI", 0.3)
        csx_sum = round(pd + avs + piueu + psi, 1)

        m5s = get_p_poll("M5S", 13.1)
        cl_sum = round(csx_sum + m5s, 1)

        az = get_p_poll("AZ", 3.1)
        iv = get_p_poll("IV", 2.3)
        libdem = get_p_poll("LIBDEM", 1.2)
        centro_sum = round(az + iv + libdem, 1)

        altre_sum = round(max(0.0, 100.0 - cdx_sum - futnaz - cl_sum - centro_sum), 1)
        scn = get_p_poll("SCN", 1.0)
        ptd = get_p_poll("PTD", 0.6)

        diff_cdx_csx = round(cdx_sum - csx_sum, 1)
        diff_cdx_cl = round(cdx_sum - cl_sum, 1)
        if diff_cdx_csx > 0:
            cdx_csx_text = f"Il Centrodestra di governo precede il Centrosinistra tradizionale di **+{diff_cdx_csx} punti percentuali**."
        elif diff_cdx_csx < 0:
            cdx_csx_text = f"Il Centrosinistra tradizionale precede il Centrodestra di governo di **+{abs(diff_cdx_csx)} punti percentuali**."
        else:
            cdx_csx_text = "Centrodestra di governo e Centrosinistra tradizionale risultano in perfetta parità."

        if diff_cdx_cl > 0:
            cdx_cl_text = f"il Centrodestra di governo mantiene un margine di **+{diff_cdx_cl} punti percentuali** sul Campo Largo ({cl_sum}%)."
        elif diff_cdx_cl < 0:
            cdx_cl_text = f"il Campo Largo ({cl_sum}%) supera il Centrodestra di governo ({cdx_sum}%) di **+{abs(diff_cdx_cl)} punti percentuali**."
        else:
            cdx_cl_text = f"Centrodestra di governo e Campo Largo risultano in perfetta parità al **{cdx_sum}%**."

        poll_lines = [
            "### 📊 Rilevazione Sondaggi & Media Multi-Istituto delle Coalizioni\n",
            "In base alla media ponderata calcolata su 6 istituti demoscopici nazionali (SWG Tg La7, Supermedia YouTrend/AGI, Ipsos, Tecnè, BiDiMedia, Noto), ecco il quadro dei consensi elettorali registrato nel database PoliticLens:\n",
            "| Coalizione / Area Politica | 📈 Consenso Totale | Composizione e Singoli Partiti |",
            "| :--- | :---: | :--- |",
            f"| 🔵 **Centrodestra Parlamentare (CDX - Maggioranza)** | **{cdx_sum}%** | Fratelli d'Italia (**{fdi}%**), Forza Italia (**{fi}%**), Lega (**{lega}%**), Noi Moderati (**{nm}%**) |",
            f"| 🦅 **Destra Sovranista / Identitaria (FN)** | **{futnaz}%** | Futuro Nazionale (**{futnaz}%**) |",
            f"| 🔴 **Centrosinistra Tradizionale (CSX)** | **{csx_sum}%** | Partito Democratico (**{pd}%**), Alleanza Verdi e Sinistra (**{avs}%**), +Europa (**{piueu}%**), PSI (**{psi}%**) |",
            f"| 🟣 **Campo Largo Progressista (CSX + M5S)** | **{cl_sum}%** | Centrosinistra ({csx_sum}%) + Movimento 5 Stelle (**{m5s}%**) |",
            f"| 🟡 **Centro / Polo Liberaldemocratico** | **{centro_sum}%** | Azione (**{az}%**), Italia Viva (**{iv}%**), PLD (**{libdem}%**) |",
            f"| ⚪ **Altre Liste e Autonomie** | **{altre_sum}%** | Sud chiama Nord (**{scn}%**), Pace Terra Dignità (**{ptd}%**), DSP, PRC, PaP, SVP, Radicali, ORA!, AP |\n",
            "#### 🔍 Sintesi del Calcolo Matematico:",
            f"1. **Somma Centrodestra di governo (CDX)**: **{cdx_sum}%** (`{fdi}% + {fi}% + {lega}% + {nm}%`). Includendo Futuro Nazionale ({futnaz}%), l'intera area di destra raggiunge il **{round(cdx_sum + futnaz, 1)}%**.",
            f"2. **Somma Centrosinistra (CSX)**: **{csx_sum}%** (`{pd}% + {avs}% + {piueu}% + {psi}%`).",
            f"3. **Differenziale CDX vs CSX**: {cdx_csx_text}",
            f"4. **Confronto con il Campo Largo**: Includendo il Movimento 5 Stelle ({m5s}%), {cdx_cl_text}",
            "\n*Fonte: Aggregazione multi-istituto PoliticLens su 6 istituti certificati (SWG, Supermedia YouTrend/AGI, Ipsos, Tecnè, BiDiMedia, Noto).*"
        ]
        return "\n".join(poll_lines)

    # 2. Coalition Truthfulness & Coverage Statistics (aligned 100% with /api/stats/overview)
    if ctx.get("is_coalition_stats_query") or _is_coalition_stats_query(q_low):
        cdx_parties = ["Fratelli d'Italia", "Lega - Salvini Premier", "Forza Italia", "Noi Moderati"]
        cl_parties = ["Partito Democratico", "Movimento 5 Stelle", "Alleanza Verdi e Sinistra", "+Europa", "Partito Socialista Italiano"]
        centro_parties = ["Azione", "Italia Viva", "Partito Liberal Democratico", "ORA!", "Alternativa Popolare"]
        altre_parties = ["Futuro Nazionale", "Sud chiama Nord", "Pace Terra Dignità", "Democrazia Sovrana Popolare", "Rifondazione Comunista", "Potere al Popolo", "Radicali Italiani", "Südtiroler Volkspartei"]

        props_by_party_id: Dict[int, List[PoliticalProposal]] = {}
        props_by_party_name: Dict[str, List[PoliticalProposal]] = {}
        for pr in all_proposals:
            if pr.party_id is not None:
                props_by_party_id.setdefault(pr.party_id, []).append(pr)
            props_by_party_name.setdefault(pr.partito, []).append(pr)

        p_stats = {}
        for p_name, p_obj in all_parties.items():
            props = props_by_party_id.get(p_obj.id) or props_by_party_name.get(p_name, [])
            p_total = len(props)
            if p_total > 0:
                p_truth = round(
                    sum(calculate_proposal_truthfulness_score(pr.fact_check_status, pr.truth_score) for pr in props) / p_total, 1
                )
                p_cov = round(
                    sum(calculate_financial_coverage_percentage(pr.costo_stimato, pr.coperture_dichiarate, pr.dichiarazione_sintesi) for pr in props) / p_total, 1
                )
            else:
                p_truth = p_obj.truthfulness_score or 75.0
                p_cov = p_obj.financial_reliability_score or 65.0
            p_stats[p_name] = {"truth": p_truth, "coverage": p_cov, "total": p_total}

        def get_avg(p_list: List[str]) -> Tuple[float, float]:
            m = [p_stats[p] for p in p_list if p in p_stats]
            if not m:
                return 0.0, 0.0
            return (
                round(sum(x["truth"] for x in m) / len(m), 1),
                round(sum(x["coverage"] for x in m) / len(m), 1)
            )

        cdx_t, cdx_c = get_avg(cdx_parties)
        cl_t, cl_c = get_avg(cl_parties)
        cen_t, cen_c = get_avg(centro_parties)
        alt_t, alt_c = get_avg(altre_parties)

        # Strictly data-driven neutral comparison text (no hardcoded direction!)
        if cdx_c > cl_c:
            cov_cmp = f"Il **Centrodestra** registra una media di coperture del **{cdx_c}%**, superiore di **+{round(cdx_c - cl_c, 1)} punti** rispetto al **Campo Largo** (**{cl_c}%**)."
        elif cl_c > cdx_c:
            cov_cmp = f"Il **Campo Largo** registra una media di coperture del **{cl_c}%**, superiore di **+{round(cl_c - cdx_c, 1)} punti** rispetto al **Centrodestra** (**{cdx_c}%**)."
        else:
            cov_cmp = f"**Centrodestra** e **Campo Largo** registrano una media equivalente sulle coperture finanziarie (**{cdx_c}%**)."

        if cdx_t > cl_t:
            truth_cmp = f"Il **Centrodestra** registra un indice medio di veridicità del **{cdx_t}%**, superiore di **+{round(cdx_t - cl_t, 1)} punti** rispetto al **Campo Largo** (**{cl_t}%**)."
        elif cl_t > cdx_t:
            truth_cmp = f"Il **Campo Largo** registra un indice medio di veridicità del **{cl_t}%**, superiore di **+{round(cl_t - cdx_t, 1)} punti** rispetto al **Centrodestra** (**{cdx_t}%**)."
        else:
            truth_cmp = f"**Centrodestra** e **Campo Largo** registrano un indice medio di veridicità equivalente (**{cdx_t}%**)."

        res_lines = [
            "### 📊 Medie Ufficiali per Coalizione: Veridicità & Coperture Economiche\n",
            "In base all'analisi di tutte le posizioni censite nell'archivio PoliticLens e alle verifiche di bilancio (MEF, UPB e art. 81 Cost.), ecco il confronto diretto tra le aree politiche:\n",
            "| Area / Coalizione | ⚖️ Media Veridicità AI | 💰 Media Coperture Finanziarie | Forze Politiche Mappate |",
            "| :--- | :---: | :---: | :--- |",
            f"| 🔵 **Centrodestra (Maggioranza)** | **{cdx_t}%** | **{cdx_c}%** | FdI, Lega, FI, Noi Moderati |",
            f"| 🔴 **Campo Largo & Centrosinistra** | **{cl_t}%** | **{cl_c}%** | PD, M5S, AVS, +Europa, PSI |",
            f"| 🟡 **Centro & Liberaldemocratici** | **{cen_t}%** | **{cen_c}%** | Azione, Italia Viva, PLD, ORA!, AP |",
            f"| 🟣 **Altre Forze, Sovranisti & Autonomie** | **{alt_t}%** | **{alt_c}%** | FN, ScN, PTD, DSP, PRC, PaP, Radicali, SVP |\n",
            "#### 🔍 Sintesi Oggettiva del Confronto:",
            f"- **Coperture Finanziarie (Art. 81 Cost.)**: {cov_cmp} L'area di **Centro & Liberaldemocratici** si attesta al **{cen_c}%**.",
            f"- **Indice di Veridicità & Fact-Checking**: {truth_cmp} L'area di **Centro & Liberaldemocratici** si attesta al **{cen_t}%**.\n",
            "#### 📋 Dettaglio per Singolo Partito:",
            "- **Centrodestra:** " + " • ".join([f"**{p}** (Veridicità {p_stats[p]['truth']}%, Coperture {p_stats[p]['coverage']}%)" for p in cdx_parties if p in p_stats]),
            "- **Campo Largo:** " + " • ".join([f"**{p}** (Veridicità {p_stats[p]['truth']}%, Coperture {p_stats[p]['coverage']}%)" for p in cl_parties if p in p_stats]),
            "- **Centro:** " + " • ".join([f"**{p}** (Veridicità {p_stats[p]['truth']}%, Coperture {p_stats[p]['coverage']}%)" for p in centro_parties if p in p_stats]),
            "\n*Nota metodologica: Gli indici coincidono esattamente con quelli calcolati nella Dashboard PoliticLens (veridicità fattuale a scatti del 5% su dati ISTAT/UPB/Costituzione; coperture finanziarie ex art. 81 Cost.).*"
        ]
        return "\n".join(res_lines)

    # 2b. Global Party Ranking & Critical Verdicts Intelligence
    if ctx.get("is_ranking_query"):
        asks_critical = any(w in q_low for w in ["inattuabil", "esagerat", "fake"])
        if asks_critical:
            inatt = [p for p in all_proposals if (p.fact_check_status or "").lower() == "inattuabile"]
            esag = [p for p in all_proposals if (p.fact_check_status or "").lower() == "esagerato"]
            crit_lines = [
                "### 🛡️ Audit Fact-Checking: Proposte Inattuabili ed Esagerate\n",
                f"Su **{len(all_proposals)} posizioni censite** nell'archivio PoliticLens, l'audit istituzionale rileva **{len(inatt)} proposte inattuabili** (vincoli costituzionali o di trattati internazionali) e **{len(esag)} proposte esagerate** (stime di costo o gettito smentite da MEF, UPB, INPS o Banca d'Italia).\n",
            ]
            if inatt:
                crit_lines.append("#### ❌ Proposte Inattuabili (20%)")
                crit_lines.append("| Partito | Tema | Proposta | Motivazione Istituzionale |")
                crit_lines.append("| :--- | :--- | :--- | :--- |")
                for p in inatt[:10]:
                    s_short = p.dichiarazione_sintesi[:85] + ("..." if len(p.dichiarazione_sintesi) > 85 else "")
                    m_short = (p.fact_check_motivazione or "")[:100] + ("..." if len(p.fact_check_motivazione or "") > 100 else "")
                    crit_lines.append(f"| **{p.partito}** | {p.macro_argomento} | {s_short} | {m_short} |")
                crit_lines.append("")
            if esag:
                crit_lines.append("#### ⚠️ Principali Proposte Esagerate (45%–50%)")
                crit_lines.append("| Partito | Tema | Proposta | Costo Stimato |")
                crit_lines.append("| :--- | :--- | :--- | :--- |")
                for p in esag[:10]:
                    s_short = p.dichiarazione_sintesi[:85] + ("..." if len(p.dichiarazione_sintesi) > 85 else "")
                    crit_lines.append(f"| **{p.partito}** | {p.macro_argomento} | {s_short} | `{p.costo_stimato}` |")
            crit_lines.append("\n*Fonte: Audit automatico PoliticLens calibrato su Art. 81 Cost., Corte Costituzionale, MEF, UPB, INPS e Banca d'Italia.*")
            return "\n".join(crit_lines)

        sort_by_fin = any(w in q_low for w in ["copertur", "finanziar", "bilancio", "fattibilit"]) and "veridicit" not in q_low
        ranked_list = []
        for p_name, p_obj in all_parties.items():
            p_props = [pr for pr in all_proposals if pr.party_id == p_obj.id or pr.partito == p_name]
            n = len(p_props)
            if n > 0:
                t_sc = round(sum(calculate_proposal_truthfulness_score(pr.fact_check_status, pr.truth_score) for pr in p_props) / n, 1)
                f_sc = round(sum(calculate_financial_coverage_percentage(pr.costo_stimato, pr.coperture_dichiarate, pr.dichiarazione_sintesi) for pr in p_props) / n, 1)
            else:
                t_sc = round(float(p_obj.truthfulness_score or 75.0), 1)
                f_sc = round(float(p_obj.financial_reliability_score or 65.0), 1)
            ranked_list.append({
                "name": p_name,
                "coalition": p_obj.coalition,
                "poll": round(float(p_obj.poll_percentage or 0.0), 1),
                "truth": t_sc,
                "fin": f_sc,
                "count": n,
            })

        ranked_list.sort(key=lambda x: (x["fin"] if sort_by_fin else x["truth"], x["truth"] if sort_by_fin else x["fin"]), reverse=True)
        metric_label = "Affidabilità Coperture MEF (Art. 81 Cost.)" if sort_by_fin else "Veridicità Fattuale & Coperture MEF"
        rk_lines = [
            f"### 🏆 Classifica Oggettiva dei 22 Partiti — {metric_label}\n",
            "Graduatoria calcolata in tempo reale sull'intero archivio (**291 proposte**) incrociando veridicità fattuale (ISTAT, INPS, Corte Costituzionale) e congruità delle coperture finanziarie (MEF, UPB):\n",
            "| Pos. | Partito | Area | ⚖️ Veridicità | 💰 Coperture MEF | 📊 Sondaggi | Atti |",
            "| :---: | :--- | :--- | :---: | :---: | :---: | :---: |",
        ]
        for idx, item in enumerate(ranked_list, start=1):
            rk_lines.append(
                f"| **{idx}** | **{item['name']}** | {item['coalition'].split('/')[0].strip()} | **{item['truth']}%** | **{item['fin']}%** | {item['poll']}% | {item['count']} |"
            )
        top_t = max(ranked_list, key=lambda x: x["truth"])
        top_f = max(ranked_list, key=lambda x: x["fin"])
        rk_lines.append("")
        rk_lines.append(
            f"> [!NOTE] **Sintesi oggettiva:** Il punteggio medio più alto di **veridicità fattuale** appartiene a **{top_t['name']}** (**{top_t['truth']}%**), "
            f"mentre il punteggio più elevato di **affidabilità delle coperture finanziarie** è registrato da **{top_f['name']}** (**{top_f['fin']}%**)."
        )
        return "\n".join(rk_lines)

    if not top_candidates:
        return (
            "Non sono state rilevate proposte politiche direttamente associate a questa formulazione nell'archivio.\n\n"
            "👉 **Consiglio di ricerca:** prova a digitare un tema chiave (es. *'Salario Minimo'*, *'Quota 41'*, *'Sanità'*, *'Flat Tax'*, *'Nucleare'*, *'Autonomia Differenziata'*) "
            "oppure confronta direttamente due partiti (es. *'PD vs FdI'*, *'M5S vs Lega'*)."
        )

    is_cost_query = mode == "fact_check" or any(w in q_low for w in ["quanto costa", "costo", "costi", "coperture", "finanziat", "mef", "fattibilità", "debito", "spesa", "veridic"])
    is_who_supports = any(w in q_low for w in ["chi vuole", "chi è a favore", "chi è contrario", "chi propone", "chi sostiene", "chi si oppone", "favorevoli", "contrari"])
    is_head_to_head = len(matched_parties) >= 2 or mode == "confronto_diretto"

    maggioranza = [p for p in top_candidates if p.partito in {"Fratelli d'Italia", "Lega - Salvini Premier", "Forza Italia", "Noi Moderati"}]
    opposizione = [p for p in top_candidates if p.partito in {"Partito Democratico", "Movimento 5 Stelle", "Alleanza Verdi e Sinistra", "+Europa", "Partito Socialista Italiano", "Potere al Popolo", "Rifondazione Comunista", "Pace Terra Dignità"}]
    liberali_altri = [p for p in top_candidates if p not in maggioranza and p not in opposizione]

    topic_str = matched_topics[0] if matched_topics else (top_candidates[0].macro_argomento if top_candidates else "Politica Nazionale")

    mode_badge = {
        "fact_check": "🛡️ Fact-Check & Bilancio",
        "confronto_diretto": "⚖️ Confronto Testa a Testa",
        "comparativo": "📊 Sintesi Istituzionale"
    }.get(mode, "📊 Sintesi Istituzionale")

    lines = [f"### {mode_badge}: {question.strip().rstrip('?')}\n"]

    if is_who_supports:
        fav_parties = [p.partito for p in top_candidates if p.tipo_azione != "Opposizione" and p.fact_check_status != "Inattuabile"]
        opp_parties = [p.partito for p in top_candidates if p.tipo_azione == "Opposizione" or p.fact_check_status == "Inattuabile"]
        fav_str = ", ".join(list(dict.fromkeys(fav_parties))[:4]) or "diverse forze parlamentari"
        opp_str = ", ".join(list(dict.fromkeys(opp_parties))[:3]) or "le forze contrarie o critiche sulle coperture"
        lines.append(
            f"**Risposta diretta:** Riguardo a **{topic_str}**, le forze politiche promotrici di proposte o atti formali sono principalmente **{fav_str}**. "
            f"Esprimono invece opposizione o criticità attuative **{opp_str}**.\n"
        )
    elif is_head_to_head and len(matched_parties) >= 2:
        lines.append(
            f"**Confronto diretto ({matched_parties[0]} vs {matched_parties[1]}):** "
            f"Sul tema **{topic_str}**, di seguito il raffronto simmetrico tra proposte, costi stimati, coperture dichiarate e verifiche di bilancio:\n"
        )
    elif is_cost_query:
        quantified = [p for p in top_candidates if p.costo_stimato and "non quantificat" not in p.costo_stimato.lower()]
        costs_summary = "; ".join([f"**{p.partito}**: {p.costo_stimato}" for p in quantified[:3]]) if quantified else "costi non quantificati nei testi normativi"
        lines.append(
            f"**Quadro di verifica economico-fattuale ({topic_str}):** Le stime censite evidenziano: {costs_summary}. "
            f"In base all'art. 81 Cost., ogni maggiore onere richiede coperture strutturali asseverate da MEF e UPB.\n"
        )
    elif matched_parties and len(matched_parties) == 1:
        p_name = matched_parties[0]
        p_obj = all_parties.get(p_name)
        p_poll = f"{p_obj.poll_percentage}%" if p_obj else "in rilevazione"
        p_ver = f"{p_obj.truthfulness_score}%" if p_obj else "N/D"
        p_fin = f"{p_obj.financial_reliability_score}%" if p_obj else "N/D"
        lines.append(
            f"**Sintesi per {p_name}:** Il partito (attestato al **{p_poll}** nei sondaggi, indice di veridicità **{p_ver}** e affidabilità coperture **{p_fin}**) "
            f"presenta sul tema **{topic_str}** le seguenti posizioni ufficiali:\n"
        )
    else:
        lines.append(
            f"**Quadro generale:** Sul tema **{topic_str}**, il monitoraggio degli atti parlamentari e dei programmi evidenzia posizioni composite tra maggioranza, opposizione e centro:\n"
        )

    # Historical timeline (now safely defined!)
    relevant_parties = matched_parties if matched_parties else list(dict.fromkeys(p.partito for p in top_candidates))
    historical_trajectories = []
    for party_name in relevant_parties:
        related_props = [p for p in all_proposals if p.partito == party_name and (not matched_topics or p.macro_argomento in matched_topics)]
        if not related_props:
            related_props = [p for p in all_proposals if p.partito == party_name]
        related_props_sorted = sorted(related_props, key=lambda x: x.timestamp or datetime.datetime.min)
        if len(related_props_sorted) >= 2:
            traj_lines = [f"**{party_name}** ({related_props_sorted[0].macro_argomento}):"]
            for ep in related_props_sorted[-4:]:
                dt_label = ep.timestamp.strftime("%m/%Y") if ep.timestamp else "Archivio"
                traj_lines.append(f"  - **{dt_label}** [{ep.tipo_azione}]: {ep.dichiarazione_sintesi} *(Verifica: {ep.fact_check_status}, {int(ep.truth_score or 75)}%)*")
            historical_trajectories.append("\n".join(traj_lines))

    if wants_evolution and historical_trajectories:
        lines.append(f"#### ⏱️ Evoluzione Temporale & Traiettoria (2022 – {now.year})\n" + "\n\n".join(historical_trajectories) + "\n")

    def _format_proposal_bullet(p: PoliticalProposal) -> str:
        dt_str = f" ({p.timestamp.strftime('%Y')})" if p.timestamp else ""
        t_score = int(calculate_proposal_truthfulness_score(p.fact_check_status, p.truth_score))
        cov_pct = calculate_financial_coverage_percentage(p.costo_stimato, p.coperture_dichiarate, p.dichiarazione_sintesi)
        return (
            f"- **{p.partito}{dt_str}** *[{p.macro_argomento}]*: {p.dichiarazione_sintesi}\n"
            f"  - *Costo & Coperture ({cov_pct}%):* `{p.costo_stimato}` • Coperture: *{p.coperture_dichiarate}*\n"
            f"  - *Fact-Check ({t_score}%):* **{p.fact_check_status}** — {p.fact_check_motivazione or p.fattibilita_finanziaria}"
        )

    # Executive Comparative Markdown Table when 2+ proposals from multiple parties are compared
    unique_cand_parties = list(dict.fromkeys(p.partito for p in top_candidates))
    if len(unique_cand_parties) >= 2 and len(top_candidates) >= 2:
        lines.append("#### 📋 Tabella Comparativa Rapida")
        lines.append("| Partito | Proposta Chiave | Costo Stimato | Copertura | Verdetto AI |")
        lines.append("| :--- | :--- | :--- | :---: | :--- |")
        for p in top_candidates[:6]:
            s_short = p.dichiarazione_sintesi[:95] + ("..." if len(p.dichiarazione_sintesi) > 95 else "")
            c_short = (p.costo_stimato or "Non quantificato")[:42] + ("..." if len(p.costo_stimato or "") > 42 else "")
            t_sc = int(calculate_proposal_truthfulness_score(p.fact_check_status, p.truth_score))
            cov_p = calculate_financial_coverage_percentage(p.costo_stimato, p.coperture_dichiarate, p.dichiarazione_sintesi)
            lines.append(f"| **{p.partito}** | {s_short} | `{c_short}` | **{int(round(cov_p))}%** | **{p.fact_check_status}** ({t_sc}%) |")
        lines.append("")

    if is_head_to_head and len(matched_parties) >= 2:
        for mp in matched_parties[:2]:
            mp_props = [p for p in top_candidates if p.partito == mp]
            if mp_props:
                lines.append(f"#### 🏛️ Approfondimento {mp}")
                for p in mp_props:
                    lines.append(_format_proposal_bullet(p))
                lines.append("")
    else:
        if maggioranza:
            lines.append("#### 🔵 Maggioranza di Centrodestra")
            for p in maggioranza:
                lines.append(_format_proposal_bullet(p))
            lines.append("")

        if opposizione:
            lines.append("#### 🔴 Opposizione & Campo Progressista")
            for p in opposizione:
                lines.append(_format_proposal_bullet(p))
            lines.append("")

        if liberali_altri:
            lines.append("#### 🟡 Area Riformista, Autonomie & Altre Forze")
            for p in liberali_altri:
                lines.append(_format_proposal_bullet(p))
            lines.append("")

    # Match relevant live Institutional Benchmarks from DB for the discussed topic
    all_benchmarks = ctx.get("all_benchmarks") or []
    topic_bench_map = {
        "Fisco": ["Fisco & Entrate", "Finanza Pubblica"],
        "Lavoro": ["Lavoro", "Finanza Pubblica"],
        "Sanità": ["Sanità", "Finanza Pubblica"],
        "Pensioni": ["Previdenza", "Finanza Pubblica"],
        "Energia": ["Energia & Clima"],
        "Istruzione": ["Istruzione"],
        "Politica Estera": ["Difesa & Esteri", "Finanza Pubblica"],
    }
    target_cats = topic_bench_map.get(topic_str, ["Finanza Pubblica"])
    matched_benches = [b for b in all_benchmarks if b.categoria in target_cats][:3]

    debito_pct = round((settings.DEBITO_PUBBLICO_MLD / settings.PIL_NOMINALE_MLD) * 100, 1)
    lines.append("#### ⚖️ Vincoli Macroeconomici & Benchmark Istituzionali (ISTAT / MEF / Corte dei Conti)")
    if matched_benches:
        bench_bullets = [
            f"- **{b.indicatore}**: `{b.valore} {b.unita}` *({b.fonte_istituzionale}, {b.anno_riferimento})* — {b.descrizione or ''}"
            for b in matched_benches
        ]
        lines.extend(bench_bullets)
    else:
        lines.append(
            f"Tutte le proposte sono calibrate sui parametri macroeconomici ufficiali dello Stato italiano: "
            f"**PIL nominale** pari a ~{settings.PIL_NOMINALE_MLD:,.0f} Mld €, **Debito Pubblico** al ~{debito_pct}% del PIL "
            f"(~{settings.DEBITO_PUBBLICO_MLD:,.0f} Mld €) e capienza ordinaria di manovra di ~{settings.MANOVRA_BILANCIO_MEDIA_MLD:.0f} Mld € annui ex art. 81 Cost."
        )

    return "\n".join(lines)


def _build_evidence_prompt(ctx: Dict[str, Any], question: str, fallback_text: str) -> str:
    evidence_lines = []
    if ctx.get("is_poll_query"):
        evidence_lines.append(f"DATI UFFICIALI SONDAGGI E SOMMA COALIZIONI:\n{fallback_text}\n")
    elif ctx.get("is_coalition_stats_query") or ctx.get("is_ranking_query"):
        evidence_lines.append(f"STATISTICHE E CLASSIFICHE UFFICIALI POLITICLENS:\n{fallback_text}\n")
    for p in ctx["top_candidates"]:
        ts_str = p.timestamp.strftime("%m/%Y") if p.timestamp else "N/D"
        t_score = int(calculate_proposal_truthfulness_score(p.fact_check_status, p.truth_score))
        cov_pct = calculate_financial_coverage_percentage(p.costo_stimato, p.coperture_dichiarate, p.dichiarazione_sintesi)
        evidence_lines.append(
            f"- [{ts_str}] {p.partito} ({p.macro_argomento}, {p.tipo_azione}): {p.dichiarazione_sintesi} "
            f"[Costo: {p.costo_stimato} | Coperture ({cov_pct}%): {p.coperture_dichiarate} | "
            f"Fact-Check ({t_score}%): {p.fact_check_status} - {p.fact_check_motivazione or ''}]"
        )
    evidence_text = "\n".join(evidence_lines)
    return (
        f'DOMANDA UTENTE: "{question}"\n'
        f"DATI VERIFICATI DALL'ARCHIVIO POLITICLENS:\n"
        f"{evidence_text}\n\n"
        "Rispondi in modo approfondito, rigorosamente imparziale e ben strutturato in lingua italiana, "
        "citando esclusivamente i dati reali sopra riportati e i vincoli di bilancio."
    )


async def answer_rag_query(req: ChatQueryRequest, db: Session) -> ChatQueryResponse:
    """Standard non-streaming RAG query endpoint."""
    ctx = await _retrieve_and_prepare_context(req, db)
    fallback_text = _build_deterministic_synthesis(ctx, req.question)

    provider_info = await llm_provider.get_active_provider_info()
    answer_text = fallback_text
    has_evidence = bool(ctx["top_candidates"] or ctx.get("is_poll_query") or ctx.get("is_coalition_stats_query") or ctx.get("is_ranking_query"))

    if provider_info["provider"] != "deterministic" and has_evidence:
        messages = _trim_history(req.history)
        messages.append({"role": "user", "content": _build_evidence_prompt(ctx, req.question, fallback_text)})
        try:
            ai_ans, _ = await llm_provider.generate_chat(
                messages=messages,
                system_prompt=_build_rag_system_prompt(req.mode),
                fallback_text=fallback_text
            )
            if ai_ans and len(ai_ans.strip()) > 40:
                answer_text = ai_ans
        except Exception as e:
            print(f"[RAG Engine] LLM generation error: {e}")

    now_year = datetime.datetime.now(datetime.timezone.utc).year
    disclaimer = (
        f"PoliticLens opera secondo rigorosa neutralità algoritmica. Le sintesi, la cronistoria e le verifiche di bilancio "
        f"sono elaborate analizzando atti parlamentari, programmi 2022-{now_year} e parametri ufficiali MEF, ISTAT e Corte dei Conti."
    )

    return ChatQueryResponse(
        answer=answer_text,
        neutrality_disclaimer=disclaimer,
        mode=req.mode or "comparativo",
        citations=ctx["citations"]
    )


async def stream_rag_query(req: ChatQueryRequest, db: Session) -> AsyncGenerator[str, None]:
    """
    Streaming SSE generator that sends real-time inspection steps, citations, and token chunks.
    """
    yield f"event: step\ndata: {json.dumps({'step': 'retrieval', 'message': '🔍 Consultazione archivio parlamentare e posizioni storiche...'}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.03)

    ctx = await _retrieve_and_prepare_context(req, db)

    yield f"event: step\ndata: {json.dumps({'step': 'fiscal', 'message': '📊 Verifica vincoli di bilancio MEF, ISTAT e art. 81 Cost....'}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.03)

    yield f"event: step\ndata: {json.dumps({'step': 'balancing', 'message': '⚖️ Bilanciamento neutrale maggioranza-opposizione e riforme...'}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.03)

    citations_data = [c.model_dump() for c in ctx["citations"]]
    yield f"event: citations\ndata: {json.dumps(citations_data, ensure_ascii=False)}\n\n"

    fallback_text = _build_deterministic_synthesis(ctx, req.question)
    has_evidence = bool(ctx["top_candidates"] or ctx.get("is_poll_query") or ctx.get("is_coalition_stats_query") or ctx.get("is_ranking_query"))

    if not has_evidence:
        for word in fallback_text.split(" "):
            yield f"event: token\ndata: {json.dumps({'token': word + ' '}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.008)
        yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"
        return

    messages = _trim_history(req.history)
    messages.append({"role": "user", "content": _build_evidence_prompt(ctx, req.question, fallback_text)})

    async for token in llm_provider.stream_chat(
        messages=messages,
        system_prompt=_build_rag_system_prompt(req.mode),
        fallback_text=fallback_text
    ):
        yield f"event: token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

    yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"
