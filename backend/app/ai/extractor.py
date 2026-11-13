import json
import re
import datetime
from typing import Optional, Dict, Any, List
from app.config import settings
from app.schemas import ProposalExtractionSchema, ImpattoEconomicoSchema, FactCheckSchema
from app.ai.llm_provider import llm_provider
from app.ai.fact_checker import analyze_feasibility_and_factcheck
from app.ai.fiscal_calculator import calculate_fiscal_impact_and_coverage, sanitize_proposal_title
from app.ai.proposal_validator import sanitize_and_validate_proposal_statement
from app.ingestion.sources_config import PARTY_ALIASES, MACRO_TOPICS_KEYWORDS

EXTRACTION_SYSTEM_PROMPT = """Sei l'assistente AI analista politico e istituzionale neutrale di PoliticLens.
Il tuo compito è analizzare il testo di notizie, comunicati stampa o atti parlamentari ed estrarre ESCLUSIVAMENTE REALI PROPOSTE POLITICHE e RIFORME PROGRAMMATICHE dei partiti in formato JSON rigoroso.

LINEE GUIDA INDEROGABILI:
1. TRASFORMAZIONE IN PROPOSTA POLITICA: Non riportare mai una notizia o un titolo passivamente. Analizza il tema ed enuncia in 'dichiarazione_sintesi' la specifica proposta di legge, misura o presa di posizione di policy pubblica del partito (es: "Introduzione di una moratoria sui pignoramenti...", "Taglio delle accise compensato da...", "Incremento del fondo sanitario al 7.5% PIL...", "Riforma della giustizia con separazione delle carriere...").
2. ESCLUSIONE NOTIZIE NON POLITICO-PROGRAMMATICHE: Se l'articolo riguarda gossip, congressi di partito, dimissioni o candidature interne, polemiche personali senza atti di indirizzo, cronaca giudiziaria o nera, cerimonie o dichiarazioni generiche non riconducibili a una proposta politica concreta di governo o opposizione, DEVI ESCLUDERLO COMPLETAMENTE restituendo un array JSON vuoto: [].
3. VALUTAZIONE DI VERIDICITÀ PUNTUALE: Non usare genericamente 'Non verificabile' per proposte normative/istituzionali; se sono riforme a invarianza finanziaria assegna 'Verificato'. Se comportano spesa pubblica senza dettagli di copertura assegna 'In attesa di copertura'. Se i dati dichiarati contrastano con ISTAT/Eurostat/Banca d'Italia assegna 'Esagerato'.
4. Neutralità politica assoluta e rispetto dei fatti oggettivi.

Rispondi ESCLUSIVAMENTE con un oggetto JSON valido (o un array di oggetti JSON se ci sono più proposte/partiti), oppure [] se il testo non contiene una proposta politica:
{
  "partito": "Nome Partito",
  "macro_argomento": "Economia | Energia | Ambiente | Diritti Civili | Esteri | Lavoro | Sanità | Istruzione | Istituzioni | Giustizia | Infrastrutture | Pensioni | Fisco",
  "dichiarazione_sintesi": "Proposta politica chiara e specifica (es: 'Disegno di legge per...', 'Moratoria su...', 'Taglio strutturale di...')",
  "tipo_azione": "Proposta di legge | Dichiarazione programmatica | Opposizione | Emendamento",
  "impatto_economico": {
    "costo_stimato": "Cifra in € o 'Non quantificato'",
    "coperture_dichiarate": "Da dove il partito intende reperire i fondi",
    "fattibilita_finanziaria": "Analisi oggettiva basata su vincoli di bilancio / PIL"
  },
  "fact_check": {
    "status": "Verificato | In attesa di copertura | Esagerato | Fake / Infondato | Inattuabile",
    "motivazione_oggettiva": "Motivazione basata sui dati ISTAT, Eurostat, Corte dei Conti, UPB",
    "fonte_verifica": "Link o riferimento istituzionale"
  },
  "fonte_url": "URL dell'articolo/documento",
  "timestamp": "ISO 8601"
}
"""

# Non-policy keywords and noise patterns to strictly exclude from database
NON_POLICY_PATTERNS = [
    r"lancio di sassi", r"scontri.*polizia", r"arrestat[oa]", r"incidente mortale", r"indagine per corruzione",
    r"si dimette da segretario", r"sfida al congresso", r"candidat[oa] al congresso", r"modifica del simbolo",
    r"pranzo tra", r"karaoke", r"leopolda", r"marchese del grillo", r"ha ancora un problema con il voto",
    r"pioggia di critiche", r"siete voi che l'avete affondata", r"concentrato dei peggiori stereotipi",
    r"non ho la sindrome dell'abbandono", r"sto benissimo anche da", r"san francesco dal vicentino",
    r"vertice arraiolos", r"allentamento delle sanzioni usa premiano", r"tre sfide per l'europa",
    r"decisioni pi[ùu] veloci della ue", r"aria pesante per i riformisti", r"verso il congresso anticipato",
    r"il giudice d[àa] ragione all'opposizione", r"chi [èe] l'ex ministro bocconiano", r"prepara la direzione",
    r"relazione della segretaria.*video", r"garanzia [èe] che non rifaremo gli errori", r"nessuno lo legge",
    r"vivaio di idee", r"anche fedez tra gli ospiti", r"acclamato candidato dai vertici", r"resta il tris",
    r"punto stampa.*piazza montecitorio", r"i dati certificano il risanamento", r"replica al pd"
]

