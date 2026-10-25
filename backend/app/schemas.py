from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_serializer

# Core sub-schemas matching Mission Brief Section 4.B
class ImpattoEconomicoSchema(BaseModel):
    costo_stimato: str = Field(default="Non quantificato", description="Cifra in € o 'Non quantificato'")
    coperture_dichiarate: str = Field(default="Non specificate", description="Da dove il partito intende prendere i fondi")
    fattibilita_finanziaria: str = Field(default="", description="Analisi oggettiva basata su vincoli di bilancio / PIL")

class FactCheckSchema(BaseModel):
    status: str = Field(default="In attesa di copertura", description="Verificato | Non verificabile | Esagerato | Fake / Infondato | In attesa di copertura")
    motivazione_oggettiva: str = Field(default="", description="Perché è bollata come fake o inattuabile (dati ISTAT, Eurostat, Corte dei Conti)")
    fonte_verifica: str = Field(default="", description="Link o riferimento istituzionale")

class ProposalExtractionSchema(BaseModel):
    partito: str = Field(description="Nome Partito")
    macro_argomento: str = Field(description="Economia | Energia | Ambiente | Diritti Civili | Esteri | Lavoro | Sanità | Istruzione")
    dichiarazione_sintesi: str = Field(description="Sintesi neutrale della proposta o presa di posizione")
    tipo_azione: str = Field(description="Proposta di legge | Dichiarazione programmatica | Opposizione | Emendamento")
    impatto_economico: ImpattoEconomicoSchema
    fact_check: FactCheckSchema
    fonte_url: str = Field(description="URL dell'articolo/documento")
    timestamp: str = Field(description="ISO 8601 timestamp")

# Response Schemas
class PoliticalPartySchema(BaseModel):
    id: int
    code: str
    name: str
    coalition: str
    leader: Optional[str] = None
    color: str
    official_website: Optional[str] = None
    description: Optional[str] = None
    dossier_ai: Optional[str] = None
    poll_percentage: Optional[float] = 0.0
    poll_trend: Optional[str] = "stabile"
    poll_sources: Optional[str] = "Media YouTrend/AGI, SWG, Ipsos, Tecnè, Noto"
    truthfulness_score: Optional[float] = 0.0
    financial_reliability_score: Optional[float] = 0.0
    proposals_count: Optional[int] = 0

    class Config:
        from_attributes = True

class PoliticalProposalDetail(BaseModel):
    id: int
    party_id: Optional[int] = None
    partito: str
    macro_argomento: str
    dichiarazione_sintesi: str
    tipo_azione: str
    costo_stimato: str
    coperture_dichiarate: str
    fattibilita_finanziaria: Optional[str] = None
    fact_check_status: str
    fact_check_motivazione: Optional[str] = None
    fact_check_fonte: Optional[str] = None
    fonte_url: str
    fonte_titolo: Optional[str] = None
    fonte_testata: Optional[str] = None
    raw_text: Optional[str] = None
    timestamp: datetime
    created_at: datetime
    party_color: Optional[str] = None

    class Config:
        from_attributes = True

class ComparisonCell(BaseModel):
    partito: str
    party_color: str
    proposals: List[PoliticalProposalDetail]
    sintesi_posizione: str
    stance_type: str # "Favorevole / Riformista", "Contrario / Opposizione", "Focalizzato su Coperture", "Neutro / Misto"

class TopicComparisonRow(BaseModel):
    macro_argomento: str
    argomento_dettaglio: Optional[str] = None
    parties: Dict[str, ComparisonCell]

class ComparisonMatrixResponse(BaseModel):
    macro_argomenti: List[str]
    partiti: List[PoliticalPartySchema]
    matrix: List[TopicComparisonRow]

# Head-to-Head AI Synthesis
class HeadToHeadSynthesisRequest(BaseModel):
    party1: str
    party2: str
    topic: Optional[str] = None

class HeadToHeadSynthesisResponse(BaseModel):
    party1: str
    party2: str
    topic: Optional[str] = None
    executive_summary: str
    convergences: List[str]
    divergences: List[str]
    cost_comparison: Dict[str, Any]
    proposals_party1: List[str]
    proposals_party2: List[str]
    institutional_verdict: str

# Chatbot RAG Schemas
class ChatMessage(BaseModel):
    role: str # "user" | "assistant" | "system"
    content: str

class ChatQueryRequest(BaseModel):
    question: str
    mode: Optional[str] = "comparativo" # "comparativo" | "confronto_diretto" | "fact_check"
    filter_party: Optional[str] = None
    filter_macro_argomento: Optional[str] = None
    history: Optional[List[ChatMessage]] = []

class CitationItem(BaseModel):
    partito: str
    macro_argomento: str
    sintesi: str
    fonte_titolo: Optional[str] = None
    fonte_testata: Optional[str] = None
    fonte_url: str
    timestamp: str
    fact_check_status: str

class ChatQueryResponse(BaseModel):
    answer: str
    neutrality_disclaimer: str
    mode: str
    citations: List[CitationItem]

# Ingestion & Feeds
class IngestionRequest(BaseModel):
    url: Optional[str] = None
    source_type: Optional[str] = "custom" # "custom" | "rss"
    raw_text: Optional[str] = None
    title: Optional[str] = None

class IngestionLogSchema(BaseModel):
    id: int
    source_name: str
    source_url: str
    articles_found: int
    proposals_extracted: int
    status: str
    log_message: Optional[str] = None
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True

# Institutional Benchmarks
class InstitutionalBenchmarkSchema(BaseModel):
    id: int
    categoria: str
    indicatore: str
    valore: float
    unita: str
    fonte_istituzionale: str
    anno_riferimento: int
    descrizione: Optional[str] = None
    url_fonte: Optional[str] = None

    class Config:
        from_attributes = True

# Dashboard Stats
class StatsOverviewResponse(BaseModel):
    total_proposals: int
    total_parties: int
    total_sources_monitored: int
    proposals_by_party: Dict[str, int]
    proposals_by_topic: Dict[str, int]
    fact_check_distribution: Dict[str, int]
    quantified_cost_percentage: float
    average_truthfulness: float = 0.0
    average_financial_feasibility: float = 0.0
    coalition_truthfulness: Dict[str, float] = {}
    party_rankings: List[Dict[str, Any]] = []
    truth_thresholds: List[Dict[str, Any]] = []
    last_ingestion_time: Optional[datetime] = None
    last_poll_time: Optional[str] = None
    benchmarks_summary: List[InstitutionalBenchmarkSchema]

# Audit Trail & Modification Changelog
class AuditLogSchema(BaseModel):
    id: int
    event_type: str
    entity_type: str
    entity_id: Optional[str] = None
    entity_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    agent_responsible: str
    details: Optional[str] = None
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True

class AuditStatsSchema(BaseModel):
    total: int
    aggiunta: int
    modifica: int
    cancellazione: int
    sondaggi: int

class AuditListResponse(BaseModel):
    total: int
    logs: List[AuditLogSchema]
    event_types: List[str]
    agents: List[str]
    stats: Optional[AuditStatsSchema] = None

