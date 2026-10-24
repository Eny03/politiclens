import urllib.request
import json

url = "https://politclens.onrender.com/api/ingestion/gaps?limit=100"
req = urllib.request.urlopen(url)
gaps = json.loads(req.read().decode())
print(f"Total gaps returned: {len(gaps)}")
zero_gaps = [g for g in gaps if g.get("existing_count") == 0]
print(f"Zero gaps (lacuna totale): {len(zero_gaps)}")
for g in zero_gaps:
    print(f"- {g['party_name']} | {g['topic']}")

print("\n--- Summary by party of zero gaps ---")
by_party = {}
for g in zero_gaps:
    by_party[g['party_name']] = by_party.get(g['party_name'], 0) + 1
for p, c in sorted(by_party.items(), key=lambda x: -x[1]):
    print(f"{p}: {c} zero gaps")
