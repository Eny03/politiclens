import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.database import SessionLocal
from app.api.stats import get_overview_stats

db = SessionLocal()
try:
    res = get_overview_stats(db)
    print(f"Average truthfulness: {res.average_truthfulness}%")
    print(f"Quantified coverage pct: {res.quantified_cost_percentage}%")
    print(f"Total parties ranked: {len(res.party_rankings)}")
    print(f"Coalition truthfulness: {res.coalition_truthfulness}")
    print("Ranked parties:")
    for p in res.party_rankings:
        print(f"  {p['poll_percentage']:4.1f}% | {p['code']:6} | {p['name']:<28} | Truth: {p['truthfulness_score']:5.1f}% | Cov: {p['financial_reliability_score']:5.1f}%")
finally:
    db.close()
