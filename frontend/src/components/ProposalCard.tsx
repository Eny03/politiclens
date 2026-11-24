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
        className="group bg-white dark:bg-slate-900/85 backdrop-blur-xs rounded-2xl border border-slate-200/85 dark:border-slate-800/90 hover:border-blue-400/70 dark:hover:border-blue-500/50 hover:shadow-lg hover:shadow-slate-900/5 dark:hover:shadow-black/30 hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between shadow-xs cursor-pointer select-none relative overflow-hidden"
      >
        {/* Subtle top party-color hairline */}
        <div
          className="h-[3px] w-full opacity-85 group-hover:opacity-100 transition-opacity"
          style={{ backgroundColor: partyColor }}
        />

        <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between">
          <div>
            {/* Top: Party & Topic & Historical Pill */}
            <div className="flex items-center justify-between gap-2 mb-2.5">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0 ring-2 ring-white dark:ring-slate-900 shadow-xs"
                  style={{ backgroundColor: partyColor }}
                />
                <span className="font-bold text-xs text-slate-900 dark:text-slate-100 tracking-tight truncate">
                  {proposal.partito}
                </span>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {isHistorical && (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300 border border-amber-200/60 dark:border-amber-800/60 whitespace-nowrap font-mono">
                    {proposalYear}
                  </span>
                )}
                <TopicBadge topic={proposal.macro_argomento} />
              </div>
            </div>

            {/* Action type subtle pill */}
            <div className="mb-1.5">
              <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                {proposal.tipo_azione || "Posizione Politica"}
              </span>
            </div>

            {/* Clear, Concise Headline without truncation */}
            <h3 className="text-slate-900 dark:text-slate-100 text-[13.5px] sm:text-sm font-bold leading-relaxed mb-3.5 group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors">
              {proposal.dichiarazione_sintesi}
            </h3>
          </div>

          <div>
            {/* Institutional Fact-Check Badge & Cost Estimate */}
            <div className="pt-2.5 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center gap-1.5 mb-3 text-[11px]">
              <StatusBadge
                status={proposal.fact_check_status}
                score={proposal.truth_score !== undefined && proposal.truth_score !== null ? Math.round(proposal.truth_score) : undefined}
                size="sm"
              />

              <span 
                title="Fattibilità Economica: compatibilità con l'Art. 81 Costituzione e coperture di bilancio"
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100/90 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 border border-slate-200/70 dark:border-slate-700/70"
              >
                <Coins className="w-2.5 h-2.5 text-amber-500 shrink-0" />
                <span className="font-medium truncate max-w-[145px] text-[10px]">
                  {proposal.costo_stimato && proposal.costo_stimato.trim() !== ""
                    ? proposal.costo_stimato
                    : "Non quantificato"}
                </span>
              </span>
            </div>

            {/* Footer Info & Expand Trigger */}
            <div className="pt-2.5 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px]">
              <span className="flex items-center gap-1.5 font-mono text-slate-400 dark:text-slate-500">
                <Calendar className="w-3 h-3 text-slate-400" />
                {formattedDate}
              </span>
              
              <div className="inline-flex items-center gap-1 font-bold text-slate-700 dark:text-slate-200 group-hover:text-blue-600 dark:group-hover:text-blue-400 group-hover:translate-x-0.5 transition-all">
                <span>Dossier & Atti</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </div>
            </div>
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
