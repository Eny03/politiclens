"use client";

import React, { useEffect, useState } from "react";
import { 
  ShieldCheck, 
  Coins, 
  AlertTriangle, 
  CheckCircle2, 
  AlertCircle, 
  XCircle, 
  Search, 
  BookOpen, 
  ExternalLink,
  Scale
} from "lucide-react";
import { fetchProposals, fetchBenchmarks, PoliticalProposal, InstitutionalBenchmark } from "@/lib/api";
import { ProposalCard } from "@/components/ProposalCard";
import { StatusBadge } from "@/components/StatusBadge";

export default function FactCheckPage() {
  const [proposals, setProposals] = useState<PoliticalProposal[]>([]);
  const [benchmarks, setBenchmarks] = useState<InstitutionalBenchmark[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("Tutti");
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [propsData, benchData] = await Promise.all([
          fetchProposals({ limit: 500 }),
          fetchBenchmarks()
        ]);
        setProposals(propsData);
        setBenchmarks(benchData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const statuses = [
    "Tutti",
    "Verificato",
    "Parzialmente verificato",
    "Posizione programmatica",
    "In attesa di copertura",
    "Esagerato",
    "Inattuabile",
    "Fake / Infondato"
  ];

  const statusCounts: Record<string, number> = { Tutti: proposals.length };
  for (const p of proposals) {
    const key = (p.fact_check_status || "").trim().toLowerCase();
    statusCounts[key] = (statusCounts[key] || 0) + 1;
  }

  const filteredProposals = proposals.filter((p) => {
    if (statusFilter !== "Tutti") {
      if ((p.fact_check_status || "").trim().toLowerCase() !== statusFilter.toLowerCase()) {
        return false;
      }
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchSintesi = p.dichiarazione_sintesi.toLowerCase().includes(q);
      const matchParty = p.partito.toLowerCase().includes(q);
      const matchMotiv = p.fact_check_motivazione?.toLowerCase().includes(q) || false;
      const matchCost = p.costo_stimato?.toLowerCase().includes(q) || false;
      return matchSintesi || matchParty || matchMotiv || matchCost;
    }
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
      {/* Page Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-5">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 mb-2">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Osservatorio Fattibilità Economica & Fact-Checking</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
          Verifica Fattibilità Finanziaria & Bilancio
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Analisi oggettiva di congruità contabile: confrontiamo i costi annunciati e le coperture dichiarate con i vincoli del bilancio dello Stato e i dati ISTAT, MEF e Corte dei Conti.
        </p>
      </div>

      {/* Institutional Benchmarks Reference Table */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-2xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
              <Scale className="w-4 h-4 text-blue-500" />
              <span>Parametri Istituzionali di Riferimento (ISTAT / MEF / Corte dei Conti)</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Indicatori economici certificati usati come benchmark di confronto per ogni stima finanziaria.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">
                <th className="p-3 font-semibold">Categoria</th>
                <th className="p-3 font-semibold">Indicatore Ufficiale</th>
                <th className="p-3 font-semibold">Valore Ufficiale</th>
                <th className="p-3 font-semibold">Fonte Ufficiale del Dato</th>
                <th className="p-3 font-semibold">Rilevanza per le Promesse</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {benchmarks.map((b) => (
                <tr key={b.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                  <td className="p-3 font-medium text-slate-700 dark:text-slate-300">
                    {b.categoria}
                  </td>
                  <td className="p-3 font-bold text-slate-900 dark:text-white">
                    {b.indicatore}
                  </td>
                  <td className="p-3 font-mono font-bold text-blue-600 dark:text-blue-400">
                    {b.valore} {b.unita}
                  </td>
                  <td className="p-3 text-slate-600 dark:text-slate-400">
                    <a
                      href={b.url_fonte || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 hover:underline text-indigo-600 dark:text-indigo-400"
                    >
                      <span>{b.fonte_istituzionale} ({b.anno_riferimento})</span>
                      <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                  </td>
                  <td className="p-3 text-slate-500 dark:text-slate-400">
                    {b.descrizione}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Filter and Search Bar */}
      <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Status Pill Filters */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {statuses.map((st) => {
            const isSelected = statusFilter === st;
            const cnt = st === "Tutti" ? proposals.length : (statusCounts[st.toLowerCase()] || 0);
            return (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all inline-flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                }`}
              >
                <span>{st}</span>
                <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${isSelected ? "bg-white/20 dark:bg-slate-900/20" : "bg-slate-200/80 dark:bg-slate-700"}`}>
                  {cnt}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <input
            type="text"
            placeholder="Cerca proposta o motivazione..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg pl-8 pr-3 py-2 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
        </div>
      </div>

      {/* Proposals Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Risultati trovati: {filteredProposals.length}</span>
        </div>

        {loading ? (
          <div className="p-16 text-center text-slate-400">
            Caricamento delle verifiche di bilancio...
          </div>
        ) : filteredProposals.length === 0 ? (
          <div className="p-12 text-center bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-500">
            Nessuna proposta corrispondente ai filtri selezionati.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredProposals.map((prop) => (
              <ProposalCard key={prop.id} proposal={prop} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
