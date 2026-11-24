import json
import datetime
import asyncio
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.config import settings
from app.models import PoliticalProposal, PoliticalParty, IngestionLog, AuditLog
from app.ingestion.rss_fetcher import fetch_all_active_feeds
from app.ingestion.text_extractor import compute_content_hash
from app.ai.extractor import extract_proposals_from_text, NON_POLICY_PATTERNS
from app.ai.embeddings import get_text_embedding
from app.ai.proposal_validator import sanitize_and_validate_proposal_statement
from app.ai.policy_merger import find_matching_existing_proposal, merge_or_update_policy_proposal
from app.ai.fact_checker import calculate_proposal_truthfulness_score, analyze_feasibility_and_factcheck
from app.ai.fiscal_calculator import calculate_fiscal_impact_and_coverage

# FIX ARCH-03 + BUG-05: use AsyncIOScheduler instead of BackgroundScheduler to avoid
# asyncio.run() conflicts with the FastAPI event loop.
scheduler = AsyncIOScheduler()

async def run_pipeline_scan():
    """
    Executes a complete scanning pass over monitored RSS feeds:
    1. Fetches new articles.
    2. Filters and deduplicates against database.
    3. Runs AI extraction & fact-checking.
    4. Computes embeddings.
    5. Saves proposals and creates an IngestionLog entry.
    """
    db: Session = SessionLocal()
    total_articles = 0
    total_proposals = 0
    
    try:
        # Offload synchronous network I/O to a worker thread so the FastAPI async loop is never blocked
        articles = await asyncio.to_thread(fetch_all_active_feeds, max_items_per_feed=settings.MAX_ARTICLES_PER_FEED)
        total_articles = len(articles)
        
        for art in articles:
            raw_text = art["raw_text"]
            content_hash = compute_content_hash(raw_text)
            
            # Check deduplication
            existing = db.query(PoliticalProposal).filter(PoliticalProposal.content_hash == content_hash).first()
            if existing:
                continue
                
            extracted_items = await extract_proposals_from_text(
                text=raw_text,
                url=art["url"],
                title=art["title"],
                published_at=art["published_at"]
            )
            
            for item in extracted_items:
                # Pre-ingestion Quality Gate 1: Must match a recognized mapped political party
                party_obj = db.query(PoliticalParty).filter(
                    (PoliticalParty.name.ilike(f"%{item.partito}%")) |
                    (PoliticalParty.code.ilike(f"%{item.partito}%"))
                ).first()
                if not party_obj:
                    print(f"[Ingestion Gatekeeper] Scartata proposta: partito sconosciuto o non censito ('{item.partito}')")
                    continue
                party_id = party_obj.id

                # Pre-ingestion Quality Gate 2: Strict Policy Validation (rejects slogans, media headlines, rally events, web domains)
                # FIX BUG-04: imports moved to top-level, no longer repeated inside loop
                val_stmt = sanitize_and_validate_proposal_statement(item.dichiarazione_sintesi)
                if not val_stmt:
                    print(f"[Ingestion Gatekeeper] Scartata proposta non conforme alle linee guida di policy: '{item.dichiarazione_sintesi[:60]}...'")
                    continue
                item.dichiarazione_sintesi = val_stmt

                # Pre-ingestion Quality Gate 3: Check against gossip & non-policy keywords
                is_gossip = any(re.search(pat, item.dichiarazione_sintesi, re.IGNORECASE) for pat in NON_POLICY_PATTERNS)
                if is_gossip:
                    print(f"[Ingestion Gatekeeper] Scartata proposta per match con pattern di cronaca/gossip: '{item.dichiarazione_sintesi[:50]}...'")
                    continue

                # Compute embedding
                text_to_embed = f"{item.partito} {item.macro_argomento} {item.dichiarazione_sintesi}"
                emb_list = await get_text_embedding(text_to_embed)
                emb_json = json.dumps(emb_list) if emb_list else None
                item_hash = compute_content_hash(f"{item.partito}_{item.macro_argomento}_{item.dichiarazione_sintesi}")

                # AI Semantic Deduplication & Policy Evolution
                matching_existing = find_matching_existing_proposal(
                    db=db,
                    party_id=party_id,
                    partito=item.partito,
                    macro_argomento=item.macro_argomento,
                    dichiarazione_sintesi=item.dichiarazione_sintesi,
                    emb_list=emb_list,
                    new_timestamp=art.get("published_at")
                )

                if matching_existing:
                    # Update existing proposal with the newest position / amended details
                    print(f"[AI Ingestion] Aggiornamento posizione per {item.partito} ({item.macro_argomento}): '{item.dichiarazione_sintesi[:60]}...'")
                    old_sintesi = matching_existing.dichiarazione_sintesi
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
                    # Audit log: modifica a programma o idea
                    audit_entry = AuditLog(
                        event_type="modifica",
                        entity_type="programma",
                        entity_id=str(matching_existing.id),
                        entity_name=f"{item.partito}: {item.macro_argomento}",
                        old_value=old_sintesi[:90] + "..." if len(old_sintesi) > 90 else old_sintesi,
                        new_value=item.dichiarazione_sintesi[:90] + "..." if len(item.dichiarazione_sintesi) > 90 else item.dichiarazione_sintesi,
                        agent_responsible="PolicyMergerAgent",
                        details=f"Modifica proposta su {item.macro_argomento}: '{item.dichiarazione_sintesi}'. Costo: {item.impatto_economico.costo_stimato}. Coperture: {item.impatto_economico.coperture_dichiarate}.",
                        timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                    )
                    db.add(audit_entry)
                else:
                    if db.query(PoliticalProposal).filter(PoliticalProposal.content_hash == item_hash).first():
                        continue
                    dt = datetime.datetime.fromisoformat(item.timestamp) if item.timestamp else art["published_at"]
                    feas, fc_st, fc_mot, fc_src, init_truth_score = analyze_feasibility_and_factcheck(
                        partito=party_obj.name,
                        macro_argomento=item.macro_argomento,
                        sintesi=item.dichiarazione_sintesi,
                        costo_stimato=item.impatto_economico.costo_stimato,
                        coperture=item.impatto_economico.coperture_dichiarate,
                        raw_text=raw_text,
                        tipo_azione=item.tipo_azione
                    )
                    proposal_record = PoliticalProposal(
                        party_id=party_id,
                        partito=party_obj.name,
                        macro_argomento=item.macro_argomento,
                        dichiarazione_sintesi=item.dichiarazione_sintesi,
                        tipo_azione=item.tipo_azione,
                        costo_stimato=item.impatto_economico.costo_stimato,
                        coperture_dichiarate=item.impatto_economico.coperture_dichiarate,
                        fattibilita_finanziaria=item.impatto_economico.fattibilita_finanziaria or feas,
                        fact_check_status=fc_st,
                        fact_check_motivazione=fc_mot,
                        fact_check_fonte=fc_src,
                        truth_score=init_truth_score,
                        fonte_url=item.fonte_url or art["url"],
                        fonte_titolo=art["title"],
                        fonte_testata=art["source_name"],
                        raw_text=raw_text,
                        content_hash=item_hash,
                        embedding=emb_json,
                        timestamp=dt
                    )
                    db.add(proposal_record)
                    db.flush()
                    audit_entry = AuditLog(
                        event_type="aggiunta",
                        entity_type="programma",
                        entity_id=str(proposal_record.id),
                        entity_name=f"{party_obj.name}: {item.macro_argomento}",
                        old_value=None,
                        new_value=item.dichiarazione_sintesi[:90] + "..." if len(item.dichiarazione_sintesi) > 90 else item.dichiarazione_sintesi,
                        agent_responsible="PolicyDistillerAgent",
                        details=f"Aggiunta nuova proposta per {party_obj.name} su {item.macro_argomento}: '{item.dichiarazione_sintesi}'. Fonte: {art.get('source_name', 'Web')}.",
                        timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                    )
                    db.add(audit_entry)
                    total_proposals += 1
                
        # Step 2: Autonomous Targeted Gap Search (Active Learning for Missing Parties & Topics)
        now_dt = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        gap_info_msg = ""
        if now_dt.minute in (0, 20, 40) or total_proposals == 0:
            try:
                from app.ingestion.gap_detector import autonomous_targeted_gap_search
                print("[Scheduler] Rilevamento lacune informative in corso...")
                gap_res = await autonomous_targeted_gap_search(db, max_gaps=2)
                if gap_res:
                    gap_added = gap_res.get("proposals_added_or_updated", 0)
                    total_proposals += gap_added
                    gap_info_msg = f" • {gap_res.get('message', '')}"
                    print(f"[Scheduler] Gap search: {gap_res.get('message')}")
            except Exception as ge:
                print(f"[Scheduler] Targeted gap search notice: {ge}")

        # Step 2b: Multi-Agent AI Consensus Engine (OpenWebScout + PolicyDistiller + FiscalAuditor + ConsensusArbiter)
        # Paced to run every 60 minutes (at the top of the hour) for in-depth web consensus
        if now_dt.minute == 0:
            try:
                from app.ai.multi_agent_consensus import run_multi_agent_consensus_pipeline
                print("[Scheduler] Esecuzione Consensus Multi-AI continuo su tutto il web...")
                consensus_res = await run_multi_agent_consensus_pipeline(db)
                if consensus_res:
                    c_added = consensus_res.get("proposals_added", 0)
                    total_proposals += c_added
                    print(f"[Scheduler] Multi-AI Consensus: {consensus_res.get('message')}")
            except Exception as ce:
                print(f"[Scheduler] Multi-AI Consensus notice: {ce}")

        # Step 2c: Safe Data-Consistency Audit (only repairs proposals missing fiscal/fact-check data; NEVER mutates historical timestamps!)
        if total_proposals == 0:
            try:
                candidate = db.query(PoliticalProposal).filter(
                    (PoliticalProposal.truth_score.is_(None)) |
                    (PoliticalProposal.coperture_dichiarate.ilike("%non specificat%")) |
                    (PoliticalProposal.costo_stimato.ilike("%non quantificat%"))
                ).first()
                if candidate:
                    old_sintesi = candidate.dichiarazione_sintesi
                    audit_res = calculate_fiscal_impact_and_coverage(
                        partito=candidate.partito,
                        macro_argomento=candidate.macro_argomento,
                        sintesi=candidate.dichiarazione_sintesi,
                        costo_stimato=candidate.costo_stimato,
                        coperture_dichiarate=candidate.coperture_dichiarate
                    )
                    candidate.costo_stimato = audit_res["costo_stimato"]
                    candidate.coperture_dichiarate = audit_res["coperture_dichiarate"]
                    candidate.fattibilita_finanziaria = audit_res["fattibilita_finanziaria"]
                    _, fc_st, fc_mot, fc_src, t_score = analyze_feasibility_and_factcheck(
                        partito=candidate.partito,
                        macro_argomento=candidate.macro_argomento,
                        sintesi=candidate.dichiarazione_sintesi,
                        costo_stimato=candidate.costo_stimato,
                        coperture=candidate.coperture_dichiarate,
                        raw_text=candidate.raw_text or "",
                        tipo_azione=candidate.tipo_azione or ""
                    )
                    candidate.fact_check_status = fc_st
                    candidate.fact_check_motivazione = fc_mot
                    candidate.fact_check_fonte = fc_src
                    candidate.truth_score = t_score

                    audit_entry = AuditLog(
                        event_type="modifica",
                        entity_type="programma",
                        entity_id=str(candidate.id),
                        entity_name=f"{candidate.partito}: {candidate.macro_argomento}",
                        old_value=old_sintesi[:90] + "..." if len(old_sintesi) > 90 else old_sintesi,
                        new_value=candidate.dichiarazione_sintesi[:90] + "..." if len(candidate.dichiarazione_sintesi) > 90 else candidate.dichiarazione_sintesi,
                        agent_responsible="FiscalAuditorAgent",
                        details=f"Integrazione coperture e verifica fattuale su {candidate.macro_argomento}: '{candidate.dichiarazione_sintesi}'.",
                        timestamp=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                    )
                    db.add(audit_entry)
                    total_proposals += 1
                    gap_info_msg += f" • Integrata copertura finanziaria per {candidate.partito} ({candidate.macro_argomento})"
            except Exception as fe:
                print(f"[Scheduler] Fiscal audit cycle notice: {fe}")

        # Step 2d: Quality Gatekeeper Auto-Audit (scans and purges non-policy slogans, media brands and headline snippets)
        if total_proposals > 0:
            try:
                from app.ai.proposal_validator import purge_and_audit_invalid_proposals
                purge_res = purge_and_audit_invalid_proposals(db)
                if purge_res.get("deleted_count") or purge_res.get("cleaned_count"):
                    print(f"[Scheduler Gatekeeper] Audit completato: {purge_res.get('deleted_count')} eliminate, {purge_res.get('cleaned_count')} ripulite.")
            except Exception as qe:
                print(f"[Scheduler] Gatekeeper auto-audit notice: {qe}")

        # Step 3: Autonomously synthesize and update AI Dossiers for all political parties
        if total_proposals > 0:
            try:
                from app.ingestion.dossier_generator import update_all_party_dossiers
                update_all_party_dossiers(db)
            except Exception as de:
                print(f"[Scheduler] AI Dossier generation warning: {de}")

        # Record Ingestion Log (poll refresh runs in its own dedicated scheduled job without duplication)
        log_entry = IngestionLog(
            source_name="AI Universal Web Crawler & Monitor",
            source_url="Scansione Web Nazionale & Ricerca Mirata Lacune",
            articles_found=total_articles,
            proposals_extracted=total_proposals,
            status="SUCCESS",
            log_message=f"Scansione completata: {total_articles} articoli analizzati dal web, {total_proposals} posizioni formalizzate censite/aggiornate{gap_info_msg}."
        )
        db.add(log_entry)

        db.commit()
        print(f"[Scheduler] Pipeline completed: {total_articles} articles, {total_proposals} proposals processed{gap_info_msg}.")

    except Exception as e:
        db.rollback()
        print(f"[Scheduler] Ingestion error: {e}")
        try:
            err_log = IngestionLog(
                source_name="AI Universal Web Crawler & Monitor",
                source_url="Web & Feeds",
                articles_found=total_articles,
                proposals_extracted=total_proposals,
                status="FAILED",
                log_message=f"Errore durante l'ingestion: {str(e)}"
            )
            db.add(err_log)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()

