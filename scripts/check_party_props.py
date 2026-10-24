import urllib.request
import json

url = "https://politclens.onrender.com/api/proposals?limit=300"
req = urllib.request.urlopen(url)
props = json.loads(req.read().decode())
print(f"Total proposals returned: {len(props)}")

targets = ["Partito Socialista Italiano", "Alternativa Popolare", "Pace Terra Dignità", "Sud chiama Nord"]
for t in targets:
    p_props = [p for p in props if p.get("partito") == t]
    print(f"\n=== {t} ({len(p_props)} proposals) ===")
    for p in p_props:
        text = p.get('sintesi') or p.get('titolo') or p.get('descrizione') or ''
        print(f"  [{p.get('macro_argomento')}] {text[:70]}...")
