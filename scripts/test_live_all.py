import urllib.request
import json

base_url = "https://politclens.onrender.com"

print("="*80)
print("VERIFICA LIVE RENDER: STATISTICHE E BENCHMARK")
print("="*80)

# 1. Stats Overview
req = urllib.request.urlopen(f"{base_url}/api/stats/overview", timeout=15)
stats = json.loads(req.read().decode())
print(f"Media Veridicità Nazionale: {stats.get('average_truthfulness')}%")
print(f"Coperture Quantificate: {stats.get('quantified_cost_percentage')}%")
print(f"Totale Proposte: {stats.get('total_proposals')}")
print(f"Distribuzione Fact-Check: {stats.get('fact_check_distribution')}")

print("\n" + "="*80)
print("VERIFICA LIVE RENDER: 22 PARTITI (SONDAGGI & METRICHE)")
print("="*80)

req_p = urllib.request.urlopen(f"{base_url}/api/parties", timeout=15)
parties = json.loads(req_p.read().decode())
parties_sorted = sorted(parties, key=lambda x: x.get("poll_percentage", 0), reverse=True)

total_poll = sum(p.get("poll_percentage", 0) for p in parties_sorted)
print(f"Totale Partiti Mappati: {len(parties_sorted)}")
print(f"Somma Percentuali Sondaggi: {round(total_poll, 1)}%\n")

for p in parties_sorted:
    print(f"  {p.get('poll_percentage', 0):4.1f}% | {p.get('code'):6} | {p.get('name'):<28} | Veridicità: {p.get('truthfulness_score', 0):4.1f}% | Coperture: {p.get('financial_reliability_score', 0):4.1f}% | Fonte: {p.get('poll_sources')}")

print("\n" + "="*80)
print("VERIFICA LIVE RENDER: TEST CHAT SUI SONDAGGI (CDX E CSX)")
print("="*80)

chat_req_data = json.dumps({"question": "Dai sondaggi quale è la somma di cdx e csx"}).encode("utf-8")
req_chat = urllib.request.Request(
    f"{base_url}/api/chat",
    data=chat_req_data,
    headers={"Content-Type": "application/json"}
)
chat_res = json.loads(urllib.request.urlopen(req_chat, timeout=20).read().decode())
print("Risposta AI:\n")
print(chat_res.get("answer", "").encode("ascii", "backslashreplace").decode("ascii"))
print("\n" + "="*80)
