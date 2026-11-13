import time
from typing import Dict, List
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ChatQueryRequest, ChatQueryResponse
from app.ai.rag_engine import answer_rag_query, stream_rag_query
from app.ai.llm_provider import llm_provider
from app.api.admin import extract_client_ip

router = APIRouter(prefix="/api/chat", tags=["Chatbot RAG Neutrale"])

# In-memory rate limiting to protect LLM endpoints against flooding/DDoS
_chat_rate_limits: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW_SEC = 60.0
MAX_CHAT_REQUESTS_PER_MIN = 30

def enforce_chat_rate_limit(request: Request):
    """FIX SEC-03: enforces max 30 chat requests per minute per IP to protect LLM quota."""
    client_ip = extract_client_ip(request)
    now = time.time()
    timestamps = _chat_rate_limits.setdefault(client_ip, [])
    valid_timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW_SEC]
    if len(valid_timestamps) >= MAX_CHAT_REQUESTS_PER_MIN:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite di frequenza raggiunto: massimo 30 domande al minuto per client. Riprova tra poco."
        )
    valid_timestamps.append(now)
    _chat_rate_limits[client_ip] = valid_timestamps

@router.get("/provider")
async def get_active_provider():
    """Returns active AI provider details (Ollama, Groq, Gemini, or Institutional Offline)."""
    return await llm_provider.get_active_provider_info()

@router.post("", response_model=ChatQueryResponse)
async def chat_with_politiclens(req: ChatQueryRequest, request: Request, db: Session = Depends(get_db)):
    """
    Standard non-streaming RAG-powered conversational endpoint.
    Retrieves evidence from indexed proposals and generates an encyclopedic, strictly neutral comparative response with citations.
    """
    enforce_chat_rate_limit(request)
    return await answer_rag_query(req, db)

@router.post("/stream")
async def chat_with_politiclens_stream(req: ChatQueryRequest, request: Request, db: Session = Depends(get_db)):
    """
    Real-time Token-by-Token Streaming SSE endpoint with Inspection Steps:
    - event: step (retrieval, fiscal check, neutrality balancing)
    - event: citations (sources and fact-check cards)
    - event: token (real-time stream of tokens)
    - event: done (completion signal)
    """
    enforce_chat_rate_limit(request)
    return StreamingResponse(
        stream_rag_query(req, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
