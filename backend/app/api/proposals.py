from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import PoliticalProposal, PoliticalParty
from app.schemas import PoliticalProposalDetail

router = APIRouter(prefix="/api/proposals", tags=["Proposte e Posizioni Politiche"])

@router.get("", response_model=List[PoliticalProposalDetail])
def get_proposals(
    party: Optional[str] = Query(None, description="Filtra per nome partito o codice"),
    topic: Optional[str] = Query(None, description="Filtra per macro-argomento"),
    status: Optional[str] = Query(None, description="Filtra per fact_check_status"),
    action_type: Optional[str] = Query(None, description="Filtra per tipo_azione"),
    year: Optional[int] = Query(None, description="Filtra per anno di pubblicazione (dal 2022 in poi)"),
    search: Optional[str] = Query(None, description="Ricerca testuale nella sintesi o coperture"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Returns filtered political proposals with pagination and metadata.
    """
    query = db.query(PoliticalProposal)

    if party:
        query = query.filter(PoliticalProposal.partito.ilike(f"%{party}%"))
    if topic:
        query = query.filter(PoliticalProposal.macro_argomento.ilike(f"%{topic}%"))
    if status:
        query = query.filter(PoliticalProposal.fact_check_status.ilike(f"%{status}%"))
    if action_type:
        query = query.filter(PoliticalProposal.tipo_azione.ilike(f"%{action_type}%"))
    if year:
        from sqlalchemy import extract
        query = query.filter(extract('year', PoliticalProposal.timestamp) == year)
    if search:
        query = query.filter(
            or_(
                PoliticalProposal.dichiarazione_sintesi.ilike(f"%{search}%"),
                PoliticalProposal.coperture_dichiarate.ilike(f"%{search}%"),
                PoliticalProposal.fattibilita_finanziaria.ilike(f"%{search}%")
            )
        )

    proposals = query.order_by(PoliticalProposal.timestamp.desc()).offset(offset).limit(limit).all()

    # Pre-fetch parties for color mapping
    parties_map = {p.name.lower(): p.color for p in db.query(PoliticalParty).all()}

    output = []
    for p in proposals:
        detail = PoliticalProposalDetail.model_validate(p)
        detail.party_color = parties_map.get(p.partito.lower(), "#3b82f6")
        output.append(detail)
        
    return output

@router.post("/audit-cleanup")
def run_quality_cleanup(db: Session = Depends(get_db)):
    """Triggers the QualityGatekeeperAgent to audit and purge invalid proposals, event titles or URL noise."""
    from app.ai.proposal_validator import purge_and_audit_invalid_proposals
    res = purge_and_audit_invalid_proposals(db)
    return {
        "status": "SUCCESS",
        "message": f"Bonifica completata: {res['deleted_count']} rimosse, {res['cleaned_count']} riformulate.",
        "details": res
    }

@router.get("/{proposal_id}", response_model=PoliticalProposalDetail)
def get_proposal_by_id(proposal_id: int, db: Session = Depends(get_db)):
    """Returns a single proposal by ID."""
    p = db.query(PoliticalProposal).filter(PoliticalProposal.id == proposal_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proposta non trovata")
    
    party = db.query(PoliticalParty).filter(PoliticalParty.id == p.party_id).first() if p.party_id else None
    detail = PoliticalProposalDetail.model_validate(p)
    detail.party_color = party.color if party else "#3b82f6"
    return detail

@router.delete("/{proposal_id}")
def delete_proposal_by_id(proposal_id: int, db: Session = Depends(get_db)):
    """Deletes an invalid proposal by ID and registers an audit log entry."""
    from app.models import AuditLog
    import datetime
    p = db.query(PoliticalProposal).filter(PoliticalProposal.id == proposal_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proposta non trovata")
    
    stmt = p.dichiarazione_sintesi
    db.add(AuditLog(
        event_type="cancellazione",
        entity_type="programma",
        entity_id=str(p.id),
        entity_name=f"{p.partito}: {p.macro_argomento}",
        old_value=stmt[:90] + "..." if len(stmt) > 90 else stmt,
        new_value=None,
        agent_responsible="QualityGatekeeperAgent",
        details=f"Cancellata proposta non conforme alle linee guida di policy (ID {p.id}): '{stmt}'.",
        timestamp=datetime.datetime.utcnow()
    ))
    db.delete(p)
    db.commit()
    return {"success": True, "deleted_id": proposal_id}

