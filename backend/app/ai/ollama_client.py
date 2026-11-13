import json
import time
import asyncio
from typing import Optional, Dict, Any, List
import httpx
from app.config import settings

class OllamaClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._cached_available: Optional[bool] = None
        self._last_check_time: float = 0
        self._lock: Optional[asyncio.Lock] = None
        
    async def is_available(self) -> bool:
        """Checks if local Ollama server is running and reachable (cached for 60s, thread-safe with asyncio.Lock)."""
        now = time.time()
        if self._cached_available is not None and (now - self._last_check_time) < 60:
            return self._cached_available

        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            # Double check inside lock to prevent redundant HTTP probes
            now = time.time()
            if self._cached_available is not None and (now - self._last_check_time) < 60:
                return self._cached_available

            try:
                async with httpx.AsyncClient(timeout=0.6) as client:
                    res = await client.get(f"{self.base_url}/api/tags")
                    self._cached_available = (res.status_code == 200)
            except Exception:
                self._cached_available = False

            self._last_check_time = now
            return self._cached_available

    async def list_models(self) -> List[str]:
        """Returns list of installed local models in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        format_json: bool = False
    ) -> Optional[str]:
        """
        Calls Ollama chat endpoint with specified messages.
        Supports structured JSON mode if format_json is True.
        """
        selected_model = model or settings.OLLAMA_EXTRACTION_MODEL
        payload: Dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if format_json:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("message", {}).get("content", "")
                else:
                    print(f"[OllamaClient] HTTP error {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[OllamaClient] Request failed: {e}")
        return None

    async def get_embedding(self, text: str, model: Optional[str] = None) -> Optional[List[float]]:
        """Calls Ollama embeddings endpoint."""
        embed_model = model or settings.OLLAMA_EMBED_MODEL
        payload = {
            "model": embed_model,
            "prompt": text
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                if res.status_code == 200:
                    return res.json().get("embedding")
        except Exception as e:
            print(f"[OllamaClient] Embedding failed: {e}")
        return None

ollama_client = OllamaClient()
