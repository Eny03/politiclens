import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.database import Base

class PoliticalParty(Base):
    __tablename__ = "political_parties"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True) # e.g. "FDI", "PD", "M5S", "LEGA", "FI", "AVS", "AZ", "IV", "PIUEU"
    name = Column(String(100), nullable=False, unique=True)
    coalition = Column(String(100), nullable=False) # "Centrodestra", "Centrosinistra", "Movimento 5 Stelle", "Centro / Civici", "Altro"
    leader = Column(String(100), nullable=True)
    color = Column(String(20), default="#3b82f6") # Hex color for UI representation
    official_website = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    dossier_ai = Column(Text, nullable=True)
    poll_percentage = Column(Float, default=0.0)
    poll_trend = Column(String(20), default="stabile")
    poll_sources = Column(String(255), default="Media YouTrend/AGI, SWG, Ipsos, Tecnè, Noto")
    truthfulness_score = Column(Float, default=0.0)
    financial_reliability_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    proposals = relationship("PoliticalProposal", back_populates="party_rel")

class PoliticalProposal(Base):
    __tablename__ = "political_proposals"

    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("political_parties.id"), nullable=True)
    partito = Column(String(100), index=True, nullable=False) # Normalized party name
    macro_argomento = Column(String(100), index=True, nullable=False) # "Economia", "Energia", "Ambiente", "Diritti Civili", "Esteri", "Lavoro", "Sanità", "Istruzione", etc.
    dichiarazione_sintesi = Column(Text, nullable=False)
    tipo_azione = Column(String(100), nullable=False) # "Proposta di legge", "Dichiarazione programmatica", "Opposizione", "Emendamento"
    
    # Impatto Economico
    costo_stimato = Column(String(100), default="Non quantificato")
    coperture_dichiarate = Column(Text, default="Non specificate")
    fattibilita_finanziaria = Column(Text, nullable=True)
    
    # Fact Check
    fact_check_status = Column(String(50), default="In attesa di copertura", index=True) # "Verificato", "Non verificabile", "Esagerato", "Fake / Infondato", "In attesa di copertura"
    fact_check_motivazione = Column(Text, nullable=True)
    fact_check_fonte = Column(String(500), nullable=True)
    truth_score = Column(Float, default=75.0) # Voto di veridicità a salti del 5% (0.0 to 100.0)
    
    # Metadata & Tracking
    fonte_url = Column(String(1000), nullable=False)
    fonte_titolo = Column(String(500), nullable=True)
    fonte_testata = Column(String(200), nullable=True) # e.g. "ANSA", "Il Sole 24 Ore", "Gazzetta Ufficiale", "Atti Parlamentari"
    raw_text = Column(Text, nullable=True)
    content_hash = Column(String(64), unique=True, index=True, nullable=True)
    
    # Semantic Search Embedding (Vector serialized as JSON string or pgvector)
    embedding = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    party_rel = relationship("PoliticalParty", back_populates="proposals")

class IngestionLog(Base):
    __tablename__ = "ingestion_logs"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(200), nullable=False)
    source_url = Column(String(1000), nullable=False)
    articles_found = Column(Integer, default=0)
    proposals_extracted = Column(Integer, default=0)
    status = Column(String(50), default="SUCCESS") # "SUCCESS", "PARTIAL", "FAILED"
    log_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class InstitutionalBenchmark(Base):
    __tablename__ = "institutional_benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String(100), nullable=False) # e.g. "Finanza Pubblica", "Sanità", "Occupazione", "Energia"
    indicatore = Column(String(200), nullable=False)
    valore = Column(Float, nullable=False)
    unita = Column(String(50), nullable=False) # e.g. "Miliardi €", "% PIL", "Unità", "%"
    fonte_istituzionale = Column(String(200), nullable=False) # "ISTAT", "Banca d'Italia", "Corte dei Conti", "Eurostat", "MEF"
    anno_riferimento = Column(Integer, nullable=False)
    descrizione = Column(Text, nullable=True)
    url_fonte = Column(String(500), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True) # "POLL_UPDATE", "PROPOSAL_CREATED", "PROPOSAL_UPDATED", "FACT_CHECK_AUDIT", "INGESTION_SCAN", "BENCHMARK_SYNC"
    entity_type = Column(String(50), nullable=False, index=True) # "party", "proposal", "benchmark", "source"
    entity_id = Column(String(100), nullable=True)
    entity_name = Column(String(255), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    agent_responsible = Column(String(100), nullable=False, default="System") # "PollTrackerAgent", "PolicyDistillerAgent", "FiscalAuditorAgent", "ReconciliationAgent", "System"
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class VisitorLog(Base):
    __tablename__ = "visitor_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(100), nullable=False, index=True)
    path = Column(String(500), nullable=False, index=True)
    method = Column(String(10), default="GET")
    user_agent = Column(String(500), nullable=True)
    device_type = Column(String(50), default="Desktop") # "Desktop", "Smartphone", "Tablet", "Bot / Crawler"
    browser = Column(String(100), default="Altro")       # "Google Chrome", "Mozilla Firefox", "Apple Safari", "Microsoft Edge", "Altro"
    os_name = Column(String(100), default="Sconosciuto") # "Windows", "macOS", "iOS", "Android", "Linux", "Sconosciuto"
    country = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)


