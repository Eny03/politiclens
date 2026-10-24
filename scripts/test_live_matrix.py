import urllib.request
import json

url = "https://politclens.onrender.com/api/comparison/matrix"
res = urllib.request.urlopen(url, timeout=10)
data = json.loads(res.read().decode())
for row in data.get("matrix", []):
    if row.get("macro_argomento") == "Politica Estera":
        fdi_cell = row.get("parties", {}).get("Fratelli d'Italia", {})
        pd_cell = row.get("parties", {}).get("Partito Democratico", {})
        print("FdI stance:", fdi_cell.get("stance_type"))
        print("FdI props count:", len(fdi_cell.get("proposals", [])))
        for p in fdi_cell.get("proposals", []):
            print("  -", p.get("dichiarazione_sintesi")[:80])
        print("\nPD stance:", pd_cell.get("stance_type"))
        print("PD props count:", len(pd_cell.get("proposals", [])))
        for p in pd_cell.get("proposals", []):
            print("  -", p.get("dichiarazione_sintesi")[:80])
