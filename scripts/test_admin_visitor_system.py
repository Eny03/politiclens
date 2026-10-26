import sys
import os
import time

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_visitor_system():
    print("1. Testing unauthorized access to /api/admin/visitors/stats...")
    # Simulate an external client IP with no auth key
    r_unauth = client.get("/api/admin/visitors/stats", headers={"x-forwarded-for": "198.51.100.77"})
    assert r_unauth.status_code == 403, f"Expected 403 for unauthorized IP, got {r_unauth.status_code}: {r_unauth.text}"
    print("   [OK] Unauthorized access successfully blocked with 403 Forbidden!")

    print("\n2. Simulating realistic visitors with different IPs...")
    # Visit 1: Mobile user from Rome (IP 93.45.12.34)
    client.get(
        "/parties",
        headers={
            "x-forwarded-for": "93.45.12.34",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "cf-ipcountry": "IT"
        }
    )
    # Visit 2: Desktop Chrome user from Milan (IP 151.18.25.60)
    client.get(
        "/compare",
        headers={
            "x-forwarded-for": "151.18.25.60",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "cf-ipcountry": "IT"
        }
    )
    # Visit 3: Search / chat user
    client.get(
        "/chat",
        headers={
            "x-forwarded-for": "151.18.25.60",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "cf-ipcountry": "IT"
        }
    )
    # Visit 4: Firefox desktop user from Naples (IP 79.22.40.11)
    client.get(
        "/fact-check",
        headers={
            "x-forwarded-for": "79.22.40.11",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
            "cf-ipcountry": "IT"
        }
    )

    # Allow background logging thread to write to SQLite
    time.sleep(0.5)

    print("\n3. Testing authorized admin verification (/api/admin/verify)...")
    # Verify localhost access
    r_ver_local = client.post("/api/admin/verify")
    assert r_ver_local.status_code == 200, f"Local verify failed: {r_ver_local.text}"
    ver_data = r_ver_local.json()
    print("   Local verification:", ver_data)
    assert ver_data["authorized"] == True, "Local machine should be authorized by default!"

    # Verify external IP with correct master token
    r_ver_ext = client.post(
        "/api/admin/verify",
        headers={"x-forwarded-for": "203.0.113.88", "x-admin-token": settings.ADMIN_SECRET_KEY}
    )
    assert r_ver_ext.status_code == 200
    assert r_ver_ext.json()["authorized"] == True
    print("   Remote token verification: Authorized successfully!")

    print("\n4. Testing /api/admin/visitors/stats (Telemetry metrics)...")
    r_stats = client.get("/api/admin/visitors/stats")
    assert r_stats.status_code == 200, f"Stats failed: {r_stats.text}"
    stats = r_stats.json()
    print("   [ONLINE] Online Adesso (ultimi 5 min):", stats.get("online_now_count"))
    print("   [VISITORS] Visitatori Unici Oggi:", stats.get("today_visitors_count"))
    print("   [TOTAL] Visitatori Unici Totali:", stats.get("total_visitors_count"))
    print("   [PAGES] Totale Richieste / Visualizzazioni:", stats.get("total_page_views"))
    print("   [DEVICE] Device Breakdown:", stats.get("device_breakdown"))
    print("   [BROWSER] Browser Breakdown:", stats.get("browser_breakdown"))
    print("   [TOP PATHS] Top Paths:", stats.get("top_paths"))

    assert stats.get("total_visitors_count") >= 3, "Expected at least 3 unique IPs!"
    assert stats.get("online_now_count") >= 3, "Expected online now to count recent visitors!"

    print("\n5. Testing /api/admin/visitors/list (IP table)...")
    r_list = client.get("/api/admin/visitors/list")
    assert r_list.status_code == 200, f"List failed: {r_list.text}"
    data = r_list.json()
    visitors = data.get("visitors", [])
    print(f"   Totale IP unici registrati: {len(visitors)}")
    for v in visitors:
        online_str = "[ONLINE]" if v["is_online_now"] else "[OFFLINE]"
        print(f"     - {online_str} | IP: {v['ip_address']:<15} | Visite: {v['total_visits']} | {v['device_type']} ({v['browser']}) | Ultimo path: {v['last_path']}")

    print("\n>>> TEST SISTEMA MONITORAGGIO VISITATORI E IP COMPLETATO CON SUCCESSO! <<<")

if __name__ == "__main__":
    test_visitor_system()
