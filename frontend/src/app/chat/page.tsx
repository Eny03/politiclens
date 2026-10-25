"use client";

import React, { useState, useRef, useEffect } from "react";
import { 
  Bot, 
  Send, 
  Sparkles, 
  Scale, 
  ExternalLink, 
  BookOpen, 
  RotateCcw,
  Copy, 
  Check, 
  CornerDownRight, 
  HelpCircle, 
  TrendingUp, 
  Building2,
  Share2,
  Download,
  ChevronDown,
  ChevronUp,
  Cpu,
  ShieldCheck,
  Search,
  CheckCircle2
} from "lucide-react";
import { CitationItem } from "@/lib/api";
import { MarkdownMessage } from "@/components/MarkdownMessage";

interface ChatStep {
  step: string;
  message: string;
  completed?: boolean;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: CitationItem[];
  disclaimer?: string;
  timestamp: string;
  steps?: ChatStep[];
}

const STARTER_PROMPTS = [
  {
    title: "Evoluzione Salario Minimo",
    query: "Come è cambiata la posizione del PD sul salario minimo dal 2023 ad oggi?",
    mode: "comparativo",
  },
  {
    title: "Lega & Quota 41 nel tempo",
    query: "Come si è evoluta la proposta di Quota 41 della Lega dal 2022 al presente?",
    mode: "comparativo",
  },
  {
    title: "Cuneo & Flat Tax (2022-2026)",
    query: "Quali sono le differenze tra Fratelli d'Italia e il PD su cuneo fiscale e Flat Tax?",
    mode: "confronto_diretto",
  },
  {
    title: "Futuro Nazionale vs ORA!",
    query: "Quali sono le posizioni distinte di Futuro Nazionale rispetto a ORA! su fisco e liberalizzazioni?",
    mode: "confronto_diretto",
  },
  {
    title: "Sanità & Liste d'Attesa",
    query: "Quali sono le proposte dei partiti sul Fondo Sanitario Nazionale e il taglio delle liste d'attesa?",
    mode: "comparativo",
  },
  {
    title: "Verifica Coperture MEF",
    query: "L'aumento delle pensioni minime ha coperture finanziarie certificate dalla Ragioneria Generale dello Stato?",
    mode: "fact_check",
  },
];

