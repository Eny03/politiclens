"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  Users,
  Radio,
  Globe,
  Smartphone,
  Monitor,
  Tablet,
  Eye,
  RefreshCw,
  Search,
  Filter,
  ShieldAlert,
  ShieldCheck,
  Lock,
  Unlock,
  Key,
  Clock,
  ArrowLeft,
  Activity,
  Trash2,
  CheckCircle2,
  AlertCircle,
  ExternalLink
} from "lucide-react";
import {
  fetchVisitorStats,
  fetchVisitorList,
  verifyAdminAccess,
  loginAdmin,
  clearVisitorLogs,
  VisitorStatsResponse,
  VisitorIPItem
} from "@/lib/api";

export default function AdminVisitorsPage() {
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [clientIp, setClientIp] = useState<string>("");
  const [secretInput, setSecretInput] = useState<string>("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<boolean>(false);

  // Telemetry data
  const [stats, setStats] = useState<VisitorStatsResponse | null>(null);
  const [visitors, setVisitors] = useState<VisitorIPItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  // Filters & Search
  const [filterType, setFilterType] = useState<string>("all"); // "all", "online_now", "today"
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Clear modal
  const [clearing, setClearing] = useState<boolean>(false);

  // Check initial authorization (reads localStorage or query key)
  useEffect(() => {
    async function checkAuth() {
      // Check query parameter ?key=... or ?auth_key=...
      const urlParams = new URLSearchParams(window.location.search);
      const queryKey = urlParams.get("key") || urlParams.get("auth_key");
      const activeToken = queryKey || localStorage.getItem("politiclens_admin_token") || "";

      if (queryKey) {
        localStorage.setItem("politiclens_admin_token", queryKey);
      }

      try {
        const verifyRes = await verifyAdminAccess(activeToken);
        setClientIp(verifyRes.client_ip || "");
        if (verifyRes.authorized) {
          setAuthorized(true);
        } else {
          setAuthorized(false);
        }
      } catch {
        setAuthorized(false);
      }
    }
    checkAuth();
  }, []);

  const loadData = useCallback(async () => {
    const token = localStorage.getItem("politiclens_admin_token") || "";
    try {
      setLoading(true);
      const [statsData, listData] = await Promise.all([
        fetchVisitorStats(token),
        fetchVisitorList({ search: searchQuery.trim(), filter_type: filterType, limit: 150 }, token)
      ]);
      setStats(statsData);
      setVisitors(listData.visitors || []);
      setLastRefreshed(new Date());
      setAuthorized(true);
    } catch (err: any) {
      if (err?.message === "403_FORBIDDEN") {
        setAuthorized(false);
      } else {
        console.error("Error loading visitor telemetry:", err);
      }
    } finally {
      setLoading(false);
    }
  }, [searchQuery, filterType]);

  // Load telemetry when authorized
  useEffect(() => {
    if (authorized) {
      loadData();
    }
  }, [authorized, loadData]);

  // Auto-refresh interval (every 10 seconds)
  useEffect(() => {
    if (!authorized || !autoRefresh) return;
    const interval = setInterval(() => {
      loadData();
    }, 10000);
    return () => clearInterval(interval);
  }, [authorized, autoRefresh, loadData]);

  // Handle manual login/unlock
  const handleAuthorizeDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    try {
      const res = await loginAdmin(secretInput.trim());
      if (res.success && res.token) {
        localStorage.setItem("politiclens_admin_token", res.token);
        setAuthSuccess(true);
        setTimeout(() => {
          setAuthorized(true);
        }, 500);
      }
    } catch (err: any) {
      setAuthError(err.message || "Chiave segreta non valida.");
    }
  };

  const handleClearLogs = async () => {
    if (!confirm("Sei sicuro di voler azzerare il registro di tracciamento dei visitatori?")) return;
    const token = localStorage.getItem("politiclens_admin_token") || "";
    try {
      setClearing(true);
      await clearVisitorLogs(token);
      await loadData();
    } catch (err) {
      alert("Errore durante la cancellazione dei log.");
    } finally {
      setClearing(false);
    }
  };

  // -------------------------------------------------------------
  // Render: Unauthorized View (Protezione Solo per Questo PC)
  // -------------------------------------------------------------
  if (authorized === false) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
          <div className="w-14 h-14 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-xl flex items-center justify-center mx-auto mb-5">
            <Lock className="w-7 h-7" />
          </div>

          <h1 className="text-xl font-bold text-center text-white mb-2">
            Accesso Riservato Amministratore
          </h1>
          <p className="text-sm text-slate-400 text-center mb-6 leading-relaxed">
            Questa sezione è riservata esclusivamente al proprietario su <strong className="text-white">questo PC</strong> per visualizzare il numero di utenti online e l&apos;elenco degli indirizzi IP.
          </p>

          <form onSubmit={handleAuthorizeDevice} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Chiave Master di Sblocco
              </label>
              <div className="relative">
                <input
                  type="password"
                  value={secretInput}
                  onChange={(e) => setSecretInput(e.target.value)}
                  placeholder="Inserisci la Master Key..."
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            {authError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-400 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            {authSuccess && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-400 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>Dispositivo autorizzato! Caricamento in corso...</span>
              </div>
            )}

            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-xl transition shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2"
            >
              <Unlock className="w-4 h-4" />
              <span>Autorizza Questo PC</span>
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
            <span>IP rilevato: {clientIp || "in verifica..."}</span>
            <Link href="/" className="text-blue-400 hover:underline">
              Torna alla Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // Render: Authorized Telemetry Dashboard
  // -------------------------------------------------------------
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 pb-16">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
              title="Torna alla Home"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-white tracking-tight">
                  Telemetria & Monitoraggio Visitatori
                </h1>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Questo PC Autorizzato
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Piattaforma di sorveglianza traffico in tempo reale • PoliticLens Observer
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Auto refresh switch */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                autoRefresh
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                  : "bg-slate-800 border-slate-700 text-slate-400"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  autoRefresh ? "bg-emerald-400 animate-pulse" : "bg-slate-500"
                }`}
              />
              Auto-refresh (10s): {autoRefresh ? "Attivo" : "Disattivato"}
            </button>

            {/* Manual refresh button */}
            <button
              onClick={() => loadData()}
              disabled={loading}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition disabled:opacity-50"
              title="Aggiorna ora"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-400" : ""}`} />
            </button>

            {/* Clear logs button */}
            <button
              onClick={handleClearLogs}
              disabled={clearing}
              className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg transition"
              title="Azzera registro visitatori"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        {/* 4 Top Metric Cards */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Online Adesso */}
          <div className="bg-gradient-to-br from-emerald-950/40 via-slate-900 to-slate-900 border border-emerald-500/30 rounded-2xl p-5 relative overflow-hidden shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                </span>
                Online Adesso
              </span>
              <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-xl">
                <Radio className="w-5 h-5" />
              </div>
            </div>
            <div className="text-3xl font-extrabold text-white">
              {stats?.online_now_count ?? 0}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Dispositivi attivi negli ultimi 5 minuti
            </p>
          </div>

          {/* Card 2: Visitatori Oggi */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
                Visitatori Unici Oggi
              </span>
              <div className="p-2 bg-blue-500/10 text-blue-400 rounded-xl">
                <Users className="w-5 h-5" />
              </div>
            </div>
            <div className="text-3xl font-extrabold text-white">
              {stats?.today_visitors_count ?? 0}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              IP unici registrati oggi dalle ore 00:00
            </p>
          </div>

          {/* Card 3: Visitatori Totali */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                Visitatori Totali Storici
              </span>
              <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl">
                <Globe className="w-5 h-5" />
              </div>
            </div>
            <div className="text-3xl font-extrabold text-white">
              {stats?.total_visitors_count ?? 0}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Totale di tutti gli IP unici censiti
            </p>
          </div>

          {/* Card 4: Pagine Viste Totali */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">
                Visualizzazioni Pagine
              </span>
              <div className="p-2 bg-purple-500/10 text-purple-400 rounded-xl">
                <Eye className="w-5 h-5" />
              </div>
            </div>
            <div className="text-3xl font-extrabold text-white">
              {stats?.total_page_views ?? 0}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Richieste e consultazioni totali
            </p>
          </div>
        </section>

        {/* Breakdown Visuals (Dispositivi, Browser, Top Paths) */}
        {stats && (
          <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Dispositivi */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-blue-400" />
                Ripartizione Dispositivi
              </h3>
              <div className="space-y-3">
                {Object.entries(stats.device_breakdown || {}).map(([dev, count]) => {
                  const total = stats.total_page_views || 1;
                  const pct = Math.round((count / total) * 100);
                  return (
                    <div key={dev}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-300 font-medium">{dev}</span>
                        <span className="text-slate-400">{count} ({pct}%)</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Browser */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Monitor className="w-4 h-4 text-indigo-400" />
                Browser Più Utilizzati
              </h3>
              <div className="space-y-3">
                {Object.entries(stats.browser_breakdown || {}).map(([br, count]) => {
                  const total = stats.total_page_views || 1;
                  const pct = Math.round((count / total) * 100);
                  return (
                    <div key={br}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-300 font-medium">{br}</span>
                        <span className="text-slate-400">{count} ({pct}%)</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Pagine più visitate */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
              <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                Pagine Più Consultate
              </h3>
              <div className="space-y-2.5">
                {(stats.top_paths || []).slice(0, 5).map((p, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-xs p-2 bg-slate-950/60 rounded-xl border border-slate-800/80"
                  >
                    <span className="font-mono text-slate-300 truncate max-w-[180px]">
                      {p.path === "/" ? "/ (Home)" : p.path}
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-slate-800 font-semibold text-emerald-400 text-xs">
                      {p.count} visite
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Detailed IP Address Table */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          {/* Table Header Controls */}
          <div className="p-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-white">
                Registro Dettagliato degli Indirizzi IP
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Elenco completo di tutti gli IP che si sono collegati, con data, dispositivo e storico delle pagine
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Filter Pills */}
              <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                <button
                  onClick={() => setFilterType("all")}
                  className={`px-3 py-1.5 rounded-lg transition font-medium ${
                    filterType === "all"
                      ? "bg-slate-800 text-white shadow"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Tutti ({stats?.total_visitors_count ?? 0})
                </button>
                <button
                  onClick={() => setFilterType("online_now")}
                  className={`px-3 py-1.5 rounded-lg transition font-medium flex items-center gap-1.5 ${
                    filterType === "online_now"
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Online Adesso ({stats?.online_now_count ?? 0})
                </button>
                <button
                  onClick={() => setFilterType("today")}
                  className={`px-3 py-1.5 rounded-lg transition font-medium ${
                    filterType === "today"
                      ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Oggi ({stats?.today_visitors_count ?? 0})
                </button>
              </div>

              {/* Search IP Input */}
              <div className="relative">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Cerca IP o pagina..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 w-48"
                />
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 uppercase font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-5 py-3.5">Stato Presenza</th>
                  <th className="px-5 py-3.5">Indirizzo IP</th>
                  <th className="px-5 py-3.5">Dispositivo & Browser</th>
                  <th className="px-5 py-3.5 text-center">Visite</th>
                  <th className="px-5 py-3.5">Ultima Attività</th>
                  <th className="px-5 py-3.5">Prima Rilevazione</th>
                  <th className="px-5 py-3.5">Pagine Consultate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {visitors.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-10 text-center text-slate-500">
                      Nessun visitatore trovato per i filtri selezionati.
                    </td>
                  </tr>
                ) : (
                  visitors.map((v) => {
                    const isCurrentPC = clientIp && v.ip_address.includes(clientIp);
                    return (
                      <tr
                        key={v.ip_address}
                        className={`hover:bg-slate-800/30 transition ${
                          v.is_online_now ? "bg-emerald-950/10" : ""
                        }`}
                      >
                        {/* Status */}
                        <td className="px-5 py-4 whitespace-nowrap">
                          {v.is_online_now ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                              Online Adesso
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400">
                              Offline
                            </span>
                          )}
                        </td>

                        {/* IP Address */}
                        <td className="px-5 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-semibold text-white tracking-wide">
                              {v.ip_address}
                            </span>
                            {isCurrentPC && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                                Questo PC
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Device & Browser */}
                        <td className="px-5 py-4 whitespace-nowrap">
                          <div className="text-slate-200 font-medium">
                            {v.device_type}
                          </div>
                          <div className="text-slate-500 text-[11px]">
                            {v.browser} • {v.os_name}
                          </div>
                        </td>

                        {/* Visit Count */}
                        <td className="px-5 py-4 text-center whitespace-nowrap">
                          <span className="px-2.5 py-1 rounded-lg bg-slate-800/80 font-bold text-slate-200">
                            {v.total_visits}
                          </span>
                        </td>

                        {/* Last Seen */}
                        <td className="px-5 py-4 whitespace-nowrap text-slate-300">
                          {v.last_seen ? (
                            <div>
                              <div>{new Date(v.last_seen).toLocaleTimeString("it-IT")}</div>
                              <div className="text-slate-500 text-[11px]">
                                {new Date(v.last_seen).toLocaleDateString("it-IT")}
                              </div>
                            </div>
                          ) : (
                            "—"
                          )}
                        </td>

                        {/* First Seen */}
                        <td className="px-5 py-4 whitespace-nowrap text-slate-400">
                          {v.first_seen ? (
                            <div>
                              <div>{new Date(v.first_seen).toLocaleTimeString("it-IT")}</div>
                              <div className="text-slate-500 text-[11px]">
                                {new Date(v.first_seen).toLocaleDateString("it-IT")}
                              </div>
                            </div>
                          ) : (
                            "—"
                          )}
                        </td>

                        {/* Visited Paths */}
                        <td className="px-5 py-4">
                          <div className="flex flex-wrap gap-1.5 max-w-xs">
                            {v.recent_paths && v.recent_paths.length > 0 ? (
                              v.recent_paths.map((p, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-950 text-slate-400 border border-slate-800"
                                >
                                  {p === "/" ? "Home" : p.replace("/", "")}
                                </span>
                              ))
                            ) : (
                              <span className="text-slate-500 font-mono text-[11px]">{v.last_path}</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Table Footer */}
          <div className="p-4 bg-slate-950/60 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
            <div>
              Ultimo aggiornamento automatico:{" "}
              <strong className="text-slate-400">{lastRefreshed.toLocaleTimeString("it-IT")}</strong>
            </div>
            <div>
              Visualizzati {visitors.length} IP unici filtrati
            </div>
          </div>
        </section>

        {/* Security / Privacy Institutional Notice */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 text-xs text-slate-400 flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div className="space-y-1 leading-relaxed">
            <h4 className="font-semibold text-slate-200">
              Protezione della Privacy & Accesso Esclusivo da Questo PC
            </h4>
            <p>
              I dati di telemetria, gli indirizzi IP e i log di connessione sono protetti e visibili <strong>esclusivamente da questo computer</strong>.
              Qualsiasi utente che cerchi di accedere a questo pannello o alle relative API da altri dispositivi o dall&apos;esterno senza la Master Key viene bloccato con un codice di protezione 403 Forbidden.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
