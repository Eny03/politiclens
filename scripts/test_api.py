import os
import sys
import json

db_path = os.path.abspath('backend/politiclens.db')
os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
sys.path.insert(0, os.path.abspath('backend'))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 1. Test /api/parties
r = client.get('/api/parties')
assert r.status_code == 200, f"Error {r.status_code}: {r.text}"
parties = r.json()
print(f"API Parties Count: {len(parties)}")
fn = [p for p in parties if 'futuro' in p['name'].lower()]
ora = [p for p in parties if p['name'] == 'ORA!']
assert len(fn) == 1, "Futuro Nazionale missing or duplicated!"
assert len(ora) == 1, "ORA! missing or duplicated!"
print(f"Futuro Nazionale: {fn[0]['name']} | Leader: {fn[0]['leader']} | Sondaggi: {fn[0]['poll_percentage']}%")
print(f"ORA!: {ora[0]['name']} | Leader: {ora[0]['leader']} | Sondaggi: {ora[0]['poll_percentage']}%")

# 2. Test /api/stats/overview
r = client.get('/api/stats/overview')
assert r.status_code == 200
stats = r.json()
print(f"Overview Stats: {stats['total_proposals']} proposals, {stats['total_parties']} parties")
assert stats['total_parties'] >= 18

# 3. Test /api/proposals
r = client.get('/api/proposals?limit=150')
assert r.status_code == 200
props = r.json()
print(f"Proposals retrieved: {len(props)}")
bad = [
    p for p in props 
    if 'indirizzo programmatico' in p['dichiarazione_sintesi'].lower() 
    or any(m in p['dichiarazione_sintesi'].lower() for m in ['la repubblica', 'sole 24', 'fatto quotidiano', 'landini annuncia', 'schillaci suona'])
]
print(f"Bad/un-rephrased proposals in API: {len(bad)}")
assert len(bad) == 0, f"Found {len(bad)} bad proposals: {bad}"
print("\n>>> ALL TESTS PASSED SUCCESSFULLY! 100% CLEAN! <<<")
