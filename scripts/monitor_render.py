import urllib.request
import json
import time

print("Monitoring live deployment on Render (https://politclens.onrender.com)...")
for attempt in range(40):
    try:
        req = urllib.request.urlopen("https://politclens.onrender.com/api/stats/overview", timeout=12)
        data = json.loads(req.read().decode())
        avg_truth = data.get("average_truthfulness")
        quant = data.get("quantified_cost_percentage")
        rankings = data.get("party_rankings", [])
        
        fn_entry = next((p for p in rankings if p.get("code") == "FUTNAZ"), None)
        fn_poll = fn_entry.get("poll_percentage") if fn_entry else None
        
        print(f"Attempt {attempt+1:02d}: Truth: {avg_truth}%, Quantified Cov: {quant}%, FN Poll: {fn_poll}%")
        if fn_poll == 6.0 and quant and quant < 85.0:
            print("\n>>> LIVE RENDER DEPLOYMENT CONFIRMED UPDATED TO LATEST COMMIT! <<<")
            break
    except Exception as e:
        print(f"Attempt {attempt+1:02d}: {e}")
    time.sleep(12)
