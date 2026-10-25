import urllib.request
import json

url = "https://politclens.onrender.com/api/proposals?limit=350"
props = json.loads(urllib.request.urlopen(url).read().decode())
print(f"Total proposals returned: {len(props)}")

for party_name in ["Partito Democratico", "Fratelli d'Italia", "Movimento 5 Stelle", "Lega - Salvini Premier"]:
    p_props = [p for p in props if p.get("partito") == party_name]
    print(f"\n=== {party_name} ({len(p_props)} proposals) ===")
    from collections import Counter
    statuses = [p.get("fact_check_status") for p in p_props]
    print(Counter(statuses))
    for p in p_props:
        print(f"  [{p.get('fact_check_status')}] [{p.get('costo_stimato')[:30]}] {p.get('dichiarazione_sintesi')[:60]}...")
