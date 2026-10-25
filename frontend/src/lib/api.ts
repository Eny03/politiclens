const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

export interface PoliticalParty {
  id: number;
  code: string;
  name: string;
  coalition: string;
  leader?: string;
  color: string;
  official_website?: string;
  description?: string;
  dossier_ai?: string;
  poll_percentage?: number;
  poll_trend?: string;
  poll_sources?: string;
  truthfulness_score?: number;
  financial_reliability_score?: number;
  proposals_count: number;
}

export interface AIDossierPillar {
  tema: string;
  proposta_chiave: string;
  tipo_azione: string;
  costo: string;
  coperture: string;
  status_verifica: string;
  motivazione: string;
  fonte_url: string;
  fonte_testata: string;
}

export interface AIDossierQuote {
  data: string;
  titolo: string;
  dichiarazione: string;
  fonte: string;
  url: string;
}

export interface AIDossierData {
  partito_nome: string;
  partito_codice: string;
  coalizione: string;
  leader?: string;
  sintesi_strategica: string;
  evoluzione_storica_legislatura?: { periodo: string; sintesi: string }[];
  punti_di_forza?: string;
  criticita_osservatorio?: string;
  score_affidabilita: string;
  statistiche_atti: {
    totale_atti: number;
    verificati: number;
    in_attesa_copertura: number;
    esagerati_o_non_quantificati: number;
  };
  pilastri_programmatici: AIDossierPillar[];
  valutazione_finanziaria: {
    score_fattibilita: string;
    atti_quantificati: string;
    impegno_economico_stimato?: string;
    analisi_coperture: string;
  };
  dichiarazioni_recenti_web: AIDossierQuote[];
  parametri_macro_confronto: Record<string, string>;
  ultimo_aggiornamento_web: string;
}

export interface PoliticalProposal {
  id: number;
  party_id?: number;
  partito: string;
  macro_argomento: string;
  dichiarazione_sintesi: string;
  tipo_azione: string;
  costo_stimato: string;
  coperture_dichiarate: string;
  fattibilita_finanziaria?: string;
  fact_check_status: string;
  fact_check_motivazione?: string;
  fact_check_fonte?: string;
  truth_score?: number;
  fonte_url: string;
  fonte_titolo?: string;
  fonte_testata?: string;
  raw_text?: string;
  timestamp: string;
  created_at: string;
  party_color?: string;
}

export interface ComparisonCell {
  partito: string;
  party_color: string;
  proposals: PoliticalProposal[];
  sintesi_posizione: string;
  stance_type: string;
}

export interface TopicComparisonRow {
  macro_argomento: string;
  argomento_dettaglio?: string;
  parties: Record<string, ComparisonCell>;
}

export interface ComparisonMatrixResponse {
  macro_argomenti: string[];
  partiti: PoliticalParty[];
  matrix: TopicComparisonRow[];
}

export interface CitationItem {
  partito: string;
  macro_argomento: string;
  sintesi: string;
  fonte_titolo?: string;
  fonte_testata?: string;
  fonte_url: string;
  timestamp: string;
  fact_check_status: string;
}

export interface ChatQueryResponse {
  answer: string;
  neutrality_disclaimer: string;
  mode: string;
  citations: CitationItem[];
}

export interface InstitutionalBenchmark {
  id: number;
  categoria: string;
  indicatore: string;
  valore: number;
  unita: string;
  fonte_istituzionale: string;
  anno_riferimento: number;
  descrizione?: string;
  url_fonte?: string;
}

export interface PartyRankingItem {
  name: string;
  code: string;
  color: string;
  coalition: string;
  leader?: string;
  poll_percentage: number;
  poll_trend: string;
  truthfulness_score: number;
  truthfulness_tier?: { min_score: number; tier: string; label: string; desc: string };
  financial_reliability_score: number;
  proposals_count: number;
}

export interface StatsOverview {
  total_proposals: number;
  total_parties: number;
  total_sources_monitored: number;
  proposals_by_party: Record<string, number>;
  proposals_by_topic: Record<string, number>;
  fact_check_distribution: Record<string, number>;
  quantified_cost_percentage: number;
  average_truthfulness?: number;
  average_financial_feasibility?: number;
  coalition_truthfulness?: Record<string, number>;
  party_rankings?: PartyRankingItem[];
  truth_thresholds?: Array<{ min_score: number; tier: string; label: string; desc: string }>;
  last_ingestion_time?: string;
  last_poll_time?: string;
  benchmarks_summary: InstitutionalBenchmark[];
}

export interface IngestionLog {
  id: number;
  source_name: string;
  source_url: string;
  articles_found: number;
  proposals_extracted: number;
  status: string;
  log_message?: string;
  timestamp: string;
}