const DEFAULT_WELCOME: Message = {
  id: "welcome-1",
  role: "assistant",
  content:
    "Benvenuto su **PoliticLens AI Intelligence**.\n\nAnalizzo l'intero archivio parlamentare, i programmi di governo e le dichiarazioni dei partiti partendo dal 2022 in poi con **monitoraggio continuo e sviluppi futuri** per fornirti **confronti rigorosamente imparziali** e verifiche di bilancio (**MEF, ISTAT, UPB, Corte dei Conti, Art. 81 Cost.**).\n\nPoni qualsiasi domanda, confronta schieramenti o verifica la fattibilità economica di una legge.",
  timestamp: "Oggi",
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([DEFAULT_WELCOME]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<string>("comparativo");
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeSteps, setActiveSteps] = useState<ChatStep[]>([]);
  const [isAccordionOpen, setIsAccordionOpen] = useState(true);
  const [providerLabel, setProviderLabel] = useState<string>("AI Multi-Engine");
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrollingRef = useRef<boolean>(false);

  const handleScroll = () => {
    const container = chatContainerRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    const isScrolledUp = distanceFromBottom > 90;
    isUserScrollingRef.current = isScrolledUp;
    setShowScrollBottomBtn(isScrolledUp);
  };

  const scrollToBottom = (force = false) => {
    if (force) {
      isUserScrollingRef.current = false;
      setShowScrollBottomBtn(false);
    }
    if (!isUserScrollingRef.current && chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  // Load chat history from localStorage on client mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("politiclens_chat_history");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
        }
      }
    } catch (e) {
      console.warn("Failed to read chat history:", e);
    }

    // Check active AI provider
    fetch("/api/chat/provider")
      .then(res => res.json())
      .then(data => {
        if (data && data.label) {
          setProviderLabel(data.label);
        }
      })
      .catch(() => {});
  }, []);

  // Sync to localStorage
  useEffect(() => {
    if (messages.length > 1) {
      try {
        localStorage.setItem("politiclens_chat_history", JSON.stringify(messages));
      } catch (e) {
        console.warn("Failed to persist chat history:", e);
      }
    }
  }, [messages]);

  useEffect(() => {
    scrollToBottom(false);
  }, [messages, loading, activeSteps]);

  const handleSend = async (textToSend?: string, selectedMode?: string) => {
    const queryText = (textToSend || input).trim();
    if (!queryText || loading) return;

    const currentMode = selectedMode || mode;
    const userMsgId = `user-${Date.now()}`;
    const userMsg: Message = {
      id: userMsgId,
      role: "user",
      content: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    setLoading(true);
    setActiveSteps([]);
    setIsAccordionOpen(true);
    setTimeout(() => scrollToBottom(true), 30);

    const assistantMsgId = `assistant-${Date.now()}`;
    let streamedContent = "";
    let capturedCitations: CitationItem[] = [];
    const collectedSteps: ChatStep[] = [];

    // History payload for conversational memory
    const historyPayload = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: queryText,
          mode: currentMode,
          history: historyPayload,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("HTTP error connecting to streaming endpoint");
      }

      // Initialize placeholder assistant message
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: "assistant",
          content: "",
          citations: [],
          disclaimer:
            "PoliticLens opera secondo rigorosa neutralità algoritmica. Le sintesi e le verifiche di bilancio sono elaborate analizzando atti parlamentari e parametri ufficiali MEF, ISTAT e Corte dei Conti.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          steps: [],
        },
      ]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const rawEvent of events) {
          if (!rawEvent.trim()) continue;
          const lines = rawEvent.split("\n");
          let eventType = "";
          let dataStr = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.substring(7).trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.substring(6).trim();
            }
          }

          if (eventType === "step") {
            try {
              const stepObj = JSON.parse(dataStr);
              collectedSteps.push({ ...stepObj, completed: true });
              setActiveSteps([...collectedSteps]);
            } catch (e) {}
          } else if (eventType === "citations") {
            try {
              capturedCitations = JSON.parse(dataStr);
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantMsgId ? { ...m, citations: capturedCitations } : m))
              );
            } catch (e) {}
          } else if (eventType === "token") {
            try {
              const tokenObj = JSON.parse(dataStr);
              streamedContent += tokenObj.token;
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantMsgId ? { ...m, content: streamedContent } : m))
              );
            } catch (e) {}
          } else if (eventType === "done") {
            // Completed
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, content: streamedContent, steps: collectedSteps }
                  : m
              )
            );
          }
        }
      }
    } catch (err: any) {
      console.error("[Streaming Error]", err);
      // Fallback: update the message with error notice
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? {
                ...m,
                content:
                  streamedContent ||
                  "Si è verificato un errore temporaneo nel flusso streaming. Riprova tra qualche istante.",
              }
            : m
        )
      );
    } finally {
      setLoading(false);
      setActiveSteps([]);
    }
  };

  const handleCopy = (content: string, id: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(content);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const handleExportMarkdown = (msg: Message) => {
    const text = `# Risposta PoliticLens AI - ${msg.timestamp}\n\n${msg.content}\n\n---\n*Fonte: PoliticLens Institutional Intelligence*`;
    const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `politiclens_risposta_${Date.now()}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleShare = async (msg: Message) => {
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({
          title: "PoliticLens AI - Intelligence Politica",
          text: msg.content.substring(0, 200) + "...",
          url: window.location.href,
        });
      } catch (e) {}
    } else {
      handleCopy(window.location.href, msg.id);
    }
  };

  const handleReset = () => {
    localStorage.removeItem("politiclens_chat_history");
    setMessages([
      {
        id: `welcome-${Date.now()}`,
        role: "assistant",
        content:
          "Conversazione azzerata. Poni una nuova domanda o seleziona uno dei suggerimenti in alto.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  return (
    <div className="max-w-4xl mx-auto px-3 sm:px-6 py-2 sm:py-4 flex flex-col h-[calc(100dvh-5.5rem)] md:h-[calc(100vh-8.5rem)]">
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 flex items-center justify-center font-bold shadow-xs">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-extrabold text-sm sm:text-base text-slate-900 dark:text-white">
                PoliticLens AI Stream
              </h1>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                Live RAG
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <Cpu className="w-3 h-3 text-blue-500" />
              <span>{providerLabel}</span> • Dati MEF / ISTAT / Camera dal 2022 in tempo reale
            </p>
          </div>
        </div>

        <button
          onClick={handleReset}
          className="p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-1.5 text-xs font-semibold"
          title="Azzera conversazione e cronologia locale"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Nuova Chat</span>
        </button>
      </div>

      {/* Suggested Queries Chips */}
      <div className="flex items-center gap-2 py-2.5 overflow-x-auto shrink-0 scrollbar-none border-b border-slate-100 dark:border-slate-800/60">
        <span className="text-[10px] font-bold text-slate-400 shrink-0 uppercase tracking-wider">
          Temi Chiave:
        </span>
        {STARTER_PROMPTS.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(p.query, p.mode)}
            disabled={loading}
            className="shrink-0 text-xs px-3 py-1.5 rounded-full bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all disabled:opacity-50 shadow-2xs font-medium"
          >
            {p.title}
          </button>
        ))}
      </div>

      {/* Messages Scroll Area */}
      <div 
        ref={chatContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto py-4 space-y-4 pr-1 relative"
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === "user" ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`max-w-[92%] sm:max-w-[85%] rounded-2xl px-4 py-3.5 shadow-xs transition-all ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-xs"
                  : "bg-white dark:bg-slate-900 text-slate-900 dark:text-white border border-slate-200/80 dark:border-slate-800 rounded-bl-xs"
              }`}
            >
              {msg.role === "user" ? (
                <p className="text-xs sm:text-sm font-medium whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                </p>
              ) : (
                <div className="space-y-3">
                  {/* Historical Thinking steps attached to message */}
                  {msg.steps && msg.steps.length > 0 && (
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60 text-xs">
                      <div className="flex items-center gap-1.5 font-bold text-slate-600 dark:text-slate-300 mb-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        <span>Verifiche Istituzionali Completate ({msg.steps.length})</span>
                      </div>
                      <div className="space-y-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                        {msg.steps.map((st, sIdx) => (
                          <div key={sIdx} className="flex items-center gap-1.5">
                            <span className="w-1 h-1 rounded-full bg-emerald-500" />
                            <span>{st.message}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Message Content */}
                  {msg.content ? (
                    <MarkdownMessage content={msg.content} />
                  ) : (
                    <div className="flex items-center gap-2 text-xs text-slate-400 py-1">
                      <div className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
                      <span>Elaborazione token in tempo reale...</span>
                    </div>
                  )}

                  {/* Citations Grid */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/80">
                      <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 dark:text-slate-400 mb-2">
                        <BookOpen className="w-3.5 h-3.5 text-blue-500" />
                        <span>Fonti Istituzionali & Atti Formali Citati ({msg.citations.length})</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {msg.citations.map((c, cIdx) => (
                          <a
                            key={cIdx}
                            href={c.fonte_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 hover:border-blue-300 dark:hover:border-blue-600 transition-colors flex flex-col justify-between group"
                          >
                            <div>
                              <div className="flex items-center justify-between text-[10px] font-bold mb-1">
                                <span className="text-blue-600 dark:text-blue-400">{c.partito}</span>
                                <span className="text-slate-400">{c.timestamp}</span>
                              </div>
                              <p className="text-xs text-slate-700 dark:text-slate-300 font-medium leading-relaxed">
                                {c.sintesi}
                              </p>
                            </div>
                            <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                              <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                                {c.fact_check_status}
                              </span>
                              <span className="inline-flex items-center gap-0.5 group-hover:text-blue-500">
                                <span>{c.fonte_testata || "Atti Ufficiali"}</span>
                                <ExternalLink className="w-2.5 h-2.5" />
                              </span>
                            </div>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Bottom Action Toolbar */}
                  <div className="mt-2 pt-2 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-100 dark:border-slate-800/50">
                    <span>{msg.timestamp}</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleCopy(msg.content, msg.id)}
                        className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 transition-colors flex items-center gap-1 text-[10px]"
                        title="Copia testo"
                      >
                        {copiedId === msg.id ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-500" />
                            <span className="text-emerald-500">Copiato</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span>Copia</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => handleExportMarkdown(msg)}
                        className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 transition-colors flex items-center gap-1 text-[10px]"
                        title="Esporta in Markdown"
                      >
                        <Download className="w-3 h-3" />
                        <span className="hidden sm:inline">Esporta</span>
                      </button>

                      <button
                        onClick={() => handleShare(msg)}
                        className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-700 dark:hover:text-slate-200 transition-colors flex items-center gap-1 text-[10px]"
                        title="Condividi"
                      >
                        <Share2 className="w-3 h-3" />
                        <span className="hidden sm:inline">Condividi</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Live Active Thinking Accordion during Streaming */}
        {loading && activeSteps.length > 0 && (
          <div className="max-w-[92%] sm:max-w-[85%] rounded-2xl bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/60 p-3.5 shadow-xs">
            <button
              onClick={() => setIsAccordionOpen(!isAccordionOpen)}
              className="w-full flex items-center justify-between text-left text-xs font-bold text-blue-900 dark:text-blue-200"
            >
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-ping" />
                <span>AI Reasoning & Pipeline di Analisi in Corso ({activeSteps.length} passi)</span>
              </div>
              {isAccordionOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {isAccordionOpen && (
              <div className="mt-2.5 space-y-1.5 text-xs text-blue-800 dark:text-blue-300 pl-4 border-l-2 border-blue-400">
                {activeSteps.map((s, idx) => (
                  <div key={idx} className="flex items-center gap-2 animate-fadeIn">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                    <span>{s.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {showScrollBottomBtn && (
          <button
            type="button"
            onClick={() => scrollToBottom(true)}
            className="sticky bottom-2 left-1/2 -translate-x-1/2 px-3.5 py-1.5 rounded-full bg-slate-900/90 hover:bg-slate-900 text-white dark:bg-white/95 dark:hover:bg-white dark:text-slate-900 text-xs font-bold shadow-lg transition-all flex items-center gap-1.5 backdrop-blur-xs z-10 mx-auto"
          >
            <span>↓ Torna in basso</span>
          </button>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="pt-2 shrink-0 border-t border-slate-200 dark:border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="relative flex items-center"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Chiedi un confronto, evoluzione storica 2022-2026 o coperture di una legge..."
            disabled={loading}
            className="w-full pl-4 pr-24 py-3 rounded-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-xs sm:text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 shadow-xs disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-2 px-3.5 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 dark:disabled:bg-slate-800 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors shadow-xs"
          >
            <span>Invia</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
        <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-400 px-1">
          <span>Tutte le risposte citano vincoli MEF e art. 81 Cost.</span>
          <span>Premere Invio per inviare</span>
        </div>
      </div>
    </div>
  );
}
