"use client";

import React, { useEffect, useState } from "react";
import { 
  Rss, 
  RefreshCw, 
  Play, 
  FileCode, 
  ExternalLink, 
  CheckCircle2, 
  AlertCircle, 
  Send,
  Shield,
  Layers,
  Database,
  Target,
  Sparkles,
  Search,
  Scale,
  Cpu
} from "lucide-react";
import { 
  fetchMonitoredSources, 
  fetchIngestionLogs, 
  fetchDetectedGaps,
  triggerFeedScan, 
  submitManualIngest,
  IngestionLog,
  PoliticalProposal,
  InformationGap
} from "@/lib/api";
import { formatItalianDateTime } from "@/lib/dateUtils";
import { StatusBadge } from "@/components/StatusBadge";
import { ProposalCard } from "@/components/ProposalCard";

interface MultiAgentStep {
  id: number;
  name: string;
  desc: string;
  status: "waiting" | "active" | "completed";
}

const INITIAL_STEPS: MultiAgentStep[] = [
  { id: 1, name: "1. Scouting & Text Cleaning", desc: "Estrazione testo, rimozione HTML e filtraggio polemiche", status: "waiting" },
  { id: 2, name: "2. Policy Distillation", desc: "Enunciazione proposta di legge e scorporo gossip", status: "waiting" },
  { id: 3, name: "3. Fiscal Audit (MEF/ISTAT)", desc: "Verifica coperture, stima oneri e clausole art. 81 Cost.", status: "waiting" },
  { id: 4, name: "4. Reconciliation & Embedding", desc: "Deduplicazione semantica e normalizzazione vettoriale L2 384d", status: "waiting" },
];

