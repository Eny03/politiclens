import urllib.request
import json

url_stats = "https://politclens.onrender.com/api/stats/overview"
req = urllib.request.urlopen(url_stats, timeout=15)
data = json.loads(req.read().decode())

print("="*85)
print("VERIFICA LIVE STATISTICHE E RATING PARTITI (RENDER)")
print("="*85)
print(f"Media Veridicità Nazionale: {data.get('average_truthfulness'):.1f}%")
print(f"Coperture Quantificate: {data.get('quantified_cost_percentage'):.1f}%\n")

for p in data.get("party_rankings", []):
    tier = p.get("truthfulness_tier", {})
    t_label = tier.get("label", "").encode("ascii", "backslashreplace").decode()
    t_tier = tier.get("tier", "")
    print(f"{p.get('poll_percentage'):4.1f}% | {p.get('code'):6} | {p.get('name'):<28} | Veridicità: {p.get('truthfulness_score'):5.1f}% | Soglia: {t_label:<20} | Tier: {t_tier}")

print("\n" + "="*85)
print("VERIFICA LIVE VOTI PROPOSTE (SALTI DEL 5%)")
print("="*85)
url_props = "https://politclens.onrender.com/api/proposals?limit=15"
req_p = urllib.request.urlopen(url_props, timeout=15)
props_data = json.loads(req_p.read().decode())
for pr in props_data[:10]:
    v = pr.get("truth_score")
    print(f"  [Voto: {v}%] {pr.get('fact_check_status'):<25} | {pr.get('partito'):<22} | {pr.get('dichiarazione_sintesi')[:40]}...")
print("="*85)

