import urllib.request
import json

url = "https://politclens.onrender.com/api/stats/overview"
req = urllib.request.urlopen(url, timeout=15)
data = json.loads(req.read().decode())

print("="*85)
print("VERIFICA LIVE SOGLIE 5% DI VERIDICITA PARTITO PER PARTITO (RENDER)")
print("="*85)

for p in data.get("party_rankings", []):
    tier = p.get("truthfulness_tier", {})
    t_label = tier.get("label", "").encode("ascii", "backslashreplace").decode()
    t_tier = tier.get("tier", "")
    print(f"{p.get('poll_percentage'):4.1f}% | {p.get('code'):6} | {p.get('name'):<28} | Veridicita: {p.get('truthfulness_score'):5.1f}% | Soglia: {t_label:<20} | Tier: {t_tier}")

print("="*85)
print(f"Totale Soglie 5% censite nell'API: {len(data.get('truth_thresholds', []))}")
for t in data.get("truth_thresholds", [])[:10]:
    lbl = t.get("label", "").encode("ascii", "backslashreplace").decode()
    print(f"  {t.get('min_score'):4.1f}% -> {lbl:<22} ({t.get('desc')[:45]}...)")
print("="*85)