OPPOSITION_PARTIES = {
    "Partito Democratico", "Movimento 5 Stelle", "Alleanza Verdi e Sinistra",
    "Rifondazione Comunista", "Potere al Popolo", "+Europa", "Radicali Italiani"
}

GOVERNMENT_PARTIES = {
    "Fratelli d'Italia", "Lega - Salvini Premier", "Forza Italia", "Noi Moderati", "Futuro Nazionale"
}

POLICY_ACTION_TRANSFORMATIONS = [
    (r"(?:stop|moratoria|blocco).*(?:pignorament|cartelle|esecuzion|sovraindebitamento)", "sovraindebitamento"),
    (r"(?:\bsalario minimo\b|\b9\s*euro\b|\b9€\b)", "salario_minimo"),
    (r"(?:\bcuneo fiscale\b|\btaglio del cuneo\b|\bdecontribuzione\b)", "cuneo_fiscale"),
    (r"(?:\bpensioni a 64\b|\buscita a 64\b|\bnodo tfr\b|\bquota 41\b)", "pensioni_flessibili"),
    (r"(?:\blsu\b|\blpu\b|lavoratori socialmente utili)", "lsu_lpu"),
    (r"(?:\btfr.*no tax area\b|\bcarta sanit[àa]\b|\btaglio irpef.*ceto medio\b)", "fisco_ceto_medio"),
    (r"(?:trasparenza.*prestazioni sanitarie|costi.*prestazioni sanitarie)", "sanita_trasparenza"),
    (r"(?:gioco.*tabacco|accise.*carburant)", "accise_carburanti"),
    (r"(?:propaganda russa|interferenz|disinformazione)", "interferenze_estere"),
    (r"(?:costi delle proposte|scheda tecnica|\bupb\b|trasparenza dei programmi)", "trasparenza_upb"),
    (r"(?:\bius scholae\b|cittadinanza.*scuola)", "ius_scholae"),
    (r"(?:separazione delle carriere|\bcsm\b|riforma.*giustizia)", "giustizia_carriere"),
    (r"(?:\bnucleare\b|\breattori smr\b|\biv generazione\b)", "nucleare"),
    (r"(?:rinnovabili|parchi eolici|comunit[àa] energetic|solare)", "rinnovabili"),
    (r"(?:affitti brevi|partita iva|locazioni turistiche)", "affitti_brevi"),
    (r"(?:trivelle|commissario.*trivelle|idrocarburi)", "energia_fossile"),
    (r"(?:aiuti a kiev|stop alle armi|forniture militari|negoziati di pace|\bspese militari\b)", "armi_ucraina"),
    (r"(?:fondo sanitario|7\.5% del pil|7,5% del pil)", "fondo_sanitario"),
    (r"(?:\bautonomia differenziata\b|\blegge calderoli\b|\blep\b)", "autonomia_differenziata"),
    (r"(?:\bpremierato\b|\belezione diretta del premier\b|\bddl casellati\b)", "premierato"),
    (r"(?:patrimoniale|grandi ricchezze|super ricchi|next generation tax)", "patrimoniale"),
    (r"(?:cannabis|fine vita|eutanasia legale)", "diritti_etici"),
    (r"(?:legittima difesa|caso roggero|arma da fuoco|difesa.*abitazione)", "legittima_difesa"),
    (r"(?:rigenerazione urbana|confesercenti|negozi di vicinato|commercio)", "commercio_vicinato"),
    (r"(?:detassazione premi|fringe benefit|welfare aziendale)", "fringe_benefit"),
    (r"(?:sicurezza sul lavoro|omicidio sul lavoro|patente a crediti)", "sicurezza_lavoro"),
    (r"(?:cedolare secca|canone concordato|piano casa)", "piano_casa"),
    (r"(?:asili nido gratis|congedo parentale|quoziente familiare)", "famiglia_nidi"),
    (r"(?:botta e risposta.*patrimoniale|conte.*patrimoniale|bonelli.*patrimoniale|extraprofitti)", "extraprofitti")
]

