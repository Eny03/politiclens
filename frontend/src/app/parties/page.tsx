"use client";

import React, { useEffect, useState } from "react";
import { 
  Building2, 
  ExternalLink, 
  User, 
  Layers, 
  Coins, 
  Calendar, 
  CheckCircle2, 
  FileText, 
  ShieldCheck, 
  Search, 
  Sparkles, 
  TrendingUp, 
  AlertCircle, 
  Clock, 
  Globe, 
  Share2,
  PieChart as PieIcon,
  Vote,
  Landmark,
  Zap
} from "lucide-react";
import { 
  fetchParties, 
  fetchPartyDetail, 
  PoliticalParty, 
  PoliticalProposal,
  AIDossierData 
} from "@/lib/api";
import { ProposalCard } from "@/components/ProposalCard";
import { StatusBadge } from "@/components/StatusBadge";
import { TopicBadge } from "@/components/TopicBadge";
import { MarkdownMessage } from "@/components/MarkdownMessage";


export default function PartiesPage() {
  const [parties, setParties] = useState<PoliticalParty[]>([]);
  const [selectedParty, setSelectedParty] = useState<PoliticalParty | null>(null);
  const [partyProposals, setPartyProposals] = useState<PoliticalProposal[]>([]);
  const [topicDistribution, setTopicDistribution] = useState<Record<string, number>>({});
  const [partyDossier, setPartyDossier] = useState<AIDossierData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDossier, setLoadingDossier] = useState(false);
  const [filterCoalition, setFilterCoalition] = useState<string>("Tutte");
  const [selectedTopic, setSelectedTopic] = useState<string>("Tutti");
  const [activeTab, setActiveTab] = useState<"dossier" | "web_news" | "proposals">("dossier");

  useEffect(() => {
    async function init() {
      try {
        setLoading(true);
        const data = await fetchParties();
        setParties(data);
        if (data.length > 0) {
          let chosen = data[0];
          if (typeof window !== "undefined") {
            const params = new URLSearchParams(window.location.search);
            const codeParam = params.get("code");
            if (codeParam) {
              const match = data.find(
                (p) => p.code.toLowerCase() === codeParam.toLowerCase() || p.name.toLowerCase().includes(codeParam.toLowerCase())
              );
              if (match) chosen = match;
            }
          }
          selectParty(chosen);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  const selectParty = async (party: PoliticalParty) => {
    try {
      setSelectedParty(party);
      setSelectedTopic("Tutti");
      setLoadingDossier(true);
      const detail = await fetchPartyDetail(party.id);
      setPartyProposals(detail.proposals || []);
      setTopicDistribution(detail.topic_distribution || {});
      setPartyDossier(detail.dossier || null);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDossier(false);
    }
  };

  const coalitions = [
    "Tutte",
    "Centrodestra",
    "Centrosinistra",
    "Movimento 5 Stelle",
    "Centro / Liberaldemocratici",
    "Sinistra Radicale",
    "Sovranismo Popolare",
    "Autonomie Regionali"
  ];

  const filteredParties = parties.filter((p) => {
    if (filterCoalition === "Tutte") return true;
    return p.coalition.toLowerCase().includes(filterCoalition.toLowerCase());
  });

  const filteredProposals = partyProposals.filter((p) => {
    if (selectedTopic === "Tutti") return true;
    return p.macro_argomento === selectedTopic;
  });

  // Macro-topics for filtering proposals
  const MACRO_TOPICS = [
    "Fisco",
    "Lavoro",
    "Sanità",
    "Pensioni",
    "Energia",
    "Istituzioni",
    "Immigrazione",
    "Istruzione"
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 mb-2">
            <Building2 className="w-3.5 h-3.5" />
            <span>Osservatorio Permanente Forze Politiche</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight">
            Schede Partiti & Dossier Strategici AI
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Analisi dettagliata delle forze politiche italiane: pilastri programmatici, fonti verificate e atti parlamentari depositati.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Party Selector List */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex flex-wrap items-center gap-1.5 pb-1">
            {coalitions.map((c) => (
              <button
                key={c}
                onClick={() => setFilterCoalition(c)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all shrink-0 ${
                  filterCoalition === c
                    ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs"
                    : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200"
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {filteredParties.map((p) => {
              const isSelected = selectedParty?.id === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => selectParty(p)}
                  className={`w-full text-left p-3 rounded-2xl border transition-all flex items-center justify-between ${
                    isSelected
                      ? "bg-white dark:bg-slate-900 border-blue-500 shadow-sm ring-2 ring-blue-500/20"
                      : "bg-white/60 dark:bg-slate-900/60 border-slate-200 dark:border-slate-800 hover:bg-white dark:hover:bg-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span
                      className="w-3 h-3 rounded-full shrink-0 shadow-xs"
                      style={{ backgroundColor: p.color }}
                    />
                    <div className="min-w-0">
                      <div className="font-bold text-xs sm:text-sm text-slate-900 dark:text-white leading-snug">
                        {p.name}
                      </div>
                      <div className="text-[10px] text-slate-400 leading-tight">
                        {p.coalition}
                      </div>
                    </div>
                  </div>

                  <div className="text-right shrink-0 pl-2">
                    {p.poll_percentage !== undefined && (
                      <div className="text-xs font-black text-slate-900 dark:text-white font-mono">
                        {p.poll_percentage}%
                      </div>
                    )}
                    <span className="text-[10px] font-semibold text-slate-400">
                      {p.proposals_count} atti
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Party Dossier */}
        <div className="lg:col-span-8 space-y-5">
          {selectedParty ? (
            <div className="space-y-5">
              {/* Party Profile Header Card */}
              <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-xs relative overflow-hidden">
                <div
                  className="absolute top-0 left-0 right-0 h-1.5"
                  style={{ backgroundColor: selectedParty.color }}
                />

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3 pt-1">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="w-3.5 h-3.5 rounded-full" style={{ backgroundColor: selectedParty.color }} />
                      <h2 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white">
                        {selectedParty.name}
                      </h2>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Schieramento: <strong>{selectedParty.coalition}</strong> {selectedParty.leader && `• Leader: ${selectedParty.leader}`}
                    </p>

                    <div className="flex flex-wrap items-center gap-2 pt-2.5">
                      {selectedParty.poll_percentage !== undefined && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-bold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800" title={`Rilevazione precedente: ${selectedParty.previous_poll_percentage ?? selectedParty.poll_percentage}% • Variazione: ${selectedParty.poll_trend || "stabile"}`}>
                          <TrendingUp className="w-3.5 h-3.5" />
                          <span>
                            Sondaggi: {selectedParty.poll_percentage}% 
                            {selectedParty.previous_poll_percentage !== undefined && ` (Prec: ${selectedParty.previous_poll_percentage}%, Var: ${selectedParty.poll_trend || "stabile"})`}
                          </span>
                        </span>
                      )}
                      {selectedParty.truthfulness_score !== undefined && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Veridicità: {selectedParty.truthfulness_score}%</span>
                        </span>
                      )}
                      {selectedParty.financial_reliability_score !== undefined && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                          <Coins className="w-3.5 h-3.5" />
                          <span>Coperture: {selectedParty.financial_reliability_score}%</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {selectedParty.official_website && (
                    <a
                      href={selectedParty.official_website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors self-start sm:self-auto"
                    >
                      <span>Sito Ufficiale</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>

                {selectedParty.description && (
                  <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed mb-4">
                    {selectedParty.description}
                  </p>
                )}

                {/* Sub-Tabs Switcher */}
                <div className="flex items-center gap-2 border-t border-slate-100 dark:border-slate-800 pt-3 overflow-x-auto scrollbar-none pb-1">
                  <button
                    onClick={() => setActiveTab("dossier")}
                    className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                      activeTab === "dossier"
                        ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-2xs"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                    }`}
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Dossier Strategico & Pilastri</span>
                  </button>

                  <button
                    onClick={() => setActiveTab("web_news")}
                    className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                      activeTab === "web_news"
                        ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-2xs"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                    }`}
                  >
                    <Globe className="w-3.5 h-3.5" />
                    <span>Dichiarazioni & Fonti Web ({partyDossier?.dichiarazioni_recenti_web?.length || 0})</span>
                  </button>

                  <button
                    onClick={() => setActiveTab("proposals")}
                    className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                      activeTab === "proposals"
                        ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-2xs"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>Atti & Posizioni ({partyProposals.length})</span>
                  </button>
                </div>
              </div>

              {/* Tab 1: AI Strategic Dossier View */}
              {activeTab === "dossier" && (
                <div className="space-y-5">
                  {partyDossier ? (
                    <>
                      {/* Strategic Synthesis Card */}
                      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-xs space-y-3">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-blue-500" />
                            <span>Sintesi Strategica Elaborata dall'AI</span>
                          </h3>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {partyDossier.ultimo_aggiornamento_web}
                          </span>
                        </div>
                        <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                          <MarkdownMessage content={partyDossier.sintesi_strategica} />
                        </div>
                      </div>

                      {/* Key Policy Pillars */}
                      <div className="space-y-3">
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                          <Layers className="w-4 h-4 text-indigo-500" />
                          <span>Pilastri Programmatici Chiave Rilevati dal Web</span>
                        </h3>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                          {partyDossier.pilastri_programmatici.map((pil, idx) => (
                            <div
                              key={idx}
                              className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-2xs space-y-3"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200">
                                  {pil.tema}
                                </span>
                                <span className="text-[10px] font-semibold text-slate-400">
                                  {pil.tipo_azione}
                                </span>
                              </div>

                              <p className="text-xs font-bold text-slate-900 dark:text-slate-100 leading-snug">
                                {pil.proposta_chiave}
                              </p>

                              <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                                <div className="space-y-1.5 bg-slate-50 dark:bg-slate-800/50 p-2.5 rounded-xl border border-slate-100 dark:border-slate-800 text-[11px]">
                                  <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
                                    <span className="text-slate-500 font-medium shrink-0">Stima di Costo:</span>
                                    <strong className="text-slate-900 dark:text-white font-semibold text-right">{pil.costo}</strong>
                                  </div>
                                  <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1 pt-1 border-t border-slate-200/50 dark:border-slate-700/50">
                                    <span className="text-slate-500 font-medium shrink-0">Copertura Dichiarata:</span>
                                    <strong className="text-slate-900 dark:text-white font-semibold text-right">{pil.coperture}</strong>
                                  </div>
                                </div>

                                <p className="text-slate-600 dark:text-slate-400 text-xs leading-relaxed">
                                  {pil.motivazione}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>


                      {/* Strengths & Vulnerabilities */}
                      {(partyDossier.punti_di_forza || partyDossier.criticita_osservatorio) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                          {partyDossier.punti_di_forza && (
                            <div className="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200/60 dark:border-emerald-900/40 space-y-2">
                              <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-300 font-bold text-xs uppercase tracking-wider">
                                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                                <span>Punti di Forza Programmatici</span>
                              </div>
                              <p className="text-xs text-emerald-900 dark:text-emerald-200 leading-relaxed">
                                {partyDossier.punti_di_forza}
                              </p>
                            </div>
                          )}

                          {partyDossier.criticita_osservatorio && (
                            <div className="p-4 rounded-2xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/60 dark:border-amber-900/40 space-y-2">
                              <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300 font-bold text-xs uppercase tracking-wider">
                                <AlertCircle className="w-4 h-4 text-amber-600" />
                                <span>Criticità & Vincoli Finanziari</span>
                              </div>
                              <p className="text-xs text-amber-900 dark:text-amber-200 leading-relaxed">
                                {partyDossier.criticita_osservatorio}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  ) : loadingDossier ? (
                    <div className="p-12 text-center text-xs text-slate-400 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 animate-pulse">
                      Caricamento del Dossier AI in corso...
                    </div>
                  ) : null}
                </div>
              )}

              {/* Tab 2: Dichiarazioni Web & Citations */}
              {activeTab === "web_news" && (
                <div className="space-y-3">
                  {partyDossier?.dichiarazioni_recenti_web && partyDossier.dichiarazioni_recenti_web.length > 0 ? (
                    <div className="grid grid-cols-1 gap-3">
                      {partyDossier.dichiarazioni_recenti_web.map((quote, qIdx) => (
                        <div
                          key={qIdx}
                          className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-2"
                        >
                          <div className="flex items-center justify-between text-[11px] text-slate-400">
                            <span className="font-semibold text-blue-600 dark:text-blue-400">{quote.fonte}</span>
                            <span>{quote.data}</span>
                          </div>
                          <h4 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white">
                            {quote.titolo}
                          </h4>
                          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                            "{quote.dichiarazione}"
                          </p>
                          {quote.url && (
                            <a
                              href={quote.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1 font-mono pt-1"
                            >
                              <span>Leggi l'articolo originale</span>
                              <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-8 text-center text-xs text-slate-400 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
                      Nessuna dichiarazione recente indicizzata dal web per questa forza politica.
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Catalog of Formal Proposals */}
              {activeTab === "proposals" && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-1.5 pb-1">
                    {["Tutti", ...MACRO_TOPICS].map((top) => (
                      <button
                        key={top}
                        onClick={() => setSelectedTopic(top)}
                        className={`px-3 py-1 rounded-full text-xs font-semibold transition-all shrink-0 ${
                          selectedTopic === top
                            ? "bg-blue-600 text-white shadow-xs"
                            : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200"
                        }`}
                      >
                        {top}
                      </button>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
                    {filteredProposals.map((prop) => (
                      <ProposalCard key={prop.id} proposal={prop} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-16 text-center text-xs text-slate-400 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800">
              Seleziona un partito dalla colonna di sinistra per visualizzare il dossier.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
