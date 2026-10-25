import React from "react";
import { CheckCircle2, AlertTriangle, AlertCircle, HelpCircle, XCircle } from "lucide-react";

interface StatusBadgeProps {
  status: string;
  score?: number;
  size?: "sm" | "md";
}

export function StatusBadge({ status, score, size = "md" }: StatusBadgeProps) {
  const normStatus = status?.toLowerCase() || "";
  
  let colorClasses = "bg-slate-50 text-slate-700 border-slate-200 dark:bg-slate-800/60 dark:text-slate-300 dark:border-slate-700";
  let icon = <HelpCircle className={size === "sm" ? "w-2.5 h-2.5" : "w-3.5 h-3.5"} />;

  if (normStatus.includes("verificato")) {
    colorClasses = "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60";
    icon = <CheckCircle2 className={size === "sm" ? "w-2.5 h-2.5 shrink-0" : "w-3.5 h-3.5 shrink-0"} />;
  } else if (normStatus.includes("copertura")) {
    colorClasses = "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60";
    icon = <AlertTriangle className={size === "sm" ? "w-2.5 h-2.5 shrink-0" : "w-3.5 h-3.5 shrink-0"} />;
  } else if (normStatus.includes("esagerato")) {
    colorClasses = "bg-orange-50 text-orange-800 border-orange-200 dark:bg-orange-950/40 dark:text-orange-300 dark:border-orange-800/60";
    icon = <AlertCircle className={size === "sm" ? "w-2.5 h-2.5 shrink-0" : "w-3.5 h-3.5 shrink-0"} />;
  } else if (normStatus.includes("inattuabile") || normStatus.includes("fake") || normStatus.includes("infondato")) {
    colorClasses = "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/60";
    icon = <XCircle className={size === "sm" ? "w-2.5 h-2.5 shrink-0" : "w-3.5 h-3.5 shrink-0"} />;
  }

  const padding = size === "sm" 
    ? "px-2 py-0.5 text-[10px] font-semibold" 
    : "px-2.5 py-1 text-xs font-semibold";

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border whitespace-nowrap shrink-0 shadow-2xs ${padding} ${colorClasses}`}>
      {icon}
      {score !== undefined && (
        <span className="font-mono font-bold tracking-tight">{score}%</span>
      )}
      {score !== undefined && <span className="opacity-40">•</span>}
      <span>{status}</span>
    </span>
  );
}
