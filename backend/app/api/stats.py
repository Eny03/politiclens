from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import PoliticalProposal, PoliticalParty, InstitutionalBenchmark, IngestionLog
from app.schemas import StatsOverviewResponse, InstitutionalBenchmarkSchema
from app.ingestion.sources_config import MONITORED_FEEDS

router = APIRouter(prefix="/api/stats", tags=["Statistiche & Indicatori Istituzionali"])

@router.get("/benchmarks", response_model=List[InstitutionalBenchmarkSchema])
def get_benchmarks(db: Session = Depends(get_db)):
    """Returns official institutional economic benchmarks (ISTAT, Eurostat, Corte dei Conti)."""
    return db.query(InstitutionalBenchmark).order_by(InstitutionalBenchmark.categoria).all()

@router.get("/overview", response_model=StatsOverviewResponse)
def get_overview_stats(db: Session = Depends(get_db)):
    """
    Returns high-level analytical metrics:
    - Topic breakdown
    - Party distribution
    - Fact-check status breakdown
    - Cost quantification index (% of proposals with real monetary estimation)
    """
    total_proposals = db.query(func.count(PoliticalProposal.id)).scalar() or 0
    total_parties = db.query(func.count(PoliticalParty.id)).scalar() or 0
    total_sources = len(MONITORED_FEEDS)

    # Proposals by party
    party_counts_raw = db.query(PoliticalProposal.partito, func.count(PoliticalProposal.id)).group_by(PoliticalProposal.partito).all()
    proposals_by_party: Dict[str, int] = {item[0]: item[1] for item in party_counts_raw}

    # Proposals by topic
    topic_counts_raw = db.query(PoliticalProposal.macro_argomento, func.count(PoliticalProposal.id)).group_by(PoliticalProposal.macro_argomento).all()
    proposals_by_topic: Dict[str, int] = {item[0]: item[1] for item in topic_counts_raw}

    # Fact-check distribution
    fc_counts_raw = db.query(PoliticalProposal.fact_check_status, func.count(PoliticalProposal.id)).group_by(PoliticalProposal.fact_check_status).all()
    fact_check_distribution: Dict[str, int] = {item[0]: item[1] for item in fc_counts_raw}

    all_proposals = db.query(PoliticalProposal).all()

    # 1. Coperture Economiche: Media esatta della percentuale di copertura finanziaria (fondi stanziati / costo totale * 100)
    from app.ai.fiscal_calculator import calculate_financial_coverage_percentage
    from app.ai.fact_checker import calculate_proposal_truthfulness_score

    all_cov_scores = [
        calculate_financial_coverage_percentage(p.costo_stimato, p.coperture_dichiarate, p.dichiarazione_sintesi)
        for p in all_proposals
    ]
    quantified_percentage = round(sum(all_cov_scores) / total_proposals, 1) if total_proposals > 0 else 0.0

    # 2. Indice di Veridicità e Accuratezza Fattuale (Fact-checking puramente scientifico, statistico e fattuale)
    all_truth_scores = [
        calculate_proposal_truthfulness_score(p.fact_check_status)
        for p in all_proposals
    ]
    avg_truthfulness = round(sum(all_truth_scores) / total_proposals, 1) if total_proposals > 0 else 0.0

    # Coalition truthfulness breakdown
    parties = db.query(PoliticalParty).all()
    coalition_map: Dict[str, List[float]] = {}
    party_rankings = []

    for p in parties:
        p_props = db.query(PoliticalProposal).filter(
            (PoliticalProposal.party_id == p.id) | (PoliticalProposal.partito.ilike(f"%{p.name}%"))
        ).all()
        p_total = len(p_props)
        if p_total > 0:
            p_truth = round(sum(calculate_proposal_truthfulness_score(pr.fact_check_status) for pr in p_props) / p_total, 1)
            p_fin = round(sum(calculate_financial_coverage_percentage(pr.costo_stimato, pr.coperture_dichiarate, pr.dichiarazione_sintesi) for pr in p_props) / p_total, 1)
        else:
            p_truth = p.truthfulness_score or 75.0
            p_fin = p.financial_reliability_score or 70.0
        
        c_name = p.coalition
        if "Centrodestra" in c_name:
            c_key = "Centrodestra (Maggioranza)"
        elif "Centrosinistra" in c_name or "Progressista" in c_name:
            c_key = "Centrosinistra & Campo Largo"
        elif "Movimento 5 Stelle" in c_name:
            c_key = "Movimento 5 Stelle"
        elif "Liberaldemocratici" in c_name or "Centro" in c_name:
            c_key = "Centro & Liberaldemocratici"
        else:
            c_key = "Sinistra Radicale & Altre Forze"

        coalition_map.setdefault(c_key, []).append(p_truth)

        party_rankings.append({
            "name": p.name,
            "code": p.code,
            "color": p.color,
            "coalition": p.coalition,
            "leader": p.leader,
            "poll_percentage": p.poll_percentage or 0.0,
            "poll_trend": p.poll_trend or "stabile",
            "truthfulness_score": p_truth,
            "financial_reliability_score": p_fin,
            "proposals_count": p_total
        })

    # Sort party rankings by poll percentage descending
    party_rankings.sort(key=lambda x: x["poll_percentage"], reverse=True)

    coalition_truthfulness = {
        k: round(sum(v) / len(v), 1) for k, v in coalition_map.items() if v
    }

    # Last ingestion
    last_log = db.query(IngestionLog).order_by(IngestionLog.timestamp.desc()).first()
    last_ingestion_time = last_log.timestamp if last_log else None

    # Last poll sweep time from AuditLog
    from app.models import AuditLog
    last_poll_log = db.query(AuditLog).filter(
        AuditLog.event_type.in_(["POLL_UPDATE", "POLL_SWEEP_COMPLETED"])
    ).order_by(AuditLog.timestamp.desc()).first()
    last_poll_time_str = last_poll_log.timestamp.strftime("%d/%m/%Y ore %H:%M") if last_poll_log else None

    # Benchmarks
    benchmarks = db.query(InstitutionalBenchmark).all()
    benchmarks_summary = [InstitutionalBenchmarkSchema.model_validate(b) for b in benchmarks]

    return StatsOverviewResponse(
        total_proposals=total_proposals,
        total_parties=total_parties,
        total_sources_monitored=total_sources,
        proposals_by_party=proposals_by_party,
        proposals_by_topic=proposals_by_topic,
        fact_check_distribution=fact_check_distribution,
        quantified_cost_percentage=quantified_percentage,
        average_truthfulness=avg_truthfulness,
        average_financial_feasibility=quantified_percentage,
        coalition_truthfulness=coalition_truthfulness,
        party_rankings=party_rankings,
        last_ingestion_time=last_ingestion_time,
        last_poll_time=last_poll_time_str,
        benchmarks_summary=benchmarks_summary
    )
