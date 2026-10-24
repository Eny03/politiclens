import os
import sys
import json
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal
from app.models import PoliticalParty, PoliticalProposal

def export_all():
    db = SessionLocal()
    parties = db.query(PoliticalParty).order_by(PoliticalParty.poll_percentage.desc()).all()
    proposals = db.query(PoliticalProposal).order_by(PoliticalProposal.id).all()
    
    print(f"Exporting {len(parties)} parties and {len(proposals)} proposals...")
    
    parties_list = []
    for p in parties:
        parties_list.append({
            "name": p.name,
            "code": p.code,
            "color": p.color,
            "coalition": p.coalition,
            "leader": p.leader,
            "poll_percentage": p.poll_percentage,
            "poll_trend": p.poll_trend or "stabile",
            "truthfulness_score": p.truthfulness_score or 75.0,
            "financial_reliability_score": p.financial_reliability_score or 65.0,
            "official_website": p.official_website,
            "description": p.description or ""
        })
        
    proposals_list = []
    for pr in proposals:
        ts_str = pr.timestamp.isoformat() if pr.timestamp else datetime.datetime.utcnow().isoformat()
        proposals_list.append({
            "partito": pr.partito,
            "macro_argomento": pr.macro_argomento,
            "dichiarazione_sintesi": pr.dichiarazione_sintesi,
            "tipo_azione": pr.tipo_azione,
            "costo_stimato": pr.costo_stimato or "Non quantificato",
            "coperture_dichiarate": pr.coperture_dichiarate or "In attesa di DDL formale e Relazione Tecnica MEF",
            "fattibilita_finanziaria": pr.fattibilita_finanziaria or "",
            "fact_check_status": pr.fact_check_status or "In attesa di copertura",
            "fact_check_motivazione": pr.fact_check_motivazione or "",
            "fact_check_fonte": pr.fact_check_fonte or "",
            "fonte_url": pr.fonte_url,
            "fonte_titolo": pr.fonte_titolo or "",
            "fonte_testata": pr.fonte_testata or "",
            "timestamp": ts_str
        })
        
    seed_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "data", "seed_data.py"))
    content = "import datetime\n\nPARTIES_SEED = " + json.dumps(parties_list, indent=2, ensure_ascii=False) + "\n\nPROPOSALS_SEED = " + json.dumps(proposals_list, indent=2, ensure_ascii=False) + "\n"
    
    with open(seed_file, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"Successfully saved {len(proposals_list)} proposals to {seed_file}")
    db.close()

if __name__ == "__main__":
    export_all()
