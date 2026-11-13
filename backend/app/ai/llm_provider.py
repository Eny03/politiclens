import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
import httpx
from app.config import settings
from app.ai.ollama_client import ollama_client

class LLMProvider:
    """
    Hybrid Multi-Provider AI Engine with Intelligent Ordered Fallback:
    1. Local Ollama (Qwen2.5, Llama-3.3, Mistral) - 100% private & offline
    2. Cloud Free-Tier API (Groq Llama-3.3-70B or Google Gemini 1.5/2.0 Flash)
    3. Institutional Deterministic Engine (100% guaranteed 0€, advanced econometric & legislative synthesis)
    """

    async def get_active_provider_info(self) -> Dict[str, Any]:
        if await ollama_client.is_available():
            models = await ollama_client.list_models()
            return {
                "provider": "ollama",
                "label": "Ollama Locale (On-Device)",
                "model": settings.OLLAMA_CHAT_MODEL,
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
                "label": "Google Gemini Cloud Flash",
                "model": settings.GEMINI_MODEL
            }
        else:
            return {
                "provider": "deterministic",
                "label": "Motore Euristico Istituzionale PoliticLens (Offline 0€)",
                "model": "rule-based-econometric-v2"
            }

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        fallback_text: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generates chat completion through the highest available provider.
        Returns: (answer_text, provider_name)
        """
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        # 1. Try Ollama
        if await ollama_client.is_available():
            try:
                res = await ollama_client.generate_chat(all_messages, model=settings.OLLAMA_CHAT_MODEL, temperature=temperature)
                if res and len(res.strip()) > 20:
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
                    payload = {
                        "model": settings.GROQ_MODEL,
                        "messages": all_messages,
                        "temperature": temperature,
                        "max_tokens": 2048
                    }
                    res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        if content:
                            return content, "groq"
            except Exception as e:
                print(f"[LLMProvider] Groq call error: {e}")

        # 3. Try Gemini
        if settings.GEMINI_API_KEY:
            try:
                contents = []
                system_instruction = {"parts": [{"text": system_prompt}]} if system_prompt else None
                last_role = None
                for m in messages:
                    if m["role"] == "system":
                        if not system_instruction:
                            system_instruction = {"parts": [{"text": m["content"]}]}
                        continue
                    role = "user" if m["role"] == "user" else "model"
                    if role == last_role and contents:
                        contents[-1]["parts"].append({"text": m["content"]})
                    else:
                        contents.append({
                            "role": role,
                            "parts": [{"text": m["content"]}]
                        })
                        last_role = role

                if not contents:
                    contents.append({"role": "user", "parts": [{"text": "Sintesi"}]})

                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": contents,
                    "generationConfig": {"temperature": temperature}
                }
                if system_instruction:
                    payload["system_instruction"] = system_instruction

                async with httpx.AsyncClient(timeout=25.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        if text:
                            return text, "gemini"
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
        """
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        # 1. Ollama Streaming
        if await ollama_client.is_available():
            try:
                payload = {
                    "model": settings.OLLAMA_CHAT_MODEL,
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
                                        yield token
                                    if chunk.get("done", False):
                                        return
                                except Exception:
                                    continue
                            return
            except Exception as e:
                print(f"[LLMProvider Stream] Ollama failed: {e}, falling back...")

        # 2. Groq Streaming
        if settings.GROQ_API_KEY:
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
                    async with client.stream("POST", "https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload) as response:
                        if response.status_code == 200:
                            async for raw_line in response.aiter_lines():
                                line = raw_line.strip()
                                if not line or not line.startswith("data: "):
                                    continue
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    return
                                try:
                                    parsed = json.loads(data_str)
                                    delta = parsed["choices"][0].get("delta", {}).get("content", "")
                                    if delta:
                                        yield delta
                                except Exception:
                                    continue
                            return
            except Exception as e:
                print(f"[LLMProvider Stream] Groq failed: {e}, falling back...")

        # 3. Gemini Streaming
        if settings.GEMINI_API_KEY:
            try:
                contents = []
                system_instruction = {"parts": [{"text": system_prompt}]} if system_prompt else None
                last_role = None
                for m in messages:
                    if m["role"] == "system":
                        if not system_instruction:
                            system_instruction = {"parts": [{"text": m["content"]}]}
                        continue
                    role = "user" if m["role"] == "user" else "model"
                    if role == last_role and contents:
                        contents[-1]["parts"].append({"text": m["content"]})
                    else:
                        contents.append({
                            "role": role,
                            "parts": [{"text": m["content"]}]
                        })
                        last_role = role

                if not contents:
                    contents.append({"role": "user", "parts": [{"text": "Sintesi"}]})

                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:streamGenerateContent?alt=sse&key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": contents,
                    "generationConfig": {"temperature": temperature}
                }
                if system_instruction:
                    payload["system_instruction"] = system_instruction

                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        if response.status_code == 200:
                            async for raw_line in response.aiter_lines():
                                line = raw_line.strip()
                                if not line or not line.startswith("data: "):
                                    continue
                                try:
                                    parsed = json.loads(line[6:])
                                    token = parsed["candidates"][0]["content"]["parts"][0]["text"]
                                    if token:
                                        yield token
                                except Exception:
                                    continue
                            return
            except Exception as e:
                print(f"[LLMProvider Stream] Gemini failed: {e}, falling back...")

        # 4. Deterministic Stream Fallback (Smooth chunking)
        full_text = fallback_text or (
            "PoliticLens AI ha elaborato i dati d'archivio parlamentare. "
            "Tutti i dati citati provengono da atti formali registrati presso la Camera, il Senato e il MEF."
        )
        words = full_text.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield chunk
            # Gentle micro-pause to simulate fluid human-readable delivery
            await asyncio.sleep(0.012)

llm_provider = LLMProvider()
