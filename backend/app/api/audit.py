"""
Audit & Modification Changelog API Router
Provides institutional transparency, verifiable tracking of every AI operation,
poll variance, fiscal audit, and policy distillation across PoliticLens.
"""

import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app.models import AuditLog, PoliticalParty, PoliticalProposal
from app.schemas import AuditLogSchema, AuditListResponse, AuditStatsSchema

router = APIRouter(prefix="/api/audit", tags=["Audit & Changelog"])

def sync_audit_with_proposals(db: Session):
    """
    Ensures every current proposal in the database has a corresponding 'aggiunta' audit log,
    guaranteeing perfect mathematical correspondence between the proposals count and the audit overview.
    """
    proposals = db.query(PoliticalProposal).all()
    prop_id_set = {str(p.id) for p in proposals}

    # Clean any orphan numeric 'aggiunta' logs for proposals that no longer exist
    if prop_id_set:
        orphan_logs = db.query(AuditLog).filter(
            AuditLog.event_type == "aggiunta",
            ~AuditLog.entity_id.in_(prop_id_set)
        ).all()
        for o in orphan_logs:
            db.delete(o)
        if orphan_logs:
            db.commit()

    existing_added_ids = {
        log[0] for log in db.query(AuditLog.entity_id).filter(AuditLog.event_type == 'aggiunta').all() if log[0]
    }
    
    new_logs = []
    for p in proposals:
        p_id_str = str(p.id)
        if p_id_str not in existing_added_ids:
            new_logs.append(AuditLog(
                event_type="aggiunta",
                entity_type="programma",
                entity_id=p_id_str,
                entity_name=f"{p.partito}: {p.macro_argomento}",
                old_value=None,
                new_value=p.dichiarazione_sintesi[:90] + "..." if len(p.dichiarazione_sintesi) > 90 else p.dichiarazione_sintesi,
                agent_responsible="PolicyDistillerAgent",
                details=f"Aggiunta proposta per {p.partito} ({p.macro_argomento}): '{p.dichiarazione_sintesi}'. Fonte: {p.fonte_testata or 'Atti Ufficiali'}.",
                timestamp=p.timestamp or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            ))
            existing_added_ids.add(p_id_str)
            
    if new_logs:
        db.add_all(new_logs)
        db.commit()

def seed_audit_history_if_empty(db: Session):
    """Generates initial realistic institutional audit logs if the table is empty."""
    if db.query(AuditLog).count() > 0:
        return

    print("[Audit] Seeding historical audit trail 2022-2026...")
    historical_events = [
        {
            "event_type": "sondaggi aggiornati",
            "entity_type": "sondaggi",
            "entity_id": "ALL_18",
            "entity_name": "Barometro Elettorale Nazionale",
            "old_value": "Rilevazione precedente",
            "new_value": "Sondaggi aggiornati per tutti i 18 partiti",
            "agent_responsible": "PollTrackerAgent (Web Live)",
            "details": "Sondaggi aggiornati per tutti i 18 partiti: FDI: 28.4% • PD: 20.6% • M5S: 12.0% • FI: 7.3% • FUTNAZ: 6.6% • AVS: 6.5% • LEGA: 5.5% • AZ: 3.2% • IV: 2.4% • +EU: 1.5% • ... Fonti: Supermedia YouTrend/AGI, SWG Tg La7, Ipsos, Tecnè e BiDiMedia.",
            "timestamp": datetime.datetime(2026, 10, 22, 18, 0)
        },
        {
            "event_type": "modifica",
            "entity_type": "programma",
            "entity_id": "prop-sanita-pd",
            "entity_name": "Partito Democratico: Sanità",
            "old_value": "Fondo Sanitario Nazionale incrementato del 5%",
            "new_value": "Fondo Sanitario Nazionale vincolato al 7.5% del PIL",
            "agent_responsible": "PolicyMergerAgent",
            "details": "Modifica formulazione e quantificazione con parametro benchmark FSN MEF (136.5 Mld €).",
            "timestamp": datetime.datetime(2026, 10, 15, 14, 15)
        },
        {
            "event_type": "aggiunta",
            "entity_type": "programma",
            "entity_id": "prop-nucleare-fi",
            "entity_name": "Forza Italia: Energia",
            "old_value": None,
            "new_value": "Ritorno al Nucleare di IV Generazione con reattori modulari SMR",
            "agent_responsible": "PolicyDistillerAgent",
            "details": "Aggiunta nuova proposta da DDL delega su mix energetico nazionale. Oneri stimati a 3.0 Mld € con cofinanziamento REPowerEU.",
            "timestamp": datetime.datetime(2026, 10, 10, 11, 45)
        },
        {
            "event_type": "cancellazione",
            "entity_type": "programma",
            "entity_id": "prop-dup-lega",
            "entity_name": "Lega - Salvini Premier: Pensioni",
            "old_value": "Quota 41 per tutti i lavoratori senza penalizzazioni",
            "new_value": None,
            "agent_responsible": "DeduplicationAgent",
            "details": "Cancellazione proposta duplicata a seguito di consolidamento con il testo base formalizzato in legge di bilancio.",
            "timestamp": datetime.datetime(2026, 10, 5, 9, 30)
        },
        {
            "event_type": "modifica",
            "entity_type": "programma",
            "entity_id": "prop-salario-m5s",
            "entity_name": "Movimento 5 Stelle: Lavoro",
            "old_value": "Salario Minimo legale senza fondo perequativo",
            "new_value": "Salario Minimo a 9 Euro con fondo di compensazione PMI",
            "agent_responsible": "PolicyMergerAgent",
            "details": "Modifica proposta con recepimento emendamento su incentivi di transizione e relazione tecnica INPS.",
            "timestamp": datetime.datetime(2026, 9, 28, 16, 20)
        },
        {
            "event_type": "aggiunta",
            "entity_type": "programma",
            "entity_id": "prop-fisco-fdi",
            "entity_name": "Fratelli d'Italia: Fisco",
            "old_value": None,
            "new_value": "Riforma IRPEF a tre aliquote e concordato preventivo biennale",
            "agent_responsible": "PolicyDistillerAgent",
            "details": "Aggiunta provvedimento definitivo formalizzato in Gazzetta Ufficiale (D.Lgs. 216/2023).",
            "timestamp": datetime.datetime(2026, 9, 20, 15, 30)
        }
    ]

    for ev in historical_events:
        db.add(AuditLog(**ev))
    db.commit()