def _poll_scheduler_job():
    """Dedicated background job to crawl and update political polling data every 10 minutes."""
    db: Session = SessionLocal()
    try:
        from app.ingestion.poll_tracker import run_poll_tracker_pipeline
        print("[Scheduler] Esecuzione scansione demoscopica automatica 10 min (Web Live)...")
        run_poll_tracker_pipeline(db)
    except Exception as e:
        print(f"[Scheduler] Errore aggiornamento automatico sondaggi: {e}")
    finally:
        db.close()

async def _async_poll_scheduler_job():
    """Asynchronous wrapper that offloads synchronous polling network I/O to a worker thread."""
    await asyncio.to_thread(_poll_scheduler_job)

def start_scheduler():
    """Starts the continuous 24/7 background scheduler (running every 10 minutes)."""
    if settings.ENABLE_AUTO_SCHEDULER and not scheduler.running:
        # AsyncIOScheduler schedules async coroutines natively without blocking the FastAPI event loop
        scheduler.add_job(
            run_pipeline_scan,
            "cron",
            minute="*/10",
            second="0",
            id="political_rss_monitor",
            replace_existing=True
        )
        scheduler.add_job(
            _async_poll_scheduler_job,
            "cron",
            minute="*/10",
            second="30",
            id="political_polls_monitor",
            replace_existing=True
        )
        scheduler.start()
        print(f"[Scheduler] Continuous 24/7 background scheduler active (monitoring feeds and live polls every 10 minutes).")

def stop_scheduler():
    """Stops the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)

def get_scheduler_status():
    """Returns current scheduler state, interval, server time, and exact next run time."""
    is_active = scheduler.running
    next_run = None
    if is_active:
        job = scheduler.get_job("political_rss_monitor")
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()
            
    server_now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"

    return {
        "is_active": is_active,
        "interval_minutes": 10,
        "interval_seconds": 600,
        "frequency": "Continuo 24/7 ogni 10 minuti (ai minuti :00, :10, :20, :30, :40, :50)",
        "server_time": server_now,
        "next_run_time": next_run
    }

