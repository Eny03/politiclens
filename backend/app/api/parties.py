from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import PoliticalParty, PoliticalProposal
from app.schemas import PoliticalPartySchema, PoliticalProposalDetail

router = APIRouter(prefix="/api/parties", tags=["Partiti Politici"])

@router.get("", response_model=List[PoliticalPartySchema])
def list_parties(db: Session = Depends(get_db)):
    """Returns all registered political parties with current proposal count and dynamic AI polling averages."""
    import datetime
    today_str = datetime.datetime.now().strftime("%d/%m/%Y")
    parties = db.query(PoliticalParty).order_by(PoliticalParty.poll_percentage.desc()).all()
    first_p = parties[0] if parties else None
    
    # Auto-synchronize polling tracking if not yet refreshed today
    if first_p and (not first_p.poll_sources or today_str not in first_p.poll_sources):
        try:
            from app.ingestion.poll_tracker import run_poll_tracker_pipeline
            run_poll_tracker_pipeline(db)
            parties = db.query(PoliticalParty).order_by(PoliticalParty.poll_percentage.desc()).all()
        except Exception as e:
            print(f"[Parties API] Auto-refresh poll notice: {e}")

    results = []
    for p in parties:
        count = db.query(func.count(PoliticalProposal.id)).filter(PoliticalProposal.party_id == p.id).scalar() or 0
        if count == 0:
            count = db.query(func.count(PoliticalProposal.id)).filter(PoliticalProposal.partito.ilike(f"%{p.name}%")).scalar() or 0
            
        party_data = PoliticalPartySchema(
            id=p.id,
            code=p.code,
            name=p.name,
            coalition=p.coalition,
            leader=p.leader,
            color=p.color,
            official_website=p.official_website,
            description=p.description,
            dossier_ai=p.dossier_ai,
            poll_percentage=p.poll_percentage or 0.0,
            poll_trend=p.poll_trend or "stabile",
            poll_sources=p.poll_sources or "Media YouTrend/AGI, SWG, Ipsos, Tecnè, Noto",
            truthfulness_score=p.truthfulness_score or 0.0,
            financial_reliability_score=p.financial_reliability_score or 0.0,
            proposals_count=count
        )
        results.append(party_data)
    return results

@router.get("/{party_code_or_id}")
def get_party_detail(party_code_or_id: str, db: Session = Depends(get_db)):
    """Returns specific party profile with AI Strategic Dossier, associated proposals and thematic distribution."""
    import json
    from app.ingestion.dossier_generator import generate_party_dossier

    party = None
    if party_code_or_id.isdigit():
        party = db.query(PoliticalParty).filter(PoliticalParty.id == int(party_code_or_id)).first()
    if not party:
        party = db.query(PoliticalParty).filter(PoliticalParty.code.ilike(party_code_or_id)).first()
    if not party:
        party = db.query(PoliticalParty).filter(PoliticalParty.name.ilike(f"%{party_code_or_id}%")).first()

    if not party:
        raise HTTPException(status_code=404, detail="Partito politico non trovato")

    # If dossier is not generated yet, synthesize it now
    dossier_dict = None
    if party.dossier_ai:
        try:
            dossier_dict = json.loads(party.dossier_ai)
        except Exception:
            dossier_dict = None

    if not dossier_dict:
        try:
            dossier_dict = generate_party_dossier(party, db)
            party.dossier_ai = json.dumps(dossier_dict, ensure_ascii=False)
            db.commit()
        except Exception as e:
            print(f"[PartiesAPI] Error generating dynamic dossier: {e}")

    proposals = db.query(PoliticalProposal).filter(
        (PoliticalProposal.party_id == party.id) | (PoliticalProposal.partito.ilike(f"%{party.name}%"))
    ).order_by(PoliticalProposal.timestamp.desc()).all()

    # Topic distribution
    topic_counts = {}
    for prop in proposals:
        topic_counts[prop.macro_argomento] = topic_counts.get(prop.macro_argomento, 0) + 1

    return {
        "party": PoliticalPartySchema.model_validate(party),
        "total_proposals": len(proposals),
        "topic_distribution": topic_counts,
        "dossier": dossier_dict,
        "proposals": [PoliticalProposalDetail.model_validate(p) for p in proposals]
    }

@router.post("/update-polls")
def update_polls(db: Session = Depends(get_db)):
    """
    Triggers PollTrackerAgent to ingest, extract, and reconcile latest electoral poll
    distribution from certified polling institutes (YouTrend, SWG, Ipsos, Tecnè, BiDiMedia).
    Generates AuditLog entries for every party percentage change.
    """
    from app.ingestion.poll_tracker import run_poll_tracker_pipeline
    updated = run_poll_tracker_pipeline(db)
    return {
        "status": "SUCCESS",
        "message": f"Aggiornamento demoscopico completato: {len(updated)} partiti ricalcolati con successo.",
        "updated_parties": updated
    }


