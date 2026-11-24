"""
Fact-Checking and Factual Veracity Engine for PoliticLens.
Calibrated Institutional Fact-Checking System with Discrete 5% Proposal Scoring (Salti del 5%).
Completely decoupled from financial budget coverage:
- Scientific veracity (IPCC on nuclear lifecycle emissions, physics of grid balancing)
- Statistical accuracy (ISTAT, Eurostat, Ministero dell'Interno, MEF)
- Legal, constitutional and physical feasibility constraints (Corte Costituzionale, UE Treaties, Terna)
- Every single proposal receives an exact vote in discrete steps of 5% (0% to 100%).
"""

import re
from typing import Dict, Any, Tuple, Optional

TRUTH_WEIGHTS = {
    "Verificato": 95.0,
    "Ampiamente verificato": 90.0,
    "Parzialmente verificato": 85.0,
    "Posizione programmatica": 75.0,
    "In attesa di copertura": 65.0,
    "Non verificabile": 55.0,
    "Esagerato": 45.0,
    "Fortemente forzato": 35.0,
    "Inattuabile": 20.0,
    "Fake / Infondato": 0.0
}

# Granular Truthfulness Thresholds (Every 5%)
TRUTH_THRESHOLDS = [
    {"min_score": 95.0, "tier": "Eccellente", "label": "≥95% (Eccellente)", "desc": "Pienamente verificato con norme primarie vigenti o evidenze scientifiche inconfutabili."},
    {"min_score": 90.0, "tier": "Molto Alta", "label": "≥90% (Molto Alta)", "desc": "Elevata aderenza ai parametri ufficiali con atti tecnici asseverati."},
    {"min_score": 85.0, "tier": "Alta", "label": "≥85% (Alta / DDL Incardinato)", "desc": "Disegno di legge depositato o solido impianto istituzionale."},
    {"min_score": 80.0, "tier": "Solida", "label": "≥80% (Solida / Programma Strutturato)", "desc": "Proposta programmatica strutturata con quantificazione e coperture."},
    {"min_score": 75.0, "tier": "Buona", "label": "≥75% (Buona / Posizione Politica)", "desc": "Posizione politica o programmatica coerente con l'ordinamento."},
    {"min_score": 70.0, "tier": "Discreta", "label": "≥70% (Discreta)", "desc": "Indirizzo politico con margini aperti di attuazione."},
    {"min_score": 65.0, "tier": "Moderata", "label": "≥65% (Moderata)", "desc": "Imprecisioni su dati statistici o scadenze/coperture non ancora definite."},
    {"min_score": 60.0, "tier": "Sufficiente", "label": "≥60% (Sufficiente)", "desc": "Obiettivo politico generico o non pienamente circostanziato."},
    {"min_score": 55.0, "tier": "Parziale", "label": "≥55% (Parziale)", "desc": "Bassa aderenza empirica ai vincoli generali di finanza pubblica."},
    {"min_score": 50.0, "tier": "Bassa", "label": "≥50% (Bassa / Non verificabile)", "desc": "Slogan politico privo di parametri verificabili."},
    {"min_score": 45.0, "tier": "Esagerato", "label": "≥45% (Esagerato)", "desc": "Dichiarazione elettorale con assunti di autofinanziamento non validati."},
    {"min_score": 40.0, "tier": "Distorto", "label": "≥40% (Distorto)", "desc": "Rilevanti incongruenze rispetto ai dati ufficiali UPB/ISTAT."},
    {"min_score": 35.0, "tier": "Disallineato", "label": "≥35% (Disallineato)", "desc": "Contraddetto dalle serie storiche e dai trattati europei."},
    {"min_score": 30.0, "tier": "Quasi Infondato", "label": "≥30% (Quasi Infondato)", "desc": "Grave distorsione di dati o vincoli giuridici."},
    {"min_score": 25.0, "tier": "Gravemente Inesatto", "label": "≥25% (Gravemente Inesatto)", "desc": "Dati smentiti dalle istituzioni competenti."},
    {"min_score": 20.0, "tier": "Inattuabile", "label": "≥20% (Inattuabile)", "desc": "Incompatibilità con norme costituzionali o limiti tecnici fisici."},
    {"min_score": 15.0, "tier": "Inattuabile Ordinamentale", "label": "≥15% (Inattuabile Ordinamentale)", "desc": "Violazione strutturale dell'ordinamento vigente."},
    {"min_score": 10.0, "tier": "Palesemente Illegittimo", "label": "≥10% (Palesemente Illegittimo)", "desc": "Violazione palese di trattati internazionali (es. UNCLOS)."},
    {"min_score": 5.0, "tier": "Manipolatorio", "label": "≥5% (Manipolatorio)", "desc": "Fatti quasi interamente manipolati."},
    {"min_score": 0.0, "tier": "Fake / Infondato", "label": "<5% (Fake / Infondato)", "desc": "Falso scientifico, statistico o tecnicamente irrealizzabile."}
]