def resolve_policy_transformation(policy_key: str, party_name: str) -> tuple:
    """
    Returns (statement, topic, action_type) tailored to the specific party and political alignment.
    Eliminates political inversions and decontextualized policy assignments.
    """
    if policy_key == "sovraindebitamento":
        return ("Moratoria e sospensione fino a 180 giorni delle procedure esecutive di pignoramento a tutela dei nuclei familiari e debitori in sovraindebitamento", "Economia", "Proposta di legge")

    if policy_key == "salario_minimo":
        if party_name == "Potere al Popolo":
            return ("Salario minimo legale a 10 euro lordi l'ora indicizzato all'inflazione reale con ripristino della scala mobile", "Lavoro", "Proposta di legge")
        elif party_name in {"Partito Democratico", "Movimento 5 Stelle", "Alleanza Verdi e Sinistra", "Rifondazione Comunista"}:
            return ("Introduzione del salario minimo legale a 9 euro lordi l'ora per tutti i lavoratori privi di contratti collettivi nazionali maggiormente rappresentativi", "Lavoro", "Proposta di legge")
        elif party_name == "Azione":
            return ("Salario minimo a 9 euro garantito tramite l'estensione erga omnes dei contratti collettivi leader e defiscalizzazione dei premi", "Lavoro", "Proposta di legge")
        elif party_name in {"Partito Liberal Democratico", "ORA!"}:
            return ("Abolizione dei vincoli erga omnes sui contratti nazionali e passaggio alla contrattazione aziendale e territoriale basata sulla produttività", "Lavoro", "Proposta di legge")
        return ("Priorità al rafforzamento della contrattazione collettiva di settore e detassazione dei premi di produttività rispetto al salario minimo legale", "Lavoro", "Dichiarazione programmatica")

    if policy_key == "cuneo_fiscale":
        return ("Taglio strutturale del cuneo fiscale contributivo sui redditi da lavoro dipendente fino a 35.000 euro e decontribuzione per neo-assunti", "Lavoro", "Dichiarazione programmatica")

    if policy_key == "pensioni_flessibili":
        return ("Riforma previdenziale: anticipo dell'uscita pensionistica a 64 anni con ricalcolo contributivo integrale e facoltà di conferimento del TFR a previdenza integrativa", "Pensioni", "Proposta di legge")

    if policy_key == "lsu_lpu":
        return ("Disegno di legge per il pieno riconoscimento previdenziale e la pensione equa dei lavoratori socialmente utili (LSU e LPU)", "Lavoro", "Proposta di legge")

    if policy_key == "fisco_ceto_medio":
        return ("Manovra fiscale per il ceto medio: riduzione del secondo scaglione IRPEF al 33%, estensione della no tax area under 30 e Carta Sanità per over 65", "Fisco", "Proposta di legge")

    if policy_key == "sanita_trasparenza":
        return ("Disegno di legge per la pubblicazione obbligatoria, comparativa e trasparente dei costi effettivi e dei tempi di attesa di tutte le prestazioni sanitarie", "Sanità", "Proposta di legge")

    if policy_key == "accise_carburanti":
        return ("Rimodulazione fiscale con aumento del prelievo erariale su tabacchi e giochi d'azzardo a integrale copertura della riduzione delle accise sui carburanti", "Fisco", "Proposta di legge")

    if policy_key == "interferenze_estere":
        return ("Disegno di legge per l'istituzione di una commissione d'inchiesta e presidi sanzionatori contro le interferenze estere e la disinformazione geopolitica online", "Politica Estera", "Proposta di legge")

    if policy_key == "trasparenza_upb":
        return ("Obbligo di legge di allegare una quantificazione finanziaria preventiva e asseverata dall'Ufficio Parlamentare di Bilancio per ciascuna proposta elettorale", "Istituzioni", "Proposta di legge")

    if policy_key == "ius_scholae":
        if party_name in {"Lega - Salvini Premier", "Fratelli d'Italia", "Futuro Nazionale"}:
            return ("Contrarietà alla modifica della legge sulla cittadinanza n. 91/1992 e priorità al contrasto all'immigrazione clandestina", "Diritti Civili", "Opposizione")
        elif party_name in {"Forza Italia", "Noi Moderati"}:
            return ("Riforma della cittadinanza con introduzione dello Ius Scholae per i minori stranieri dopo 10 anni di percorso scolastico completato", "Diritti Civili", "Proposta di legge")
        elif party_name in OPPOSITION_PARTIES or party_name == "Azione":
            return ("Riforma della legge sulla cittadinanza con introduzione dello Ius Soli mitigato e dello Ius Scholae per l'integrazione dei giovani", "Diritti Civili", "Proposta di legge")
        return ("Riforma della cittadinanza subordinata a un rigoroso ciclo di integrazione civica e scolastica", "Diritti Civili", "Dichiarazione programmatica")

    if policy_key == "giustizia_carriere":
        return ("Riforma costituzionale della Giustizia con netta separazione delle carriere tra magistrati requirenti e giudicanti e sdoppiamento del CSM", "Istituzioni", "Proposta di legge")

    if policy_key == "nucleare":
        if party_name in {"Movimento 5 Stelle", "Alleanza Verdi e Sinistra", "Rifondazione Comunista", "Potere al Popolo"}:
            return ("Contrarietà al riavvio del nucleare e concentrazione del 100% delle risorse su fonti rinnovabili ed efficienza energetica", "Energia", "Opposizione")
        elif party_name == "Azione":
            return ("Piano Nazionale per il Nucleare con la realizzazione di 8 reattori modulari SMR entro il 2040 per abbattere i costi industriali", "Energia", "Proposta di legge")
        elif party_name == "Partito Liberal Democratico":
            return ("Quadro normativo e regolatorio per investimenti privati nel nucleare civile SMR e snellimento delle autorizzazioni per parchi rinnovabili", "Energia", "Proposta di legge")
        elif party_name == "Radicali Italiani":
            return ("Riavvio del nucleare civile pulito di quarta generazione accompagnato dall'azzeramento dei sussidi ai combustibili fossili (SAD)", "Energia", "Proposta di legge")
        elif party_name == "ORA!":
            return ("Apertura totale del mercato all'energia nucleare avanzata (SMR e IV generazione) e abbattimento dei vincoli burocratici", "Energia", "Proposta di legge")
        elif party_name == "Lega - Salvini Premier":
            return ("Piano per il ritorno al nucleare civile di quarta generazione con Small Modular Reactors (SMR)", "Energia", "Proposta di legge")
        elif party_name == "Forza Italia":
            return ("Ritorno all'energia nucleare pulita con microreattori di quarta generazione (SMR)", "Energia", "Proposta di legge")
        return ("Reintegro dell'energia nucleare pulita di nuova generazione (Small Modular Reactors SMR) nel piano energetico nazionale entro il 2035", "Energia", "Proposta di legge")

    if policy_key == "rinnovabili":
        return ("Sblocco autorizzativo accelerato per 10 GW annui di energia rinnovabile e sostegno a 20.000 Comunità Energetiche Rinnovabili", "Energia", "Proposta di legge")

    if policy_key == "affitti_brevi":
        return ("Regolamentazione delle locazioni turistiche brevi con obbligo di partita IVA dal terzo immobile e codice identificativo nazionale per contrasto all'elusione", "Fisco", "Proposta di legge")

    if policy_key == "energia_fossile":
        return ("Normativa per la valorizzazione commissariale delle concessioni di prospezione ed estrazione di gas e idrocarburi per la sicurezza energetica nazionale", "Energia", "Dichiarazione programmatica")

    if policy_key == "armi_ucraina":
        if party_name in {"Movimento 5 Stelle", "Alleanza Verdi e Sinistra", "Rifondazione Comunista", "Potere al Popolo", "Democrazia Sovrana Popolare"}:
            return ("Mozione parlamentare per il blocco dell'invio di ulteriori armamenti e investimenti militari e mandato vincolante per una conferenza diplomatica di pace", "Politica Estera", "Opposizione")
        return ("Sostegno agli aiuti multilaterali di sicurezza e rispetto degli impegni di difesa strategica nel quadro UE e NATO", "Politica Estera", "Dichiarazione programmatica")

    if policy_key == "fondo_sanitario":
        if party_name in {"Partito Democratico", "Movimento 5 Stelle", "Alleanza Verdi e Sinistra"}:
            return ("Incremento strutturale del Fondo Sanitario Nazionale fino al 7.5% del PIL per l'abbattimento delle liste d'attesa e il piano assunzioni di medici e infermieri", "Sanità", "Proposta di legge")
        elif party_name in {"Rifondazione Comunista", "Potere al Popolo"}:
            return ("Finanziamento del Fondo Sanitario Nazionale stabilmente all'8% del PIL, reinternalizzazione dei servizi e abolizione totale dei ticket sanitari", "Sanità", "Proposta di legge")
        elif party_name in {"Azione", "Italia Viva"}:
            return ("Attivazione della linea sanitaria del MES da 37 miliardi per investimenti straordinari nei pronto soccorso e ammodernamento degli ospedali", "Sanità", "Proposta di legge")
        elif party_name in {"Partito Liberal Democratico", "ORA!"}:
            return ("Sanità di Base Universale con voucher per visite specialistiche e libera concorrenza tra strutture pubbliche e convenzionate accreditate", "Sanità", "Proposta di legge")
        elif party_name in GOVERNMENT_PARTIES:
            return ("Incremento mirato delle risorse per il personale sanitario, defiscalizzazione degli straordinari di medici e infermieri e piano anti-liste d'attesa", "Sanità", "Dichiarazione programmatica")
        return ("Potenziamento delle risorse del SSN e riorganizzazione dell'assistenza territoriale per abbattere i tempi d'attesa", "Sanità", "Dichiarazione programmatica")

    if policy_key == "autonomia_differenziata":
        if party_name in OPPOSITION_PARTIES or party_name == "Democrazia Sovrana Popolare":
            return ("Referendum abrogativo e opposizione all'Autonomia Differenziata Calderoli a tutela dei servizi essenziali e dell'unità nazionale", "Istituzioni", "Opposizione")
        elif party_name in GOVERNMENT_PARTIES:
            return ("Attuazione del regionalismo differenziato nel rispetto della determinazione preventiva e finanziamento dei Livelli Essenziali delle Prestazioni (LEP)", "Istituzioni", "Proposta di legge")
        return ("Riforma del regionalismo vincolata alla previa garanzia e finanziamento perequativo dei Livelli Essenziali delle Prestazioni (LEP)", "Istituzioni", "Dichiarazione programmatica")

    if policy_key == "premierato":
        if party_name in OPPOSITION_PARTIES:
            return ("Opposizione alla riforma costituzionale del Premierato a difesa dei poteri di garanzia del Presidente della Repubblica e del Parlamento", "Istituzioni", "Opposizione")
        elif party_name == "Italia Viva":
            return ("Riforma costituzionale del 'Sindaco d'Italia' con elezione diretta del Premier e superamento del bicameralismo paritario", "Istituzioni", "Proposta di legge")
        elif party_name in GOVERNMENT_PARTIES:
            return ("Riforma costituzionale del Premierato con elezione diretta del Presidente del Consiglio e clausola di stabilità della maggioranza", "Istituzioni", "Proposta di legge")
        return ("Riforma dell'assetto istituzionale a tutela della stabilità dei governi e della rappresentanza parlamentare", "Istituzioni", "Dichiarazione programmatica")

    if policy_key == "patrimoniale":
        if party_name in {"Alleanza Verdi e Sinistra", "Partito Democratico", "Rifondazione Comunista", "Potere al Popolo"}:
            return ("Imposta straordinaria e progressiva sui patrimoni superiori a 5 milioni di euro destinata a sanità pubblica, scuola e transizione ecologica", "Fisco", "Proposta di legge")
        elif party_name == "Movimento 5 Stelle":
            return ("Contrarietà a patrimoniali ordinarie e priorità assoluta alla tassazione straordinaria al 100% degli extraprofitti finanziari ed energetici", "Fisco", "Opposizione")
        return ("Netta contrarietà a qualsiasi forma di imposta patrimoniale e priorità alla riduzione della pressione fiscale su famiglie e imprese", "Fisco", "Opposizione")

    if policy_key == "diritti_etici":
        if party_name in GOVERNMENT_PARTIES or party_name == "Futuro Nazionale":
            return ("Contrarietà a qualsiasi legalizzazione delle droghe leggere, potenziamento delle comunità di recupero e tutela della vita dal concepimento alla morte naturale", "Diritti Civili", "Dichiarazione programmatica")
        elif party_name in {"+Europa", "Radicali Italiani"}:
            return ("Disegno di legge per la legalizzazione del fine vita assistito, testamento biologico e regolamentazione del mercato della cannabis", "Diritti Civili", "Proposta di legge")
        elif party_name in {"Partito Democratico", "Movimento 5 Stelle", "Alleanza Verdi e Sinistra", "Rifondazione Comunista", "Potere al Popolo"}:
            return ("Legge sul fine vita assistito in recepimento della Corte Costituzionale e depenalizzazione della coltivazione domestica di cannabis", "Diritti Civili", "Proposta di legge")
        return ("Normativa per la tutela dei diritti individuali e disciplina del fine vita nel rispetto della dignità della persona", "Diritti Civili", "Dichiarazione programmatica")

    if policy_key == "legittima_difesa":
        if party_name == "Lega - Salvini Premier":
            return ("Riforma della legittima difesa con presunzione assoluta di non punibilità ed esenzione dalle spese legali per le vittime di intrusioni violente", "Istituzioni", "Proposta di legge")
        elif party_name == "Forza Italia":
            return ("Riforma delle garanzie processuali dei cittadini, tutela della presunzione di innocenza e risarcimento rapido per ingiusta detenzione", "Istituzioni", "Proposta di legge")
        elif party_name == "Fratelli d'Italia":
            return ("Tutela legale rafforzata per le forze dell'ordine e inasprimento sanzionatorio per aggressioni e occupazioni abusive", "Istituzioni", "Proposta di legge")
        elif party_name in OPPOSITION_PARTIES:
            return ("Contrarietà all'allentamento dei vincoli sulle armi e priorità assoluta al potenziamento degli organici delle forze dell'ordine", "Istituzioni", "Opposizione")
        return ("Potenziamento dei presidi di pubblica sicurezza sul territorio e supporto alle vittime di reato", "Istituzioni", "Dichiarazione programmatica")

    if policy_key == "commercio_vicinato":
        return ("Piano nazionale di rigenerazione urbana e fiscalità di vantaggio per la riapertura dei negozi di vicinato nei centri storici", "Economia", "Proposta di legge")

    if policy_key == "fringe_benefit":
        return ("Innalzamento della soglia di detassazione integrale per i fringe benefit e premi di produttività aziendale fino a 3.000 euro", "Lavoro", "Proposta di legge")

    if policy_key == "sicurezza_lavoro":
        return ("Introduzione del reato di omicidio sul lavoro e inasprimento del sistema sanzionatorio con patente a crediti per le imprese edili", "Lavoro", "Proposta di legge")

    if policy_key == "piano_casa":
        return ("Estensione della cedolare secca al 10% per i contratti a canone concordato e piano straordinario per 50.000 nuovi alloggi di edilizia residenziale pubblica", "Infrastrutture", "Proposta di legge")

    if policy_key == "famiglia_nidi":
        return ("Gratuità universale degli asili nido e incremento del congedo parentale retribuito all'80% fino al sesto mese di vita del bambino", "Istruzione", "Proposta di legge")

    if policy_key == "extraprofitti":
        if party_name in {"Movimento 5 Stelle", "Alleanza Verdi e Sinistra", "Rifondazione Comunista", "Potere al Popolo"}:
            return ("Tassazione straordinaria al 100% degli extraprofitti bancari ed energetici a copertura integrale del contrasto al carovita", "Fisco", "Proposta di legge")
        elif party_name == "Forza Italia":
            return ("Netta contrarietà a qualsiasi prelievo forzoso o tassa straordinaria sugli extraprofitti bancari a tutela del credito e del risparmio privato", "Fisco", "Opposizione")
        elif party_name in {"Fratelli d'Italia", "Lega - Salvini Premier", "Noi Moderati"}:
            return ("Contributo di solidarietà negoziato con il sistema bancario e assicurativo destinato al fondo per i mutui prima casa e sgravi per famiglie", "Fisco", "Dichiarazione programmatica")
        return ("Contrarietà a tassazioni retroattive e priorità alla stabilità del sistema finanziario e creditizio per le imprese", "Fisco", "Opposizione")

    return ("Proposta politica formalizzata di indirizzo legislativo ed economico", "Economia", "Dichiarazione programmatica")

