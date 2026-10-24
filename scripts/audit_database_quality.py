import sys, os
sys.path.insert(0, 'backend')
from app.database import SessionLocal
from app.models import PoliticalProposal
from difflib import SequenceMatcher

db = SessionLocal()
props = db.query(PoliticalProposal).all()
print(f"Total proposals: {len(props)}")

# Check for non-quantified costs
unquantified = [p for p in props if not p.costo_stimato or p.costo_stimato.lower() in ["non quantificato", "non specificato", "da definire"]]
print(f"\nUnquantified proposals count: {len(unquantified)}")
for p in unquantified[:10]:
    print(f"- [{p.partito} | {p.macro_argomento}] {p.dichiarazione_sintesi[:70]}... Costo: {p.costo_stimato}")

# Check for unspecified coverages
unspecified_cov = [p for p in props if not p.coperture_dichiarate or "non specificat" in p.coperture_dichiarate.lower() or p.coperture_dichiarate.lower() in ["nessuna", "none", ""]]
print(f"\nUnspecified coverages count: {len(unspecified_cov)}")
for p in unspecified_cov[:10]:
    print(f"- [{p.partito} | {p.macro_argomento}] Copertura: {p.coperture_dichiarate[:70]}")

db.close()
