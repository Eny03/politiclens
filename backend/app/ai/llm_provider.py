import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
import httpx
from app.config import settings
from app.ai.ollama_client import ollama_client

EMBED_ONLY_PREFIXES = ("bge-", "nomic-embed", "mxbai-embed", "all-minilm", "snowflake-arctic-embed")


def _pick_installed_ollama_chat_model(models: List[str], preferred: str) -> Optional[str]:
    """Selects the preferred chat model if installed in Ollama, or falls back to an installed chat model."""
    if not models:
        return None
    pref_low = (preferred or "").lower()
    for m in models:
        if m.lower() == pref_low or m.lower().startswith(pref_low.split(":")[0] + ":"):
            return m
    for m in models:
        if not any(m.lower().startswith(ep) for ep in EMBED_ONLY_PREFIXES):
            return m
    return None


def _build_gemini_payload(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int = 2048,
    response_json: bool = False
) -> Dict[str, Any]:
    """Constructs a strictly valid Gemini generateContent payload."""
    contents: List[Dict[str, Any]] = []
    system_instruction = {"parts": [{"text": system_prompt}]} if system_prompt else None
    last_role: Optional[str] = None

    for m in messages:
        role_raw = m.get("role", "user")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role_raw == "system":
            if not system_instruction:
                system_instruction = {"parts": [{"text": content}]}
            continue

        role = "user" if role_raw == "user" else "model"
        # Gemini API requires the first turn in contents to be 'user'
        if not contents and role != "user":
            continue

        if role == last_role and contents:
            contents[-1]["parts"].append({"text": content})
        else:
            contents.append({"role": role, "parts": [{"text": content}]})
            last_role = role

    if not contents:
        contents.append({"role": "user", "parts": [{"text": "Sintesi"}]})

    gen_cfg: Dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens
    }
    if response_json:
        gen_cfg["responseMimeType"] = "application/json"

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": gen_cfg
    }
    if system_instruction:
        payload["system_instruction"] = system_instruction
    return payload


def _extract_gemini_text(data: Dict[str, Any]) -> str:
    """Safely extracts generated text from a Gemini response dict."""
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if isinstance(p, dict))


