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

    # 1. Coperture Economiche: % ponderata di proposte con copertura finanziaria asseverata o ad invarianza
    truth_weights = {
        "Verificato": 100.0,
        "In attesa di copertura": 60.0,
        "Esagerato": 30.0,
        "Inattuabile": 0.0,
        "Fake / Infondato": 0.0,
        "Non verificabile": 20.0
    }

    cov_sum = 0.0
    for p in all_proposals:
        cop = (p.coperture_dichiarate or "").strip().lower()
        cost = (p.costo_stimato or "").strip().lower()
        st = p.fact_check_status or ""
        if any(w in cost for w in ["invarianza", "saldo neutro", "costi nulli", "zero costi", "costi operativi nulli"]):
            cov_sum += 1.0
        elif st == "Inattuabile":
            cov_sum += 0.0
        elif not cop or any(w in cop for w in ["non specificat", "in attesa", "da definire", "non disponibile", "nessuna copertura", "non indicat"]):
            cov_sum += 0.0
        elif st == "In attesa di copertura":
            cov_sum += 0.5
        else:
            cov_sum += 1.0

    quantified_percentage = round((cov_sum / total_proposals * 100), 1) if total_proposals > 0 else 0.0

    # 2. Indice di Veridicità e Accuratezza Fattuale (Fact-checking ponderato)
    truth_sum = sum(truth_weights.get(p.fact_check_status, 50.0) for p in all_proposals)
    avg_truthfulness = round(truth_sum / total_proposals, 1) if total_proposals > 0 else 0.0

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
            p_truth = round(sum(truth_weights.get(pr.fact_check_status, 50.0) for pr in p_props) / p_total, 1)
            p_cov_sum = 0.0
            for pr in p_props:
                cop = (pr.coperture_dichiarate or "").strip().lower()
                cost = (pr.costo_stimato or "").strip().lower()
                st = pr.fact_check_status or ""
                if any(w in cost for w in ["invarianza", "saldo neutro", "costi nulli", "zero costi", "costi operativi nulli"]):
                    p_cov_sum += 1.0
                elif st == "Inattuabile":
                    p_cov_sum += 0.0
                elif not cop or any(w in cop for w in ["non specificat", "in attesa", "da definire", "non disponibile", "nessuna copertura", "non indicat"]):
                    p_cov_sum += 0.0
                elif st == "In attesa di copertura":
                    p_cov_sum += 0.5
                else:
                    p_cov_sum += 1.0
            p_fin = round((p_cov_sum / p_total) * 100, 1)
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
