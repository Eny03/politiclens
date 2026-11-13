import re
import json
from typing import Optional, List, Tuple, Set, Any
from difflib import SequenceMatcher
from app.ai.embeddings import cosine_similarity

STOPWORDS = {
    'del', 'dello', 'della', 'dei', 'degli', 'delle', 'al', 'allo', 'alla', 'ai', 'agli', 'alle',
    'da', 'dal', 'dallo', 'dalla', 'dai', 'dagli', 'dalle', 'in', 'nel', 'nello', 'nella', 'nei', 'negli', 'nelle',
    'su', 'sul', 'sullo', 'sulla', 'sui', 'sugli', 'sulle', 'con', 'per', 'tra', 'fra',
    'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'e', 'ed', 'o', 'od', 'ma', 'se', 'che',
    'proposta', 'disegno', 'legge', 'ddl', 'piano', 'riforma', 'misura', 'misure', 'programma', 'nazionale',
    'anche', 'tutti', 'tutte', 'senza', 'oltre', 'fino', 'come', 'stato', 'sono', 'dalla', 'degli'
}

# Exhaustive clusters for institutional Italian policy topics
POLICY_CLUSTERS = [
    ["piano mattei"],
    ["salario minimo", "retribuzione minima", "salario orario", "lavoro povero"],
    ["quota 41", "41 anni di contributi"],
    ["opzione donna"],
    ["pensione di garanzia", "pensioni minime", "minime a 1000", "minima a 1000"],
    ["settimana corta", "32 ore", "orario a 32"],
    ["sicurezza sul lavoro", "patente a crediti"],
    ["cuneo fiscale", "taglio cuneo", "decontribuzione"],
    ["flat tax", "aliquota unica", "15% per autonomi"],
    ["irpef progressiva", "scaglioni irpef", "progressività irpef"],
    ["concordato preventivo"],
    ["reddito di cittadinanza", "reddito di dignità"],
    ["fondo sanitario", "7.5% del pil", "7,5% pil", "spesa sanitaria"],
    ["liste d'attesa", "abbattimento liste"],
    ["assunzioni medici", "personale sanitario", "30.000 medici"],
    ["premierato", "elezione diretta presidente", "ddl casellati"],
    ["autonomia differenziata", "legge calderoli", "definizione dei lep"],
    ["separazione delle carriere", "sdoppiamento csm"],
    ["ponte sullo stretto", "stretto di messina"],
    ["protocollo italia-albania", "centri albanesi", "gjader"],
    ["nucleare civile", "small modular reactors", "smr", "iv generazione"],
    ["comunità energetiche", "fotovoltaico diffuso"],
    ["patrimoniale", "imposta sui grandi patrimoni"],
    ["extraprofitti", "tassazione extraprofitti"],
    ["fine vita", "suicidio assistito", "eutanasia"],
    ["cannabis", "monopolio cannabis"],
    ["ius scholae", "cittadinanza minori"],
    ["tempo pieno", "asili nido"],
    ["spese militari", "2% pil difesa", "appalti militari"],
    ["concessioni balneari", "direttiva bolkestein"],
    ["continuità territoriale", "caro voli", "insularità"]
]

def clean_and_tokenize(text: str) -> Set[str]:
    """Extracts informative content words longer than 3 characters."""
    normalized = text.lower().replace(',', ' ').replace('.', ' ').replace(':', ' ').replace('(', ' ').replace(')', ' ').replace("'", ' ').replace(';', ' ').replace('"', ' ')
    words = {w for w in normalized.split() if w not in STOPWORDS and len(w) > 3}
    return words

OPPOSITION_MARKERS = {
    "contrariet", "contrario", "contraria", "opposizione", "abrogazione", "abrogare",
    "stop", "blocco", "respingere", "bocciare", "rifiuto", "no al", "no alla"
}

def is_duplicate_proposal(
    party_a: str,
    topic_a: str,
    text_a: str,
    party_b: str,
    topic_b: str,
    text_b: str,
    emb_a: Optional[List[float]] = None,
    emb_b: Optional[List[float]] = None
) -> Tuple[bool, str]:
    """
    Unified, multi-criteria semantic deduplication check.
    Returns (True, reason) if text_a and text_b represent the same policy reform.
    Calibrated to prevent false positives and accidental erasure of distinct policy positions.
    """
    # Rule 0: Must belong to the same party and macro-topic
    if party_a.strip().lower() != party_b.strip().lower():
        return False, "Different parties"
    if topic_a.strip().lower() != topic_b.strip().lower():
        return False, "Different topics"

    t1 = text_a.lower().strip()
    t2 = text_b.lower().strip()

    # Rule 1: Exact string match
    if t1 == t2:
        return True, "Exact match"

    # Rule 1b: Stance polarity check — never duplicate favorable vs opposing policies on the same theme
    t1_opp = any(m in t1 for m in OPPOSITION_MARKERS)
    t2_opp = any(m in t2 for m in OPPOSITION_MARKERS)
    if t1_opp != t2_opp:
        return False, "Opposing political stances (in favor vs opposition)"

    # Rule 2: Policy Subject Cluster match (must share substantive content words, not just the keyword)
    words1 = clean_and_tokenize(t1)
    words2 = clean_and_tokenize(t2)
    common = words1 & words2

    for cluster in POLICY_CLUSTERS:
        has_1 = any(term in t1 for term in cluster)
        has_2 = any(term in t2 for term in cluster)
        if has_1 and has_2:
            # Require at least 2 common substantive words or ratio >= 0.50 to avoid false positives
            if len(common) >= 2 or SequenceMatcher(None, t1, t2).ratio() >= 0.50:
                return True, f"Matched subject cluster: {cluster[0]} with shared substantive context"

    # Rule 3: Asymmetric Substantive Word Containment
    # (dividing by min ensures a detailed version matches a concise version)
    if len(words1) > 0 and len(words2) > 0:
        containment = len(common) / min(len(words1), len(words2))
        if containment >= 0.55 and len(common) >= 4:
            return True, f"Word containment {containment:.2f} ({len(common)} shared substantive words)"

    # Rule 4: String Sequence Similarity (calibrated from 0.48 to 0.72 to prevent false positives)
    ratio = SequenceMatcher(None, t1, t2).ratio()
    if ratio >= 0.72:
        return True, f"SequenceMatcher ratio {ratio:.2f}"

    # Rule 5: Semantic Embedding Cosine Similarity (calibrated threshold)
    if emb_a and emb_b:
        try:
            sim = cosine_similarity(emb_a, emb_b)
            if sim >= 0.82:
                return True, f"Embedding similarity {sim:.2f}"
        except Exception:
            pass

    return False, "Not a duplicate"
