import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal
from app.ingestion.gap_detector import detect_information_gaps

db = SessionLocal()
gaps = detect_information_gaps(db, max_gaps=100)
print(f"Total gaps detected: {len(gaps)}")
zero_gaps = [g for g in gaps if g.get("existing_count") == 0]
print(f"Zero gaps (lacuna totale): {len(zero_gaps)}")
for g in zero_gaps:
    print(f"- {g['party_name']} | {g['topic']}")
db.close()
