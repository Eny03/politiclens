"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  Compass, 
  Layers, 
  Building2, 
  ShieldCheck, 
  Bot, 
  Rss, 
  MoreVertical, 
  X,
  Scale,
  History,
  Sun,
  Moon
} from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [isDark, setIsDark] = useState<boolean>(false);

  useEffect(() => {
    const saved = localStorage.getItem("politiclens_theme") || localStorage.getItem("politilens_theme");
    if (saved === "dark") {
      setIsDark(true);
      document.documentElement.classList.add("dark");
    } else {
      setIsDark(false);
      document.documentElement.classList.remove("dark");
    }
  }, []);

  // Close menu on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  // Lock body scroll and handle Escape key when lateral menu is open
  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen]);

  const toggleTheme = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (nextDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("politiclens_theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("politiclens_theme", "light");
    }
  };

  // Client-side keepalive heartbeat: pings /api/health every 4 minutes while the app is open
  useEffect(() => {
    const keepalive = () => {
      fetch("/api/health").catch(() => {});
    };
    const interval = setInterval(keepalive, 240000);
    return () => clearInterval(interval);
  }, []);

  const allSections = [
    { 
      name: "Manifesto & Idee", 
      desc: "Raccolta e confronto delle proposte politiche, programmi e battaglie dei partiti", 
      href: "/", 
      icon: <Compass className="w-5 h-5 text-blue-600 dark:text-blue-400" /> 
    },
    { 
      name: "Confronto Programmi", 
      desc: "Matrice di confronto tematico e comparatore testa a testa tra partiti", 
      href: "/compare", 
      icon: <Layers className="w-5 h-5 text-indigo-600 dark:text-indigo-400" /> 
    },
    { 
      name: "Partiti & Leader", 
      desc: "Dossier programmatici completi, schede e posizioni ufficiali per ogni partito", 
      href: "/parties", 
      icon: <Building2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" /> 
    },
    { 
      name: "Chat AI Assistente", 
      desc: "Interroga i programmi e gli atti parlamentari con citazioni trasparenti", 
      href: "/chat", 
      icon: <Bot className="w-5 h-5 text-purple-600 dark:text-purple-400" /> 
    },
    { 
      name: "Quadro Tecnico & Bilanci", 
      desc: "Scheda tecnica: fattibilità economica (Art. 81 Cost.) e veridicità delle affermazioni", 
      href: "/fact-check", 
      icon: <ShieldCheck className="w-5 h-5 text-amber-600 dark:text-amber-400" /> 
    },
    { 
      name: "Fonti & Rassegna", 
      desc: "Monitoraggio continuo feed RSS, DDL e rassegna stampa istituzionale", 
      href: "/sources", 
      icon: <Rss className="w-5 h-5 text-sky-600 dark:text-sky-400" /> 
    },
    { 
      name: "Registro Modifiche & Audit", 
      desc: "Storico immutabile delle variazioni demoscopiche e revisioni delle proposte", 
      href: "/audit", 
      icon: <History className="w-5 h-5 text-teal-600 dark:text-teal-400" /> 
    },
  ];

  const desktopNav = [
    { label: "Manifesto", href: "/", icon: <Compass className="w-3.5 h-3.5" /> },
    { label: "Confronto", href: "/compare", icon: <Layers className="w-3.5 h-3.5" /> },
    { label: "Partiti", href: "/parties", icon: <Building2 className="w-3.5 h-3.5" /> },
    { label: "Chat AI", href: "/chat", icon: <Bot className="w-3.5 h-3.5" /> },
    { label: "Fact-Check", href: "/fact-check", icon: <ShieldCheck className="w-3.5 h-3.5" /> },
    { label: "Fonti", href: "/sources", icon: <Rss className="w-3.5 h-3.5" /> },
    { label: "Audit", href: "/audit", icon: <History className="w-3.5 h-3.5" /> },
  ];

  return (
    <>
      <header className="sticky top-0 z-40 w-full max-w-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200/90 dark:border-slate-800 shadow-2xs">
        {/* Striscia Tricolore Bandiera Italiana in Cima */}
        <div className="h-[3.5px] w-full grid grid-cols-3 shadow-xs">
          <div className="bg-[#009246]" />
          <div className="bg-white dark:bg-slate-200" />
          <div className="bg-[#ce2b37]" />
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 gap-3">
            {/* Brand Logo: Solo Icona, Nome App e Live */}
            <Link href="/" className="flex items-center gap-2 sm:gap-3 group min-w-0 shrink-0">
              <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-slate-900 dark:bg-blue-600 flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform border border-slate-700/50 shrink-0">
                <Scale className="w-4 h-4 sm:w-5 sm:h-5 text-amber-300 dark:text-white" />
              </div>
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-extrabold text-base sm:text-lg lg:text-xl tracking-tight text-slate-900 dark:text-white">
                  PoliticLens
                </span>
                <span className="flex items-center gap-1.5 text-[10px] sm:text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 shrink-0">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Live
                </span>
              </div>
            </Link>

            {/* Direct Desktop Navigation Links */}
            <nav aria-label="Navigazione principale" className="hidden lg:flex items-center gap-1 bg-slate-100/80 dark:bg-slate-800/70 p-1 rounded-2xl border border-slate-200/70 dark:border-slate-700/70">
              {desktopNav.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                      isActive
                        ? "bg-white dark:bg-slate-900 text-blue-700 dark:text-blue-400 shadow-xs"
                        : "text-slate-600 dark:text-slate-300 hover:text-slate-950 dark:hover:text-white hover:bg-white/60 dark:hover:bg-slate-800"
                    }`}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Right Actions: Quick Theme Toggle + Menu Drawer */}
            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={toggleTheme}
                className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors flex items-center justify-center min-h-[40px] min-w-[40px] shadow-2xs cursor-pointer"
                aria-label={isDark ? "Attiva tema chiaro" : "Attiva tema scuro"}
                title={isDark ? "Tema Chiaro" : "Tema Scuro"}
              >
                {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
              </button>

              <button
                type="button"
                onClick={() => setMenuOpen((prev) => !prev)}
                className="p-2 sm:px-2.5 sm:py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 transition-colors flex items-center justify-center min-h-[40px] min-w-[40px] shadow-2xs relative z-50 cursor-pointer"
                aria-label="Menu laterale (tutte le sezioni)"
                title="Menu principale (⋮)"
              >
                {menuOpen ? (
                  <X className="w-5 h-5 text-slate-700 dark:text-slate-200" />
                ) : (
                  <MoreVertical className="w-5 h-5 text-slate-700 dark:text-slate-200" />
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Lateral Slide-Over Drawer (Right Side) - Works 100% reliably on PC and Mobile */}
      {menuOpen && (
        <div className="fixed inset-0 z-[150] flex justify-end">
          {/* Backdrop overlay */}
          <div 
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-xs transition-opacity animate-in fade-in duration-200" 
            onClick={() => setMenuOpen(false)}
            aria-hidden="true"
          />

          {/* Right-Side Lateral Drawer Panel */}
          <aside 
            className="relative z-10 w-full sm:w-[420px] h-full max-h-screen bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200"
            role="dialog"
            aria-modal="true"
            aria-label="Menu di navigazione"
          >
            {/* Header with Title and Close Button */}
            <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-100 dark:border-slate-800 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
                  <Scale className="w-4 h-4" />
                </div>
                <div>
                  <div className="font-bold text-sm text-slate-900 dark:text-white leading-tight">
                    PoliticLens Menu
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Navigazione & Strumenti Civici
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-800 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                aria-label="Chiudi menu"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable Navigation List */}
            <div className="flex-1 overflow-y-auto overscroll-contain p-4 sm:p-5 space-y-2">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 pb-1">
                Sezioni della Piattaforma
              </div>

              {allSections.map((sec) => {
                const isActive = pathname === sec.href;
                return (
                  <Link
                    key={sec.href}
                    href={sec.href}
                    onClick={() => setMenuOpen(false)}
                    className={`p-3 rounded-2xl border transition-all flex items-start gap-3 group ${
                      isActive
                        ? "bg-blue-50/80 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800 shadow-2xs"
                        : "bg-slate-50/70 dark:bg-slate-800/40 border-slate-200/70 dark:border-slate-800 hover:bg-white dark:hover:bg-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                    }`}
                  >
                    <div className="p-2 rounded-xl bg-white dark:bg-slate-800 shadow-2xs border border-slate-100 dark:border-slate-700 shrink-0 group-hover:scale-105 transition-transform">
                      {sec.icon}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className={`text-xs sm:text-sm font-bold ${isActive ? "text-blue-900 dark:text-blue-300" : "text-slate-900 dark:text-white"}`}>
                          {sec.name}
                        </span>
                        {isActive && (
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                            Attiva
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">
                        {sec.desc}
                      </p>
                    </div>
                  </Link>
                );
              })}
            </div>

            {/* Footer inside Drawer */}
            <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/60 shrink-0 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">Tema Visivo:</span>
                <button
                  type="button"
                  onClick={toggleTheme}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors cursor-pointer"
                >
                  {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-slate-600" />}
                  <span>{isDark ? "Tema Chiaro" : "Tema Scuro"}</span>
                </button>
              </div>

              <div className="flex items-center gap-2 text-[10px] text-slate-400 pt-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0 animate-pulse" />
                <span>Aggiornato in tempo reale con fonti pubbliche e atti ufficiali</span>
              </div>
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
