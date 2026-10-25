import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_endpoints():
    print("1. Testing /api/health...")
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("   Health OK:", r.json())

    print("\n2. Testing /api/stats/overview...")
    r = client.get("/api/stats/overview")
    assert r.status_code == 200, f"Stats overview failed: {r.text}"
    stats = r.json()
    print("   Total Proposals:", stats.get("total_proposals"))
    print("   Total Parties:", stats.get("total_parties"))
    print("   Average Truthfulness:", stats.get("average_truthfulness"))
    print("   Quantified Cost % (Coperture):", stats.get("quantified_cost_percentage"))
    rankings = stats.get("party_rankings", [])
    print(f"   Party Rankings count: {len(rankings)}")
    for p in rankings[:5]:
        print(f"     - {p['name']} ({p['code']}): {p['poll_percentage']}% | Truth: {p['truthfulness_score']}% | Fin: {p['financial_reliability_score']}%")

    print("\n3. Testing /api/parties...")
    r = client.get("/api/parties")
    assert r.status_code == 200, f"Parties check failed: {r.text}"
    parties = r.json()
    print(f"   Total Parties returned: {len(parties)}")
    fdi = next((p for p in parties if p["code"] == "FDI"), None)
    fn = next((p for p in parties if p["code"] == "FUTNAZ"), None)
    print(f"   FDI: {fdi['poll_percentage']}% | Truth: {fdi['truthfulness_score']}% | Fin: {fdi['financial_reliability_score']}%" if fdi else "FDI not found")
    print(f"   Futuro Nazionale: {fn['poll_percentage']}% | Truth: {fn['truthfulness_score']}% | Fin: {fn['financial_reliability_score']}%" if fn else "FN not found")

    print("\n4. Testing /api/parties/FDI (AI Strategic Dossier)...")
    r = client.get("/api/parties/FDI")
    assert r.status_code == 200, f"Party FDI detail failed: {r.text}"
    p_detail = r.json()
    dossier = p_detail.get("dossier")
    print("   Dossier present:", bool(dossier))
    if isinstance(dossier, dict):
        print("   Punti di forza:", dossier.get("punti_di_forza"))
        print("   Sintesi Strategica:", dossier.get("sintesi_strategica", "")[:90] + "...")

    print("\n5. Testing /api/proposals (sample 5)...")
    r = client.get("/api/proposals?limit=5")
    assert r.status_code == 200, f"Proposals failed: {r.text}"
    props = r.json()
    for p in props[:3]:
        print(f"   Proposal ID {p['id']}: [{p['partito']}] truth_score={p.get('truth_score')}% ({p.get('fact_check_status')})")

    print("\n6. Testing /api/audit/logs...")
    r = client.get("/api/audit/logs?limit=5")
    assert r.status_code == 200, f"Audit failed: {r.text}"
    audit_data = r.json()
    logs = audit_data.get("logs", [])
    print(f"   Audit logs count: {len(logs)} (Total: {audit_data.get('total')})")
    for a in logs[:3]:
        print(f"   - [{a.get('agent_responsible')}] {a.get('event_type')}: {a.get('entity_name')}")

    print("\n7. Testing /api/chat/provider...")
    r = client.get("/api/chat/provider")
    assert r.status_code == 200, f"Chat provider failed: {r.text}"
    print("   Chat Provider:", r.json())

    print("\n8. Testing /api/comparison/matrix...")
    r = client.get("/api/comparison/matrix")
    assert r.status_code == 200, f"Comparison matrix failed: {r.text}"
    matrix = r.json()
    print("   Comparison topics count:", len(matrix.get("macro_argomenti", [])))
    print("   Parties in matrix:", len(matrix.get("partiti", [])))
    print("   Matrix rows:", len(matrix.get("matrix", [])))

    print("\n>>> TUTTE LE OPERAZIONI AI DEL BACKEND FUNZIONANO CORRETTAMENTE! <<<")

if __name__ == "__main__":
    test_endpoints()
