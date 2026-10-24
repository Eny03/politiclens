import urllib.request
import json
import time

print("Monitoring live deployment on Render...")
for attempt in range(25):
    try:
        req = urllib.request.urlopen("https://politclens.onrender.com/api/stats/overview", timeout=10)
        data = json.loads(req.read().decode())
        tot_prop = data.get("total_proposals")
        print(f"Attempt {attempt+1}: total proposals on live Render = {tot_prop}")
        if tot_prop and tot_prop >= 300:
            print(">>> Live Render updated with new proposals! <<<")
            break
    except Exception as e:
        print(f"Attempt {attempt+1}: {e}")
    time.sleep(6)
