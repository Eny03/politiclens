import urllib.request
import json

res = urllib.request.urlopen('https://politclens.onrender.com/api/stats/overview', timeout=15)
data = json.loads(res.read().decode())
print('total_proposals:', data.get('total_proposals'))
print('average_truthfulness:', data.get('average_truthfulness'))
print('average_financial_feasibility:', data.get('average_financial_feasibility'))
for p in data.get('party_rankings', [])[:10]:
    print(f"{p.get('name')}: truth={p.get('truthfulness_score')}, fin={p.get('financial_reliability_score')}, poll={p.get('poll_percentage')}")