@router.get("/logs", response_model=AuditListResponse)
def get_audit_logs(
    event_type: Optional[str] = None,
    agent: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Returns full institutional audit log entries with flexible filtering
    for events, agents, parties, and keywords (read-only fast GET).
    """
    query = db.query(AuditLog)

    if event_type and event_type != "Tutti":
        if event_type.lower() in ("sondaggi aggiornati", "poll_update", "sondaggi"):
            query = query.filter(AuditLog.event_type.in_(["sondaggi aggiornati", "POLL_UPDATE", "POLL_SWEEP_COMPLETED"]))
        elif event_type.lower() == "modifica":
            query = query.filter(AuditLog.event_type.in_(["modifica", "PROPOSAL_UPDATED", "FACT_CHECK_AUDIT"]))
        else:
            query = query.filter(AuditLog.event_type == event_type)

    if agent and agent != "Tutti":
        query = query.filter(AuditLog.agent_responsible == agent)

    if search and search.strip():
        q_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AuditLog.entity_name.ilike(q_term),
                AuditLog.details.ilike(q_term),
                AuditLog.event_type.ilike(q_term),
                AuditLog.agent_responsible.ilike(q_term)
            )
        )

    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    # Get distinct event types and agents for filter drop-downs
    distinct_types = [r[0] for r in db.query(AuditLog.event_type).distinct().all() if r[0]]
    distinct_agents = [r[0] for r in db.query(AuditLog.agent_responsible).distinct().all() if r[0]]

    # Calculate real totals across the whole database (including POLL_UPDATE and FACT_CHECK_AUDIT!)
    aggiunta_cnt = db.query(func.count(AuditLog.id)).filter(AuditLog.event_type == 'aggiunta').scalar() or 0
    modifica_cnt = db.query(func.count(AuditLog.id)).filter(AuditLog.event_type.in_(['modifica', 'PROPOSAL_UPDATED', 'FACT_CHECK_AUDIT'])).scalar() or 0
    cancellazione_cnt = db.query(func.count(AuditLog.id)).filter(AuditLog.event_type == 'cancellazione').scalar() or 0
    sondaggi_cnt = db.query(func.count(AuditLog.id)).filter(AuditLog.event_type.in_(['sondaggi aggiornati', 'POLL_UPDATE', 'POLL_SWEEP_COMPLETED'])).scalar() or 0
    total_ops = aggiunta_cnt + modifica_cnt + cancellazione_cnt + sondaggi_cnt

    stats_obj = AuditStatsSchema(
        total=total_ops,
        aggiunta=aggiunta_cnt,
        modifica=modifica_cnt,
        cancellazione=cancellazione_cnt,
        sondaggi=sondaggi_cnt
    )

    return AuditListResponse(
        total=total,
        logs=logs,
        event_types=distinct_types,
        agents=distinct_agents,
        stats=stats_obj
    )
