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
    """FIX SEC-03: enforces max 30 chat requests per minute per IP with periodic pruning to prevent memory growth."""
    client_ip = extract_client_ip(request)
    now = time.time()
    # Periodic cleanup when map grows large
    if len(_chat_rate_limits) > 500:
        stale_ips = [ip for ip, ts_list in _chat_rate_limits.items() if not any(now - t < RATE_LIMIT_WINDOW_SEC for t in ts_list)]
        for ip in stale_ips:
            _chat_rate_limits.pop(ip, None)

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

@router.get("/suggestions")
async def get_chat_suggestions():
    """Returns curated multi-mode starter prompts showcasing evolution, direct comparison, fact-check, polls & rankings."""
    return [
        {
            "title": "Evoluzione Salario Minimo",
            "query": "Come è cambiata la posizione del PD sul salario minimo dal 2023 ad oggi?",
            "mode": "comparativo"
        },
        {
            "title": "Lega & Quota 41 nel tempo",
            "query": "Come si è evoluta la proposta di Quota 41 della Lega dal 2022 al presente?",
            "mode": "comparativo"
        },
        {
            "title": "FdI vs PD su Fisco & Flat Tax",
            "query": "Quali sono le differenze tra Fratelli d'Italia e il PD su cuneo fiscale e Flat Tax?",
            "mode": "confronto_diretto"
        },
        {
            "title": "Classifica Veridicità & Coperture",
            "query": "Quali partiti hanno il punteggio più alto di veridicità e coperture finanziarie MEF?",
            "mode": "fact_check"
        },
        {
            "title": "Ultimi Sondaggi Elettorali",
            "query": "Quali sono gli ultimi sondaggi elettorali aggiornati in Italia?",
            "mode": "comparativo"
        },
        {
            "title": "Verifica Pensioni Minime 1.000€",
            "query": "L'aumento delle pensioni minime a 1.000 euro ha coperture finanziarie certificate dalla Ragioneria Generale dello Stato?",
            "mode": "fact_check"
        },
        {
            "title": "Nucleare vs Rinnovabili",
            "query": "Come si posizionano i partiti italiani tra nucleare SMR e fonti rinnovabili?",
            "mode": "comparativo"
        },
        {
            "title": "Futuro Nazionale vs ORA!",
            "query": "Quali sono le posizioni distinte di Futuro Nazionale rispetto a ORA! su fisco e liberalizzazioni?",
            "mode": "confronto_diretto"
        }
    ]

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