def _extract_dynamic_policy_statement(full_text: str, lower: str, party_name: Optional[str] = None) -> Optional[tuple]:
    """
    Intelligently identifies concrete policy commitments across any political news or parliamentary report.
    Extracts the policy statement, maps it to the proper macro-topic, and determines the action type.
    If party_name is specified, verifies that the policy action is attributable to that party.
    """
    sentences = re.split(r"(?<=[.!?])\s+", full_text)
    
    ACTION_PATTERNS = [
        # DDL / Proposte di legge
        (r"(?:presenta|deposita|approva|firma)\s+(?:un |una |il |la |lo |l')?(?:ddl|disegno di legge|proposta di legge|emendamento|mozione|odg|ordine del giorno)\s+(?:per|su|volto a|contro|a favore di|di)\s+([^.!?]{18,220})", "Proposta di legge"),
        # Riforme e Piani Programmatici
        (r"(?:propone|chiede|annuncia|lancia un piano per|punta a|intende introdurre|intende cancellare|intende ridurre|intende riformare|priorit[àa] [èe]|propone di|chiede lo stanziamento di)\s+(?:di |la |il |un |l'|lo )?([^.!?]{18,220})", "Dichiarazione programmatica"),
        # Impegno programmatico e misure
        (r"(?:impegna il governo a|prevede l'introduzione di|chiede la riforma di|promette di finanziare|approvato il piano per)\s+([^.!?]{18,220})", "Dichiarazione programmatica"),
        # Opposizione o Contrarietà
        (r"(?:si oppone a|voter[àa] contro|chiede lo stop a|contrariet[àa] al|boccia la proposta di|chiede di bloccare|no secco a)\s+(?:la |il |lo |l'|i |le )?([^.!?]{18,220})", "Opposizione"),
        # Misure e Azioni Dirette
        (r"(?:taglio|riduzione|azzeramento|aumento|incremento|blocco|stop|moratoria|istituzione|reintroduzione|potenziamento|stanziamento)\s+(?:del(?:la|lo|l'|le|i)?|delle|degli|di|a|per)\s+([^.!?]{18,220})", "Dichiarazione programmatica")
    ]

    POLEMIC_KEYWORDS = [
        "arrestato", "indagato", "sfida", "congresso", "lite", "bufera", "scandalo", "insulti", 
        "marchese", "farsa", "ipocrisia", "vergogna", "chiacchiere", "faida", "rissa verbale"
    ]

    party_aliases = [a.lower() for a in PARTY_ALIASES.get(party_name, [])] if party_name else []

    for idx, sentence in enumerate(sentences):
        s_clean = sentence.strip()
        s_lower = s_clean.lower()
        
        # Must not be pure political gossip or attack
        if any(noise in s_lower for noise in POLEMIC_KEYWORDS):
            continue
            
        # If party specified, ensure party is mentioned in current sentence, previous sentence, or next sentence
        if party_aliases:
            context_window = s_lower
            if idx > 0:
                context_window = sentences[idx - 1].lower() + " " + context_window
            if idx + 1 < len(sentences):
                context_window = context_window + " " + sentences[idx + 1].lower()
            if not any(re.search(r"\b" + re.escape(a) + r"\b", context_window) for a in party_aliases):
                continue

        for pattern, act_type in ACTION_PATTERNS:
            m = re.search(pattern, s_clean, re.I)
            if m:
                extracted_clause = m.group(1).strip()
                extracted_clause = re.sub(r"\s+", " ", extracted_clause)
                extracted_clause = re.sub(r"^(?:che\s+|di\s+|per\s+|a\s+|e\s+)", "", extracted_clause, flags=re.I).strip()
                extracted_clause = re.sub(r"[,;:\-–—\s]+$", "", extracted_clause).strip()
                
                if len(extracted_clause) >= 18:
                    detected_topic = "Economia"
                    for topic, kws in MACRO_TOPICS_KEYWORDS.items():
                        if any(kw in s_lower or kw in extracted_clause.lower() for kw in kws):
                            detected_topic = topic
                            break
                            
                    formatted_synthesis = extracted_clause[0].upper() + extracted_clause[1:]
                    return formatted_synthesis, detected_topic, act_type

    return None

