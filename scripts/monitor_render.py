import urllib.request
import json
import time

print("Monitoring live deployment on Render...")
for attempt in range(30):
    try:
        req = urllib.request.urlopen("https://politclens.onrender.com/api/stats/overview", timeout=10)
        data = json.loads(req.read().decode())
        avg_truth = data.get("average_truthfulness")
        quant = data.get("quantified_cost_percentage")
        rankings = data.get("party_rankings", [])
        top_party = rankings[0] if rankings else {}
        print(f"Attempt {attempt+1}: Truthfulness = {avg_truth}%, Quantified = {quant}%, Top party = {top_party.get('code')} ({top_party.get('poll_percentage')}%)")
        if avg_truth and avg_truth < 80.0:
            print(">>> LIVE RENDER DEPLOYMENT SUCCESSFUL! <<<")
            break
    except Exception as e:
        print(f"Attempt {attempt+1}: {e}")
    time.sleep(10)
