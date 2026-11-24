"use client";

import React from "react";
import { 
  Building2, 
  ExternalLink, 
  CheckCircle2, 
  TrendingUp, 
  Coins, 
  ShieldCheck, 
  Layers,
  ChevronRight,
  Info,
  AlertTriangle,
  Flame,
  CheckCircle,
  Scale
} from "lucide-react";

interface MarkdownMessageProps {
  content: string;
}

// Inline parser for bold, italic, links, tags, and citation pills
function renderInline(text: string): React.ReactNode[] {
  // Regex matches: [link](url) | **bold** | *italic* | `code` | [^1] / [1]
  const tokenRegex = /(\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|\[(\d+)\])/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = tokenRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const fullMatch = match[0];
    if (fullMatch.startsWith("[") && match[2] && match[3]) {
      // Safe Link (allow only http(s) or relative root paths)
      const hrefUrl = match[3].trim();
      const isSafeUrl = /^https?:\/\//i.test(hrefUrl) || hrefUrl.startsWith("/");
      if (isSafeUrl) {
        parts.push(
          <a
            key={`link-${match.index}`}
            href={hrefUrl}
            target={hrefUrl.startsWith("/") ? undefined : "_blank"}
            rel={hrefUrl.startsWith("/") ? undefined : "noopener noreferrer"}
            className="text-blue-600 dark:text-blue-400 font-semibold underline underline-offset-2 hover:text-blue-800 dark:hover:text-blue-300 inline-flex items-center gap-0.5 mx-0.5"
          >
            <span>{match[2]}</span>
            {!hrefUrl.startsWith("/") && <ExternalLink className="w-2.5 h-2.5 inline shrink-0" />}
          </a>
        );
      } else {
        parts.push(match[2]);
      }
    } else if (match[7]) {
      // Citation pill [1], [2]
      parts.push(
        <span
          key={`cite-${match.index}`}
          className="inline-flex items-center justify-center px-1.5 py-0.2 text-[10px] font-black rounded-full bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 align-super mx-0.5 shadow-xs"
        >
          {match[7]}
        </span>
      );
    } else if (fullMatch.startsWith("**") && match[4]) {
      // Bold - with highlight if it contains financial keywords
      const boldText = match[4];
      const isFinancial = /art\.?\s*81|mef|istat|invarianza|patto di stabilità|corte dei conti|upb/i.test(boldText);
      parts.push(
        <strong 
          key={`b-${match.index}`} 
          className={`font-black ${isFinancial ? "text-amber-700 dark:text-amber-400 bg-amber-500/10 px-1 py-0.5 rounded" : "text-slate-900 dark:text-white"}`}
        >
          {boldText}
        </strong>
      );
    } else if (fullMatch.startsWith("*") && match[5]) {
      // Italic
      parts.push(
        <em key={`i-${match.index}`} className="italic text-slate-700 dark:text-slate-300">
          {match[5]}
        </em>
      );
    } else if (fullMatch.startsWith("`") && match[6]) {
      // Code / Pill
      const codeText = match[6];
      const isCost = /mld|mln|€|invarianza/i.test(codeText);
      parts.push(
        <code
          key={`c-${match.index}`}
          className={`inline-block leading-snug font-mono text-[11px] px-1.5 py-0.5 rounded-md border font-semibold ${
            isCost 
              ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border-emerald-300/60 dark:border-emerald-700/60"
              : "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 border-slate-200/60 dark:border-slate-700/60"
          }`}
        >
          {codeText}
        </code>
      );
    }

    lastIndex = tokenRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts;
}

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];

  let i = 0;
  while (i < lines.length) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // 1. Table Detection (| col | col |)
    if (trimmed.startsWith("|") && trimmed.endsWith("|") && i + 1 < lines.length && lines[i + 1].includes("---")) {
      const headerCols = trimmed.split("|").slice(1, -1).map(c => c.trim());
      i += 2; // skip header & separator line
      const tableRows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith("|") && lines[i].trim().endsWith("|")) {
        const rowCols = lines[i].trim().split("|").slice(1, -1).map(c => c.trim());
        tableRows.push(rowCols);
        i++;
      }
      elements.push(
        <div key={`table-${i}`} className="my-3 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-xs">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-slate-100/90 dark:bg-slate-800/80 text-slate-700 dark:text-slate-200 uppercase tracking-wider text-[11px] font-bold">
              <tr>
                {headerCols.map((col, cIdx) => (
                  <th key={cIdx} className="px-3.5 py-2.5 border-b border-slate-200 dark:border-slate-700 font-extrabold">
                    {renderInline(col)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/60 dark:divide-slate-800">
              {tableRows.map((row, rIdx) => (
                <tr key={rIdx} className={rIdx % 2 === 0 ? "bg-white dark:bg-slate-900/40" : "bg-slate-50/50 dark:bg-slate-800/20"}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="px-3.5 py-2 text-slate-700 dark:text-slate-300">
                      {renderInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // 2. Unordered List Items (- or *)
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      const listItems: string[] = [];
      while (i < lines.length && (lines[i].trim().startsWith("- ") || lines[i].trim().startsWith("* "))) {
        listItems.push(lines[i].trim().slice(2));
        i++;
      }
      elements.push(
        <ul key={`ul-${i}`} className="my-2 space-y-1.5 pl-1">
          {listItems.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0 mt-2 shadow-xs" />
              <div className="flex-1">{renderInline(item)}</div>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // 3. Numbered List Items (1. , 2. )
    if (/^\d+\.\s+/.test(trimmed)) {
      const numItems: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        numItems.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i++;
      }
      elements.push(
        <ol key={`ol-${i}`} className="my-2 space-y-1.5 pl-1">
          {numItems.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed">
              <span className="flex items-center justify-center w-4 h-4 rounded-full bg-blue-100 dark:bg-blue-900/70 text-blue-700 dark:text-blue-300 text-[10px] font-black shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <div className="flex-1">{renderInline(item)}</div>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // 4. Alert / Callout Boxes (> [!NOTE], > [!TIP], > [!WARNING], > [!IMPORTANT])
    if (trimmed.startsWith("> [!NOTE]") || trimmed.startsWith("> [!TIP]") || trimmed.startsWith("> [!WARNING]") || trimmed.startsWith("> [!IMPORTANT]") || trimmed.startsWith("> ")) {
      let calloutType = "note";
      let textContent = trimmed;

      if (trimmed.startsWith("> [!NOTE]")) {
        calloutType = "note";
        textContent = trimmed.replace("> [!NOTE]", "").trim();
      } else if (trimmed.startsWith("> [!TIP]")) {
        calloutType = "tip";
        textContent = trimmed.replace("> [!TIP]", "").trim();
      } else if (trimmed.startsWith("> [!WARNING]")) {
        calloutType = "warning";
        textContent = trimmed.replace("> [!WARNING]", "").trim();
      } else if (trimmed.startsWith("> [!IMPORTANT]")) {
        calloutType = "important";
        textContent = trimmed.replace("> [!IMPORTANT]", "").trim();
      } else {
        textContent = trimmed.slice(2).trim();
      }

      // Collect consecutive quote lines
      i++;
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        textContent += " " + lines[i].trim().slice(1).trim();
        i++;
      }

      const styles = {
        note: {
          border: "border-blue-500",
          bg: "bg-blue-50/70 dark:bg-blue-950/30",
          text: "text-blue-900 dark:text-blue-200",
          icon: <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
        },
        tip: {
          border: "border-emerald-500",
          bg: "bg-emerald-50/70 dark:bg-emerald-950/30",
          text: "text-emerald-900 dark:text-emerald-200",
          icon: <CheckCircle className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
        },
        warning: {
          border: "border-amber-500",
          bg: "bg-amber-50/70 dark:bg-amber-950/30",
          text: "text-amber-900 dark:text-amber-200",
          icon: <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        },
        important: {
          border: "border-purple-500",
          bg: "bg-purple-50/70 dark:bg-purple-950/30",
          text: "text-purple-900 dark:text-purple-200",
          icon: <Scale className="w-4 h-4 text-purple-600 dark:text-purple-400 shrink-0 mt-0.5" />
        }
      }[calloutType] || {
        border: "border-blue-500",
        bg: "bg-blue-50/50 dark:bg-blue-950/20",
        text: "text-slate-800 dark:text-slate-200",
        icon: <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
      };

      elements.push(
        <div
          key={`callout-${i}`}
          className={`my-3 p-3 border-l-4 ${styles.border} ${styles.bg} rounded-r-xl text-xs sm:text-sm flex items-start gap-2.5 shadow-xs`}
        >
          {styles.icon}
          <div className={`flex-1 ${styles.text} leading-relaxed`}>
            {renderInline(textContent)}
          </div>
        </div>
      );
      continue;
    }

    // 5. Divider
    if (trimmed === "---" || trimmed === "***") {
      elements.push(
        <hr
          key={`hr-${i}`}
          className="my-3 border-t border-slate-200 dark:border-slate-800"
        />
      );
      i++;
      continue;
    }

    // 6a. Heading 1 & 2: # / ##
    if (trimmed.startsWith("# ") || trimmed.startsWith("## ")) {
      const headingText = trimmed.replace(/^#{1,2}\s+/, "");
      elements.push(
        <div
          key={`h2-${i}`}
          className="mt-4 mb-2 pt-2 border-t border-slate-200/80 dark:border-slate-800 first:border-0 first:pt-0"
        >
          <h2 className="text-sm sm:text-base font-black tracking-tight text-slate-900 dark:text-white flex items-center gap-1.5">
            {renderInline(headingText)}
          </h2>
        </div>
      );
      i++;
      continue;
    }

    // 6. Heading 3: ###
    if (trimmed.startsWith("### ")) {
      const headingText = trimmed.slice(4);
      elements.push(
        <div
          key={`h3-${i}`}
          className="mt-3.5 mb-1.5 pt-2 border-t border-slate-100 dark:border-slate-800/80 first:border-0 first:pt-0"
        >
          <h3 className="text-xs sm:text-sm font-black tracking-tight text-slate-900 dark:text-white flex items-center gap-1.5">
            {renderInline(headingText)}
          </h3>
        </div>
      );
      i++;
      continue;
    }

    // 7. Heading 4: ####
    if (trimmed.startsWith("#### ")) {
      const headingText = trimmed.slice(5);
      elements.push(
        <h4
          key={`h4-${i}`}
          className="mt-2.5 mb-1 text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1"
        >
          {renderInline(headingText)}
        </h4>
      );
      i++;
      continue;
    }

    // 8. Empty line / spacer
    if (!trimmed) {
      elements.push(<div key={`empty-${i}`} className="h-1.5" />);
      i++;
      continue;
    }

    // 9. Standard Paragraph
    elements.push(
      <p
        key={`p-${i}`}
        className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed my-1"
      >
        {renderInline(trimmed)}
      </p>
    );
    i++;
  }

  return <div className="space-y-0.5">{elements}</div>;
}
