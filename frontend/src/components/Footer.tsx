import { Scale, ShieldCheck, ExternalLink } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full bg-slate-900 text-slate-300 border-t border-slate-800 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Col 1: Mission */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2 text-white">
              <Scale className="w-5 h-5 text-blue-400" />
              <span className="font-bold text-lg">PoliticLens</span>
              <span className="text-xs px-2 py-0.5 rounded bg-blue-900/60 text-blue-300 border border-blue-700">
                100% Open-Source
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed max-w-md">
              Piattaforma autonoma e neutrale di analisi e comparazione politica italiana.
              Monitora costantemente programmi, atti parlamentari e testate giornalistiche per generare
              un manifesto dinamico verificato e privo di qualunque giudizio morale o favoritismo ideologico.
            </p>
            <div className="flex items-center gap-2 text-xs text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
              <span>Verifiche conformi ai benchmark ISTAT, MEF, Corte dei Conti ed Eurostat</span>
            </div>
          </div>

          {/* Col 2: Fonti Istituzionali */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-white mb-3">
              Fonti Ufficiali di Verifica
            </h4>
            <ul className="space-y-1.5 text-xs text-slate-400">
              <li>
                <a href="https://www.istat.it" target="_blank" rel="noopener noreferrer" className="hover:text-blue-400 flex items-center gap-1">
                  ISTAT - Conti Nazionali <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a href="https://www.corteconti.it" target="_blank" rel="noopener noreferrer" className="hover:text-blue-400 flex items-center gap-1">
                  Corte dei Conti <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a href="https://www.rgs.mef.gov.it" target="_blank" rel="noopener noreferrer" className="hover:text-blue-400 flex items-center gap-1">
                  Ragioneria Generale dello Stato <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a href="https://www.upbilancio.it" target="_blank" rel="noopener noreferrer" className="hover:text-blue-400 flex items-center gap-1">
                  Ufficio Parlamentare di Bilancio <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a href="https://www.camera.it" target="_blank" rel="noopener noreferrer" className="hover:text-blue-400 flex items-center gap-1">
                  Camera dei Deputati & Senato <ExternalLink className="w-3 h-3" />
                </a>
              </li>
            </ul>
          </div>

          {/* Col 3: Stack & Trasparenza */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-white mb-3">
              Architettura Tecnologica
            </h4>
            <ul className="space-y-1.5 text-xs text-slate-400">
              <li>• FastAPI (Python 3.11+)</li>
              <li>• Ollama (Qwen 2.5 / Llama 3.3)</li>
              <li>• PostgreSQL + pgvector / SQLite</li>
              <li>• Next.js App Router & Tailwind</li>
              <li>• Nessuna API a pagamento</li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <div>
            © {new Date().getFullYear()} PoliticLens. Rilasciato sotto licenza MIT. Costo di licenza zero.
          </div>
          <div className="flex items-center gap-4">
            <span className="text-slate-400">Neutralità Algoritmica Certificata</span>
            <span className="text-slate-600">•</span>
            <a
              href="/admin/visitors"
              className="text-slate-600 hover:text-slate-400 transition flex items-center gap-1 text-[11px]"
              title="Pannello Telemetria Riservato (Solo da questo PC)"
            >
              Telemetria
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
