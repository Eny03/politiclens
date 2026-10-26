import os
from typing import Optional
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "PoliticLens"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./politiclens.db")
    
    # Local LLM / Ollama settings (100% open-source)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EXTRACTION_MODEL: str = os.getenv("OLLAMA_EXTRACTION_MODEL", "qwen2.5:14b")
    OLLAMA_CHAT_MODEL: str = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:14b")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")

    # Cloud Free-Tier LLM Providers
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Ingestion & Scheduler (Scansione e aggiornamento continuo ogni 10 minuti)
    INGESTION_INTERVAL_MINUTES: int = int(os.getenv("INGESTION_INTERVAL_MINUTES", "10"))
    MAX_ARTICLES_PER_FEED: int = int(os.getenv("MAX_ARTICLES_PER_FEED", "5"))
    ENABLE_AUTO_SCHEDULER: bool = os.getenv("ENABLE_AUTO_SCHEDULER", "true").lower() == "true"
    
    # Admin & Device Access Control (Solo da questo PC)
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "politiclens-admin-2026-pc")
    
    # Benchmark Parameters (Italia / ISTAT / MEF / Eurostat 2024-2025)
    PIL_NOMINALE_MLD: float = 2120.0        # ~2.120 Mld €
    DEBITO_PUBBLICO_MLD: float = 2950.0     # ~2.950 Mld € (~139% PIL)
    ENTRATE_TRIBUTARIE_MLD: float = 585.0   # ~585 Mld €
    SPESA_SANITARIA_SSN_MLD: float = 136.5  # ~136.5 Mld € (~6.4% PIL)
    SPESA_ISTRUZIONE_MLD: float = 78.0      # ~78 Mld € (~3.7% PIL)
    SPESA_DIFESA_MLD: float = 32.0          # ~32 Mld € (~1.5% PIL)
    MANOVRA_BILANCIO_MEDIA_MLD: float = 30.0 # ~30 Mld € annuali manovra tipica

settings = Settings()
