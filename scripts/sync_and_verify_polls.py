import os
import sys

sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal
from app.models import PoliticalParty, PollMeasurement
from app.ingestion.poll_tracker import run_poll_tracker_pipeline, SURVEY_INSTITUTES_OBSERVATIONS

db = SessionLocal()
try:
    print("--- 1. Resetting Parties to Certified Supermedia Baselines ---")
    parties = db.query(PoliticalParty).all()
    for p in parties:
        bench = SURVEY_INSTITUTES_OBSERVATIONS.get(p.code)
        if not bench and p.code == "NOI_MOD":
            bench = SURVEY_INSTITUTES_OBSERVATIONS.get("NM")
        elif not bench and p.code == "NM":
            bench = SURVEY_INSTITUTES_OBSERVATIONS.get("NOI_MOD")
        if bench:
            prev_w = bench["previous_wave"]
            s_vals = list(bench["surveys"].values())
            curr_pct = round(sum(s_vals) / len(s_vals), 1)
            delta = round(curr_pct - prev_w, 1)
            trend = f"+{delta:.1f}%" if delta > 0 else (f"{delta:.1f}%" if delta < 0 else "stabile")
            
            p.previous_poll_percentage = prev_w
            p.poll_percentage = curr_pct
            p.poll_trend = trend
            p.poll_sources = f"Supermedia AGI/YouTrend 11 Nov 2026 (SWG, Ipsos, Tecnè, BiDiMedia, Noto) • Rilevazione precedente: {prev_w}% (Var: {trend})"
            print(f"Party {p.code:8s} -> Current: {curr_pct:4.1f}% | Prev: {prev_w:4.1f}% | Trend: {trend:7s}")
    db.commit()

    print("\n--- 2. Running PollTracker Pipeline to test dynamic wave tracking ---")
    res = run_poll_tracker_pipeline(db)
    print(f"Pipeline executed successfully. Processed {len(res)} party updates.")

    print("\n--- 3. Verifying Results in Database ---")
    parties_after = db.query(PoliticalParty).order_by(PoliticalParty.poll_percentage.desc()).all()
    total_pct = sum(p.poll_percentage or 0 for p in parties_after)
    for p in parties_after:
        print(f"{p.name:30s} ({p.code:7s}): {p.poll_percentage:4.1f}% | Prev: {p.previous_poll_percentage or 0:4.1f}% | Trend: {p.poll_trend or 'stabile':7s}")
    print(f"\nTotal Poll Percentage: {total_pct:.1f}% (Normalized)")

finally:
    db.close()
