import math
import re
import json
import hashlib
from typing import List, Dict, Any, Tuple
import numpy as np
from app.ai.ollama_client import ollama_client

DIMENSION = 384

def _stable_hash(s: str) -> int:
    """Computes stable 32-bit integer hash independent of Python process hash randomization."""
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)

def _normalize_vector(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm > 0:
        return vec / norm
    return vec

def _standardize_dimension(v: List[float], target_dim: int = DIMENSION) -> np.ndarray:
    """
    Standardizes any vector to target_dim (default 384) via linear resampling
    and applies L2 normalization. Handles mismatch between Ollama (e.g. 768, 1024)
    and deterministic (384) vectors.
    """
    if not v:
        return np.zeros(target_dim, dtype=np.float32)
    arr = np.array(v, dtype=np.float32)
    current_dim = len(arr)
    if current_dim == target_dim:
        return _normalize_vector(arr)
    
    # 1D linear interpolation across normalized domain [0, 1]
    x_old = np.linspace(0.0, 1.0, current_dim)
    x_new = np.linspace(0.0, 1.0, target_dim)
    resampled = np.interp(x_new, x_old, arr)
    return _normalize_vector(resampled)

def _local_deterministic_embedding(text: str, dim: int = DIMENSION) -> List[float]:
    """
    High-fidelity deterministic local text embedding generator.
    Creates a dense normalized vector based on single words, word bigrams, and character n-grams.
    FIX AI-09: includes consecutive word bigrams (e.g. 'salario minimo', 'quota 41', 'cuneo fiscale')
    for rich semantic phrase preservation.
    """
    clean_words = re.findall(r"\w+", text.lower())
    vec = np.zeros(dim, dtype=np.float32)
    
    if not clean_words:
        return vec.tolist()
        
    for i, word in enumerate(clean_words):
        # 1. Stable Word hash
        h = _stable_hash(word) % dim
        vec[h] += 1.0

        # 2. Word Bigram hash (pairs of consecutive words: key for compound policy phrases)
        if i < len(clean_words) - 1:
            w_bg = f"{word}_{clean_words[i+1]}"
            h_wbg = _stable_hash(w_bg) % dim
            vec[h_wbg] += 0.85

        # 3. Character bigram hashes (sub-word morphologic features)
        for j in range(len(word) - 1):
            bg = word[j:j+2]
            h_bg = (_stable_hash(bg) * 31) % dim
            vec[h_bg] += 0.4
            
    vec = _normalize_vector(vec)
    return vec.tolist()

async def get_text_embedding(text: str) -> List[float]:
    """
    Returns text embedding:
    Attempts local Ollama (bge-m3 / nomic-embed-text) first.
    If Ollama returns a vector of different dimension, standardizes to DIMENSION (384).
    Falls back gracefully to local deterministic vector if Ollama is not running.
    """
    if await ollama_client.is_available():
        emb = await ollama_client.get_embedding(text)
        if emb and len(emb) > 0:
            return _standardize_dimension(emb, DIMENSION).tolist()
            
    return _local_deterministic_embedding(text, DIMENSION)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Computes cosine similarity between two vector lists.
    FIX PERF-04: fast-path vector normalization without redundant interpolation
    when vectors are already of target DIMENSION.
    """
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
