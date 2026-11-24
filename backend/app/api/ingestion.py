import json
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import IngestionLog, PoliticalProposal, PoliticalParty
from app.schemas import IngestionLogSchema, IngestionRequest, ProposalExtractionSchema, PoliticalProposalDetail
from app.ingestion.scheduler import run_pipeline_scan, get_scheduler_status
from app.ingestion.sources_config import MONITORED_FEEDS
from app.ingestion.text_extractor import fetch_article_text, compute_content_hash
from app.ai.extractor import extract_proposals_from_text
from app.ai.embeddings import get_text_embedding

router = APIRouter(prefix="/api/ingestion", tags=["Pipeline di Ingestion & Fonti"])

async def _background_run_pipeline_scan():
    """Background runner for feed scan with isolated DB session."""
    try:
        await run_pipeline_scan()
    except Exception as e:
        print(f"[Ingestion Background Task] Error running pipeline scan: {e}")

async def _background_run_multi_agent_consensus():
    """Background runner for multi-agent consensus with dedicated DB session."""
    from app.ai.multi_agent_consensus import run_multi_agent_consensus_pipeline
    db: Session = SessionLocal()
    try:
        await run_multi_agent_consensus_pipeline(db)
    except Exception as e:
        print(f"[Consensus Background Task] Error running multi-agent consensus: {e}")
    finally:
        db.close()

@router.get("/status")
def get_ingestion_scheduler_status():
    """Returns the live status of the continuous hourly ingestion scheduler."""
    return get_scheduler_status()

@router.get("/sources")
def get_monitored_sources():
    """Returns the list of monitored RSS feeds and news outlets."""
    return MONITORED_FEEDS