def _extract_heuristically(
    text: str,
    url: str,
    title: Optional[str] = None,
    published_at: Optional[datetime.datetime] = None
) -> List[ProposalExtractionSchema]:
    """
    High-accuracy heuristic extractor with strict policy filtering.
    Excludes gossip, internal friction, non-policy quotes, and general cronaca.
    Transforms actionable news into concrete, structured political proposals.
    """
    full_text = f"{title or ''} {text}".strip()
    lower = full_text.lower()
    ts = (published_at or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)).isoformat()

    # 1. Strict Exclusion Filter: discard pure gossip, internal friction, congress elections, clashes, media polemics
    for pattern in NON_POLICY_PATTERNS:
        if re.search(pattern, lower, re.I):
            return []

    # Exclude journalistic polemics / commentary / generic regional events
    JOURNALISTIC_NOISE = [
        r"schillaci suona l'allarme", r"guida verso il muro", r"l'ira di meloni", r"ora chiarire come proseguire",
        r"vannacci conta pi[ùu] di salvini", r"punto in comune tra le proposte", r"aria pesante per i riformisti",
        r"ecco la manovra da \d+ milioni", r"spuntano \d+ miliardi", r"botta e risposta", r"guerra verbale"
    ]
    for noise in JOURNALISTIC_NOISE:
        if re.search(noise, lower, re.I):
            return []

    # 2. Detect party: MUST be explicitly present, never default to random party
    matched_parties = []
    for party, aliases in PARTY_ALIASES.items():
        if any(re.search(r"\b" + re.escape(a) + r"\b", lower) for a in aliases):
            matched_parties.append(party)
            
    if not matched_parties:
        return []

    # 3. Policy Proposal Transformation
    matched_key = None
    for pattern, key in POLICY_ACTION_TRANSFORMATIONS:
        if re.search(pattern, lower, re.I):
            matched_key = key
            break

    # Extract cost if mentioned
    raw_cost = None
    cost_match = re.search(r"(?:costo|spesa|stanziat[oi]|investimento|risorse|fondo)\s*(?:pari a|stimato in|di)?\s*(\d+(?:[.,]\d+)?\s*(?:miliardi|milioni|mld|mln)?\s*€|\d+(?:[.,]\d+)?\s*(?:miliardi|milioni|mld|mln)\s*euro)", lower)
    if cost_match:
        raw_cost = cost_match.group(1).strip()

    # Extract coverage if mentioned
    raw_cov = None
    cov_match = re.search(r"(?:coperture|copertur[ae]|finanziat[oa]|risorse da)\s*(?:tramite|mediante|con|da)\s*([^.,;\n]{10,80})", lower)
    if cov_match:
        raw_cov = cov_match.group(1).strip()

    results = []
    seen_syntheses = set()

    for party_name in matched_parties[:2]: # At most 2 explicit parties per article
        party_aliases = [a.lower() for a in PARTY_ALIASES.get(party_name, [party_name.lower()])]
        party_in_title = any(re.search(r"\b" + re.escape(a) + r"\b", (title or "").lower()) for a in party_aliases)

        # 1. Always prioritize dynamic extraction linked to this specific party
        dynamic_res = _extract_dynamic_policy_statement(full_text, lower, party_name)
        if dynamic_res:
            proposal_synthesis, chosen_topic, action_type = dynamic_res
        elif matched_key:
            # Check if party is in proximity (within 250 chars) of the matched policy keyword, or in title
            party_near_key = False
            for pat, k in POLICY_ACTION_TRANSFORMATIONS:
                if k == matched_key:
                    m = re.search(pat, lower)
                    if m:
                        start_pos = max(0, m.start() - 250)
                        end_pos = min(len(lower), m.end() + 250)
                        window = lower[start_pos:end_pos]
                        if any(re.search(r"\b" + re.escape(a) + r"\b", window) for a in party_aliases):
                            party_near_key = True
                            break
            if not (party_in_title or party_near_key):
                continue
            proposal_synthesis, chosen_topic, action_type = resolve_policy_transformation(matched_key, party_name)
        else:
            continue

        # Prevent cross-party clones from the same article
        synth_lower = proposal_synthesis.strip().lower()
        if synth_lower in seen_syntheses:
            continue
        seen_syntheses.add(synth_lower)

        # Quality Gate: Strict Proposal Validation (discards incomplete texts, clickbait, and vague slogans)
        valid_synthesis = sanitize_and_validate_proposal_statement(proposal_synthesis)
        if not valid_synthesis:
            continue

        clean_title = sanitize_proposal_title(valid_synthesis, chosen_topic)
        fiscal_res = calculate_fiscal_impact_and_coverage(
            partito=party_name,
            macro_argomento=chosen_topic,
            sintesi=clean_title,
            costo_stimato=raw_cost,
            coperture_dichiarate=raw_cov
        )

        item = ProposalExtractionSchema(
            partito=party_name,
            macro_argomento=chosen_topic,
            dichiarazione_sintesi=clean_title,
            tipo_azione=action_type,
            impatto_economico=ImpattoEconomicoSchema(
                costo_stimato=fiscal_res["costo_stimato"],
                coperture_dichiarate=fiscal_res["coperture_dichiarate"],
                fattibilita_finanziaria=fiscal_res["fattibilita_finanziaria"]
            ),
            fact_check=FactCheckSchema(
                status=fiscal_res["fact_check_status"],
                motivazione_oggettiva=fiscal_res["fact_check_motivazione"],
                fonte_verifica=fiscal_res["fact_check_fonte"]
            ),
            fonte_url=url,
            timestamp=ts
        )
        results.append(item)

    return results

