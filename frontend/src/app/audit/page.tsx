"use client";

import React, { useEffect, useState, useCallback } from "react";

import { 
  History, 
  Search, 
  Filter, 
  RefreshCw, 
  CheckCircle2, 
  TrendingUp, 
  FileText, 
  ShieldCheck, 
  Cpu, 
  Clock, 
  Scale, 
  ExternalLink,
  ChevronRight,
  Database,
  PlusCircle,
  Edit3,
  Trash2
} from "lucide-react";
import { fetchAuditLogs, triggerPollUpdate, AuditLog, AuditStats } from "@/lib/api";
import { formatItalianDateTime } from "@/lib/dateUtils";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [stats, setStats] = useState<AuditStats | null>(null);
  const [eventTypes, setEventTypes] = useState<string[]>([]);
  const [agents, setAgents] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Filters
  const [selectedEventType, setSelectedEventType] = useState<string>("Tutti");
  const [selectedAgent, setSelectedAgent] = useState<string>("Tutti");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Poll update trigger state
  const [updatingPolls, setUpdatingPolls] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadLogs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchAuditLogs({
        event_type: selectedEventType !== "Tutti" ? selectedEventType : undefined,
        agent: selectedAgent !== "Tutti" ? selectedAgent : undefined,
        search: searchQuery.trim() || undefined,
        limit: 100
      });
      setLogs(res.logs || []);
      setTotal(res.total || 0);
      if (res.stats) setStats(res.stats);
      if (res.event_types && res.event_types.length > 0) setEventTypes(res.event_types);
      if (res.agents && res.agents.length > 0) setAgents(res.agents);
    } catch (err) {
      console.error("Error loading audit logs:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedEventType, selectedAgent, searchQuery]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);


  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadLogs();
  };

  const handleRunPollSweep = async () => {
    try {
      setUpdatingPolls(true);
      setActionMessage(null);
      const res = await triggerPollUpdate();
      setActionMessage(res.message);
      await loadLogs();
    } catch (e: any) {
      setActionMessage("Errore durante l'aggiornamento dei sondaggi.");
    } finally {
      setUpdatingPolls(false);
    }
  };

  const getEventBadge = (type: string) => {
    const t = (type || "").toLowerCase();
    if (t === "aggiunta" || t === "proposal_created") {
      return {
        label: "Aggiunta",
        icon: <PlusCircle className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />,
        badgeClass: "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800"
      };
    }
    if (t === "modifica" || t === "proposal_updated" || t === "fact_check_audit") {
      return {
        label: "Modifica",
        icon: <Edit3 className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />,
        badgeClass: "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800"
      };
    }
    if (t === "cancellazione") {
      return {
        label: "Cancellazione",
        icon: <Trash2 className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />,
        badgeClass: "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800"
      };
    }
    if (t.includes("sondagg") || t.startsWith("poll")) {
      return {
        label: "Sondaggi aggiornati",
        icon: <TrendingUp className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />,
        badgeClass: "bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800"
      };
    }
    return {
      label: type,
      icon: <Scale className="w-3.5 h-3.5 text-slate-600" />,
      badgeClass: "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700"
    };
  };

  const aggiuntaCount = logs.filter(l => l.event_type.toLowerCase() === "aggiunta" || l.event_type.startsWith("PROPOSAL_CR")).length;
  const modificaCount = logs.filter(l => l.event_type.toLowerCase() === "modifica" || l.event_type.startsWith("PROPOSAL_UP") || l.event_type.startsWith("FACT")).length;
  const cancellazioneCount = logs.filter(l => l.event_type.toLowerCase() === "cancellazione").length;
  const pollCount = logs.filter(l => l.event_type.toLowerCase().includes("sondagg") || l.event_type.startsWith("POLL")).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
      {/* 1. Header (Airy & Clean Editorial Style) */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 mb-2">
            <History className="w-3.5 h-3.5" />
            <span>Trasparenza Civica & Audit Trail Algoritmico</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
            Registro di Tutte le Modifiche & Log Operazioni AI
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-3xl">
            Tracciamento trasparente e cronologico di ogni modifica: rilevazioni demoscopiche periodiche dei sondaggi, verifiche di sostenibilità economica e sintesi di nuovi atti e dichiarazioni in tempo reale.
          </p>
        </div>
      </div>

      {actionMessage && (
        <div className="p-3.5 rounded-xl bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800 text-xs text-blue-800 dark:text-blue-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button 
            onClick={() => setActionMessage(null)}
            className="text-xs font-bold text-blue-600 hover:underline"
          >
            Chiudi
          </button>
        </div>
      )}

      {/* 2. Micro Stats Overview Cards (5 Columns: Totale, Aggiunte, Modifiche, Cancellazioni, Sondaggi) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 sm:gap-4">
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-2xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Totale Operazioni</span>
          <span className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white mt-0.5 block">{stats?.total ?? total}</span>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Operazioni certificate</span>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-2xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Aggiunte a Programmi</span>
          <span className="text-xl sm:text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-0.5 block">{stats?.aggiunta ?? aggiuntaCount}</span>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Nuove proposte censite</span>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-2xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Modifiche o Rettifiche</span>
          <span className="text-xl sm:text-2xl font-black text-amber-600 dark:text-amber-400 mt-0.5 block">{stats?.modifica ?? modificaCount}</span>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Evoluzioni e coperture</span>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-2xs">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Cancellazioni</span>
          <span className="text-xl sm:text-2xl font-black text-rose-600 dark:text-rose-400 mt-0.5 block">{stats?.cancellazione ?? cancellazioneCount}</span>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Doppioni o testi rimossi</span>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-2xs col-span-2 sm:col-span-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">Sondaggi Aggiornati</span>
          <span className="text-xl sm:text-2xl font-black text-blue-600 dark:text-blue-400 mt-0.5 block">{stats?.sondaggi ?? pollCount}</span>
          <span className="text-[10px] text-slate-500 mt-0.5 block">1 unico log 18 partiti</span>
        </div>
      </div>

      {/* 3. Filter & Search Controls */}
      <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-2xs space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="Cerca nei log per partito, atto o motivazione..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs sm:text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 rounded-xl pl-9 pr-4 py-2.5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
            />
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            {searchQuery && (
              <button
                type="button"
                onClick={() => { setSearchQuery(""); loadLogs(); }}
                className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-slate-600 font-semibold"
              >
                Cancella
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="text-xs sm:text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-hidden font-medium"
            >
              <option value="Tutti">Tutti gli Agenti AI</option>
              {agents.map((ag) => (
                <option key={ag} value={ag}>
                  {ag}
                </option>
              ))}
            </select>

            <button
              type="submit"
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100 transition-colors shrink-0"
            >
              Filtra
            </button>
          </div>
        </form>

        {/* Event Type Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none pt-1">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1 shrink-0">
            Tipo Evento:
          </span>
          {["Tutti", "aggiunta", "modifica", "cancellazione", "sondaggi aggiornati"].map((evt) => {
            const isSelected = selectedEventType === evt;
            const badge = getEventBadge(evt);
            return (
              <button
                key={evt}
                onClick={() => setSelectedEventType(evt)}
                className={`px-3 py-1 rounded-full text-xs font-semibold shrink-0 transition-all ${
                  isSelected
                    ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-2xs"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200"
                }`}
              >
                {evt === "Tutti" ? "Tutti gli Eventi" : badge.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 4. Audit Log List (Anti-Overlap, Crisp Editorial Timeline) */}
      <div className="space-y-3">
        {loading ? (
          <div className="p-16 text-center text-xs text-slate-400 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 animate-pulse">
            Caricamento del registro di audit in corso...
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 space-y-2">
            <History className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto" />
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Nessuna modifica trovata</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Nessun log corrisponde ai criteri di ricerca selezionati. Prova a reimpostare i filtri.
            </p>
          </div>
        ) : (
          logs.map((log) => {
            const badge = getEventBadge(log.event_type);
            const formattedDate = formatItalianDateTime(log.timestamp, true);

            return (
              <article
                key={log.id}
                className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-4 sm:p-5 hover:border-slate-300 dark:hover:border-slate-700 transition-all shadow-2xs flex flex-col sm:flex-row sm:items-start justify-between gap-4"
              >
                <div className="space-y-2 min-w-0 flex-1">
                  {/* Event & Agent Header */}
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${badge.badgeClass}`}>
                      {badge.icon}
                      <span>{badge.label}</span>
                    </span>

                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200/70 dark:border-slate-700/70">
                      <Cpu className="w-3 h-3 text-slate-400" />
                      <span>{log.agent_responsible}</span>
                    </span>
                  </div>

                  {/* Entity Name */}
                  <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white leading-snug break-words">
                    {log.entity_name}
                  </h3>

                  {/* Value Transition (Old -> New) */}
                  {(log.old_value || log.new_value) && (
                    <div className="flex flex-wrap items-center gap-2 text-xs py-1">
                      {log.old_value && (
                        <div className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800/80 text-slate-500 line-through text-[11px]">
                          {log.old_value}
                        </div>
                      )}
                      {log.old_value && log.new_value && (
                        <span className="text-slate-400 font-bold">➔</span>
                      )}
                      {log.new_value && (
                        <div className="px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-200/70 dark:border-emerald-800/70 font-semibold text-[11px]">
                          {log.new_value}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Details Description */}
                  {log.details && (
                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed pt-0.5 break-words">
                      {log.details}
                    </p>
                  )}
                </div>

                {/* Timestamp & Meta */}
                <div className="shrink-0 flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-1 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400">
                    <Clock className="w-3 h-3 text-slate-400" />
                    <span>{formattedDate}</span>
                  </div>
                  <span className="text-[10px] font-semibold text-slate-400">
                    ID #{log.id}
                  </span>
                </div>
              </article>
            );
          })
        )}
      </div>
    </div>
  );
}