export async function fetchStatsOverview(): Promise<StatsOverview> {
  const res = await fetch(`${API_BASE_URL}/api/stats/overview`, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero delle statistiche generali");
  return res.json();
}

export async function fetchComparisonMatrix(): Promise<ComparisonMatrixResponse> {
  const res = await fetch(`${API_BASE_URL}/api/comparison/matrix`, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero della matrice di comparazione");
  return res.json();
}

export async function fetchParties(): Promise<PoliticalParty[]> {
  const res = await fetch(`${API_BASE_URL}/api/parties`, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero dei partiti");
  return res.json();
}

export async function fetchPartyDetail(partyCodeOrId: string | number) {
  const res = await fetch(`${API_BASE_URL}/api/parties/${partyCodeOrId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero del dossier del partito");
  return res.json();
}

export async function fetchProposals(params?: {
  party?: string;
  topic?: string;
  status?: string;
  action_type?: string;
  year?: number;
  search?: string;
  limit?: number;
}): Promise<PoliticalProposal[]> {
  const query = new URLSearchParams();
  if (params?.party) query.set("party", params.party);
  if (params?.topic) query.set("topic", params.topic);
  if (params?.status) query.set("status", params.status);
  if (params?.action_type) query.set("action_type", params.action_type);
  if (params?.year) query.set("year", params.year.toString());
  if (params?.search) query.set("search", params.search);
  if (params?.limit) query.set("limit", params.limit.toString());

  const res = await fetch(`${API_BASE_URL}/api/proposals?${query.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero delle proposte");
  return res.json();
}

export async function sendChatMessage(body: {
  question: string;
  mode?: string;
  filter_party?: string;
  filter_macro_argomento?: string;
}): Promise<ChatQueryResponse> {
  const res = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Errore nella risposta del chatbot neutrale");
  return res.json();
}

export async function fetchMonitoredSources(): Promise<any[]> {
  const res = await fetch(`${API_BASE_URL}/api/ingestion/sources`, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero delle fonti");
  return res.json();
}

export async function fetchIngestionLogs(): Promise<IngestionLog[]> {
  const res = await fetch(`${API_BASE_URL}/api/ingestion/logs`, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero dei log di ingestion");
  return res.json();
}

export async function triggerFeedScan(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/ingestion/trigger`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Errore nell'avvio della scansione");
  return res.json();
}

export async function submitManualIngest(data: {
  url?: string;
  raw_text?: string;
  title?: string;
}): Promise<PoliticalProposal[]> {
  const res = await fetch(`${API_BASE_URL}/api/ingestion/manual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Errore nell'estrazione e ingestion manuale");
  return res.json();
}

export interface SchedulerStatus {
  is_active: boolean;
  interval_minutes: number;
  interval_seconds?: number;
  frequency: string;
  server_time?: string;
  next_run_time?: string;
}

export async function fetchBenchmarks(): Promise<InstitutionalBenchmark[]> {
  const res = await fetch(`${API_BASE_URL}/api/stats/benchmarks`, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero dei parametri istituzionali");
  return res.json();
}

export async function fetchSchedulerStatus(): Promise<SchedulerStatus> {
  const res = await fetch(`${API_BASE_URL}/api/ingestion/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero dello stato dello scheduler");
  return res.json();
}

export interface InformationGap {
  party_name: string;
  party_code: string;
  topic: string;
  gap_score: number;
  existing_count: number;
  reason: string;
  queries: string[];
}

export async function fetchDetectedGaps(limit: number = 100, party?: string): Promise<InformationGap[]> {
  try {
    const url = party 
      ? `${API_BASE_URL}/api/ingestion/gaps?limit=${limit}&party=${encodeURIComponent(party)}`
      : `${API_BASE_URL}/api/ingestion/gaps?limit=${limit}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch (e) {
    return [];
  }
}

export interface AuditLog {
  id: number;
  event_type: string;
  entity_type: string;
  entity_id?: string;
  entity_name: string;
  old_value?: string;
  new_value?: string;
  agent_responsible: string;
  details?: string;
  timestamp: string;
}

export interface AuditStats {
  total: number;
  aggiunta: number;
  modifica: number;
  cancellazione: number;
  sondaggi: number;
}

export interface AuditListResponse {
  total: number;
  logs: AuditLog[];
  event_types: string[];
  agents: string[];
  stats?: AuditStats;
}

export async function fetchAuditLogs(params?: {
  event_type?: string;
  agent?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditListResponse> {
  const query = new URLSearchParams();
  if (params?.event_type && params.event_type !== "Tutti") query.append("event_type", params.event_type);
  if (params?.agent && params.agent !== "Tutti") query.append("agent", params.agent);
  if (params?.search) query.append("search", params.search);
  if (params?.limit) query.append("limit", params.limit.toString());
  if (params?.offset) query.append("offset", params.offset.toString());

  const url = `${API_BASE_URL}/api/audit/logs${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Errore nel recupero del registro di audit");
  return res.json();
}

export async function triggerPollUpdate(): Promise<{ status: string; message: string; updated_parties: any[] }> {
  const res = await fetch(`${API_BASE_URL}/api/parties/update-polls`, {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  });
  if (!res.ok) throw new Error("Errore nell'aggiornamento dei sondaggi elettorali");
  return res.json();
}



