"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Layers, 
  ArrowLeftRight, 
  Search, 
  ExternalLink,
  Building2,
  Calendar,
  CheckCircle2,
  Coins,
  ChevronRight,
  Filter,
  Sparkles,
  Info,
  Download,
  Maximize2,
  Minimize2,
  TrendingUp,
  Scale,
  FileSpreadsheet,
  AlertCircle
} from "lucide-react";
import { 
  fetchComparisonMatrix, 
  fetchParties, 
  ComparisonMatrixResponse, 
  PoliticalParty,
  PoliticalProposal
} from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { TopicBadge } from "@/components/TopicBadge";

interface HeadToHeadSynthesis {
  party1: string;
  party2: string;
  topic?: string;
  executive_summary: string;
  convergences: string[];
  divergences: string[];
  cost_comparison: {
    party1_name: string;
    party1_total_mld: number;
    party1_quantified_count: number;
    party2_name: string;
    party2_total_mld: number;
    party2_quantified_count: number;
    ratio_summary: string;
    compliance_mef: string;
  };
  proposals_party1: string[];
  proposals_party2: string[];
  institutional_verdict: string;
}

export default function ComparePage() {
  const [matrixData, setMatrixData] = useState<ComparisonMatrixResponse | null>(null);
  const [parties, setParties] = useState<PoliticalParty[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [selectedTopic, setSelectedTopic] = useState<string>("Tutti");
  const [selectedCoalition, setSelectedCoalition] = useState<string>("Tutte");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [viewMode, setViewMode] = useState<"head-to-head" | "matrix">("head-to-head");
  const [isCompactView, setIsCompactView] = useState<boolean>(false);

  // Head-to-Head selection
  const [partyA, setPartyA] = useState<string>("Fratelli d'Italia");
  const [partyB, setPartyB] = useState<string>("Partito Democratico");
  const [synthesis, setSynthesis] = useState<HeadToHeadSynthesis | null>(null);
  const [loadingSynthesis, setLoadingSynthesis] = useState<boolean>(false);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [matrix, partiesList] = await Promise.all([
          fetchComparisonMatrix(),
          fetchParties()
        ]);
        setMatrixData(matrix);
        setParties(partiesList);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Fetch AI Head-to-Head synthesis whenever partyA, partyB or selectedTopic changes
  useEffect(() => {
    if (!partyA || !partyB || partyA === partyB) return;
    
    let isCancelled = false;
    async function loadSynthesis() {
      try {
        setLoadingSynthesis(true);
        const queryTopic = selectedTopic !== "Tutti" ? selectedTopic : undefined;
        const res = await fetch("/api/comparison/head-to-head-synthesis", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            party1: partyA,
            party2: partyB,
            topic: queryTopic
          })
        });
        if (res.ok && !isCancelled) {
          const data = await res.json();
          setSynthesis(data);
        }
      } catch (e) {
        console.warn("Could not fetch head to head synthesis:", e);
      } finally {
        if (!isCancelled) setLoadingSynthesis(false);
      }
    }

    loadSynthesis();
    return () => { isCancelled = true; };
  }, [partyA, partyB, selectedTopic]);

  const defaultMacroTopics = [
    "Tutti",
    "Fisco",
    "Lavoro",
    "Sanità",
    "Pensioni",
    "Energia",
    "Istituzioni",
    "Immigrazione",
    "Istruzione",
    "Infrastrutture",
    "Politica Estera",
    "Diritti Civili"
  ];
  const macroTopics = matrixData?.macro_argomenti?.length ? ["Tutti", ...matrixData.macro_argomenti] : defaultMacroTopics;

  // Filter parties by coalition
  const filteredParties = parties.filter((p) => {
    if (selectedCoalition === "Tutte") return true;
    return p.coalition.toLowerCase().includes(selectedCoalition.toLowerCase());
  });

  // Filter matrix rows by topic & search
  const filteredRows = matrixData?.matrix.filter((row) => {
    if (selectedTopic !== "Tutti" && row.macro_argomento !== selectedTopic) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const topicMatches = row.macro_argomento.toLowerCase().includes(q);
      const contentMatches = Object.values(row.parties).some((c) =>
        c.sintesi_posizione.toLowerCase().includes(q) ||
        c.proposals?.some(p => p.dichiarazione_sintesi.toLowerCase().includes(q))
      );
      return topicMatches || contentMatches;
    }
    return true;
  });

  // Export Matrix to CSV
  const handleExportCSV = () => {
    if (!matrixData) return;
    const headers = ["Macro-Argomento", ...parties.map(p => `"${p.name}"`)];
    const rows: string[] = [headers.join(",")];

    for (const row of matrixData.matrix) {
      const rowCols = [`"${row.macro_argomento}"`];
      for (const p of parties) {
        const cell = row.parties[p.name];
        const text = cell?.proposals?.map(pr => pr.dichiarazione_sintesi).join(" | ") || "Nessun atto censito";
        rowCols.push(`"${text.replace(/"/g, '""')}"`);
      }
      rows.push(rowCols.join(","));
    }

    const csvContent = "\uFEFF" + rows.join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `politiclens_manifesto_comparativo_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 w-full max-w-full min-w-0">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5 w-full min-w-0">
        <div className="min-w-0 flex-1">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 mb-2">
            <Layers className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Manifesto Comparativo Indipendente</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
            Confronto Programmi & Sintesi Strategica AI
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Confronta le proposte dei partiti su ciascun tema, calcola convergenze, divergenze e stima dei relativi costi finanziari.
          </p>
        </div>

        {/* View Switcher Tabs & Matrix Controls */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full lg:w-auto shrink-0">
          {/* Main Segmented Toggle */}
          <div className="grid grid-cols-2 p-1 bg-slate-200/70 dark:bg-slate-800 rounded-xl w-full sm:w-auto">
            <button
              onClick={() => setViewMode("head-to-head")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all text-center ${
                viewMode === "head-to-head"
                  ? "bg-white dark:bg-slate-900 text-slate-950 dark:text-white shadow-xs"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <ArrowLeftRight className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
              <span>Testa a Testa</span>
              <span className="hidden xl:inline">(2 Forze)</span>
            </button>
            <button
              onClick={() => setViewMode("matrix")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center justify-center transition-all text-center ${
                viewMode === "matrix"
                  ? "bg-white dark:bg-slate-900 text-slate-950 dark:text-white shadow-xs"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <span>Matrice 18 Partiti</span>
            </button>
          </div>

          {/* Matrix Controls (Compact toggle + CSV Export) */}
          {viewMode === "matrix" && (
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <button
                onClick={() => setIsCompactView(!isCompactView)}
                className="flex-1 sm:flex-initial px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors flex items-center justify-center gap-1.5 border border-slate-200 dark:border-slate-700"
                title="Attiva/disattiva visuale compatta"
              >
                {isCompactView ? <Maximize2 className="w-3.5 h-3.5 shrink-0" /> : <Minimize2 className="w-3.5 h-3.5 shrink-0" />}
                <span>{isCompactView ? "Espandi" : "Compatta"}</span>
              </button>

              <button
                onClick={handleExportCSV}
                className="flex-1 sm:flex-initial px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/60 dark:hover:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 transition-colors flex items-center justify-center gap-1.5 shadow-2xs"
                title="Esporta matrice in CSV / Excel"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 shrink-0" />
                <span>Esporta CSV</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Quick Macro-Topic Pills - Wraps on Desktop PC and Mobile */}
      <div className="w-full max-w-full min-w-0 flex flex-wrap items-center gap-1.5 pb-1">
        {macroTopics.map((topic) => {
          const isSelected = selectedTopic === topic;
          return (
            <button
              key={topic}
              onClick={() => setSelectedTopic(topic)}
              className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                isSelected
                  ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-2xs font-bold"
                  : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800"
              }`}
            >
              {topic}
            </button>
          );
        })}
      </div>

      {/* Search Input */}
      <div className="relative">
        <input
          type="text"
          placeholder="Cerca un argomento o parola chiave (es. salario minimo, flat tax, nucleare, sanità, premierato)..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full text-xs sm:text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-blue-500 shadow-2xs"
        />
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery("")}
            className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-slate-600 font-semibold"
          >
            Cancella
          </button>
        )}
      </div>

      {loading ? (
        <div className="p-16 text-center text-xs text-slate-400 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 animate-pulse">
          Caricamento della matrice comparativa in corso...
        </div>
      ) : viewMode === "head-to-head" ? (
        /* Head-to-Head Comparison View */
        <div className="space-y-5 w-full max-w-full min-w-0">
          {/* Party Pickers Bar */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs w-full min-w-0">
            <div className="min-w-0">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: parties.find(p => p.name === partyA)?.color || "#3b82f6" }} />
                <span>Primo Partito:</span>
              </label>
              <select
                value={partyA}
                onChange={(e) => setPartyA(e.target.value)}
                className="w-full min-w-0 text-xs sm:text-sm font-semibold bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 rounded-xl p-2.5 text-slate-900 dark:text-slate-100 focus:outline-hidden truncate"
              >
                {parties.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name} ({p.coalition})
                  </option>
                ))}
              </select>
            </div>
            <div className="min-w-0">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: parties.find(p => p.name === partyB)?.color || "#ef4444" }} />
                <span>Secondo Partito:</span>
              </label>
              <select
                value={partyB}
                onChange={(e) => setPartyB(e.target.value)}
                className="w-full min-w-0 text-xs sm:text-sm font-semibold bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 rounded-xl p-2.5 text-slate-900 dark:text-slate-100 focus:outline-hidden truncate"
              >
                {parties.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name} ({p.coalition})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* AI STRATEGIC SYNTHESIS CARD */}
          <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-2xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2 min-w-0">
                <div className="p-1.5 rounded-xl bg-blue-600 text-white shadow-2xs shrink-0">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="font-bold text-sm sm:text-base text-slate-900 dark:text-white leading-snug">
                    Sintesi Strategica AI: {partyA} vs {partyB}
                  </h3>
                  <p className="text-[11px] text-slate-500 leading-tight">
                    Analisi autonoma di convergenze programmatiche, divergenze e rapporto economico
                  </p>
                </div>
              </div>

              {loadingSynthesis && (
                <div className="flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 font-medium shrink-0">
                  <div className="w-2 h-2 rounded-full bg-blue-600 animate-ping" />
                  <span>Elaborazione AI...</span>
                </div>
              )}
            </div>

            {synthesis && (
              <div className="space-y-4 text-xs sm:text-sm">
                <p className="text-slate-700 dark:text-slate-300 leading-relaxed break-words">
                  {synthesis.executive_summary}
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Convergences */}
                  <div className="p-4 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/70 dark:border-emerald-900/50 space-y-2 min-w-0">
                    <div className="flex items-center gap-1.5 font-bold text-emerald-900 dark:text-emerald-300">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
                      <span>Punti di Convergenza & Terreno Comune</span>
                    </div>
                    <ul className="space-y-1.5 text-xs text-emerald-950 dark:text-emerald-200">
                      {synthesis.convergences.map((c, i) => (
                        <li key={i} className="flex items-start gap-1.5 break-words">
                          <span className="text-emerald-500 font-bold shrink-0 mt-0.5">•</span>
                          <span>{c}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Divergences */}
                  <div className="p-4 rounded-xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200/70 dark:border-rose-900/50 space-y-2 min-w-0">
                    <div className="flex items-center gap-1.5 font-bold text-rose-900 dark:text-rose-300">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0" />
                      <span>Punti di Contrasto & Divergenze Primarie</span>
                    </div>
                    <ul className="space-y-1.5 text-xs text-rose-950 dark:text-rose-200">
                      {synthesis.divergences.map((d, i) => (
                        <li key={i} className="flex items-start gap-1.5 break-words">
                          <span className="text-rose-500 font-bold shrink-0 mt-0.5">•</span>
                          <span>{d}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Cost ratio comparison box */}
                <div className="p-3.5 rounded-xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/70 dark:border-amber-900/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                  <div className="flex items-start sm:items-center gap-2 min-w-0 flex-1">
                    <Coins className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5 sm:mt-0" />
                    <div className="min-w-0 flex-1 leading-snug">
                      <strong className="text-amber-950 dark:text-amber-200">Rapporto di Costo Comparato: </strong>
                      <span className="text-amber-900 dark:text-amber-300 font-mono break-words">
                        {synthesis.cost_comparison.ratio_summary}
                      </span>
                    </div>
                  </div>
                  <div className="text-[11px] text-amber-800 dark:text-amber-400 font-semibold shrink-0 pt-1 sm:pt-0">
                    {synthesis.cost_comparison.compliance_mef}
                  </div>
                </div>
              </div>
            )}
          </div>


          {/* Comparison Rows */}
          <div className="space-y-4">
            {filteredRows?.length === 0 ? (
              <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 text-xs text-slate-500">
                Nessun argomento trovato per i filtri selezionati.
              </div>
            ) : (
              filteredRows?.map((row) => {
                const cellA = row.parties[partyA];
                const cellB = row.parties[partyB];
                const propsA = cellA?.proposals || [];
                const propsB = cellB?.proposals || [];

                return (
                  <div
                    key={row.macro_argomento}
                    className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-2xs space-y-0"
                  >
                    {/* Topic Header Strip */}
                    <div className="bg-slate-50 dark:bg-slate-800/60 px-4 sm:px-6 py-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                      <TopicBadge topic={row.macro_argomento} />
                      <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                        {propsA.length} vs {propsB.length} misure censite
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-100 dark:divide-slate-800 p-4 sm:p-5 gap-4 sm:gap-6">
                      {/* Party A Column */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between pb-1">
                          <div className="flex items-center gap-2">
                            <span
                              className="w-2.5 h-2.5 rounded-full"
                              style={{ backgroundColor: cellA?.party_color || "#3b82f6" }}
                            />
                            <h4 className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white">
                              {partyA}
                            </h4>
                          </div>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                            {cellA?.stance_type}
                          </span>
                        </div>

                        {propsA.length === 0 ? (
                          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 text-[11px] text-slate-400">
                            Nessuna posizione formalizzata su questo tema.
                          </div>
                        ) : (
                          <div className="space-y-2.5">
                            {propsA.map((prop, pIdx) => (
                              <div
                                key={prop.id || pIdx}
                                className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 space-y-2"
                              >
                                <div className="flex items-center justify-between gap-1">
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                                    {prop.tipo_azione || "Proposta"}
                                  </span>
                                  <StatusBadge status={prop.fact_check_status} score={prop.truth_score} size="sm" />
                                </div>
                                <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                                  {prop.dichiarazione_sintesi}
                                </p>
                                <div className="flex flex-col gap-1 pt-1 border-t border-slate-200/60 dark:border-slate-700/60 text-[10px] text-slate-500">
                                  <div className="flex items-center justify-between gap-2">
                                    <span>Costo: <strong className="text-slate-800 dark:text-slate-200">{prop.costo_stimato}</strong></span>
                                    {prop.fonte_url && (
                                      <a
                                        href={prop.fonte_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-0.5"
                                      >
                                        <span>Fonte</span>
                                        <ExternalLink className="w-2.5 h-2.5" />
                                      </a>
                                    )}
                                  </div>
                                  {prop.coperture_dichiarate && (
                                    <div className="text-[10px] text-slate-500 leading-tight">
                                      Copertura: <span className="text-slate-700 dark:text-slate-300 font-medium">{prop.coperture_dichiarate}</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Party B Column */}
                      <div className="space-y-3 pt-4 md:pt-0">
                        <div className="flex items-center justify-between pb-1">
                          <div className="flex items-center gap-2">
                            <span
                              className="w-2.5 h-2.5 rounded-full"
                              style={{ backgroundColor: cellB?.party_color || "#ef4444" }}
                            />
                            <h4 className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white">
                              {partyB}
                            </h4>
                          </div>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                            {cellB?.stance_type}
                          </span>
                        </div>

                        {propsB.length === 0 ? (
                          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 text-[11px] text-slate-400">
                            Nessuna posizione formalizzata su questo tema.
                          </div>
                        ) : (
                          <div className="space-y-2.5">
                            {propsB.map((prop, pIdx) => (
                              <div
                                key={prop.id || pIdx}
                                className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 space-y-2"
                              >
                                <div className="flex items-center justify-between gap-1">
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                                    {prop.tipo_azione || "Proposta"}
                                  </span>
                                  <StatusBadge status={prop.fact_check_status} score={prop.truth_score} size="sm" />
                                </div>
                                <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                                  {prop.dichiarazione_sintesi}
                                </p>
                                <div className="flex flex-col gap-1 pt-1 border-t border-slate-200/60 dark:border-slate-700/60 text-[10px] text-slate-500">
                                  <div className="flex items-center justify-between gap-2">
                                    <span>Costo: <strong className="text-slate-800 dark:text-slate-200">{prop.costo_stimato}</strong></span>
                                    {prop.fonte_url && (
                                      <a
                                        href={prop.fonte_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-0.5"
                                      >
                                        <span>Fonte</span>
                                        <ExternalLink className="w-2.5 h-2.5" />
                                      </a>
                                    )}
                                  </div>
                                  {prop.coperture_dichiarate && (
                                    <div className="text-[10px] text-slate-500 leading-tight">
                                      Copertura: <span className="text-slate-700 dark:text-slate-300 font-medium">{prop.coperture_dichiarate}</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      ) : (
        /* Full Party Matrix View */
        <div className="space-y-4 w-full max-w-full min-w-0">
          <div className="w-full max-w-full min-w-0 flex items-center gap-1.5 overflow-x-auto pb-1.5 scrollbar-none">
            {["Tutte", "Centrodestra", "Centrosinistra", "Movimento 5 Stelle", "Centro / Liberaldemocratici", "Sinistra Radicale"].map((c) => (
              <button
                key={c}
                onClick={() => setSelectedCoalition(c)}
                className={`shrink-0 whitespace-nowrap px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  selectedCoalition === c
                    ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-2xs"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="space-y-4">
            {filteredRows?.map((row) => (
              <div
                key={row.macro_argomento}
                className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 sm:p-5 shadow-2xs space-y-3 w-full max-w-full min-w-0"
              >
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2.5">
                  <TopicBadge topic={row.macro_argomento} />
                  <span className="text-[11px] text-slate-500">
                    Confronto esteso forze politiche
                  </span>
                </div>

                <div className={`grid gap-2.5 ${isCompactView ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4" : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"}`}>
                  {filteredParties.map((party) => {
                    const cell = row.parties[party.name];
                    const hasProposals = cell && cell.proposals.length > 0;
                    if (!hasProposals) return null;

                    return (
                      <div
                        key={party.code}
                        className={`p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 flex flex-col justify-between min-w-0 ${isCompactView ? "space-y-1 text-[11px]" : "space-y-1.5 text-xs"}`}
                      >
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-1.5 font-bold text-slate-900 dark:text-white">
                              <span
                                className="w-2 h-2 rounded-full shrink-0"
                                style={{ backgroundColor: party.color }}
                              />
                              <span className="truncate">{party.name}</span>
                            </div>
                            <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 shrink-0">
                              {cell.proposals.length} {cell.proposals.length === 1 ? "atto" : "atti"}
                            </span>
                          </div>

                          {!isCompactView && (
                            <div className="space-y-1.5 pt-0.5">
                              {cell.proposals.slice(0, 2).map((p, idx) => (
                                <div key={idx} className="text-[11px] text-slate-700 dark:text-slate-300 leading-snug">
                                  • {p.dichiarazione_sintesi}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        <div className="pt-2 border-t border-slate-200/50 dark:border-slate-700/50 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[10px] text-slate-500 mt-2">
                          <span className="leading-tight">{cell.proposals[0]?.costo_stimato || "Non quantificato"}</span>
                          <StatusBadge status={cell.proposals[0]?.fact_check_status || "Verificato"} score={cell.proposals[0]?.truth_score} size="sm" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