async def extract_proposals_from_text(
    text: str,
    url: str,
    title: Optional[str] = None,
    published_at: Optional[datetime.datetime] = None
) -> List[ProposalExtractionSchema]:
    """
    Main extraction function implementing Section 4.B of the Mission Brief.
    Extracts structured political proposals using Multi-Provider LLM (Ollama, Groq, Gemini)
    if available, or robust heuristic fallback.
    """
    ts = (published_at or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)).isoformat()
    provider_info = await llm_provider.get_active_provider_info()
    
    if provider_info["provider"] != "deterministic":
        user_prompt = f"""Estrai le proposte politiche dal seguente testo:
URL Fonte: {url}
Titolo: {title or 'N/A'}
Data: {ts}
Testo:
{text[:3500]}
"""
        messages = [
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            raw_output, used_p = await llm_provider.generate_chat(
                messages=messages,
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1
            )
            
            if raw_output:
                clean_json_str = re.sub(r"^```json\s*", "", raw_output.strip())
                clean_json_str = re.sub(r"\s*```$", "", clean_json_str)
                # Find outermost JSON brackets if wrapped in commentary
                match_json = re.search(r"(\[.*\]|\{.*\})", clean_json_str, re.DOTALL)
                if match_json:
                    clean_json_str = match_json.group(1)
                
                parsed = json.loads(clean_json_str)
                proposals = []
                items = parsed if isinstance(parsed, list) else [parsed]
                for it in items:
                    if not isinstance(it, dict) or not it.get("partito") or not it.get("dichiarazione_sintesi"):
                        continue
                    val_stmt = sanitize_and_validate_proposal_statement(it["dichiarazione_sintesi"])
                    if not val_stmt:
                        continue
                    it["dichiarazione_sintesi"] = val_stmt
                    if "fonte_url" not in it or not it["fonte_url"]:
                        it["fonte_url"] = url
                    if "timestamp" not in it or not it["timestamp"]:
                        it["timestamp"] = ts
                        
                    validated = ProposalExtractionSchema.model_validate(it)
                    proposals.append(validated)
                    
                if proposals:
                    return proposals
        except Exception as e:
            print(f"[Extractor] LLM extraction warning: {e}. Falling back to institutional heuristic parser.")

    # Fallback to robust institutional heuristic extractor
    return _extract_heuristically(text, url, title, published_at)
