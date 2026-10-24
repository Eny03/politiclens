import sys, os
sys.path.insert(0, 'backend')
from app.database import SessionLocal
from app.models import PoliticalProposal
from difflib import SequenceMatcher

db = SessionLocal()
props = db.query(PoliticalProposal).all()

by_party_topic = {}
for p in props:
    by_party_topic.setdefault((p.partito, p.macro_argomento), []).append(p)

to_merge = []

STOPWORDS = {
    'del', 'dello', 'della', 'dei', 'degli', 'delle', 'al', 'allo', 'alla', 'ai', 'agli', 'alle',
    'da', 'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle', 'in', 'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
    'su', 'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle', 'con', 'per', 'tra', 'fra',
    'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'e', 'ed', 'o', 'od', 'ma', 'se', 'che',
    'proposta', 'disegno', 'legge', 'ddl', 'piano', 'riforma', 'misura', 'misure', 'programma', 'nazionale',
    'per', 'con', 'anche', 'tutti', 'tutte', 'senza', 'oltre', 'fino'
}

for (party, topic), p_list in by_party_topic.items():
    for i in range(len(p_list)):
        for j in range(i + 1, len(p_list)):
            p1 = p_list[i]
            p2 = p_list[j]
            t1 = p1.dichiarazione_sintesi.lower()
            t2 = p2.dichiarazione_sintesi.lower()
            
            w1 = {w.strip('.,;:()[]"\'') for w in t1.split() if w.strip('.,;:()[]"\'') not in STOPWORDS and len(w) > 3}
            w2 = {w.strip('.,;:()[]"\'') for w in t2.split() if w.strip('.,;:()[]"\'') not in STOPWORDS and len(w) > 3}
            
            inter = w1 & w2
            overlap = len(inter) / min(len(w1), len(w2)) if min(len(w1), len(w2)) > 0 else 0
            ratio = SequenceMatcher(None, t1, t2).ratio()
            
            # Key subject triggers
            same_subject = False
            for subj in ['mattei', 'salario minimo', 'quota 41', 'settimana lavorativa', 'ius scholae', 'autonomia differenziata', 'ponte sullo stretto', 'fondo sanitario', 'flat tax', 'cannabis', 'nucleare']:
                if subj in t1 and subj in t2:
                    same_subject = True
                    break
                    
            if same_subject or overlap >= 0.5 or ratio >= 0.45:
                to_merge.append({
                    "party": party,
                    "topic": topic,
                    "p1": p1,
                    "p2": p2,
                    "overlap": overlap,
                    "ratio": ratio,
                    "shared_words": list(inter)
                })

print(f"Total potential duplicates found: {len(to_merge)}")
for m in to_merge:
    print(f"\n[{m['party']} | {m['topic']}] Overlap: {m['overlap']:.2f}, Ratio: {m['ratio']:.2f}")
    print(f"   A (id={m['p1'].id}): {m['p1'].dichiarazione_sintesi}")
    print(f"   B (id={m['p2'].id}): {m['p2'].dichiarazione_sintesi}")
    print(f"   Shared: {m['shared_words']}")

db.close()
