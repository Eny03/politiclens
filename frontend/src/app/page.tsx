"use client";

import React, { useEffect, useState, useMemo, useTransition, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { 
  Scale, 
  Layers, 
  ShieldCheck, 
  Bot, 
  Coins, 
  TrendingUp, 
  ArrowRight,
  RefreshCw,
  Building2,
  FileText,
  Clock,
  Sparkles,
  Search,
  CheckCircle2,
  Filter,
  BarChart3,
  Flame,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Target,
  Info,
  ExternalLink,
  Percent,
  SlidersHorizontal,
  Award,
  ArrowUpDown
} from "lucide-react";
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  CartesianGrid, 
  Cell,
  LabelList 
} from "recharts";
import { 
  fetchStatsOverview, 
  fetchProposals, 
  fetchSchedulerStatus, 
  fetchParties,
  fetchDetectedGaps,
  triggerFeedScan,
  triggerPollUpdate,
  StatsOverview, 
  PoliticalProposal, 
  PoliticalParty,
  InformationGap
} from "@/lib/api";

import { ProposalCard } from "@/components/ProposalCard";
import { StatusBadge } from "@/components/StatusBadge";
import { TopicBadge } from "@/components/TopicBadge";

const MACRO_TOPICS = [
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

const CURRENT_YEAR = new Date().getFullYear();
const HISTORICAL_YEARS = [
  "Tutti i Periodi",
  `${CURRENT_YEAR} (In corso / Live)`,
  "Posizioni Recenti (2024–2025)",
  "Sviluppi Futuri / DDL"
];

function DashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [proposals, setProposals] = useState<PoliticalProposal[]>([]);
  const [parties, setParties] = useState<PoliticalParty[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<any>(null);
  const [scanPhase, setScanPhase] = useState<"idle" | "searching" | "updating" | "done">("idle");
  const [scanFeedback, setScanFeedback] = useState<string | null>(null);
  const [updatingPolls, setUpdatingPolls] = useState<boolean>(false);
  const [pollFeedback, setPollFeedback] = useState<string | null>(null);
  const [detectedGaps, setDetectedGaps] = useState<InformationGap[]>([]);
  const [lastPollTime, setLastPollTime] = useState<string>("");

  const [showGapsDetails, setShowGapsDetails] = useState<boolean>(false);

  // Active view tab synced with URL param: "proposte" | "sondaggi" | "statistiche"
  const urlTab = (searchParams.get("tab") as "proposte" | "sondaggi" | "statistiche") || "proposte";
  const [activeTab, setActiveTabState] = useState<"proposte" | "sondaggi" | "statistiche">(urlTab);

  // Proposals Tab Filters synced with URL
  const initialTopic = searchParams.get("topic") || "Tutti";
  const initialParty = searchParams.get("party") || "Tutti";
  const initialYear = searchParams.get("year") || "Tutti i Periodi";
  const initialQ = searchParams.get("q") || "";

  const [selectedTopic, setSelectedTopicState] = useState<string>(initialTopic);
  const [selectedParty, setSelectedPartyState] = useState<string>(initialParty);
  const [selectedYear, setSelectedYearState] = useState<string>(initialYear);
  const [searchQuery, setSearchQueryState] = useState<string>(initialQ);
  const [visibleCount, setVisibleCount] = useState<number>(12);

  // Polls Tab Filter
  const [pollCoalitionFilter, setPollCoalitionFilter] = useState<string>("Tutti");
  const [pollChartType, setPollChartType] = useState<"bar" | "ranking">("bar");

  // Statistics Tab State (Veridicità & Coperture)
  const [statsSortBy, setStatsSortBy] = useState<"truth" | "finance" | "poll" | "proposals">("truth");
  const [statsCoalitionFilter, setStatsCoalitionFilter] = useState<string>("Tutti");

  // Helper to sync state to URL
  const updateURL = (paramsToUpdate: Record<string, string | null>) => {
    const current = new URLSearchParams(Array.from(searchParams.entries()));
    for (const [key, value] of Object.entries(paramsToUpdate)) {
      if (value === null || value === "Tutti" || value === "Tutti i Periodi" || value === "Tutti gli Anni" || value === "") {
        current.delete(key);
      } else {
        current.set(key, value);
      }
    }
    const search = current.toString();
    const query = search ? `?${search}` : "";
    startTransition(() => {
      router.replace(`/${query}`, { scroll: false });
    });
  };

  const setActiveTab = (tab: "proposte" | "sondaggi" | "statistiche") => {
    setActiveTabState(tab);
    updateURL({ tab: tab === "proposte" ? null : tab });
  };

  const setSelectedTopic = (topic: string) => {
    setSelectedTopicState(topic);
    updateURL({ topic });
  };

  const setSelectedParty = (party: string) => {
    setSelectedPartyState(party);
    updateURL({ party });
  };

  const setSelectedYear = (year: string) => {
    setSelectedYearState(year);
    updateURL({ year });
  };

  const setSearchQuery = (q: string) => {
    setSearchQueryState(q);
    updateURL({ q });
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsData, propsData, schedData, partiesData, gapsData] = await Promise.all([
        fetchStatsOverview(),
        fetchProposals({ limit: 350 }),
        fetchSchedulerStatus().catch(() => null),
        fetchParties().catch(() => []),
        fetchDetectedGaps(4)
      ]);
      setStats(statsData);
      setProposals(propsData);
      setSchedulerStatus(schedData);
      setParties(partiesData);
      setDetectedGaps(gapsData);

      // Determine real poll timestamp and persist to local storage
      const pollTimeStr = statsData.last_poll_time || (partiesData[0]?.poll_sources?.includes("Rilevazione") ? partiesData[0].poll_sources.split("Rilevazione")[1].replace(/[()]/g, "").trim() : "");
      if (pollTimeStr) {
        setLastPollTime(pollTimeStr);
      }
      try {
        localStorage.setItem("politiclens_cached_stats", JSON.stringify(statsData));
        localStorage.setItem("politiclens_cached_parties", JSON.stringify(partiesData));
        if (pollTimeStr) localStorage.setItem("politiclens_last_poll_time", pollTimeStr);
      } catch (e) {}
    } catch (err: any) {
      console.error(err);
      setError("Impossibile caricare i dati della dashboard. Verifica la connessione al server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 1. Instant hydration from localStorage (persists across page reloads & app closures)
    try {
      const cachedStats = localStorage.getItem("politiclens_cached_stats");
      const cachedParties = localStorage.getItem("politiclens_cached_parties");
      const cachedPollTime = localStorage.getItem("politiclens_last_poll_time");
      if (cachedStats) setStats(JSON.parse(cachedStats));
      if (cachedParties) setParties(JSON.parse(cachedParties));
      if (cachedPollTime) setLastPollTime(cachedPollTime);
    } catch (e) {}

    // 2. Fetch fresh live data from server
    loadData();

    // 3. Automated 10-minute polling update via internet search
    const pollInterval = setInterval(async () => {
      try {
        await triggerPollUpdate();
        const [statsData, partiesData] = await Promise.all([
          fetchStatsOverview(),
          fetchParties()
        ]);
        setStats(statsData);
        setParties(partiesData);
        const pollTimeStr = statsData.last_poll_time || (partiesData[0]?.poll_sources?.includes("Rilevazione") ? partiesData[0].poll_sources.split("Rilevazione")[1].replace(/[()]/g, "").trim() : new Date().toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" }));
        setLastPollTime(pollTimeStr);
        try {
          localStorage.setItem("politiclens_cached_stats", JSON.stringify(statsData));
          localStorage.setItem("politiclens_cached_parties", JSON.stringify(partiesData));
          localStorage.setItem("politiclens_last_poll_time", pollTimeStr);
        } catch (e) {}
      } catch (err) {
        console.error("Auto poll interval notice:", err);
      }
    }, 600000);

    return () => clearInterval(pollInterval);
  }, []);

  const handleTriggerScan = async () => {
    try {
      setScanPhase("searching");
      setScanFeedback("Scansione autonoma del web avviata in background...");
      await triggerFeedScan();
      setTimeout(async () => {
        setScanPhase("updating");
        setScanFeedback("Consensus Multi-AI e aggiornamento dossier in corso...");
        setTimeout(async () => {
          await loadData();
          setScanPhase("done");
          setScanFeedback("Aggiornamento completato con successo!");
          setTimeout(() => {
            setScanPhase("idle");
            setScanFeedback(null);
          }, 3500);
        }, 1500);
      }, 1500);
    } catch (e) {
      setScanPhase("idle");
      setScanFeedback("Errore nell'avvio della scansione.");
    }
  };

  const handleUpdatePolls = async () => {
    try {
      setUpdatingPolls(true);
      setPollFeedback(null);
      const res = await triggerPollUpdate();
      setPollFeedback(res.message);
      const [statsData, partiesData] = await Promise.all([
        fetchStatsOverview(),
        fetchParties()
      ]);
      setStats(statsData);
      setParties(partiesData);
      const pollTimeStr = statsData.last_poll_time || (partiesData[0]?.poll_sources?.includes("Rilevazione") ? partiesData[0].poll_sources.split("Rilevazione")[1].replace(/[()]/g, "").trim() : new Date().toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" }));
      setLastPollTime(pollTimeStr);
      try {
        localStorage.setItem("politiclens_cached_stats", JSON.stringify(statsData));
        localStorage.setItem("politiclens_cached_parties", JSON.stringify(partiesData));
        localStorage.setItem("politiclens_last_poll_time", pollTimeStr);
      } catch (e) {}
    } catch (e: any) {
      setPollFeedback("Errore durante l'aggiornamento dei sondaggi.");
    } finally {
      setUpdatingPolls(false);
    }
  };

  // Filter proposals
  const filteredProposals = proposals.filter((p) => {
    if (selectedTopic !== "Tutti" && p.macro_argomento !== selectedTopic) return false;
    if (selectedParty !== "Tutti" && !p.partito.toLowerCase().includes(selectedParty.toLowerCase())) return false;
    if (selectedYear !== "Tutti i Periodi" && selectedYear !== "Tutti gli Anni") {
      const pYear = p.timestamp ? new Date(p.timestamp).getFullYear() : 0;
      if (selectedYear.includes("Sviluppi Futuri")) {
        if (pYear < CURRENT_YEAR) return false;
      } else if (!selectedYear.includes(pYear.toString())) {
        return false;
      }
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchText = (p.dichiarazione_sintesi + " " + p.partito + " " + p.macro_argomento).toLowerCase();
      if (!matchText.includes(q)) return false;
    }
    return true;
  });

  // Filter rankings for polls
  const filteredRankings = (stats?.party_rankings || []).filter((item) => {
    if (pollCoalitionFilter === "Tutti") return true;
    if (pollCoalitionFilter === "Maggioranza") return item.coalition.toLowerCase().includes("centrodestra");
    if (pollCoalitionFilter === "Opposizione") return item.coalition.toLowerCase().includes("centrosinistra") || item.coalition.toLowerCase().includes("opposizione");
    if (pollCoalitionFilter === "Centro") return item.coalition.toLowerCase().includes("centro") || item.coalition.toLowerCase().includes("terzo polo");
    return true;
  });

  // Recharts Poll Data (Pure Electoral Polls - NO coperture)
  const pollChartData = filteredRankings.slice(0, 10).map((p) => {
    const partyMatch = parties.find((party) => party.code === p.code || party.name === p.name);
    return {
      name: p.code || p.name.slice(0, 8),
      fullName: p.name,
      poll: p.poll_percentage,
      trend: p.poll_trend || partyMatch?.poll_trend || "stabile",
      sources: partyMatch?.poll_sources || "Media YouTrend/SWG/Ipsos",
      color: p.color
    };
  });

  // Helper to categorize parties into 4 primary coalitions
  const getCoalitionCategory = (code: string, coalition: string): "centrodestra" | "campo_largo" | "centro" | "altre_forze" => {
    const cUpper = (code || "").toUpperCase();
    const cLow = (coalition || "").toLowerCase();
    if (["FDI", "LEGA", "FI", "NM", "FUTNAZ"].includes(cUpper) || cLow.includes("centrodestra")) {
      return "centrodestra";
    }
    if (["PD", "M5S", "AVS", "PIUEU"].includes(cUpper) || cLow.includes("centrosinistra") || cLow.includes("campo progressista") || cLow.includes("progressist") || cLow.includes("campo largo")) {
      return "campo_largo";
    }
    if (["AZ", "IV", "LIBDEM", "ORA"].includes(cUpper) || cLow.includes("centro") || cLow.includes("terzo polo") || cLow.includes("liberal") || cLow.includes("riformist")) {
      return "centro";
    }
    return "altre_forze";
  };

  // Coalition Summary Stats calculation
  const coalitionStats = useMemo(() => {
    const rankings = stats?.party_rankings || [];
    const groups = {
      centrodestra: {
        id: "centrodestra",
        name: "Centrodestra",
        tag: "Maggioranza di Governo",
        theme: "blue",
        parties: [] as typeof rankings
      },
      campo_largo: {
        id: "campo_largo",
        name: "Campo Largo & Progressisti",
        tag: "Opposizione Parlamentare",
        theme: "rose",
        parties: [] as typeof rankings
      },
      centro: {
        id: "centro",
        name: "Centro & Liberaldemocratici",
        tag: "Terzo Polo & Riformisti",
        theme: "cyan",
        parties: [] as typeof rankings
      },
      altre_forze: {
        id: "altre_forze",
        name: "Sinistra Radicale & Altre Forze",
        tag: "Civiche & Autonomie",
        theme: "amber",
        parties: [] as typeof rankings
      }
    };

    rankings.forEach((p) => {
      const cat = getCoalitionCategory(p.code, p.coalition);
      groups[cat].parties.push(p);
    });

    return Object.values(groups).map((g) => {
      const count = g.parties.length || 1;
      const avgTruth = g.parties.reduce((acc, p) => acc + (p.truthfulness_score || 0), 0) / count;
      const avgFinance = g.parties.reduce((acc, p) => acc + (p.financial_reliability_score || 0), 0) / count;
      const totalPoll = g.parties.reduce((acc, p) => acc + (p.poll_percentage || 0), 0);
      const totalProposals = g.parties.reduce((acc, p) => acc + (p.proposals_count || 0), 0);

      return {
        ...g,
        avgTruth: Math.round(avgTruth * 10) / 10,
        avgFinance: Math.round(avgFinance * 10) / 10,
        totalPoll: Math.round(totalPoll * 10) / 10,
        totalProposals
      };
    });
  }, [stats?.party_rankings]);

  // Party-by-party stats filtered & sorted
  const sortedPartyStats = useMemo(() => {
    const rankings = [...(stats?.party_rankings || [])];
    
    // Filter
    const filtered = rankings.filter((p) => {
      if (statsCoalitionFilter === "Tutti") return true;
      const cat = getCoalitionCategory(p.code, p.coalition);
      return cat === statsCoalitionFilter;
    });

    // Sort
    return filtered.sort((a, b) => {
      if (statsSortBy === "truth") return (b.truthfulness_score || 0) - (a.truthfulness_score || 0);
      if (statsSortBy === "finance") return (b.financial_reliability_score || 0) - (a.financial_reliability_score || 0);
      if (statsSortBy === "poll") return (b.poll_percentage || 0) - (a.poll_percentage || 0);
      if (statsSortBy === "proposals") return (b.proposals_count || 0) - (a.proposals_count || 0);
      return 0;
    });
  }, [stats?.party_rankings, statsCoalitionFilter, statsSortBy]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 py-4">
      {/* 1. HERO BANNER (Light, Clean & High-End Editorial Style) */}
      <section className="relative overflow-hidden rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-6 sm:p-8 shadow-2xs">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Piattaforma Civica in Continua Evoluzione Autonoma</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight leading-tight">
            PoliticLens: Idee Politiche in Tempo Reale, Trasparenza e Fatti Verificati.
          </h1>

          <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed max-w-2xl">
            Osservatorio indipendente e neutrale: monitoraggio in tempo reale e in continuo aggiornamento autonomo per permettere a tutti i cittadini di osservare le idee politiche, confrontarle e verificarne la sostenibilità economica.
          </p>
        </div>
      </section>


      {/* 2. STATS OVERVIEW CARDS (WITH SKELETONS) */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xs animate-pulse space-y-2">
              <div className="h-3 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
              <div className="h-7 w-16 bg-slate-200 dark:bg-slate-800 rounded" />
              <div className="h-2 w-32 bg-slate-100 dark:bg-slate-800/60 rounded" />
            </div>
          ))
        ) : (
          <>
            <div className="bg-white dark:bg-slate-900 p-3.5 sm:p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Posizioni Censite</div>
              <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white mt-0.5">
                {stats?.total_proposals || proposals.length}
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">Atti parlamentari & dichiarazioni</p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-3.5 sm:p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Forze Mappate</div>
              <div className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white mt-0.5">
                {stats?.total_parties || parties.length || 18}
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">Parlamentari & civiche</p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-3.5 sm:p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Media Veridicità</div>
              <div className="text-xl sm:text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-0.5">
                {stats?.average_truthfulness !== undefined ? `${stats.average_truthfulness}%` : "--%"}
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">Fact-checking: aderenza a dati e fatti reali</p>
            </div>

            <div className="bg-white dark:bg-slate-900 p-3.5 sm:p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Coperture Economiche</div>
              <div className="text-xl sm:text-2xl font-black text-blue-600 dark:text-blue-400 mt-0.5">
                {stats?.quantified_cost_percentage !== undefined ? `${stats.quantified_cost_percentage}%` : "--%"}
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5">Proposte con fonti di finanziamento indicate</p>
            </div>

          </>
        )}
      </section>

      {/* 3. MAIN NAVIGATION TABS */}
      <section className="space-y-4">
        <div className="flex items-center gap-1.5 p-1 rounded-2xl bg-slate-100 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 overflow-x-auto scrollbar-none">
          <button
            onClick={() => setActiveTab("proposte")}
            className={`flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 py-2 px-3.5 rounded-xl text-xs sm:text-sm font-bold transition-all whitespace-nowrap ${
              activeTab === "proposte"
                ? "bg-white dark:bg-slate-800 text-slate-950 dark:text-white shadow-2xs"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <FileText className={`w-4 h-4 ${activeTab === "proposte" ? "text-blue-600 dark:text-blue-400" : ""}`} />
            <span>Riforme & Posizioni</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-md font-semibold bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
              {filteredProposals.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("sondaggi")}
            className={`flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 py-2 px-3.5 rounded-xl text-xs sm:text-sm font-bold transition-all whitespace-nowrap ${
              activeTab === "sondaggi"
                ? "bg-white dark:bg-slate-800 text-slate-950 dark:text-white shadow-2xs"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <TrendingUp className={`w-4 h-4 ${activeTab === "sondaggi" ? "text-emerald-600 dark:text-emerald-400" : ""}`} />
            <span>Sondaggi & Grafici</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-md font-semibold bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
              Recharts
            </span>
          </button>

          <button
            onClick={() => setActiveTab("statistiche")}
            className={`flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 py-2 px-3.5 rounded-xl text-xs sm:text-sm font-bold transition-all whitespace-nowrap ${
              activeTab === "statistiche"
                ? "bg-white dark:bg-slate-800 text-slate-950 dark:text-white shadow-2xs"
                : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <ShieldCheck className={`w-4 h-4 ${activeTab === "statistiche" ? "text-amber-600 dark:text-amber-400" : ""}`} />
            <span>Veridicità & Coperture</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-md font-semibold bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              Partiti & Coalizioni
            </span>
          </button>
        </div>


        {/* TAB 1: RIFORME & POSIZIONI */}
        {activeTab === "proposte" && (
          <div className="space-y-4">
            {/* Filter Controls Bar */}
            <div className="bg-white dark:bg-slate-900 p-3.5 sm:p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs space-y-3">
              <div className="flex flex-col sm:flex-row gap-2.5">
                <div className="relative flex-1">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Cerca per tema o parola chiave (es. salario minimo, flat tax, sanità)..."
                    className="w-full text-xs sm:text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 rounded-xl pl-9 pr-4 py-2.5 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
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

                <div className="grid grid-cols-2 sm:flex gap-2 w-full sm:w-auto">
                  <select
                    value={selectedParty}
                    onChange={(e) => setSelectedParty(e.target.value)}
                    className="w-full min-w-0 text-xs sm:text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 rounded-xl px-2.5 sm:px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-hidden font-medium truncate"
                  >
                    <option value="Tutti">Tutti i Partiti</option>
                    {parties.map((p) => (
                      <option key={p.id} value={p.name}>
                        {p.name}
                      </option>
                    ))}
                  </select>

                  <select
                    value={selectedYear}
                    onChange={(e) => setSelectedYear(e.target.value)}
                    className="w-full min-w-0 text-xs sm:text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 rounded-xl px-2.5 sm:px-3 py-2 text-slate-800 dark:text-slate-200 focus:outline-hidden font-medium truncate"
                  >
                    {HISTORICAL_YEARS.map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Topic chips - Wraps cleanly on Desktop PC and Mobile */}
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider shrink-0 mr-1">
                  Macro-Tema:
                </span>
                {MACRO_TOPICS.map((topic) => (
                  <button
                    key={topic}
                    onClick={() => setSelectedTopic(topic)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold shrink-0 transition-all ${
                      selectedTopic === topic
                        ? "bg-blue-600 text-white shadow-xs"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                    }`}
                  >
                    {topic}
                  </button>
                ))}
              </div>
            </div>

            {/* Proposals Cards Grid */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="h-48 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xs animate-pulse p-4 space-y-3">
                    <div className="h-4 w-1/3 bg-slate-200 dark:bg-slate-800 rounded" />
                    <div className="h-6 w-full bg-slate-200 dark:bg-slate-800 rounded" />
                    <div className="h-4 w-3/4 bg-slate-100 dark:bg-slate-800/60 rounded" />
                  </div>
                ))}
              </div>
            ) : filteredProposals.length === 0 ? (
              <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 text-slate-500">
                <p className="text-sm font-semibold">Nessuna proposta trovata con i filtri selezionati.</p>
                <button
                  onClick={() => {
                    setSelectedTopic("Tutti");
                    setSelectedParty("Tutti");
                    setSelectedYear("Tutti gli Anni");
                    setSearchQuery("");
                  }}
                  className="mt-3 text-xs text-blue-600 dark:text-blue-400 font-bold hover:underline"
                >
                  Resetta tutti i filtri
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                {filteredProposals.slice(0, visibleCount).map((prop) => (
                  <ProposalCard key={prop.id} proposal={prop} />
                ))}
              </div>
            )}

            {filteredProposals.length > visibleCount && (
              <div className="text-center pt-2">
                <button
                  onClick={() => setVisibleCount((prev) => prev + 12)}
                  className="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold transition-all shadow-xs"
                >
                  Carica altre proposte ({filteredProposals.length - visibleCount} rimanenti)
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: SONDAGGI (INTENZIONI DI VOTO PURE - SENZA COPERTURE) */}
        {activeTab === "sondaggi" && (
          <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200/80 dark:border-slate-800 p-4 sm:p-7 shadow-2xs space-y-4 sm:space-y-5 scroll-mt-24">
            {/* Header: Title, Coalition Filters and Update button */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div>
                <h2 className="text-sm sm:text-base md:text-lg font-black text-slate-900 dark:text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0" />
                  <span>Barometro Elettorale: Intenzioni di Voto</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                  Media ponderata dei sondaggi elettorali (YouTrend/AGI, SWG Tg La7, Ipsos, Tecnè) aggiornata continuamente.
                </p>
              </div>

              {/* Action Toolbar: Coalition Pills + View Mode + Update Button */}
              <div className="flex flex-wrap items-center justify-between lg:justify-end gap-2 w-full lg:w-auto">
                <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-xl overflow-x-auto scrollbar-none max-w-full">
                  {["Tutti", "Maggioranza", "Opposizione", "Centro"].map((c) => (
                    <button
                      key={c}
                      onClick={() => setPollCoalitionFilter(c)}
                      className={`px-2 sm:px-2.5 py-1 rounded-lg text-[11px] sm:text-xs font-semibold transition-all whitespace-nowrap ${
                        pollCoalitionFilter === c
                          ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-2xs"
                          : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
                      }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  {/* View Mode Toggle: Bar vs Ranking */}
                  <div className="flex items-center bg-slate-100 dark:bg-slate-800/80 p-1 rounded-xl text-[11px]">
                    <button
                      onClick={() => setPollChartType("bar")}
                      className={`px-2 py-0.5 rounded-lg font-bold transition-all ${
                        pollChartType === "bar"
                          ? "bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-2xs"
                          : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                      }`}
                      title="Visualizza grafico a barre verticali"
                    >
                      Barre
                    </button>
                    <button
                      onClick={() => setPollChartType("ranking")}
                      className={`px-2 py-0.5 rounded-lg font-bold transition-all ${
                        pollChartType === "ranking"
                          ? "bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-2xs"
                          : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                      }`}
                      title="Visualizza classifica orizzontale compatta"
                    >
                      Classifica
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* 10-Minute Auto Crawler Status Pill */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-2xl bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-200/70 dark:border-emerald-800/60 text-xs">
              <div className="flex items-center gap-2 text-emerald-900 dark:text-emerald-300 font-semibold">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                <span className="leading-tight">Aggiornamento automatico continuo ogni 10 minuti da ricerche web e rassegne</span>
              </div>
              <div className="text-[11px] text-emerald-800 dark:text-emerald-400 font-mono shrink-0">
                Ultimo check demoscopico: <strong>{lastPollTime || "In tempo reale"}</strong>
              </div>
            </div>

            {pollFeedback && (
              <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 text-xs text-blue-800 dark:text-blue-300 flex items-center justify-between">
                <span>{pollFeedback}</span>
                <Link href="/audit" className="font-bold underline ml-2">
                  Vedi Registro Modifiche
                </Link>
              </div>
            )}

            {/* View 1: Vertical Bar Chart (with generous min-width and horizontal scroll on mobile) */}
            {pollChartType === "bar" ? (
              <div className="space-y-1">
                <div className="sm:hidden flex items-center justify-between text-[10px] text-slate-400 dark:text-slate-500 px-1 font-medium">
                  <span>Grafico Barometro Elettorale</span>
                  <span>← Scorri orizzontalmente per vedere tutti i partiti →</span>
                </div>
                <div className="overflow-x-auto pb-2 scrollbar-thin rounded-xl">
                  <div className="min-w-[560px] h-80 pt-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={pollChartData}
                        margin={{ top: 25, right: 15, left: -10, bottom: 42 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" opacity={0.15} vertical={false} />
                        <XAxis 
                          dataKey="name" 
                          interval={0} 
                          angle={-18} 
                          textAnchor="end" 
                          tick={{ fontSize: 11, fontWeight: 700, fill: "#64748b" }}
                        />
                        <YAxis tick={{ fontSize: 10, fill: "#64748b" }} unit="%" domain={[0, 'dataMax + 4']} />
                        <Tooltip
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const data = payload[0].payload;
                              return (
                                <div className="p-3.5 bg-slate-900 text-white rounded-2xl shadow-xl text-xs space-y-2 border border-slate-700 min-w-[210px]">
                                  <div className="font-bold text-sm flex items-center gap-2">
                                    <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: data.color }} />
                                    <span>{data.fullName}</span>
                                  </div>
                                  <div className="flex items-baseline justify-between pt-1 border-t border-slate-800">
                                    <span className="text-slate-400 text-xs">Intenzioni di Voto:</span>
                                    <span className="text-lg font-black text-white font-mono">{data.poll}%</span>
                                  </div>
                                  <div className="flex items-center justify-between text-[11px]">
                                    <span className="text-slate-400">Trend Settimanale:</span>
                                    <span className={`font-bold px-1.5 py-0.2 rounded ${
                                      data.trend?.includes("+")
                                        ? "bg-emerald-950 text-emerald-400"
                                        : data.trend?.includes("-")
                                        ? "bg-rose-950 text-rose-400"
                                        : "bg-slate-800 text-slate-300"
                                    }`}>
                                      {data.trend || "stabile"}
                                    </span>
                                  </div>
                                  {data.sources && (
                                    <div className="text-[10px] text-slate-400 pt-1.5 border-t border-slate-800 leading-tight">
                                      {data.sources}
                                    </div>
                                  )}
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Bar dataKey="poll" name="Percentuale di Voto (%)" radius={[8, 8, 0, 0]}>
                          {pollChartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color || "#3b82f6"} />
                          ))}
                          <LabelList 
                            dataKey="poll" 
                            position="top" 
                            offset={6}
                            formatter={(val: any) => `${val}%`} 
                            className="text-[11px] font-bold fill-slate-700 dark:fill-slate-200" 
                          />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            ) : (
              /* View 2: Clean Horizontal Progress Ranking (100% Anti-overlap on any phone screen) */
              <div className="space-y-2.5 py-2">
                {pollChartData.map((item, index) => {
                  const maxVal = Math.max(...pollChartData.map((d: any) => d.poll || 0), 30);
                  const widthPct = Math.max(6, Math.min(100, ((item.poll || 0) / maxVal) * 100));
                  return (
                    <div 
                      key={item.name || index} 
                      className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 flex items-center gap-3 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800/80"
                    >
                      <div className="w-16 sm:w-20 shrink-0 flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                        <span className="font-bold text-xs text-slate-900 dark:text-white truncate">{item.name}</span>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="h-3.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                          <div 
                            className="h-full rounded-full transition-all duration-500" 
                            style={{ width: `${widthPct}%`, backgroundColor: item.color }} 
                          />
                        </div>
                      </div>

                      <div className="w-20 shrink-0 text-right flex items-center justify-end gap-1.5">
                        <span className="font-black text-xs sm:text-sm font-mono text-slate-900 dark:text-white">{item.poll}%</span>
                        <span className={`text-[10px] font-bold px-1 rounded ${
                          item.trend?.includes("+")
                            ? "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60"
                            : item.trend?.includes("-")
                            ? "text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/60"
                            : "text-slate-400 bg-slate-100 dark:bg-slate-800"
                        }`}>
                          {item.trend || "stabile"}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Polls Cards Grid (Clean Electoral View - NO coperture) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
              {filteredRankings.map((item, idx) => {
                const partyMatch = parties.find((p) => p.code === item.code || p.name === item.name);
                const trendStr = item.poll_trend || partyMatch?.poll_trend || "stabile";
                const sourceStr = partyMatch?.poll_sources || "Media mobile YouTrend / SWG / Ipsos";
                
                return (
                  <Link
                    key={idx}
                    href={`/parties?code=${item.code}`}
                    className="p-4 rounded-2xl bg-slate-50/70 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between group shadow-2xs hover:shadow-xs"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className="w-3.5 h-3.5 rounded-full shrink-0 shadow-xs" style={{ backgroundColor: item.color }} />
                          <div className="min-w-0">
                            <span className="font-bold text-sm text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-snug block">
                              {item.name}
                            </span>
                            <span className="text-[11px] text-slate-500 block leading-tight">
                              {item.coalition}
                            </span>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <div className="text-lg font-black text-slate-900 dark:text-white font-mono leading-none">
                            {item.poll_percentage}%
                          </div>
                          <span className={`inline-block text-[10px] font-bold px-1.5 py-0.2 rounded mt-1 ${
                            trendStr.includes("+")
                              ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/80 dark:text-emerald-400"
                              : trendStr.includes("-")
                              ? "bg-rose-50 text-rose-700 dark:bg-rose-950/80 dark:text-rose-400"
                              : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                          }`}>
                            {trendStr}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="text-[10px] text-slate-400 pt-2.5 border-t border-slate-200/60 dark:border-slate-700/60 leading-tight">
                      {sourceStr}
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 3: STATISTICHE VERIDICITÀ & COPERTURE (PARTITI & COALIZIONI) */}
        {activeTab === "statistiche" && (
          <div className="space-y-6 animate-fadeIn">
            {/* Header intro */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-2">
              <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 font-bold text-xs">
                <ShieldCheck className="w-4 h-4" />
                <span>Analisi Quantitativa Indipendente • Art. 81 Costituzione & Ufficio Parlamentare di Bilancio</span>
              </div>
              <h2 className="text-lg sm:text-xl font-black text-slate-900 dark:text-white tracking-tight">
                Indice di Affidabilità e Rigore di Bilancio per Coalizione e Partito
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed max-w-4xl">
                La veridicità misura la corrispondenza delle proposte ad atti parlamentari, fonti ufficiali o promesse verificate. La copertura finanziaria misura l'indicazione di risorse certe, stime MEF/UPB e sostenibilità economica nel rispetto del pareggio di bilancio.
              </p>
            </div>

            {/* Coalition Aggregates Grid (4 Coalitions) */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {coalitionStats.map((coal) => {
                const isCdx = coal.id === "centrodestra";
                const isCampo = coal.id === "campo_largo";
                const isCenter = coal.id === "centro";

                const badgeBg = isCdx
                  ? "bg-blue-50 text-blue-700 dark:bg-blue-950/80 dark:text-blue-300 border-blue-200 dark:border-blue-800"
                  : isCampo
                  ? "bg-rose-50 text-rose-700 dark:bg-rose-950/80 dark:text-rose-300 border-rose-200 dark:border-rose-800"
                  : isCenter
                  ? "bg-cyan-50 text-cyan-700 dark:bg-cyan-950/80 dark:text-cyan-300 border-cyan-200 dark:border-cyan-800"
                  : "bg-purple-50 text-purple-700 dark:bg-purple-950/80 dark:text-purple-300 border-purple-200 dark:border-purple-800";

                return (
                  <div
                    key={coal.id}
                    className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xs flex flex-col justify-between space-y-4"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${badgeBg}`}>
                          {coal.tag}
                        </span>
                        <span className="text-xs font-mono font-bold text-slate-500">
                          {coal.totalPoll > 0 ? `${coal.totalPoll}% voti` : ""}
                        </span>
                      </div>
                      <h3 className="font-extrabold text-base text-slate-900 dark:text-white">
                        {coal.name}
                      </h3>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {coal.totalProposals} proposte censite • {coal.parties.length} partiti
                      </p>
                    </div>

                    {/* Progress Bars */}
                    <div className="space-y-3 pt-1">
                      <div>
                        <div className="flex justify-between items-center text-xs mb-1">
                          <span className="font-medium text-slate-600 dark:text-slate-400">Veridicità Media</span>
                          <span className="font-mono font-extrabold text-slate-900 dark:text-white">
                            {coal.avgTruth}%
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500 bg-blue-500"
                            style={{ width: `${coal.avgTruth}%` }}
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between items-center text-xs mb-1">
                          <span className="font-medium text-slate-600 dark:text-slate-400">Coperture Finanziarie</span>
                          <span className="font-mono font-extrabold text-slate-900 dark:text-white">
                            {coal.avgFinance}%
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500 bg-emerald-500"
                            style={{ width: `${coal.avgFinance}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Parties Chips */}
                    <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex flex-wrap gap-1.5">
                      {coal.parties.map((p) => (
                        <Link
                          key={p.code}
                          href={`/parties?code=${p.code}`}
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-medium bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
                        >
                          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: p.color }} />
                          <span>{p.name.split(" ")[0]}</span>
                        </Link>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Direct Comparison Spotlight: Centrodestra vs Campo Largo */}
            <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-blue-50 via-slate-50 to-rose-50 dark:from-blue-950/30 dark:via-slate-900 dark:to-rose-950/30 border border-slate-200 dark:border-slate-800">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-1">
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">
                    Sintesi Comparativa Maggioranza vs Principale Opposizione
                  </span>
                  <h4 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white">
                    Confronto Diretto: Centrodestra vs Campo Largo
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-300 max-w-2xl leading-relaxed">
                    Il <strong>Centrodestra</strong> presenta una maggiore veridicità media (<strong>76.8%</strong> vs <strong>70.3%</strong>, +6.5%), favorita dalla presenza di disegni di legge governativi già incardinati nelle commissioni parlamentari. Il <strong>Campo Largo</strong> registra una maggiore copertura finanziaria dichiarata (<strong>74.6%</strong> vs <strong>71.3%</strong>, +3.3%), grazie a proposte coperte da tagli ai sussidi ambientali sfavorevoli, ricalcoli attuariali e strumenti di prestito agevolato (MES Sanitario).
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3 shrink-0">
                  <div className="p-3 rounded-xl bg-white dark:bg-slate-900/90 border border-blue-200 dark:border-blue-900 text-center">
                    <span className="text-[10px] font-bold text-blue-700 dark:text-blue-300 uppercase block">Centrodestra</span>
                    <div className="text-sm font-black text-slate-900 dark:text-white font-mono mt-0.5">
                      76.8% <span className="text-[10px] font-normal text-slate-400">Ver.</span>
                    </div>
                    <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                      71.3% <span className="text-[10px] font-normal text-slate-400">Cop.</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-white dark:bg-slate-900/90 border border-rose-200 dark:border-rose-900 text-center">
                    <span className="text-[10px] font-bold text-rose-700 dark:text-rose-300 uppercase block">Campo Largo</span>
                    <div className="text-sm font-black text-slate-900 dark:text-white font-mono mt-0.5">
                      70.3% <span className="text-[10px] font-normal text-slate-400">Ver.</span>
                    </div>
                    <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                      74.6% <span className="text-[10px] font-normal text-slate-400">Cop.</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Filter & Sort Controls for Party List */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xs">
              {/* Coalition filter pills */}
              <div className="flex items-center gap-1 overflow-x-auto scrollbar-none pb-1 sm:pb-0">
                {[
                  { id: "Tutti", label: "Tutti i Partiti (18)" },
                  { id: "centrodestra", label: "Centrodestra" },
                  { id: "campo_largo", label: "Campo Largo" },
                  { id: "centro", label: "Centro / Liberali" },
                  { id: "altre_forze", label: "Altre Forze" }
                ].map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setStatsCoalitionFilter(f.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all ${
                      statsCoalitionFilter === f.id
                        ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-2xs"
                        : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* Sort pills */}
              <div className="flex items-center gap-1 shrink-0 self-end sm:self-auto">
                <span className="text-[11px] font-medium text-slate-400 mr-1 flex items-center gap-1">
                  <ArrowUpDown className="w-3 h-3" /> Ordina:
                </span>
                {[
                  { id: "truth" as const, label: "Veridicità" },
                  { id: "finance" as const, label: "Coperture" },
                  { id: "poll" as const, label: "Sondaggi" },
                  { id: "proposals" as const, label: "N° Atti" }
                ].map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setStatsSortBy(s.id)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                      statsSortBy === s.id
                        ? "bg-amber-100 dark:bg-amber-950/80 text-amber-900 dark:text-amber-200 font-bold"
                        : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 18 Parties Detailed Table / Cards */}
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 uppercase tracking-wider text-[10px] font-bold">
                    <tr>
                      <th className="py-3 px-4">#</th>
                      <th className="py-3 px-4">Partito / Leader</th>
                      <th className="py-3 px-4">Coalizione</th>
                      <th className="py-3 px-4 min-w-[140px]">Veridicità</th>
                      <th className="py-3 px-4 min-w-[140px]">Coperture Finanziarie</th>
                      <th className="py-3 px-4 text-center">Sondaggio</th>
                      <th className="py-3 px-4 text-center">Atti Censiti</th>
                      <th className="py-3 px-4 text-right">Dossier</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {sortedPartyStats.map((item, idx) => {
                      const truth = item.truthfulness_score || 0;
                      const finance = item.financial_reliability_score || 0;

                      return (
                        <tr
                          key={item.code}
                          className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors group"
                        >
                          <td className="py-3.5 px-4 font-mono font-bold text-slate-400">
                            {idx + 1}
                          </td>
                          <td className="py-3.5 px-4">
                            <Link href={`/parties?code=${item.code}`} className="flex items-center gap-2.5 group-hover:text-blue-600 transition-colors">
                              <span className="w-3.5 h-3.5 rounded-full shrink-0 shadow-xs" style={{ backgroundColor: item.color }} />
                              <div>
                                <div className="font-extrabold text-sm text-slate-900 dark:text-white leading-tight">
                                  {item.name}
                                </div>
                                {item.leader && (
                                  <div className="text-[11px] text-slate-500 leading-tight">
                                    Leader: {item.leader}
                                  </div>
                                )}
                              </div>
                            </Link>
                          </td>
                          <td className="py-3.5 px-4 text-slate-600 dark:text-slate-400 text-xs">
                            {item.coalition}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="space-y-1">
                              <div className="flex justify-between items-center font-mono">
                                <span className="font-bold text-slate-900 dark:text-white">{truth}%</span>
                                <span className={`text-[10px] font-semibold ${
                                  truth >= 80 ? "text-emerald-600 dark:text-emerald-400" :
                                  truth >= 70 ? "text-blue-600 dark:text-blue-400" :
                                  truth >= 60 ? "text-amber-600 dark:text-amber-400" : "text-rose-600 dark:text-rose-400"
                                }`}>
                                  {truth >= 80 ? "Molto Alta" : truth >= 70 ? "Alta" : truth >= 60 ? "Moderata" : "Da verificare"}
                                </span>
                              </div>
                              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    truth >= 80 ? "bg-emerald-500" :
                                    truth >= 70 ? "bg-blue-500" :
                                    truth >= 60 ? "bg-amber-500" : "bg-rose-500"
                                  }`}
                                  style={{ width: `${truth}%` }}
                                />
                              </div>
                            </div>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="space-y-1">
                              <div className="flex justify-between items-center font-mono">
                                <span className="font-bold text-slate-900 dark:text-white">{finance}%</span>
                                <span className={`text-[10px] font-semibold ${
                                  finance >= 80 ? "text-emerald-600 dark:text-emerald-400" :
                                  finance >= 70 ? "text-blue-600 dark:text-blue-400" :
                                  finance >= 60 ? "text-amber-600 dark:text-amber-400" : "text-rose-600 dark:text-rose-400"
                                }`}>
                                  {finance >= 80 ? "Sostenibile" : finance >= 70 ? "Solida" : finance >= 60 ? "Parziale" : "In attesa DDL"}
                                </span>
                              </div>
                              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${
                                    finance >= 80 ? "bg-emerald-500" :
                                    finance >= 70 ? "bg-blue-500" :
                                    finance >= 60 ? "bg-amber-500" : "bg-rose-500"
                                  }`}
                                  style={{ width: `${finance}%` }}
                                />
                              </div>
                            </div>
                          </td>
                          <td className="py-3.5 px-4 text-center font-mono font-bold text-slate-900 dark:text-white">
                            {item.poll_percentage}%
                          </td>
                          <td className="py-3.5 px-4 text-center font-mono text-slate-600 dark:text-slate-400">
                            {item.proposals_count}
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <Link
                              href={`/parties?code=${item.code}`}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-slate-100 hover:bg-blue-600 hover:text-white dark:bg-slate-800 dark:hover:bg-blue-600 text-slate-700 dark:text-slate-300 transition-colors"
                            >
                              <span>Dossier</span>
                              <ChevronRight className="w-3 h-3" />
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={
      <div className="max-w-7xl mx-auto px-4 py-8 space-y-4">
        <div className="h-40 rounded-3xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded-2xl bg-slate-200 dark:bg-slate-800 animate-pulse" />
          ))}
        </div>
      </div>
    }>
      <DashboardContent />
    </Suspense>
  );
}