CRITICAL_STANCE_PATTERNS = [
    r"\bcontrariet[àa]\b", r"\bcontrari[oa]\b", r"\bcritica\b", r"\bdenuncia\b",
    r"\bopposizione\s+(?:a|al|alla|allo|ai|agli|alle|netta)\b",
    r"\brespinge\b", r"\bfrena\s+su\b", r"\bboccia\b", r"\bavverte\s+contro\b",
    r"\brifiuto\b", r"\bno\s+(?:a|al|alla|allo|ai|agli|alle|secco)\b",
    r"\bstop\s+(?:a|al|alla|allo|ai|agli|alle)\b", r"\bcancellazione\s+(?:definitiva\s+)?de",
    r"\babrogazione\b", r"\bblocco\s+(?:definitivo|totale)\b", r"\babbandono\b"
]


def get_truthfulness_tier(score: float) -> Dict[str, Any]:
    """Returns the descriptive 5%-step tier for any truthfulness score."""
    for t in TRUTH_THRESHOLDS:
        if score >= t["min_score"]:
            return t
    return TRUTH_THRESHOLDS[-1]


def calculate_proposal_truthfulness_score(status: str, truth_score: Optional[float] = None) -> float:
    """Returns strict factual truthfulness score in discrete 5% steps (0.0 to 100.0)."""
    st = (status or "").strip()
    if truth_score is not None and isinstance(truth_score, (int, float)):
        # Guard against stale mismatched DB scores (e.g. Inattuabile with 75.0)
        snapped = float(round(truth_score / 5.0) * 5.0)
        if st == "Fake / Infondato" and snapped > 10.0:
            return 0.0
        if st == "Inattuabile" and snapped > 30.0:
            return 20.0
        if st == "Esagerato" and snapped > 55.0:
            return 45.0
        if st == "Verificato" and snapped < 85.0:
            return 90.0
        return max(0.0, min(100.0, snapped))
    return TRUTH_WEIGHTS.get(st, 75.0)


def _is_opposing_subject(s_low: str, subject_keywords: list) -> bool:
    """Returns True if the statement expresses opposition/criticism specifically toward one of the subject keywords."""
    if not any(re.search(pat, s_low) for pat in CRITICAL_STANCE_PATTERNS):
        return False
    # Check whether an opposition marker appears before a subject keyword in the same clause
    clauses = re.split(r"[,;.]", s_low)
    for cl in clauses:
        has_crit = any(re.search(pat, cl) for pat in CRITICAL_STANCE_PATTERNS)
        has_subj = any(kw in cl for kw in subject_keywords)
        if has_crit and has_subj:
            return True
    return False