@router.get("/gaps")
def get_detected_information_gaps(
    limit: int = Query(100, ge=1, le=300),
    party: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Returns the political information voids currently detected by the AI.
    The autonomous ingestion crawler targets these specific parties and topics
    during each scheduled scanning pass to fill missing policy statements.
    """
    from app.ingestion.gap_detector import detect_information_gaps
    gaps = detect_information_gaps(db, max_gaps=limit)
    if party and party != "Tutti":
        gaps = [g for g in gaps if g["party_name"].lower() == party.lower() or party.lower() in g["party_name"].lower()]
    return gaps

@router.get("/logs", response_model=List[IngestionLogSchema])
def get_ingestion_logs(limit: int = 20, db: Session = Depends(get_db)):
    """Returns recent ingestion run logs for full auditability."""
    return db.query(IngestionLog).order_by(IngestionLog.timestamp.desc()).limit(limit).all()

@router.post("/trigger")
async def trigger_ingestion_scan(background_tasks: BackgroundTasks):
    """Triggers an immediate background scanning cycle of all monitored feeds."""
    background_tasks.add_task(_background_run_pipeline_scan)
    return {"status": "TRIGGERED", "message": "Scansione asincrona dei feed avviata in background."}

@router.post("/update-dossiers")
def trigger_dossiers_update(db: Session = Depends(get_db)):
    """Regenerates the enhanced AI dossiers and metrics for all political parties."""
    from app.ingestion.dossier_generator import update_all_party_dossiers
    update_all_party_dossiers(db)
    return {"status": "UPDATED", "message": "Dossier strategici e parametri finanziari dei 22 partiti aggiornati con successo."}

@router.post("/consensus/trigger")
async def trigger_multi_agent_consensus(background_tasks: BackgroundTasks):
    """Triggers an immediate multi-agent AI consensus cycle across the open web."""
    background_tasks.add_task(_background_run_multi_agent_consensus)
    return {"status": "CONSENSUS_TRIGGERED", "message": "Pipeline Multi-AI Consensus (Scout + Distiller + FiscalAuditor + Arbiter) avviata in background."}

@router.post("/manual", response_model=List[PoliticalProposalDetail])
async def ingest_manual(req: IngestionRequest, db: Session = Depends(get_db)):
    """
    Manually ingests an article URL or raw text (e.g. parliamentary transcript or party release).
    Extracts structured schema (Section 4.B) and stores it in the database.
    """
    text = req.raw_text
    url = req.url or "https://manual-entry.politiclens.local"
    title = req.title or "Inserimento Manuale / Comunicato Diretto"
    
    if req.url and not text:
        fetched = await fetch_article_text(req.url)
        if not fetched:
            raise HTTPException(status_code=400, detail="Impossibile estrarre il testo dall'URL specificato.")
        text = fetched
        
    if not text or len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Testo insufficiente per l'analisi.")

    content_hash = compute_content_hash(text)
    extracted_items = await extract_proposals_from_text(
        text=text,
        url=url,
        title=title,
        published_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )
    
    saved_proposals = []
    from app.ai.policy_merger import find_matching_existing_proposal, merge_or_update_policy_proposal
    from app.ai.fact_checker import analyze_feasibility_and_factcheck
    from app.models import AuditLog

    for item in extracted_items:
        party_obj = db.query(PoliticalParty).filter(
            (PoliticalParty.name.ilike(item.partito)) |
            (PoliticalParty.code.ilike(item.partito))
        ).first()
        if not party_obj:
            party_obj = db.query(PoliticalParty).filter(PoliticalParty.name.ilike(f"%{item.partito}%")).first()
        party_id = party_obj.id if party_obj else None
        canonical_party = party_obj.name if party_obj else item.partito
        item.partito = canonical_party

        text_to_embed = f"{canonical_party} {item.macro_argomento} {item.dichiarazione_sintesi}"
        emb_list = await get_text_embedding(text_to_embed)
        emb_json = json.dumps(emb_list) if emb_list else None
        # Per-item unique hash prevents IntegrityError when 2+ proposals come from the same article
        item_hash = compute_content_hash(f"{canonical_party}_{item.macro_argomento}_{item.dichiarazione_sintesi}")

        feas_fc, fc_st, fc_mot, fc_src, truth_sc = analyze_feasibility_and_factcheck(
            partito=canonical_party,
            macro_argomento=item.macro_argomento,
            sintesi=item.dichiarazione_sintesi,
            costo_stimato=item.impatto_economico.costo_stimato,
            coperture=item.impatto_economico.coperture_dichiarate,
            raw_text=text[:2000],
            tipo_azione=item.tipo_azione
        )
        item.fact_check.status = fc_st
        item.fact_check.motivazione_oggettiva = fc_mot
        item.fact_check.fonte_verifica = fc_src

        matching_existing = find_matching_existing_proposal(
            db=db,
            party_id=party_id,
            partito=canonical_party,
            macro_argomento=item.macro_argomento,
            dichiarazione_sintesi=item.dichiarazione_sintesi,
            emb_list=emb_list,
            new_timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        )

        if matching_existing:
            old_syn = matching_existing.dichiarazione_sintesi
            safe_hash = item_hash if not db.query(PoliticalProposal).filter(
                PoliticalProposal.content_hash == item_hash,
                PoliticalProposal.id != matching_existing.id
            ).first() else matching_existing.content_hash
            proposal_record = merge_or_update_policy_proposal(
                db=db,
                existing=matching_existing,
                item=item,
                url=url,
                title=title,
                source_name="Inserimento Diretto / Scraper",
                published_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
                raw_text=text[:2000],
                content_hash=safe_hash,
                emb_json=emb_json
            )
            proposal_record.truth_score = truth_sc
            db.add(AuditLog(
                event_type="modifica",
                entity_type="programma",
                entity_id=str(proposal_record.id),
                entity_name=f"{canonical_party}: {item.macro_argomento}",
                old_value=old_syn[:90] + "..." if len(old_syn) > 90 else old_syn,
                new_value=item.dichiarazione_sintesi[:90] + "..." if len(item.dichiarazione_sintesi) > 90 else item.dichiarazione_sintesi,
                agent_responsible="ManualIngestionAgent",
                details=f"Aggiornamento manuale posizione per {canonical_party} ({item.macro_argomento}).",
                timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            ))
            db.commit()
            db.refresh(proposal_record)
        else:
            existing_hash_rec = db.query(PoliticalProposal).filter(PoliticalProposal.content_hash == item_hash).first()
            if existing_hash_rec:
                proposal_record = existing_hash_rec
            else:
                proposal_record = PoliticalProposal(
                    party_id=party_id,
                    partito=canonical_party,
                    macro_argomento=item.macro_argomento,
                    dichiarazione_sintesi=item.dichiarazione_sintesi,
                    tipo_azione=item.tipo_azione,
                    costo_stimato=item.impatto_economico.costo_stimato,
                    coperture_dichiarate=item.impatto_economico.coperture_dichiarate,
                    fattibilita_finanziaria=item.impatto_economico.fattibilita_finanziaria or feas_fc,
                    fact_check_status=fc_st,
                    fact_check_motivazione=fc_mot,
                    fact_check_fonte=fc_src,
                    truth_score=truth_sc,
                    fonte_url=item.fonte_url or url,
                    fonte_titolo=title,
                    fonte_testata="Inserimento Diretto / Scraper",
                    raw_text=text[:2000],
                    content_hash=item_hash,
                    embedding=emb_json,
                    timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                )
                db.add(proposal_record)
                db.flush()
                db.add(AuditLog(
                    event_type="aggiunta",
                    entity_type="programma",
                    entity_id=str(proposal_record.id),
                    entity_name=f"{canonical_party}: {item.macro_argomento}",
                    old_value=None,
                    new_value=item.dichiarazione_sintesi[:90] + "..." if len(item.dichiarazione_sintesi) > 90 else item.dichiarazione_sintesi,
                    agent_responsible="ManualIngestionAgent",
                    details=f"Aggiunta manuale proposta per {canonical_party} ({item.macro_argomento}): '{item.dichiarazione_sintesi}'.",
                    timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                ))
                db.commit()
                db.refresh(proposal_record)
        
        detail = PoliticalProposalDetail.model_validate(proposal_record)
        detail.party_color = party_obj.color if party_obj else "#3b82f6"
        saved_proposals.append(detail)
        
    return saved_proposals