export default function SourcesPage() {
  const [sources, setSources] = useState<any[]>([]);
  const [logs, setLogs] = useState<IngestionLog[]>([]);
  const [gaps, setGaps] = useState<InformationGap[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [selectedGapParty, setSelectedGapParty] = useState<string>("Tutti");
  const [showAllGaps, setShowAllGaps] = useState<boolean>(true);

  // Manual ingest form state
  const [manualUrl, setManualUrl] = useState("");
  const [manualTitle, setManualTitle] = useState("");
  const [manualText, setManualText] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [extractedProposals, setExtractedProposals] = useState<PoliticalProposal[]>([]);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [agentSteps, setAgentSteps] = useState<MultiAgentStep[]>(INITIAL_STEPS);

  const loadData = async () => {
    try {
      setLoading(true);
      const [srcs, lgs, gps] = await Promise.all([
        fetchMonitoredSources(),
        fetchIngestionLogs(),
        fetchDetectedGaps(100)
      ]);
      setSources(srcs);
      setLogs(lgs);
      setGaps(gps);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTriggerScan = async () => {
    try {
      setIsScanning(true);
      setScanMessage(null);
      await triggerFeedScan();
      setScanMessage("Scansione continua dei feed avviata in background! I nuovi articoli vengono processati dal Consensus Multi-AI.");
      setTimeout(() => {
        loadData();
      }, 3000);
    } catch (err: any) {
      setScanMessage("Errore nell'avvio della scansione.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualText.trim() && !manualUrl.trim()) return;

    try {
      setExtracting(true);
      setExtractError(null);
      setExtractedProposals([]);

      // Step 1: Scouting & Cleaning
      setAgentSteps([
        { ...INITIAL_STEPS[0], status: "active" },
        { ...INITIAL_STEPS[1], status: "waiting" },
        { ...INITIAL_STEPS[2], status: "waiting" },
        { ...INITIAL_STEPS[3], status: "waiting" },
      ]);

      const step1Timer = setTimeout(() => {
        setAgentSteps([
          { ...INITIAL_STEPS[0], status: "completed" },
          { ...INITIAL_STEPS[1], status: "active" },
          { ...INITIAL_STEPS[2], status: "waiting" },
          { ...INITIAL_STEPS[3], status: "waiting" },
        ]);
      }, 500);

      const step2Timer = setTimeout(() => {
        setAgentSteps([
          { ...INITIAL_STEPS[0], status: "completed" },
          { ...INITIAL_STEPS[1], status: "completed" },
          { ...INITIAL_STEPS[2], status: "active" },
          { ...INITIAL_STEPS[3], status: "waiting" },
        ]);
      }, 1000);

      const step3Timer = setTimeout(() => {
        setAgentSteps([
          { ...INITIAL_STEPS[0], status: "completed" },
          { ...INITIAL_STEPS[1], status: "completed" },
          { ...INITIAL_STEPS[2], status: "completed" },
          { ...INITIAL_STEPS[3], status: "active" },
        ]);
      }, 1500);

      const result = await submitManualIngest({
        url: manualUrl || undefined,
        title: manualTitle || undefined,
        raw_text: manualText || undefined,
      });

      clearTimeout(step1Timer);
      clearTimeout(step2Timer);
      clearTimeout(step3Timer);

      setAgentSteps([
        { ...INITIAL_STEPS[0], status: "completed" },
        { ...INITIAL_STEPS[1], status: "completed" },
        { ...INITIAL_STEPS[2], status: "completed" },
        { ...INITIAL_STEPS[3], status: "completed" },
      ]);

      setExtractedProposals(result);
      loadData();
    } catch (err: any) {
      setExtractError("Errore durante l'estrazione: " + (err.message || "Verificare il testo inserito"));
      setAgentSteps(INITIAL_STEPS);
    } finally {
      setExtracting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* Page Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300 mb-2">
            <Rss className="w-3.5 h-3.5" />
            <span>Centro Ingestion & Multi-Agent Consensus</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
            Monitoraggio Fonti, Ingestion & Trasparenza
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Scansione autonoma continua 24/7 di tutto il web: agenzie di stampa (ANSA, Sole 24 Ore, Rai), canali dei partiti, atti parlamentari e fact-checking finanziario.
          </p>
        </div>
      </div>

      {scanMessage && (
        <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300 text-xs font-medium flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0" />
          <span>{scanMessage}</span>
        </div>
      )}

      {/* Active Information Gap Targets */}
      {gaps.length > 0 && (() => {
        const uniqueParties = Array.from(new Set(gaps.map((g) => g.party_name))).sort();
        const filteredGaps = selectedGapParty === "Tutti"
          ? (showAllGaps ? gaps : gaps.slice(0, 8))
          : gaps.filter((g) => g.party_name === selectedGapParty);

        const totalZeros = gaps.filter((g) => g.existing_count === 0).length;
        const totalMinimal = gaps.filter((g) => g.existing_count > 0).length;

        return (
          <section className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/60 flex items-center justify-center text-blue-600 dark:text-blue-400 border border-blue-200/60 dark:border-blue-900/60 shrink-0">
                  <Target className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 flex-wrap">
                    <span>Radar di Ricerca Continua dell'AI (Active Gap Hunter)</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                      Auto-Learning Web
                    </span>
                    {totalZeros > 0 ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300">
                        {totalZeros} vuoti assoluti in ricerca
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                        100% temi presidiati
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
                      {gaps.length} target di approfondimento attivo
                    </span>
                  </h2>
                  <p className="text-xs text-slate-500">
                    Questo è il radar con cui l'AI scandaglia autonomamente Google News e DuckDuckGo ogni 10-30 min per individuare nuovi atti parlamentari e arricchire i temi a copertura minima.
                  </p>
                </div>
              </div>

              {/* Controls: Filter by party & View Toggle */}
              <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
                <select
                  value={selectedGapParty}
                  onChange={(e) => setSelectedGapParty(e.target.value)}
                  className="px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-hidden"
                >
                  <option value="Tutti">Tutti i partiti ({gaps.length})</option>
                  {uniqueParties.map((p) => {
                    const cnt = gaps.filter((g) => g.party_name === p).length;
                    return (
                      <option key={p} value={p}>
                        {p} ({cnt})
                      </option>
                    );
                  })}
                </select>

                {selectedGapParty === "Tutti" && gaps.length > 8 && (
                  <button
                    type="button"
                    onClick={() => setShowAllGaps(!showAllGaps)}
                    className="px-3 py-1.5 rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/60 hover:bg-blue-100 dark:hover:bg-blue-900/60 text-xs font-semibold text-blue-700 dark:text-blue-300 transition-colors cursor-pointer"
                  >
                    {showAllGaps ? "Mostra solo priorità (8)" : `Mostra tutte (${gaps.length})`}
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
              {filteredGaps.map((g, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 text-xs space-y-1.5 hover:border-blue-300 dark:hover:border-blue-800 transition-colors"
                >
                  <div className="flex items-center justify-between text-[11px] font-bold text-blue-600 dark:text-blue-400">
                    <span>{g.party_name}</span>
                    <span className="text-slate-400 font-normal">{g.topic}</span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                    {g.reason}
                  </p>
                  <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-200/50 dark:border-slate-700/50 flex items-center justify-between">
                    <span>Posizioni censite: <strong>{g.existing_count}</strong></span>
                    <span className="text-[9px] uppercase font-bold text-amber-600 dark:text-amber-400">Target Attivo</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        );
      })()}

      {/* Main Grid: Sources List vs Manual Ingestion Tool */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Monitored Sources */}
        <div className="lg:col-span-5 space-y-4">
          <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Rss className="w-4 h-4 text-orange-500" />
            <span>Fonti Istituzionali & Press Monitorate ({sources.length})</span>
          </h2>

          <div className="space-y-2.5 max-h-[550px] overflow-y-auto pr-1">
            {sources.map((src, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span>{src.name}</span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    Categoria: <strong>{src.category}</strong> • Affidabilità: {src.reliability}
                  </div>
                </div>
                <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  Live
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Ingest & Multi-Agent Consensus Extraction Tool */}
        <div className="lg:col-span-7 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-6 shadow-xs space-y-5">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <FileCode className="w-4 h-4 text-indigo-500" />
              <span>Estrazione Schematizzata Diretta (Multi-Agent Consensus)</span>
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Inserisci un articolo o comunicato stampa per attivare i 4 step del consenso: Scouting, Distillazione, Audit MEF ed Embedding.
            </p>
          </div>

          <form onSubmit={handleManualSubmit} className="space-y-3.5">
            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                URL Articolo o Comunicato (Opzionale se inserisci il testo)
              </label>
              <input
                type="url"
                placeholder="https://..."
                value={manualUrl}
                onChange={(e) => setManualUrl(e.target.value)}
                className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2.5 text-slate-900 dark:text-slate-100 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Titolo Notizia / Dichiarazione Formale
              </label>
              <input
                type="text"
                placeholder="es. Proposta di legge su salario minimo e sgravi fiscali..."
                value={manualTitle}
                onChange={(e) => setManualTitle(e.target.value)}
                className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2.5 text-slate-900 dark:text-slate-100 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Testo Integrale dell'Articolo o Proposta
              </label>
              <textarea
                rows={4}
                placeholder="Incolla qui il testo dell'articolo o comunicato per avviare l'analisi multi-agente..."
                value={manualText}
                onChange={(e) => setManualText(e.target.value)}
                className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-2.5 text-slate-900 dark:text-slate-100 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* VISUAL 4-STEP MULTI-AGENT PROGRESS INDICATOR */}
            {(extracting || agentSteps.some(s => s.status === "completed")) && (
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/80 space-y-2.5">
                <div className="text-xs font-bold text-slate-900 dark:text-white flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-blue-500" />
                    <span>Avanzamento Consenso Multi-Agente AI:</span>
                  </span>
                  {extracting && (
                    <span className="text-[10px] text-blue-600 dark:text-blue-400 animate-pulse font-semibold">
                      In elaborazione...
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  {agentSteps.map((step) => (
                    <div
                      key={step.id}
                      className={`p-2.5 rounded-xl border transition-all flex items-start gap-2 ${
                        step.status === "completed"
                          ? "bg-emerald-50/70 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200"
                          : step.status === "active"
                          ? "bg-blue-50/70 dark:bg-blue-950/30 border-blue-400 dark:border-blue-600 text-blue-900 dark:text-blue-200 shadow-xs"
                          : "bg-white/50 dark:bg-slate-900/40 border-slate-200/60 dark:border-slate-800 text-slate-400"
                      }`}
                    >
                      <div className="shrink-0 mt-0.5">
                        {step.status === "completed" ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                        ) : step.status === "active" ? (
                          <div className="w-4 h-4 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-slate-300 dark:border-slate-700" />
                        )}
                      </div>
                      <div>
                        <div className="font-bold text-[11px] leading-snug">{step.name}</div>
                        <div className="text-[10px] opacity-80 leading-tight mt-0.5">{step.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {extractError && (
              <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{extractError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={extracting || (!manualText.trim() && !manualUrl.trim())}
              className="inline-flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white shadow-md disabled:opacity-50 transition-all"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{extracting ? "Analisi Multi-Agente in corso..." : "Estrai, Valuta e Integra nel Database"}</span>
            </button>
          </form>

          {/* Extracted Results Showcase */}
          {extractedProposals.length > 0 && (
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold text-xs uppercase tracking-wider">
                <CheckCircle2 className="w-4 h-4" />
                <span>{extractedProposals.length} Posizione/i estratta/e e verificate dall'AI!</span>
              </div>
              <div className="space-y-3">
                {extractedProposals.map((p) => (
                  <ProposalCard key={p.id} proposal={p} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Ingestion Transparency Audit Logs */}
      <section className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-6 shadow-xs space-y-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
          <Shield className="w-4 h-4 text-emerald-500" />
          <span>Registro di Controllo e Trasparenza delle Scansioni (Audit Log)</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">
                <th className="p-3 font-semibold">Data & Ora</th>
                <th className="p-3 font-semibold">Sorgente Monitorata</th>
                <th className="p-3 font-semibold">Articoli Analizzati</th>
                <th className="p-3 font-semibold">Posizioni Estratte</th>
                <th className="p-3 font-semibold">Stato</th>
                <th className="p-3 font-semibold">Note di Log</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                  <td className="p-3 font-mono text-slate-500">
                    {formatItalianDateTime(log.timestamp, true)}
                  </td>
                  <td className="p-3 font-semibold text-slate-900 dark:text-white">
                    {log.source_name}
                  </td>
                  <td className="p-3 font-mono">{log.articles_found}</td>
                  <td className="p-3 font-mono font-bold text-blue-600 dark:text-blue-400">
                    {log.proposals_extracted}
                  </td>
                  <td className="p-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${
                        log.status === "SUCCESS"
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                          : "bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
                      }`}
                    >
                      {log.status}
                    </span>
                  </td>
                  <td className="p-3 text-slate-500 max-w-xs truncate">
                    {log.log_message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
