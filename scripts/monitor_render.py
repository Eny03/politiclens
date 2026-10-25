import urllib.request
import json
import time

print("Monitoring live deployment on Render (https://politclens.onrender.com)...")
for attempt in range(40):
    try:
        req = urllib.request.urlopen("https://politclens.onrender.com/api/stats/overview", timeout=12)
        data = json.loads(req.read().decode())
        rankings = data.get("party_rankings", [])
        avg_truth = data.get("average_truthfulness", 0)
        fdi_party = next((p for p in rankings if p.get("code") == "FDI"), {})
        fdi_truth = fdi_party.get("truthfulness_score", 0)
        
        # Also check proposals endpoint
        p_req = urllib.request.urlopen("https://politclens.onrender.com/api/proposals?limit=5", timeout=12)
        p_data = json.loads(p_req.read().decode())
        has_truth_score = p_data and "truth_score" in p_data[0] and p_data[0]["truth_score"] is not None

        print(f"Attempt {attempt+1:02d}: Avg Truth = {avg_truth:.1f}%, FDI Truth = {fdi_truth:.1f}%, Proposal truth_score = {has_truth_score}")
        if avg_truth >= 74.0 and fdi_truth >= 75.0 and has_truth_score:
            print("\n>>> LIVE RENDER DEPLOYMENT CONFIRMED UPDATED WITH CALIBRATED 5% PROPOSAL VOTING! <<<")
            break
    except Exception as e:
        print(f"Attempt {attempt+1:02d}: {e}")
    time.sleep(12)

