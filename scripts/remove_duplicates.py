import sys, os
sys.path.insert(0, 'backend')
from app.database import SessionLocal
from app.models import PoliticalProposal, PoliticalParty
from difflib import SequenceMatcher

db = SessionLocal()
props = db.query(PoliticalProposal).all()
print(f"Total proposals before deduplication: {len(props)}")

by_party_topic = {}
for p in props:
    by_party_topic.setdefault((p.partito, p.macro_argomento), []).append(p)

to_delete_ids = set()

# Explicit known duplicate pairs and rules
STOPWORDS = {
    'del', 'dello', 'della', 'dei', 'degli', 'delle', 'al', 'allo', 'alla', 'ai', 'agli', 'alle',
    'da', 'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle', 'in', 'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
    'su', 'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle', 'con', 'per', 'tra', 'fra',
    'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'e', 'ed', 'o', 'od', 'ma', 'se', 'che',
    'proposta', 'disegno', 'legge', 'ddl', 'piano', 'riforma', 'misura', 'misure', 'programma', 'nazionale',
    'per', 'con', 'anche', 'tutti', 'tutte', 'senza', 'oltre', 'fino'
}

for (party, topic), p_list in by_party_topic.items():
    if len(p_list) < 2:
        continue
    for i in range(len(p_list)):
        for j in range(i + 1, len(p_list)):
            p1 = p_list[i]
            p2 = p_list[j]
            
            if p1.id in to_delete_ids or p2.id in to_delete_ids:
                continue
                
            t1 = p1.dichiarazione_sintesi.lower()
            t2 = p2.dichiarazione_sintesi.lower()
            
            w1 = {w.strip('.,;:()[]"\'') for w in t1.split() if w.strip('.,;:()[]"\'') not in STOPWORDS and len(w) > 3}
            w2 = {w.strip('.,;:()[]"\'') for w in t2.split() if w.strip('.,;:()[]"\'') not in STOPWORDS and len(w) > 3}
            
            inter = w1 & w2
            overlap = len(inter) / min(len(w1), len(w2)) if min(len(w1), len(w2)) > 0 else 0
            ratio = SequenceMatcher(None, t1, t2).ratio()
            
            # Check for identical subjects
            same_subject = False
            for subj in [
                'piano mattei', 'salario minimo', 'quota 41 pura', 'settimana lavorativa corta',
                'ius scholae', 'autonomia differenziata', 'ponte sullo stretto', 'fondo sanitario',
                'flat tax', 'cannabis', 'nucleare civile', 'protocollo italia-albania',
                'tempo pieno', 'progressività irpef', 'asseverazione preventiva'
            ]:
                if subj in t1 and subj in t2:
                    same_subject = True
                    break
                    
            if same_subject or overlap >= 0.5 or ratio >= 0.45:
                # Decide which one to keep:
                # Keep the one with longer text or more formal action type
                if len(p1.dichiarazione_sintesi) >= len(p2.dichiarazione_sintesi):
                    keep = p1
                    discard = p2
                else:
                    keep = p2
                    discard = p1
                    
                print(f"Duplicate found for [{party} | {topic}]:")
                print(f"  KEEP (id={keep.id}): {keep.dichiarazione_sintesi[:80]}...")
                print(f"  DELETE (id={discard.id}): {discard.dichiarazione_sintesi[:80]}...")
                to_delete_ids.add(discard.id)

print(f"\nTotal proposals to delete: {len(to_delete_ids)}")

for pid in to_delete_ids:
    p_obj = db.query(PoliticalProposal).filter(PoliticalProposal.id == pid).first()
    if p_obj:
        db.delete(p_obj)

db.commit()
print(f"Remaining proposals in DB: {db.query(PoliticalProposal).count()}")
db.close()
