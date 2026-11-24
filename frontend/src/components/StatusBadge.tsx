import React from "react";
import { CheckCircle2, Check, AlertTriangle, AlertCircle, HelpCircle, XCircle, FileText } from "lucide-react";

interface StatusBadgeProps {
  status: string;
  score?: number;
  size?: "sm" | "md";
}

export function StatusBadge({ status, score, size = "md" }: StatusBadgeProps) {
  const normStatus = status?.toLowerCase() || "";
  const iconSize = size === "sm" ? "w-2.5 h-2.5 shrink-0" : "w-3.5 h-3.5 shrink-0";

  let colorClasses = "bg-slate-50 text-slate-700 border-slate-200 dark:bg-slate-800/60 dark:text-slate-300 dark:border-slate-700";
  let icon = <HelpCircle className={iconSize} />;

  if (normStatus.includes("parzialmente")) {
    colorClasses = "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-950/40 dark:text-teal-300 dark:border-teal-800/60";
    icon = <Check className={iconSize} />;
  } else if (normStatus.includes("verificato")) {
    colorClasses = "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60";
    icon = <CheckCircle2 className={iconSize} />;
  } else if (normStatus.includes("programmatica")) {
    colorClasses = "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800/60";
    icon = <FileText className={iconSize} />;
  } else if (normStatus.includes("copertura")) {
    colorClasses = "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60";
    icon = <AlertTriangle className={iconSize} />;
  } else if (normStatus.includes("esagerato")) {
    colorClasses = "bg-orange-50 text-orange-800 border-orange-200 dark:bg-orange-950/40 dark:text-orange-300 dark:border-orange-800/60";
    icon = <AlertCircle className={iconSize} />;
  } else if (normStatus.includes("inattuabile") || normStatus.includes("fake") || normStatus.includes("infondato")) {
    colorClasses = "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/60";
    icon = <XCircle className={iconSize} />;
  }

  const padding = size === "sm" 
    ? "px-2 py-0.5 text-[10px] font-semibold" 
    : "px-2.5 py-1 text-xs font-semibold";

  const hasScore = score !== undefined && score !== null;

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border whitespace-nowrap shrink-0 shadow-2xs ${padding} ${colorClasses}`}>
      {icon}
      {hasScore && (
        <span className="font-mono font-bold tracking-tight">{Math.round(score)}%</span>
      )}
      {hasScore && <span className="opacity-40">•</span>}
      <span>{status}</span>
    </span>
  );
}
