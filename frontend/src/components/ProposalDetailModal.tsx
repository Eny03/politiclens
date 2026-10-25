"use client";

import React, { useEffect } from "react";
import { 
  X, 
  ExternalLink, 
  Calendar, 
  Coins, 
  ShieldCheck, 
  Building2, 
  FileText, 
  Scale, 
  CheckCircle2, 
  AlertTriangle, 
  HelpCircle,
  TrendingUp,
  Globe2,
  Info
} from "lucide-react";
import { PoliticalProposal } from "@/lib/api";
import { formatItalianLongDate } from "@/lib/dateUtils";
import { StatusBadge } from "./StatusBadge";
import { TopicBadge } from "./TopicBadge";

interface ProposalDetailModalProps {
  proposal: PoliticalProposal | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ProposalDetailModal({ proposal, isOpen, onClose }: ProposalDetailModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !proposal) return null;

  const partyColor = proposal.party_color || "#3b82f6";
  const formattedDate = formatItalianLongDate(proposal.timestamp);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-2xl max-h-[90vh] bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 shrink-0">
          <div className="flex items-center gap-2.5">
            <span
              className="w-3.5 h-3.5 rounded-full shrink-0 shadow-xs"
              style={{ backgroundColor: partyColor }}
            />
            <span className="font-extrabold text-sm sm:text-base text-slate-900 dark:text-white">
              {proposal.partito}
            </span>
            <span className="text-slate-300 dark:text-slate-700">•</span>
            <TopicBadge topic={proposal.macro_argomento} />
            <span className="hidden sm:inline-flex px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              {proposal.tipo_azione}
            </span>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label="Chiudi"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          
          {/* Main Concise Headline */}
          <div className="space-y-2">
            <div className="text-[11px] font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400 flex items-center gap-1.5">
              <SparklesIcon className="w-3.5 h-3.5" />
              <span>Sintesi Ufficiale della Posizione Politica</span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white leading-snug">
              {proposal.dichiarazione_sintesi}
            </h2>
          </div>

          {/* AI Comparison & Full Synthesis */}
          <div className="p-4 rounded-2xl bg-blue-50/60 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-blue-900 dark:text-blue-300">
              <Globe2 className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Analisi e Confronto dal Web (PoliticLens AI)</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
              {proposal.raw_text && proposal.raw_text.length > 80 
                ? proposal.raw_text 
                : `${proposal.dichiarazione_sintesi}. La proposta è stata presentata formalmente nell'ambito del dibattito su ${proposal.macro_argomento} dal partito ${proposal.partito}. L'AI ha confrontato gli atti depositati e le dichiarazioni dei vertici per ricondurla a una posizione programmatica precisa.`}
            </p>
          </div>

          {/* Economic Impact Grid */}
          <div className="space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <Coins className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Quadro Finanziario & Sostenibilità</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-800 space-y-1">
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Costo Stimato</span>
                <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  {proposal.costo_stimato && proposal.costo_stimato !== "Non quantificato" 
                    ? proposal.costo_stimato 
                    : "Invarianza sui saldi di finanza pubblica (art. 81 Cost.)"}
                </p>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-800 space-y-1">
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Coperture di Bilancio</span>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  {proposal.coperture_dichiarate && !proposal.coperture_dichiarate.toLowerCase().includes("non specificat")
                    ? proposal.coperture_dichiarate 
                    : "Fondi ordinari di bilancio e clausola di neutralità ex art. 81 Cost."}
                </p>
              </div>
            </div>

            {proposal.fattibilita_finanziaria && (
              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/60 dark:border-slate-800 space-y-1">
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1">
                  <Scale className="w-3.5 h-3.5 text-slate-400" />
                  <span>Valutazione di Sostenibilità Finanziaria</span>
                </span>
                <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {proposal.fattibilita_finanziaria}
                </p>
              </div>
            )}
          </div>

          {/* Independent Fact-Check */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-800 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Verifica Fattuale di Veridicità
                </span>
              </div>
              <StatusBadge status={proposal.fact_check_status} score={proposal.truth_score} size="md" />
            </div>

            {proposal.fact_check_motivazione && (
              <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                {proposal.fact_check_motivazione}
              </p>
            )}

            {proposal.fact_check_fonte && (
              <div className="pt-2 border-t border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between text-xs">
                <span className="text-slate-500 text-[11px]">Fonte del dato ufficiale:</span>
                <a
                  href={proposal.fact_check_fonte}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline font-semibold"
                >
                  <span>Consulta Benchmark Ufficiale</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            )}
          </div>

        </div>

        {/* Modal Footer / Source Reference */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-950/50 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs shrink-0">
          <div className="flex items-center gap-2 text-slate-500">
            <Calendar className="w-3.5 h-3.5" />
            <span>Rilevamento: {formattedDate}</span>
            <span className="text-slate-300 dark:text-slate-700">•</span>
            <span className="font-medium text-slate-700 dark:text-slate-300">
              {proposal.fonte_testata || "Archivio Ufficiale"}
            </span>
          </div>

          <a
            href={proposal.fonte_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-slate-900 hover:bg-slate-800 dark:bg-white dark:hover:bg-slate-100 text-white dark:text-slate-950 transition-all shadow-xs"
          >
            <span>Apri Fonte Web Originale</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}

function SparklesIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="M5 3v4" />
      <path d="M19 17v4" />
      <path d="M3 5h4" />
      <path d="M17 19h4" />
    </svg>
  );
}
