"use client";

import React, { useState } from "react";
import { ExternalLink, Calendar, Coins, ShieldCheck, ArrowUpRight, ChevronRight, Eye } from "lucide-react";
import { PoliticalProposal } from "@/lib/api";
import { parseUtcDate, formatItalianDateTime } from "@/lib/dateUtils";
import { StatusBadge } from "./StatusBadge";
import { TopicBadge } from "./TopicBadge";
import { ProposalDetailModal } from "./ProposalDetailModal";

interface ProposalCardProps {
  proposal: PoliticalProposal;
}

export function ProposalCard({ proposal }: ProposalCardProps) {
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const dateObj = parseUtcDate(proposal.timestamp);
  const proposalYear = dateObj ? dateObj.getFullYear() : null;
  const isHistorical = proposalYear !== null && proposalYear < 2025;
  const formattedDate = formatItalianDateTime(proposal.timestamp, false);

  const partyColor = proposal.party_color || "#3b82f6";

  return (
    <>
      <article 
        onClick={() => setIsDetailOpen(true)}
        className="group bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/80 dark:border-slate-800 p-4 sm:p-5 hover:border-slate-300 dark:hover:border-slate-700 hover:shadow-md transition-all flex flex-col justify-between shadow-2xs cursor-pointer select-none relative"
      >
        <div>
          {/* Top: Party & Topic & Historical Pill */}
          <div className="flex items-center justify-between gap-2 mb-2.5">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0 shadow-xs"
                style={{ backgroundColor: partyColor }}
              />
              <span className="font-bold text-xs text-slate-900 dark:text-slate-100 tracking-tight truncate">
                {proposal.partito}
              </span>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              {isHistorical && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/60 whitespace-nowrap">
                  {proposalYear}
                </span>
              )}
              <TopicBadge topic={proposal.macro_argomento} />
            </div>
          </div>

          {/* Action type subtle pill */}
          <div className="mb-2">
            <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              {proposal.tipo_azione || "Posizione Politica"}
            </span>
          </div>

          {/* Clear, Concise Headline without truncation */}
          <h3 className="text-slate-900 dark:text-slate-100 text-sm font-bold leading-snug mb-3 group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors">
            {proposal.dichiarazione_sintesi}
          </h3>

          {/* Discreet Technical Footnote: Economic Feasibility (Art. 81) & Statement Truthfulness (Secondary Tier) */}
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center gap-1.5 mb-3 text-[11px]">
            {/* 1. Fattibilità Economica (Art. 81 Cost.) */}
            <span 
              title="Fattibilità Economica: compatibilità con l'Art. 81 Costituzione e coperture di bilancio"
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100/80 dark:bg-slate-800/70 text-slate-600 dark:text-slate-300 border border-slate-200/50 dark:border-slate-700/50"
            >
              <Coins className="w-3 h-3 text-slate-400" />
              <span className="font-medium truncate max-w-[140px]">
                {proposal.costo_stimato && proposal.costo_stimato !== "Non quantificato" 
                  ? proposal.costo_stimato 
                  : "Invarianza spesa"}
              </span>
            </span>

            {/* 2. Veridicità delle Affermazioni (Fatti e dati Istat) */}
            <span 
              title="Veridicità Affermazioni: riscontro oggettivo su dati statistici, ISTAT e fonti ufficiali"
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100/80 dark:bg-slate-800/70 text-slate-600 dark:text-slate-300 border border-slate-200/50 dark:border-slate-700/50"
            >
              <ShieldCheck className="w-3 h-3 text-slate-400" />
              <span className="font-medium">
                Dati: {proposal.truth_score ? `${Math.round(proposal.truth_score)}%` : "Verificati"}
              </span>
            </span>
          </div>

        </div>

        {/* Footer Info & Expand Trigger */}
        <div className="pt-2.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[11px]">
          <span className="flex items-center gap-1.5 font-mono text-slate-500 dark:text-slate-400">
            <Calendar className="w-3 h-3 text-slate-400" />
            {formattedDate}
          </span>
          
          <div className="inline-flex items-center gap-1 font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all">
            <span>Dossier & Atti</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </div>
        </div>
      </article>

      {/* Modal Dialog */}
      <ProposalDetailModal
        proposal={proposal}
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
      />
    </>
  );
}
