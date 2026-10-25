import json
import re
import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models import PoliticalProposal
from app.schemas import ProposalExtractionSchema
from app.ai.embeddings import cosine_similarity
from app.ai.deduplication_engine import is_duplicate_proposal, POLICY_CLUSTERS

# Highly specific policy sub-measure clusters: only merges if the EXACT same reform is referenced
CORE_POLICY_TOPIC_GROUPS = [
    ["salario minimo", "retribuzione minima", "salario orario"],
    ["quota 41"],
    ["opzione donna"],
    ["pensioni minime", "minime a 1000", "innalzamento pensioni"],
    ["anticipo a 64", "uscita a 64"],
    ["conferimento del tfr", "tfr a previdenza"],
    ["cuneo fiscale", "decontribuzione dipendenti"],
    ["settimana corta", "32 ore", "orario di lavoro a 32"],
    ["sicurezza sul lavoro", "omicidio sul lavoro"],
    ["flat tax", "aliquota unica 15%"],
    ["irpef a tre aliquote", "scaglioni irpef", "taglio seconda aliquota"],
    ["concordato preventivo biennale"],
    ["reddito di cittadinanza", "reddito di dignità", "indennità universale"],
    ["fondo sanitario al 7.5%", "7,5% del pil sanità", "rifinanziamento ssn"],
    ["liste d'attesa", "abbattimento liste attesa", "cup unico"],
    ["assunzioni medici", "tetto assunzioni sanità", "personale sanitario"],
    ["premierato", "elezione diretta presidente del consiglio", "ddl casellati"],
    ["autonomia differenziata", "legge calderoli"],
    ["separazione delle carriere", "sdoppiamento csm", "carriere magistrati"],
    ["ponte sullo stretto", "stretto di messina"],
    ["piano mattei"],
    ["protocollo albania", "accordo albania", "centri albania"],
    ["nucleare", "reattori smr", "iv generazione nucleare"],
    ["comunità energetiche", "10 gw rinnovabili", "parchi eolici"],
    ["patrimoniale", "imposta sui grandi patrimoni", "next generation tax"],
    ["extraprofitti banche", "tassazione extraprofitti", "prelievo su banche"],
    ["fine vita", "suicidio assistito", "eutanasia legale"],
    ["cannabis legale", "legalizzazione cannabis"],
    ["ius scholae", "ius soli", "cittadinanza studenti"],
    ["stipendi docenti", "tempo pieno scuola", "asili nido gratuiti"],
    ["spese militari", "armi a kiev", "2% pil difesa"],
    ["concessioni balneari", "licenze taxi", "gare balneari"],
    ["scala mobile", "indicizzazione salari all'inflazione"],
    ["sovranità monetaria", "uscita euro", "uscita nato"],
    ["statuto speciale alto adige", "competenze bolzano", "autonomia bilinguismo"]
]

def find_matching_existing_proposal(
    db: Session,
    party_id: Optional[int],
    partito: str,
    macro_argomento: str,
    dichiarazione_sintesi: str,
    emb_list: Optional[List[float]] = None,
    new_timestamp: Optional[datetime.datetime] = None
) -> Optional[PoliticalProposal]:
    """
    Autonomous AI Policy Deduplicator & Chronological Evolution Tracker (2022 -> Presente & Futuro):
    - If a matching proposal is found within the same period (<= 180 days and same calendar year),
      returns it to update/refine details.
    - If the matching proposal belongs to an earlier historical phase (e.g. 2022 campaign vs 2024/2026/future),
      and the statement or costs have evolved, returns None so a NEW evolutionary proposal is inserted,
      preserving the historical trajectory across time.
    """
    query = db.query(PoliticalProposal).filter(
        (PoliticalProposal.macro_argomento == macro_argomento)
    )
    if party_id:
        query = query.filter((PoliticalProposal.party_id == party_id) | (PoliticalProposal.partito == partito))
    else:
        query = query.filter(PoliticalProposal.partito == partito)

    candidates = query.all()
    if not candidates:
        return None

    # Unified Anti-Duplicate and Policy Evolution Check
    for cand in candidates:
        cand_emb = None
        if cand.embedding:
            try:
                cand_emb = json.loads(cand.embedding)
            except Exception:
                pass
                
        is_dup, reason = is_duplicate_proposal(
            party_a=partito,
            topic_a=macro_argomento,
            text_a=dichiarazione_sintesi,
            party_b=cand.partito,
            topic_b=cand.macro_argomento,
            text_b=cand.dichiarazione_sintesi,
            emb_a=emb_list,
            emb_b=cand_emb
        )
        if is_dup:
            print(f"[PolicyMerger] Duplicate detected ({reason}): linking to existing id={cand.id}")
            return cand

    return None

def merge_or_update_policy_proposal(
    db: Session,
    existing: PoliticalProposal,
    item: ProposalExtractionSchema,
    url: str,
    title: Optional[str],
    source_name: Optional[str],
    published_at: Optional[datetime.datetime],
    raw_text: Optional[str],
    content_hash: Optional[str],
    emb_json: Optional[str]
) -> PoliticalProposal:
    """
    Autonomous AI Policy Merger & Evolver:
    Updates an existing proposal within its active timeframe with the latest details, costs, and fact-check data.
    """
    dt = datetime.datetime.fromisoformat(item.timestamp) if item.timestamp else (published_at or datetime.datetime.utcnow())

    # Update statement with latest formulation
    existing.dichiarazione_sintesi = item.dichiarazione_sintesi

    if item.tipo_azione:
        existing.tipo_azione = item.tipo_azione

    # Update economic quantification if newer data provides real numbers
    if item.impatto_economico.costo_stimato and item.impatto_economico.costo_stimato != "Non quantificato":
        existing.costo_stimato = item.impatto_economico.costo_stimato

    if item.impatto_economico.coperture_dichiarate and item.impatto_economico.coperture_dichiarate != "Non specificate":
        existing.coperture_dichiarate = item.impatto_economico.coperture_dichiarate

    if item.impatto_economico.fattibilita_finanziaria:
        existing.fattibilita_finanziaria = item.impatto_economico.fattibilita_finanziaria

    # Update fact-check verification
    from app.ai.fact_checker import calculate_proposal_truthfulness_score
    if item.fact_check.status:
        existing.fact_check_status = item.fact_check.status
        existing.truth_score = calculate_proposal_truthfulness_score(item.fact_check.status)

    if item.fact_check.motivazione_oggettiva:
        existing.fact_check_motivazione = item.fact_check.motivazione_oggettiva

    if item.fact_check.fonte_verifica:
        existing.fact_check_fonte = item.fact_check.fonte_verifica

    # Update tracking metadata and newer timestamp
    existing.fonte_url = item.fonte_url or url
    if title:
        existing.fonte_titolo = title
    if source_name:
        existing.fonte_testata = source_name
    if raw_text:
        existing.raw_text = raw_text
    if content_hash:
        existing.content_hash = content_hash
    if emb_json:
        existing.embedding = emb_json

    existing.timestamp = dt

    return existing