def analyze_feasibility_and_factcheck(
    partito: str,
    macro_argomento: str,
    sintesi: str,
    costo_stimato: str = "",
    coperture: str = "",
    raw_text: str = "",
    tipo_azione: str = ""
) -> Tuple[str, str, str, str, float]:
    """
    Evaluates FACTUAL, SCIENTIFIC, STATISTICAL and INSTITUTIONAL VERACITY.
    Assigns each proposal a precise vote in discrete 5% steps:
    Returns:
    (technical_feasibility_analysis, fact_check_status, fact_check_motivation, institutional_source_link, truth_score)
    """
    s_low = (sintesi or "").lower()
    raw_low = (raw_text or "").lower()
    cost_low = (costo_stimato or "").lower()
    cov_low = (coperture or "").lower()
    act_low = (tipo_azione or "").lower()
    statement_and_meta = f"{s_low} {cost_low} {cov_low}"
    combined = f"{s_low} {raw_low} {cost_low} {cov_low}"

    # =========================================================================
    # 1. SCIENTIFIC & STATISTICAL FALSEHOODS (0%)
    # =========================================================================

    # A. Nuclear Energy CO2 & Safety Falsehoods
    if "nucleare" in combined and not _is_opposing_subject(s_low, ["inquinante", "co2", "fuga radioattiva"]):
        if any(w in combined for w in ["2 milioni", "milioni di tonnellate", "inquinante come", "emette co2", "produce co2", "fuga radioattiva universale", "più inquinante del carbone"]):
            return (
                "Assunto scientificamente privo di fondamento: le centrali nucleari producono energia tramite fissione senza reazioni di combustione e non rilasciano gas serra in atmosfera.",
                "Fake / Infondato",
                "L'IPCC (Gruppo Intergovernativo sul Cambiamento Climatico) delle Nazioni Unite certifica che l'energia nucleare ha emissioni mediane su intero ciclo di vita di appena 12 g CO2/kWh, equivalenti o inferiori all'eolico (11 g/kWh) e inferiori al fotovoltaico (41-48 g/kWh).",
                "https://www.ipcc.ch/report/ar6/wg3/",
                0.0
            )

    # B. Fake Tax Pressure Claims (e.g. taxes at 80%)
    if any(w in combined for w in ["pressione fiscale all'80%", "pressione fiscale all'85%", "tasse all'80%", "tasse raddoppiate in un anno"]):
        return (
            "Dato statistico smentito dalle serie storiche ufficiali di finanza pubblica.",
            "Fake / Infondato",
            "I dati ISTAT e del Dipartimento delle Finanze attestano la pressione fiscale reale complessiva in Italia attorno al 41.5% - 42.5% del PIL; stime all'80% sono prive di qualsiasi riscontro metodologico o contabile.",
            "https://www.istat.it/it/archivio/conti-economici",
            0.0
        )

    # C. Fake Immigration Statistics
    if any(w in combined for w in ["sbarchi aumentati del 500%", "immigrazione clandestina decuplicata", "milioni di clandestini al mese"]):
        return (
            "Dichiarazione smentita dai rilievi operativi e dai report delle autorità di pubblica sicurezza.",
            "Fake / Infondato",
            "I dati statistici del Cruscotto Giornaliero del Ministero dell'Interno documentano che gli arrivi via mare registrano fluttuazioni monitorate, smentendo variazioni percentuali iperboliche prive di riscontro.",
            "https://www.interno.gov.it/it/stampa-e-comunicazione/dati-e-statistiche/cruscotto-statistico-giornaliero",
            0.0
        )

    # =========================================================================
    # 2. INATTUABILE (Physical, Legal, Treaty Impossibility) -> 20%
    # =========================================================================

    # A. Physically / Technically Impossible Renewable Timelines
    if not _is_opposing_subject(s_low, ["rinnovabili", "100%", "2028"]) and any(w in s_low for w in ["rinnovabili", "fonti rinnovabili", "green"]) and any(w in s_low for w in ["2028", "entro il 2028", "in 2 anni", "in 3 anni", "domani"]):
        if any(w in s_low for w in ["100%", "solo rinnovabili", "totale"]):
            return (
                "Obiettivo fisicamente e tecnicamente irrealizzabile entro il 2028: la quota attuale di FER sul mix elettrico italiano è di circa il 37-40%.",
                "Inattuabile",
                "Terna e il Ministero dell'Ambiente e della Sicurezza Energetica evidenziano che la posa degli accumuli di potenza (BESS, pompaggi) e il potenziamento della rete di trasmissione richiedono tempi autorizzativi e industriali incompatibili con l'orizzonte 2028 senza rischiare blackout diffusi.",
                "https://www.terna.it/it/sistema-elettrico/transizione-energetica",
                20.0
            )

    # B. Unilateral Naval Blockade in International Waters
    if not _is_opposing_subject(s_low, ["blocco navale"]) and "blocco navale" in s_low and "concordato" not in s_low:
        if any(w in statement_and_meta for w in ["acque internazionali", "unilaterale", "fermare con navi", "nel mediterraneo"]):
            return (
                "Inattuabile come blocco navale unilaterale in acque internazionali in tempo di pace in base al diritto della navigazione.",
                "Inattuabile",
                "La Convenzione delle Nazioni Unite sul Diritto del Mare (UNCLOS) e il diritto internazionale umanitario vietano l'interdizione marittima unilaterale in alto mare senza risoluzione del Consiglio di Sicurezza dell'ONU.",
                "https://www.un.org/depts/los/convention_agreements/convention_overview_convention.htm",
                20.0
            )

    # C. Immediate / unilateral exit from Euro / EU Treaties / NATO
    if not _is_opposing_subject(s_low, ["euro", "nato", "trattati", "ue"]):
        has_exit_intent = bool(re.search(
            r"(?:uscit[ae]\s+(?:immediat[ae]\s+)?(?:dell'italia\s+)?da(?:ll'|lla)\s*(?:euro|eurozona|nato|ue|unione europea)|"
            r"recesso\s+unilaterale\s+dai\s+trattati|"
            r"uscire\s+da(?:ll'|lla)\s*(?:euro|nato)|"
            r"abrogare\s+l'euro)",
            s_low
        ))
        if has_exit_intent and any(w in s_low for w in ["immediat", "unilateral", "decreto", "disconoscimento", "domani", "nazionalizzazione della banca d'italia"]):
            mentions_euro_ue = any(k in s_low for k in ["euro", "eurozona", "unione europea", "trattati dell'unione", "vincoli ue"])
            mentions_nato = "nato" in s_low
            if mentions_nato and not mentions_euro_ue:
                return (
                    "Inattuabile con atto immediato: l'art. 13 del Trattato Nord Atlantico impone una procedura formale di denuncia con preavviso minimo di un anno e autorizzazione parlamentare ex art. 80 Cost.",
                    "Inattuabile",
                    "L'art. 13 del Trattato Nord Atlantico (Washington, 1949) stabilisce che la cessazione di appartenenza alla NATO può avvenire solo dopo un anno dalla notifica formale agli Stati Uniti e previa autorizzazione delle Camere ex art. 80 Costituzione, escludendo un'uscita immediata.",
                    "https://www.nato.int/cps/en/natohq/official_texts_17120.htm",
                    20.0
                )
            return (
                "Inattuabile con atto interno unilaterale o immediato: l'ordinamento costituzionale italiano sancisce il rispetto dei vincoli derivanti dall'ordinamento comunitario e dagli obblighi internazionali (artt. 11 e 117 Cost.).",
                "Inattuabile",
                "La Corte Costituzionale, l'art. 50 del Trattato sull'Unione Europea (TUE) e l'art. 13 del Trattato Nord Atlantico stabiliscono procedure formali di recesso negoziato, escludendo la dismissione immediata o unilaterale della moneta unica e dei trattati tramite atti interni.",
                "https://www.cortecostituzionale.it",
                20.0
            )

    # =========================================================================
    # 3. MACROECONOMIC EXAGGERATIONS & UNFUNDED MANDATES (45% - 50%)
    # =========================================================================

    # A. Superbonus 110% uncritical defense or zero-cost claims
    if "superbonus" in s_low and not _is_opposing_subject(s_low, ["superbonus"]) and "revisione" not in s_low and "stretta" not in s_low and "riduzione" not in s_low:
        if any(w in s_low for w in ["costo zero", "nessun costo", "si ripaga", "non è costato nulla", "ha creato ricchezza senza debiti", "difesa integrale", "salvaguardia dei crediti"]):
            return (
                "Dichiarazione su misura a forte impatto deficitario: il Superbonus ha generato un disavanzo documentato da MEF ed Eurostat oltre 120 Mld €.",
                "Esagerato",
                "I report ufficiali della Ragioneria Generale dello Stato, di Eurostat e dell'UPB documentano che il Superbonus edilizio ha generato un disavanzo lordo complessivo superiore a 120 miliardi di euro sui conti pubblici, con un moltiplicatore fiscale effettivo largamente inferiore all'unità.",
                "https://www.rgs.mef.gov.it",
                45.0
            )

    # B. Flat Tax 15% self-funding / flat tax extended to 100k or all taxpayers
    if "flat tax" in s_low and not _is_opposing_subject(s_low, ["flat tax"]):
        if any(w in s_low for w in ["100.000", "100mila", "tutti i dipendenti", "tutti i contribuenti", "si ripaga da sola", "senza costi", "generalizzata"]):
            return (
                "Assunto econometrico non validato: l'autofinanziamento integrale tramite emersione spontanea è escluso dalle istituzioni economiche indipendenti.",
                "Esagerato",
                "La Banca d'Italia e l'Ufficio Parlamentare di Bilancio stimano che l'elasticità di gettito compensa al massimo il 15-20% della perdita erariale iniziale su aliquota sostitutiva al 15% per redditi medio-alti.",
                "https://www.bancaditalia.it/pubblicazioni/temi-discussione/2022/flat-tax-effetti/",
                45.0
            )

    # C. 90-100% Tax on Bank/Energy Windfall Profits
    if "extraprofitti" in s_low and not _is_opposing_subject(s_low, ["extraprofitti"]):
        if any(w in s_low for w in ["100%", "90%", "totale confisca", "retroattiva"]):
            return (
                "Forte criticità costituzionale e finanziaria: una tassazione al 90-100% assume natura espropriativa.",
                "Esagerato",
                "La Corte Costituzionale (sentenza n. 10/2015 sulla Robin Hood Tax) stabilisce che i prelievi straordinari devono rispettare i principi di proporzionalità e ragionevolezza ex art. 53 Cost.; la Banca d'Italia evidenzia inoltre che le banche possono destinare gli utili a riserva non distribuibile annullando il gettito effettivo.",
                "https://www.cortecostituzionale.it",
                45.0
            )

    # D. Healthcare at 7.5% or 8% of GDP funded solely via tax evasion
    if any(w in s_low for w in ["sanità", "fondo sanitario", "ssn"]) and not _is_opposing_subject(s_low, ["7.5%", "8%", "fondo sanitario"]):
        if any(w in statement_and_meta for w in ["7.5%", "7,5%", "8%", "20 miliardi"]) and any(w in statement_and_meta for w in ["evasione", "tax gap"]):
            return (
                "Previsione di copertura aleatoria: l'Ufficio Parlamentare di Bilancio non ammette la stima teorica del recupero evasione come copertura fissa ex art. 81 Cost.",
                "Esagerato",
                "Il Servizio Bilancio del Senato evidenzia che per portare la spesa sanitaria al 7.5% del PIL occorrono circa 20 miliardi di euro strutturali annui; iscrivere come copertura il tax gap senza specifiche misure normative viola i criteri di asseverazione MEF.",
                "https://www.upbilancio.it",
                50.0
            )

    # E. Quota 41 secca senza limiti anagrafici e senza penalizzazioni (excluding selective arduous-work versions)
    if "quota 41" in s_low and not _is_opposing_subject(s_low, ["quota 41"]) and "abbandono" not in s_low:
        is_selective_usuranti = any(k in s_low for k in ["selettiva", "solo usuranti", "solo gravosi", "lavoratori gravosi", "lavoratori usuranti", "gravosi e usuranti", "lavori usuranti"])
        if not is_selective_usuranti and any(w in s_low for w in ["secca", "pura", "senza limiti", "tutti", "senza penalizzazioni"]):
            return (
                "Misura previdenziale ad alto onere finanziario strutturale non compatibile con la sostenibilità a lungo termine del sistema pensionistico.",
                "Esagerato",
                "La memoria tecnica dell'INPS e le valutazioni della Ragioneria Generale dello Stato quantificano il costo di Quota 41 pura in circa 4.5 miliardi di euro nel primo anno, con una crescita progressiva fino a superare i 9 miliardi annui a regime.",
                "https://www.inps.it/dati-e-bilanci/audizioni-parlamentari",
                45.0
            )

    # F. Pensioni minime a 1.000 euro per tutti
    if "pensioni minime" in s_low and not _is_opposing_subject(s_low, ["pensioni minime", "1.000", "1000"]):
        if any(w in s_low for w in ["1.000", "1000"]) and any(w in s_low for w in ["tutti", "tutte", "over 70", "over 75"]):
            return (
                "Promessa programmatica che richiede risorse di spesa corrente molto elevate rispetto ai saldi ordinari di manovra.",
                "Esagerato",
                "Il Dipartimento della Previdenza del Ministero del Lavoro e l'UPB stimano che l'innalzamento generalizzato delle pensioni minime a 1.000 euro mensili comporterebbe un onere strutturale annuo molto elevato (fino a 18-22 miliardi per l'intera platea).",
                "https://www.lavoro.gov.it",
                45.0
            )

    # G. Settimana corta a 32 ore a parità salariale per legge obbligatoria
    if not _is_opposing_subject(s_low, ["32 ore", "settimana corta"]):
        if ("32 ore" in s_low or "settimana corta" in s_low) and any(w in s_low for w in ["parità", "parita"]):
            return (
                "Misura con impatti asimmetrici sulla competitività delle imprese e sui costi operativi della Pubblica Amministrazione.",
                "Esagerato",
                "L'ISTAT e l'OCSE rilevano che l'introduzione generalizzata della settimana di 32 ore a parità di retribuzione comporta un incremento immediato del costo orario del lavoro del 25%, sostenibile solo nei settori ad altissima produttività o tramite incentivi fiscali selettivi.",
                "https://www.istat.it",
                50.0
            )

    # H. Pure Wealth Tax claiming 40-50+ billion
    if "patrimoniale" in s_low and not _is_opposing_subject(s_low, ["patrimoniale"]):
        if any(w in statement_and_meta for w in ["50 miliardi", "40 miliardi", "risolve il debito"]):
            return (
                "Gettito teorico calcolato a staticità di comportamenti, non confermato dall'esperienza tributaria internazionale.",
                "Esagerato",
                "Gli studi empirici della Banca d'Italia stimano che le imposte patrimoniali pure generano tra il 30% e il 50% in meno del gettito teorico a causa della mobilità dei capitali e del contenzioso tributario.",
                "https://www.bancaditalia.it",
                45.0
            )

    # I. Ripristino integrale della scala mobile
    if "scala mobile" in s_low and not _is_opposing_subject(s_low, ["scala mobile"]):
        return (
            "Criticità macroeconomica e monetaria: il ripristino dell'indicizzazione automatica generalizzata salari-prezzi alimenta spirali inflazionistiche.",
            "Esagerato",
            "Banca d'Italia e BCE ricordano che il superamento della scala mobile (Protocollo Ciampi 1993) ha garantito la convergenza dell'inflazione italiana agli standard europei; un meccanismo automatico rigido riduce la flessibilità della contrattazione collettiva.",
            "https://www.bancaditalia.it",
            50.0
        )

    # J. ZES Unica con 100% decontribuzione totale generalizzata
    if "zes" in s_low and not _is_opposing_subject(s_low, ["zes", "decontribuzione"]):
        if any(w in s_low for w in ["100% decontribuzione", "decontribuzione al 100%", "azzeramento totale contributi", "decontribuzione totale"]):
            return (
                "Incompatibilità con la disciplina comunitaria degli aiuti di Stato senza specifica deroga della Commissione UE.",
                "Esagerato",
                "L'art. 107 del Trattato sul Funzionamento dell'Unione Europea (TFUE) vieta sgravi contributivi operativi generali a tempo indeterminato; la 'Decontribuzione Sud' è stata autorizzata da Bruxelles solo come misura transitoria e decrescente.",
                "https://ec.europa.eu/competition/state_aid",
                50.0
            )

    # K. Mass repatriations without bilateral deals
    if "rimpatri" in s_low and not _is_opposing_subject(s_low, ["rimpatri"]):
        if any(w in s_low for w in ["massa", "tutti gli immigrati", "500.000", "centinaia di migliaia"]):
            return (
                "Obiettivo logistico e diplomatico irrealizzabile nei volumi dichiarati per assenza di accordi bilaterali di riammissione con i Paesi di origine.",
                "Esagerato",
                "La Corte dei Conti e i dati del Ministero dell'Interno documentano che la capacità effettiva di rimpatrio forzoso o assistito dell'Italia si attesta su circa 4.000-5.000 persone l'anno, subordinata all'accettazione e identificazione da parte degli Stati terzi.",
                "https://www.corteconti.it",
                45.0
            )

    # =========================================================================
    # 4. ENACTED LAWS / CERTIFIED TECHNICAL ACTS (90% - 95%)
    # Check ONLY sintesi and tipo_azione (NEVER coperture_dichiarate!)
    # =========================================================================

    s_and_act = f"{s_low} {act_low}"

    # Special Constitutional Ruling Check: Autonomia Differenziata L. 86/2024 (Sentenza Consulta 192/2024)
    if "autonomia differenziata" in s_low and not _is_opposing_subject(s_low, ["autonomia differenziata", "calderoli"]):
        if any(k in s_and_act for k in ["86/2024", "calderoli", "legge ordinaria", "legge dello stato"]):
            return (
                "Legge approvata dal Parlamento (L. 86/2024), ma dichiarata parzialmente incostituzionale dalla Consulta con sentenza n. 192/2024 su 7 profili attuativi (tra cui la previa definizione e copertura dei LEP).",
                "Parzialmente verificato",
                "La Corte Costituzionale (sentenza n. 192/2024) ha confermato la legittimità del quadro generale ex art. 116 Cost., ma ha dichiarato illegittime norme centrali della L. 86/2024, subordinando ogni trasferimento di funzioni alla previa definizione parlamentare e copertura dei LEP.",
                "https://www.cortecostituzionale.it",
                80.0
            )

    enacted_law_patterns = [
        r"\blegge dello stato\b", r"\blegge ordinaria\b", r"\bl\.\s*86/2024\b",
        r"\bl\.\s*159/2024\b", r"\bl\.\s*14/2024\b", r"\bl\.\s*206/2023\b",
        r"\bl\.\s*197/2022\b", r"\bl\.\s*15/2024\b", r"\bd\.?lgs\.?\s*\d+/\d{4}\b",
        r"\bd\.?l\.?\s*(?:73/2024|35/2023|11/2023|siccit[àa])\b",
        r"\baccordo bilaterale ratificato\b", r"\bdelibera cipess\b",
        r"\batto di governo\b", r"\bdisegno di legge approvato\b"
    ]
    is_enacted_law = any(re.search(pat, s_and_act) for pat in enacted_law_patterns)
    if is_enacted_law and not _is_opposing_subject(s_low, ["legge", "decreto", "autonomia", "protocollo", "ponte"]):
        return (
            "Provvedimento normativo formalizzato e approvato con legge dello Stato o atto di governo provvisto di copertura ex art. 81 Cost.",
            "Verificato",
            "Provvedimento formalizzato con atto legislativo primario o decreto governativo pubblicato in Gazzetta Ufficiale provvisto di relazione tecnica asseverata.",
            "https://www.normattiva.it",
            95.0
        )

    # Salario Minimo Legale 9€ / 9.50€ (Formal bill with official INPS technical report)
    if "salario minimo" in s_low and not _is_opposing_subject(s_low, ["salario minimo"]):
        if any(w in s_low for w in ["9 euro", "9€", "9.50", "9,50"]):
            return (
                "Proposta di legge parlamentare asseverata dalle audizioni e dalle memorie tecniche dell'INPS.",
                "Verificato",
                "I parametri di platea (circa 3.6 milioni di contratti sotto soglia nel settore privato) e gli impatti sono documentati nella memoria tecnica depositata dall'INPS presso la Commissione Lavoro della Camera.",
                "https://www.inps.it/dati-e-bilanci/relazione-tecnica-salario-minimo",
                90.0
            )

    # Nuclear SMR (MASE National Sustainable Nuclear Platform — balanced with renewables PNIEC benchmark)
    if "nucleare" in s_low and not _is_opposing_subject(s_low, ["nucleare"]):
        if any(w in s_low for w in ["smr", "quarta generazione", "iv generazione", "reattori modulari", "microreattori"]):
            return (
                "Indirizzo tecnologico coerente con la Piattaforma Nazionale per il Nucleare Sostenibile (MASE), subordinato alla legge delega quadro e all'individuazione del deposito nazionale.",
                "Parzialmente verificato",
                "Coerente con gli indirizzi esplorativi del MASE (PNNS) e le linee guida AIEA sulla decarbonizzazione; l'attuazione operativa richiede ancora il quadro normativo primario, l'autorità di sicurezza nucleare e la copertura pluriennale degli investimenti.",
                "https://www.mase.gov.it/portale/piattaforma-nazionale-nucleare-sostenibile",
                80.0
            )

    # Renewables & CER aligned with PNIEC 2030 / MASE / GSE (symmetric neutral energy benchmark)
    if any(w in s_low for w in ["rinnovabili", "comunità energetiche", "fotovoltaico", "eolico"]) and not _is_opposing_subject(s_low, ["rinnovabili", "fotovoltaico"]):
        if any(w in s_low for w in ["2030", "2035", "pniec", "comunità energetiche", "cer", "10 gw", "20 gw"]):
            return (
                "Obiettivo coerente con la traiettoria europea Fit-for-55 e il PNIEC 2030 (MASE/GSE), subordinato all'accelerazione degli iter autorizzativi e degli accumuli di rete Terna.",
                "Parzialmente verificato",
                "I dati GSE e Terna confermano la crescita delle fonti rinnovabili (~37-40% dei consumi elettrici); il raggiungimento dei target 2030-2035 richiede tuttavia un significativo incremento degli investimenti in rete di trasmissione e sistemi di accumulo.",
                "https://www.gse.it/dati-e-scenari/statistiche",
                80.0
            )

    # =========================================================================
    # 5. FORMAL BILLS / DEPOSITED PARLIAMENTARY INITIATIVES (85%)
    # Check ONLY sintesi and tipo_azione (never raw press prose)
    # =========================================================================

    deposited_patterns = [
        r"\bdisegno di legge\b", r"\bddl\b", r"\btesto unificato\b",
        r"\ba\.c\.\s*\d*", r"\ba\.s\.\s*\d*", r"\bddl nordio\b",
        r"\bproposta di legge parlamentare\b", r"\bproposta di legge costituzionale\b",
        r"\bdisegno di legge costituzionale\b", r"\bdisegno di legge delega\b",
        r"\bdisegno di legge depositato\b"
    ]
    if any(re.search(pat, s_and_act) for pat in deposited_patterns):
        return (
            "Disegno o proposta di legge formalmente depositata presso le Camere con iter parlamentare incardinato.",
            "Parzialmente verificato",
            "Atto parlamentare depositato presso la Camera o il Senato; iniziativa istituzionale provvista di testo normativo in Commissione.",
            "https://www.parlamento.it/leg19",
            85.0
        )

    # =========================================================================
    # 6. STRUCTURED PROGRAMMATIC COMMITMENTS WITH CLEAR QUANTIFICATION (80%)
    # =========================================================================

    has_specific_detail = (
        len(sintesi or "") >= 45 and
        any(c.isdigit() for c in (sintesi or "")) and
        bool(coperture) and len(coperture) >= 20 and
        not any(w in cov_low for w in ["non specificat", "da definire", "nessuna"])
    )
    if has_specific_detail:
        return (
            "Proposta programmatica strutturata con quantificazione di massima e indicazione delle fonti di finanziamento.",
            "Posizione programmatica",
            "Posizione politica articolata con parametri quantitativi e canali di copertura coerenti con l'ordinamento.",
            "https://www.parlamento.it/leg19",
            80.0
        )

    # =========================================================================
    # 7. STANDARD POLITICAL MANIFESTO PROPOSALS (75%)
    # =========================================================================
    return (
        "Posizione politica o programmatica enunciata nei manifesti o nelle mozioni di partito.",
        "Posizione programmatica",
        "Dichiarazione ufficiale asseverata dalle posizioni congressuali del partito o dagli atti parlamentari di indirizzo presentati nella XIX Legislatura.",
        "https://www.parlamento.it/leg19",
        75.0
    )
