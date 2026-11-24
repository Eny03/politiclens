import re
import hashlib
from typing import List
import numpy as np

DIMENSION = 384

ITALIAN_STOPWORDS = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "a", "da", "in",
    "con", "su", "per", "tra", "fra", "del", "dello", "della", "dei", "degli", "delle",
    "al", "allo", "alla", "ai", "agli", "alle", "dal", "dallo", "dalla", "dai", "dagli", "dalle",
    "nel", "nello", "nella", "nei", "negli", "nelle", "sul", "sullo", "sulla", "sui", "sugli", "sulle",
    "e", "ed", "o", "od", "ma", "se", "che", "chi", "cui", "non", "piu", "più", "come", "anche",
    "sono", "stato", "stata", "stati", "state", "essere", "avere", "tutti", "tutte", "tutto",
    "questo", "questa", "questi", "queste", "quello", "quella", "ogni", "suo", "sua", "loro",
    "alla", "dalle", "nelle", "degli", "delle", "degli", "verso", "senza", "oltre", "fino", "circa"
}


def _stable_hash(s: str) -> int:
    """Computes stable 32-bit integer hash independent of Python process hash randomization."""
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)


def _normalize_vector(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm > 0:
        return vec / norm
    return vec


def _standardize_dimension(v: List[float], target_dim: int = DIMENSION) -> np.ndarray:
    """Standardizes any vector to target_dim (default 384) and applies L2 normalization."""
    if not v:
        return np.zeros(target_dim, dtype=np.float32)
    arr = np.array(v, dtype=np.float32)
    current_dim = len(arr)
    if current_dim == target_dim:
        return _normalize_vector(arr)

    x_old = np.linspace(0.0, 1.0, current_dim)
    x_new = np.linspace(0.0, 1.0, target_dim)
    resampled = np.interp(x_new, x_old, arr)
    return _normalize_vector(resampled)


def _local_deterministic_embedding(text: str, dim: int = DIMENSION) -> List[float]:
    """
    High-fidelity deterministic local text embedding generator (consistent 384-dim space).
    Uses stopword-filtered content words, word bigrams (e.g. 'salario_minimo', 'quota_41',
    'cuneo_fiscale'), signed random projection (Feature Hashing), and character trigrams
    for sharp Italian semantic retrieval and deduplication.
    """
    raw_words = re.findall(r"[a-zA-ZÀ-ÿ0-9]+", (text or "").lower())
    content_words = [w for w in raw_words if (len(w) > 2 or w.isdigit()) and w not in ITALIAN_STOPWORDS]
    if not content_words:
        content_words = raw_words

    vec = np.zeros(dim, dtype=np.float32)
    if not content_words:
        return vec.tolist()

    def _add_feature(feat: str, weight: float):
        h = _stable_hash(feat)
        idx = h % dim
        sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
        vec[idx] += sign * weight

    for i, word in enumerate(content_words):
        # 1. Word unigram (and 5-char stem prefix for Italian morphological variants)
        _add_feature(f"w:{word}", 1.2)
        if len(word) >= 6:
            _add_feature(f"s:{word[:5]}", 0.7)

        # 2. Consecutive content-word bigram (captures compound policy phrases)
        if i < len(content_words) - 1:
            _add_feature(f"bg:{word}_{content_words[i + 1]}", 1.5)

        # 3. Character trigrams on content words (morphological robustness without stopword noise)
        if len(word) >= 4:
            for j in range(len(word) - 2):
                _add_feature(f"c3:{word[j:j + 3]}", 0.25)

    vec = _normalize_vector(vec)
    return vec.tolist()


async def get_text_embedding(text: str) -> List[float]:
    """
    Returns consistent 384-dim text embedding aligned with the indexed database vector space.
    Using the unified deterministic feature-hashing space prevents cross-space mismatch
    between query vectors and seeded database embeddings.
    """
    return _local_deterministic_embedding(text, DIMENSION)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two vector lists."""
    if not v1 or not v2:
        return 0.0
    if len(v1) == DIMENSION and len(v2) == DIMENSION:
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
    else:
        a = _standardize_dimension(v1, DIMENSION)
        b = _standardize_dimension(v2, DIMENSION)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