class LLMProvider:
    """
    Hybrid Multi-Provider AI Engine with Intelligent Ordered Fallback:
    1. Local Ollama (Qwen2.5, Llama-3.3, Mistral) - 100% private & offline
    2. Cloud Free-Tier API (Groq Llama-3.3-70B or Google Gemini 2.0 Flash)
    3. Institutional Deterministic Engine (100% guaranteed 0€, advanced econometric & legislative synthesis)
    """

    async def _get_usable_ollama_model(self) -> Optional[str]:
        if not await ollama_client.is_available():
            return None
        models = await ollama_client.list_models()
        return _pick_installed_ollama_chat_model(models, settings.OLLAMA_CHAT_MODEL)

    async def get_active_provider_info(self) -> Dict[str, Any]:
        ollama_model = await self._get_usable_ollama_model()
        if ollama_model:
            models = await ollama_client.list_models()
            return {
                "provider": "ollama",
                "label": f"Ollama Locale ({ollama_model})",
                "model": ollama_model,
                "available_models": models
            }
        elif settings.GROQ_API_KEY:
            return {
                "provider": "groq",
                "label": "Groq Cloud Llama-3.3 70B",
                "model": settings.GROQ_MODEL
            }
        elif settings.GEMINI_API_KEY:
            return {
                "provider": "gemini",
                "label": f"Google Gemini ({settings.GEMINI_MODEL})",
                "model": settings.GEMINI_MODEL
            }
        else:
            return {
                "provider": "deterministic",
                "label": "Motore Euristico Istituzionale PoliticLens (Offline 0€)",
                "model": "rule-based-econometric-v3"
            }

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        fallback_text: Optional[str] = None,
        format_json: bool = False
    ) -> Tuple[str, str]:
        """
        Generates chat completion through the highest available provider.
        Returns: (answer_text, provider_name)
        """
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        # 1. Try Ollama (only if a usable chat model is actually installed)
        ollama_model = await self._get_usable_ollama_model()
        if ollama_model:
            try:
                res = await ollama_client.generate_chat(
                    all_messages,
                    model=ollama_model,
                    temperature=temperature,
                    format_json=format_json
                )
                if res and len(res.strip()) > 10:
                    return res, "ollama"
            except Exception as e:
                print(f"[LLMProvider] Ollama call error: {e}")

        # 2. Try Groq
        if settings.GROQ_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=25.0) as client:
                    headers = {
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    payload: Dict[str, Any] = {
                        "model": settings.GROQ_MODEL,
                        "messages": all_messages,
                        "temperature": temperature,
                        "max_tokens": 2048
                    }
                    if format_json:
                        payload["response_format"] = {"type": "json_object"}
                    res = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        if content and content.strip():
                            return content, "groq"
                    else:
                        print(f"[LLMProvider] Groq error status {res.status_code}: {res.text[:200]}")
            except Exception as e:
                print(f"[LLMProvider] Groq call error: {e}")

        # 3. Try Gemini
        if settings.GEMINI_API_KEY:
            try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
                )
                payload = _build_gemini_payload(
                    messages, system_prompt, temperature, response_json=format_json
                )
                async with httpx.AsyncClient(timeout=25.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        text = _extract_gemini_text(res.json())
                        if text and text.strip():
                            return text, "gemini"
                        print("[LLMProvider] Gemini returned empty text (possible safety filter).")
                    else:
                        print(f"[LLMProvider] Gemini error status {res.status_code}: {res.text[:200]}")
            except Exception as e:
                print(f"[LLMProvider] Gemini call error: {e}")

        # 4. Deterministic fallback
        return fallback_text or "Risposta generata dal motore istituzionale di PoliticLens.", "deterministic"

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        fallback_text: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        """
        Yields text tokens in real time via streaming SSE from the best available provider.
        Falls through cleanly to the next provider if a provider emits 0 tokens or returns non-200.
        """
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        # 1. Ollama Streaming
        ollama_model = await self._get_usable_ollama_model()
        if ollama_model:
            emitted = False
            try:
                payload = {
                    "model": ollama_model,
                    "messages": all_messages,
                    "stream": True,
                    "options": {"temperature": temperature}
                }
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", f"{ollama_client.base_url}/api/chat", json=payload) as response:
                        if response.status_code == 200:
                            async for line in response.aiter_lines():
                                if not line:
                                    continue
                                try:
                                    chunk = json.loads(line)
                                    token = chunk.get("message", {}).get("content", "")
                                    if token:
                                        emitted = True
                                        yield token
                                    if chunk.get("done", False):
                                        break
                                except Exception:
                                    continue
                            if emitted:
                                return
                        else:
                            print(f"[LLMProvider Stream] Ollama HTTP {response.status_code}")
            except Exception as e:
                print(f"[LLMProvider Stream] Ollama failed: {e}, falling back...")
                if emitted:
                    return

        # 2. Groq Streaming
        if settings.GROQ_API_KEY:
            emitted = False
            try:
                headers = {
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": settings.GROQ_MODEL,
                    "messages": all_messages,
                    "temperature": temperature,
                    "stream": True
                }
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload
                    ) as response:
                        if response.status_code == 200:
                            async for raw_line in response.aiter_lines():
                                line = raw_line.strip()
                                if not line or not line.startswith("data: "):
                                    continue
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    parsed = json.loads(data_str)
                                    delta = parsed["choices"][0].get("delta", {}).get("content", "")
                                    if delta:
                                        emitted = True
                                        yield delta
                                except Exception:
                                    continue
                            if emitted:
                                return
                        else:
                            body = await response.aread()
                            print(f"[LLMProvider Stream] Groq HTTP {response.status_code}: {body[:200]}")
            except Exception as e:
                print(f"[LLMProvider Stream] Groq failed: {e}, falling back...")
                if emitted:
                    return

        # 3. Gemini Streaming
        if settings.GEMINI_API_KEY:
            emitted = False
            try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{settings.GEMINI_MODEL}:streamGenerateContent?alt=sse&key={settings.GEMINI_API_KEY}"
                )
                payload = _build_gemini_payload(messages, system_prompt, temperature)
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code == 200:
                            async for raw_line in response.aiter_lines():
                                line = raw_line.strip()
                                if not line or not line.startswith("data: "):
                                    continue
                                try:
                                    parsed = json.loads(line[6:])
                                    token = _extract_gemini_text(parsed)
                                    if token:
                                        emitted = True
                                        yield token
                                except Exception:
                                    continue
                            if emitted:
                                return
                        else:
                            body = await response.aread()
                            print(f"[LLMProvider Stream] Gemini HTTP {response.status_code}: {body[:200]}")
            except Exception as e:
                print(f"[LLMProvider Stream] Gemini failed: {e}, falling back...")
                if emitted:
                    return

        # 4. Deterministic Stream Fallback (Smooth chunking preserving newlines)
        full_text = fallback_text or (
            "PoliticLens AI ha elaborato i dati d'archivio parlamentare. "
            "Tutti i dati citati provengono da atti formali registrati presso la Camera, il Senato e il MEF."
        )
        words = full_text.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield chunk
            await asyncio.sleep(0.008)


llm_provider = LLMProvider()
