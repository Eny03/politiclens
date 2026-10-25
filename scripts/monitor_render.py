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
        top_party = rankings[0] if rankings else {}
        top_truth = top_party.get("truthfulness_score", 0)
        top_tier = top_party.get("truthfulness_tier", {})
        
        print(f"Attempt {attempt+1:02d}: National Avg Truth = {avg_truth:.1f}%, Top Party ({top_party.get('code')}) = {top_truth:.1f}% [{top_tier.get('label')}]")
        if avg_truth < 80.0 and top_truth < 80.0:
            print("\n>>> LIVE RENDER DEPLOYMENT CONFIRMED UPDATED WITH STRICT FACT-CHECKING MODEL! <<<")
            break
    except Exception as e:
        print(f"Attempt {attempt+1:02d}: {e}")
    time.sleep(12)

