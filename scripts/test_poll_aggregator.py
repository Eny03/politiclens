import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.database import SessionLocal
from app.ingestion.poll_tracker import PollTrackerAgent

db = SessionLocal()
try:
    agent = PollTrackerAgent(db)
    data = agent.fetch_latest_survey_data()
    print("Total party entries:", len(data))
    total_sum = sum(v["poll_percentage"] for k, v in data.items() if k not in ["NOI_MOD", "PA"])
    print(f"Total percentage sum: {total_sum:.1f}%")
    for k, v in sorted(data.items(), key=lambda x: x[1]["poll_percentage"], reverse=True):
        if k not in ["NOI_MOD", "PA"]:
            print(f"{k:8}: {v['poll_percentage']:4.1f}% | {v['name']:<30} | {v['poll_sources']}")
finally:
    db.close()
