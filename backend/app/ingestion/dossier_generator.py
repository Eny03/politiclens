import json
import datetime
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import PoliticalParty, PoliticalProposal, InstitutionalBenchmark
from app.ai.fiscal_calculator import calculate_fiscal_impact_and_coverage, calculate_financial_coverage_percentage
from app.ai.fact_checker import calculate_proposal_truthfulness_score

# Specialized Institutional Knowledge Base for all 18 Monitored Political Forces
PARTY_PROFILES_KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "Fratelli d'Italia": {
        "identita": "Conservatorismo nazionale, sovranismo economico ed eurorealismo",
        "ruolo_legislatura": "Prima forza politica della XIX Legislatura e guida del Governo Meloni (118 deputati, 66 senatori).",
        "visione_economica": "Politica dell'offerta ('Non disturbare chi vuole fare'), incentivi selettivi all'occupazione ('Più assumi meno paghi') e rigore nei saldi primari di bilancio sotto i vincoli del Patto di Stabilità UE.",
        "battaglie_chiave": [
            "Riforma costituzionale del Premierato con elezione diretta del Presidente del Consiglio (AS 935)",
            "Taglio strutturale del cuneo fiscale contributivo per redditi fino a 35.000€ (10.8 Mld/anno)",
            "Piano Mattei per l'Africa e protocollo bilaterale Italia-Albania per la gestione dei flussi migratori",
            "Riforma IRPEF a tre aliquote (23%, 35%, 43%) e concordato preventivo biennale"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": "Proposta di blocco navale navale per l'immigrazione e taglio drastico delle accise sui carburanti."},
            {"periodo": "2023-2024 (Esercizio di governo)", "sintesi": "Pragmatismo multilaterale: transizione dal blocco navale al Piano Mattei e accordo Albania; sterilizzazione del cuneo anziché taglio accise."},
            {"periodo": "2025-2026 (Consolidamento)", "sintesi": "Accorpamento del taglio cuneo con l'IRPEF a tre aliquote resa strutturale e accelerazione sul Premierato in Parlamento."}
        ],
        "punti_forza": "Elevata disciplina di bilancio rispettata dal MEF; coesione parlamentare maggioritaria; riforme fiscali finanziate con gettito e riordino tax expenditures.",
        "criticita": "Coperture del concordato biennale soggette a volatilità di adesione; pressione della spesa sanitaria in percentuale sul PIL (6.4%); tensioni con gli alleati su pensioni e autonomia."
    },
    "Partito Democratico": {
        "identita": "Socialdemocrazia, progressismo ecologista ed europeismo federale",
        "ruolo_legislatura": "Prima forza di opposizione parlamentare guidata dalla segretaria Elly Schlein (69 deputati, 38 senatori).",
        "visione_economica": "Rafforzamento del welfare pubblico, redistribuzione fiscale progressiva, contrasto al lavoro povero e transizione ecologica finanziata con risorse PNRR e prelievi sui grandi patrimoni.",
        "battaglie_chiave": [
            "Salario minimo legale universale a 9 euro (aggiornato a 9.50€ lordi) per tutti i settori contrattuali",
            "Fondo Sanitario Nazionale indicizzato obbligatoriamente al 7.5% del PIL e sblocco delle assunzioni mediche",
            "Tempo pieno scolastico generalizzato al Sud e allineamento degli stipendi dei docenti alla media UE",
            "Contributo di solidarietà sui patrimoni superiori a 5 milioni di euro e contrasto all'autonomia differenziata"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": "Difesa dell'impianto Draghi, dote per i diciottenni finanziata da imposte di successione ed estensione del Reddito di Cittadinanza."},
            {"periodo": "2023-2024 (Segreteria Schlein)", "sintesi": "Svolta a sinistra con centralità assoluta della battaglia sul salario minimo a 9€ unitaria con M5S/AVS e raccolta firme per il referendum sull'Autonomia."},
            {"periodo": "2025-2026 (Contromanovre)", "sintesi": "Rilancio del salario minimo a 9.50€ causa inflazione e focus totale sulla salvaguardia del Servizio Sanitario Nazionale contro la privatizzazione strisciante."}
        ],
        "punti_forza": "Coerenza programmatica sui temi del lavoro debole e dei diritti civili; convergenza su mozioni unitarie con le altre forze d'opposizione.",
        "criticita": "La richiesta di portare il FSN al 7.5% del PIL (+20 Mld) presuppone entrate da evasione fiscale che l'Ufficio Parlamentare di Bilancio non consente di iscrivere come coperture fisse preventive."
    },
    "Movimento 5 Stelle": {
        "identita": "Progressismo sociale, pacifismo, transizione ecologica integrale e giustizia distributiva",
        "ruolo_legislatura": "Seconda forza di opposizione parlamentare a guida Giuseppe Conte (52 deputati, 28 senatori).",
        "visione_economica": "Interventismo economico espansivo, tutela del reddito minimo universale, settimana lavorativa corta a 32 ore a parità di stipendio e tassazione straordinaria su extraprofitti finanziari.",
        "battaglie_chiave": [
            "Ripristino di un'indennità universale di dignità (nuovo Reddito di Cittadinanza)",
            "Settimana lavorativa corta a 32 ore a parità salariale per redistribuire il lavoro e favorire la produttività",
            "Tassazione straordinaria al 100% degli extraprofitti bancari, assicurativi e delle industrie belliche",
            "Blocco definitivo del Ponte sullo Stretto di Messina e dirottamento dei 13.5 Mld su ferrovie e acquedotti"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": "Difesa del Reddito di Cittadinanza e rivendicazione del Superbonus 110% per l'edilizia residenziale."},
            {"periodo": "2023-2024 (Riorganizzazione)", "sintesi": "Opposizione dura all'escalation delle spese militari NATO al 2% PIL e presentazione della proposta di legge per la settimana corta a 32 ore."},
            {"periodo": "2025-2026 (Nuova costituente)", "sintesi": "Riformulazione del profilo identitario progressista, no ad alleanze subalterne e rilancio del piano d'investimenti idrici e ferroviari al Sud."}
        ],
        "punti_forza": "Elevata presa sulle fasce di disagio sociale ed economico del Mezzogiorno; intransigenza sulle tematiche pacifiste e contrarietà alle armi.",
        "criticita": "Le stime di gettito derivanti da extraprofitti bancari (attesi 8.5 Mld) sono considerate aleatorie dalla Banca d'Italia e soggette a ricorsi di incostituzionalità se applicate retroattivamente."
    },
    "Lega - Salvini Premier": {
        "identita": "Autonomismo federale, conservatorismo identitario e sovranismo economico",
        "ruolo_legislatura": "Pilastro fondante della maggioranza di centrodestra guidato da Matteo Salvini (66 deputati, 29 senatori).",
        "visione_economica": "Riduzione generalizzata delle imposte sul ceto produttivo autonomo (Flat Tax), sblocco delle grandi opere strategiche e superamento anticipato delle rigidità previdenziali Fornero.",
        "battaglie_chiave": [
            "Attuazione integrale della Legge sull'Autonomia Differenziata regionale (L. 86/2024)",
            "Pensione con Quota 41 pura (41 anni di contributi a prescindere dall'età anagrafica)",
            "Realizzazione del Ponte sullo Stretto di Messina (investimento pluriennale di 13.5 miliardi €)",
            "Estensione della Flat Tax al 15% fino a 100.000 euro per tutte le partite IVA e liberi professionisti"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": "Quota 41 immediata, Flat tax generalizzata per tutti e blocco sbarchi."},
            {"periodo": "2023-2024 (Azione ministeriale)", "sintesi": "Approvazione storica della Legge Calderoli sull'autonomia, avvio cantieri Ponte e mediazione previdenziale su Quota 103 per vincoli di cassa."},
            {"periodo": "2025-2026 (Consolidamento)", "sintesi": "Difesa dell'autonomia contro i referendum, piano casa per giovani coppie e rilancio dell'energia nucleare pulita con reattori SMR."}
        ],
        "punti_forza": "Capacità di condizionamento dell'agenda infrastrutturale e regionale; radicamento amministrativo negli enti locali del Nord.",
        "criticita": "Il costo di Quota 41 secca (stimato da INPS in 4.5 Mld nel primo anno e 9 Mld a regime) non trova spazio finanziario compatibile con i saldi di bilancio della Ragioneria Generale dello Stato."
    },
    "Forza Italia": {
        "identita": "Liberalismo cattolico, popolarismo europeo (PPE) e garantismo giudiziario",
        "ruolo_legislatura": "Componente moderata, centrista e atlantista del centrodestra guidata da Antonio Tajani (45 deputati, 18 senatori).",
        "visione_economica": "Economia sociale di mercato, tutela del risparmio privato, riduzione dell'imposizione sul ceto medio, sburocratizzazione e valorizzazione delle piccole e medie imprese.",
        "battaglie_chiave": [
            "Innalzamento progressivo delle pensioni minime verso i 1.000 euro mensili",
            "Separazione delle carriere tra magistratura requirente e giudicante (riforma costituzionale della giustizia)",
            "Taglio della seconda aliquota IRPEF dal 35% al 33% estendendo lo scaglione a 60.000€",
            "Apertura al riconoscimento della cittadinanza per gli studenti stranieri (Ius Scholae a 10 anni)"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": "Impegno storico di Silvio Berlusconi per le pensioni minime a 1.000 euro e Flat tax per tutti."},
            {"periodo": "2023-2024 (Riorganizzazione Tajani)", "sintesi": "Rafforzamento del profilo istituzionale, lealtà europeista nel PPE, innalzamento delle minime a 614€ e mediazione sulla giustizia."},
            {"periodo": "2025-2026 (Profilo moderato)", "sintesi": "Posizionamento distintivo al centro della coalizione: sì allo Ius Scholae, sostegno alle banche contro prelievi forzosi e taglio IRPEF per il ceto medio."}
        ],
        "punti_forza": "Affidabilità istituzionale a livello UE e con i mercati finanziari; credibilità sul fronte della riforma della giustizia civile e penale.",
        "criticita": "L'innalzamento generalizzato delle pensioni minime a 1.000 euro per tutti i pensionati comporterebbe un onere strutturale superiore a 18 miliardi annui, non sostenibile a debito."
    },
    "Alleanza Verdi e Sinistra": {
        "identita": "Ecosocialismo, giustizia climatica, antifascismo e pacifismo radicale",
        "ruolo_legislatura": "Formazione di sinistra ecologista guidata da Angelo Bonelli e Nicola Fratoianni (12 deputati, 4 senatori).",
        "visione_economica": "Superamento del modello estrattivista, piano industriale verde per 10 GW/anno di rinnovabili, trasporto pubblico gratuito e ridistribuzione della ricchezza tramite imposta patrimoniale progressiva.",
        "battaglie_chiave": [
            "Imposta di solidarietà sui grandi patrimoni superiori a 5 milioni di euro (gettito atteso 10 Mld/anno)",
            "Salario minimo a 10 euro netti indicizzato all'inflazione e introduzione del reato di omicidio sul lavoro",
            "Moratoria totale sul nucleare e cancellazione definitiva del progetto del Ponte sullo Stretto",
            "Istituzione del trasporto pubblico locale gratuito per studenti e giovani under 26 su base nazionale"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": "Costruzione dell'alleanza rosso-verde per la transizione ecologica radicale e stop ai sussidi fossili."},
            {"periodo": "2023-2024 (Consolidamento europeo)", "sintesi": "Successo alle europee (oltre il 6%), battaglie parlamentari per la tutela del clima e opposizione intransigente al decreto Sicurezza."},
            {"periodo": "2025-2026 (Opposizione ecologista)", "sintesi": "Ricorsi contro i progetti infrastrutturali a forte impatto ambientale e pressing per l'approvazione urgente della legge sul clima."}
        ],
        "punti_forza": "Coerenza programmatica totale sulle sfide climatiche e dei diritti umani; forte attrazione tra l'elettorato giovanile.",
        "criticita": "Il gettito teorico delle imposte patrimoniali pure è stimato dalla Banca d'Italia in misura inferiore del 40% rispetto alle tabelle dichiarate a causa di elusione e delocalizzazioni finanziarie."
    },
    "Azione": {
        "identita": "Liberalismo sociale, pragmatismo tecnocratico e riformismo atlantista",
        "ruolo_legislatura": "Partito liberaldemocratico autonomo all'opposizione guidato da Carlo Calenda (12 deputati, 4 senatori).",
        "visione_economica": "Efficienza dell'amministrazione pubblica, investimenti mirati sulla sanità, ripristino di Industria 4.0/Transizione 5.0, nucleare energetico e meritocrazia scolastica.",
        "battaglie_chiave": [
            "Piano straordinario da 10 miliardi per la Sanità pubblica: eliminazione del tetto alle assunzioni e azzeramento liste attesa",
            "Ritorno dell'energia nucleare con reattori di IV generazione per raggiungere zero emissioni al 2050",
            "Estensione erga omnes dei contratti collettivi CNEL (alternativa tecnica al salario minimo per legge)",
            "Azzeramento totale delle imposte sul lavoro per i giovani under 30 nei primi tre anni di carriera"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": "Esperienza del Terzo Polo con Italia Viva incentrata su continuità dell'agenda Draghi."},
            {"periodo": "2023-2024 (Autonomia politica)", "sintesi": "Separazione dal Terzo Polo, concentrazione sui dossier tecnici: sanità pubblica, piano nucleare e contromanovre documentate voce per voce."},
            {"periodo": "2025-2026 (Polo pragmatico)", "sintesi": "Azione di opposizione costruttiva sui singoli provvedimenti (sanità e competitività) rifiutando populismi di destra e sinistra."}
        ],
        "punti_forza": "Analisi economica supportata da relazioni tecniche dettagliate; proposte allineate ai benchmark OCSE ed Eurostat.",
        "criticita": "Difficoltà nel creare masse critiche elettorali autonome senza alleanze di coalizione stabili."
    },
    "Italia Viva": {
        "identita": "Riformismo centrista, liberismo dinamico, garantismo e modernizzazione infrastrutturale",
        "ruolo_legislatura": "Forza centrista all'opposizione guidata dall'ex Presidente del Consiglio Matteo Renzi (7 deputati, 7 senatori).",
        "visione_economica": "Decontribuzione per le assunzioni a tempo indeterminato, sblocco degli appalti pubblici con commissari straordinari (modello Genova), attrazione d'investimenti e rifiuto dell'assistenzialismo.",
        "battaglie_chiave": [
            "Piano 'Shock': sblocco immediato di 30 miliardi di cantieri infrastrutturali già finanziati ma fermi",
            "Elezione diretta del Presidente del Consiglio sul modello del 'Sindaco d'Italia'",
            "Defiscalizzazione totale degli straordinari e dei premi di produttività aziendale",
            "Separazione netta delle carriere tra magistrati requirenti e giudicanti"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": "Promozione dell'agenda Draghi nel Terzo Polo e no ai sussidi a fondo perduto."},
            {"periodo": "2023-2024 (Riorientamento strategico)", "sintesi": "Rottura del Terzo Polo con Calenda, riavvicinamento dialogante con il centrosinistra e referendum sulla giustizia."},
            {"periodo": "2025-2026 (Costruzione alternativa)", "sintesi": "Offensiva garantista in Parlamento, proposta per il Sindaco d'Italia e mobilitazione per la crescita economica contro la stagnazione."}
        ],
        "punti_forza": "Forte esperienza amministrativa di governo e competenza nelle dinamiche parlamentari di Camera e Senato.",
        "criticita": "Consenso elettorale contenuto nei sondaggi (~2-3%) e necessità di accordi di coalizione per superare gli sbarramenti."
    },
    "+Europa": {
        "identita": "Liberalismo classico, federalismo europeo integrale e radicalismo dei diritti civili",
        "ruolo_legislatura": "Forza europeista e libertaria guidata da Riccardo Magi ed Emma Bonino (3 deputati).",
        "visione_economica": "Concorrenza nei mercati protetti (concessioni balneari, taxi, farmacie), abbattimento della spesa pubblica clientelare, federalismo fiscale europeo e contrasto al debito pubblico a carico delle future generazioni.",
        "battaglie_chiave": [
            "Costruzione degli Stati Uniti d'Europa con esercito comune e bilancio federale autonomo",
            "Legalizzazione della cannabis per fini terapeutici e ricreativi (gettito stimato +7 Mld/anno)",
            "Legge sul Fine Vita con regolamentazione dell'eutanasia legale e testamento biologico",
            "Superamento della Legge Bossi-Fini e introduzione di canali legali di ingresso per motivi di lavoro"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": "Alleanza con il PD a difesa dell'ancoraggio europeo contro il sovranismo di destra."},
            {"periodo": "2023-2024 (Stati Uniti d'Europa)", "sintesi": "Lista di scopo alle elezioni europee per il federalismo continentale e mobilitazione sul referendum cittadinanza."},
            {"periodo": "2025-2026 (Diritti e concorrenza)", "sintesi": "Battaglie alla Camera su carceri, libertà civili e diffide contro il rinnovo delle concessioni balneari prive di gare."}
        ],
        "punti_forza": "Riferimento di trasparenza sui temi delle libertà individuali, dei diritti riproduttivi e dell'integrazione comunitaria.",
        "criticita": "Marginalità numerica nei seggi parlamentari che limita l'incidenza diretta sull'approvazione delle leggi di bilancio."
    },
    "Partito Liberal Democratico": {
        "identita": "Liberismo economico anglosassone, efficienza del mercato e rigore fiscale",
        "ruolo_legislatura": "Nuova formazione politica liberale guidata dall'on. Luigi Marattin.",
        "visione_economica": "Taglio lineare della spesa pubblica inefficiente per ridurre le aliquote fiscali, privatizzazione delle municipalizzate partecipate in perdita e rifiuto totale del deficit pubblico.",
        "battaglie_chiave": [
            "Contrattazione aziendale e territoriale con clausola di opt-out dai contratti collettivi nazionali (CCNL)",
            "Privatizzazione e messa a gara delle società partecipate pubbliche locali",
            "Abolizione di ogni prepensionamento assistenziale e rispetto rigoroso del pareggio di bilancio",
            "Abbassamento delle aliquote marginali IRPEF con rimozione dei sussidi a pioggia alle imprese"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022-2024 (Genesi)", "sintesi": "Critica dall'interno al centrismo privo di radicamento liberale autentico e separazione da Italia Viva."},
            {"periodo": "2024-2025 (Fondazione)", "sintesi": "Nascita del Partito Liberal Democratico con manifesto liberista basato su scuola, merito e concorrenza."},
            {"periodo": "2026 (Consolidamento)", "sintesi": "Campagna per il pareggio strutturale di bilancio e mobilitazione per la deregolamentazione economica del lavoro."}
        ],
        "punti_forza": "Assoluto rigore metodologico sui conti pubblici e rispetto stringente dei parametri di contabilità di Stato.",
        "criticita": "Forza politica giovane in fase di insediamento territoriale; assenza di una rappresentanza parlamentare di gruppo autonomo."
    },
    "Noi Moderati": {
        "identita": "Cristianesimo sociale, sussidiarietà territoriale e popolarismo di centro",
        "ruolo_legislatura": "Quarta componente della coalizione di governo guidata da Maurizio Lupi (9 deputati, 3 senatori).",
        "visione_economica": "Potenziamento del quoziente familiare fiscale, detassazione del welfare aziendale e valorizzazione del Terzo Settore e degli enti non profit.",
        "battaglie_chiave": [
            "Introduzione del quoziente familiare per rimodulare le aliquote IRPEF sul numero effettivo dei figli",
            "Sgravi contributivi al 100% per le imprese che offrono asili nido aziendali e borse di studio",
            "Sostegno strutturale alle scuole paritarie con buoni scuola per le famiglie a basso reddito",
            "Valorizzazione della sussidiarietà orizzontale e del volontariato nella gestione dei servizi alla persona"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022-2024 (Azione d'aula)", "sintesi": "Ruolo di raccordo centrista nel centrodestra a tutela della famiglia e delle detrazioni fiscali."},
            {"periodo": "2025-2026 (Consolidamento)", "sintesi": "Focus costante sul sostegno alla natalità nella Legge di Bilancio e sul potenziamento dei congedi parentali."}
        ],
        "punti_forza": "Ruolo di cerniera moderata di governo, forte legame con il mondo cattolico e l'associazionismo sociale.",
        "criticita": "Spazio di visibilità limitato rispetto ai due partiti maggiori della coalizione (FdI e Lega)."
    },
    "Futuro Nazionale": {
        "identita": "Sovranismo identitario radicale, tradizionalismo culturale e difesa della sovranità nazionale",
        "ruolo_legislatura": "Movimento politico guidato dal generale Roberto Vannacci.",
        "visione_economica": "Protezionismo dei settori produttivi strategici italiani, rifiuto delle direttive green UE su automobili e case, potenziamento delle risorse per le forze di sicurezza e difesa.",
        "battaglie_chiave": [
            "Blocco dell'applicazione delle direttive europee 'Case Green' e dello stop ai motori endotermici al 2035",
            "Incremento straordinario dei fondi per equipaggiamenti e tutele legali delle Forze Armate e di Polizia",
            "Ripristino della leva militare o civile universale su base obbligatoria per i giovani",
            "Primato della sovranità costituzionale italiana rispetto ai vincoli e regolamenti dell'Unione Europea"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2023-2024 (Origine)", "sintesi": "Successo editoriale del libro-manifesto e record di preferenze personali alle elezioni europee."},
            {"periodo": "2025-2026 (Strutturazione)", "sintesi": "Aggregazione di comitati territoriali identitari su temi di sovranità nazionale e sicurezza urbana."}
        ],
        "punti_forza": "Forte appeal mediatico su un elettorato fortemente critico verso il politicamente corretto e la burocrazia di Bruxelles.",
        "criticita": "Mancanza di una quantificazione finanziaria formale depositata nelle commissioni parlamentari competenti."
    },
    "ORA!": {
        "identita": "Riformismo liberale radicale, meritocrazia, sradicamento corporativo e concorrenza",
        "ruolo_legislatura": "Movimento d'opinione e proposta politica fondato da Michele Boldrin e Alberto Forchielli.",
        "visione_economica": "Taglio netto dei sussidi alle 'imprese zombie', liberalizzazione totale dei mercati chiusi (balneari, taxi, ordini professionali) e shock di produttività per il sistema-Paese.",
        "battaglie_chiave": [
            "Messa all'asta trasparente di tutte le concessioni demaniali balneari e delle licenze taxi",
            "Riforma radicale della governance universitaria con finanziamenti legati all'impatto scientifico",
            "Riduzione strutturale del debito pubblico tramite dismissioni patrimoniali e azzeramento prebende",
            "Defiscalizzazione per attrarre talenti, ricercatori e capitali esteri ad alta produttività"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2024 (Lancio)", "sintesi": "Pubblicazione del programma di rottura contro corporativismo e stagnazione della produttività italiana."},
            {"periodo": "2025-2026 (Crescita)", "sintesi": "Tour universitario e incontri pubblici per mobilitare la diaspora italiana qualificata all'estero."}
        ],
        "punti_forza": "Approccio scientifico basato sull'evidenza empirica e sui dati economici internazionali.",
        "criticita": "Assenza di una macchina di partito tradizionale sul territorio e seggi parlamentari."
    },
    "Democrazia Sovrana Popolare": {
        "identita": "Sovranismo popolare, antiliberismo, anticapitalismo e neutralità geopolitica",
        "ruolo_legislatura": "Movimento antisistema guidato da Marco Rizzo.",
        "visione_economica": "Uscita dell'Italia dall'Euro e dalla NATO, nazionalizzazione del settore bancario, energetico e delle telecomunicazioni, e tutela assoluta della sovranità alimentare e industriale.",
        "battaglie_chiave": [
            "Recupero della sovranità monetaria nazionale con l'uscita dalla zona Euro e dalla BCE",
            "Nazionalizzazione dei settori strategici (ENI, ENEL, Leonardo, autostrade e sanità)",
            "Uscita immediata dalla NATO e revoca di ogni sanzione economica internazionale",
            "Ripristino della piena tutela dei diritti dei lavoratori con reintroduzione dell'art. 18 dello Statuto"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022-2024 (Radicamento)", "sintesi": "Mobilitazione contro le sanzioni e la cobelligeranza nel conflitto ucraino."},
            {"periodo": "2025-2026 (Azione)", "sintesi": "Campagne referendarie popolari e presenza su piazze e fabbriche in difesa della sovranità costituzionale."}
        ],
        "punti_forza": "Radicalismo identitario che canalizza il malcontento delle fasce colpite dalla globalizzazione e dalla deindustrializzazione.",
        "criticita": "Proposte incompatibili con i trattati istituzionali internazionali dell'UE e rischio di isolamento economico sistemico."
    },
    "Rifondazione Comunista": {
        "identita": "Comunismo democratico, anticapitalismo, pacifismo e diritti del lavoro",
        "ruolo_legislatura": "Partito della sinistra di classe guidato da Maurizio Acerbo (aderente al Partito della Sinistra Europea).",
        "visione_economica": "Reintroduzione della Scala Mobile per adeguare automaticamente le retribuzioni all'inflazione reale, settimana lavorativa a 32 ore a parità di salario e imposta patrimoniale progressiva sui grandi patrimoni.",
        "battaglie_chiave": [
            "Reintroduzione della scala mobile a cadenza semestrale sui salari dei lavoratori dipendenti",
            "Riduzione dell'orario normale di lavoro a 32 ore settimanali a parità di retribuzione",
            "Abrogazione totale del Jobs Act, della Legge Fornero e dei voucher per il lavoro",
            "Imposta patrimoniale straordinaria progressiva a partire dai patrimoni superiori a 1 milione di euro"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022-2024", "sintesi": "Opposizione continua alle politiche di austerità europee e sostegno alle lotte dei lavoratori in crisi industriale."},
            {"periodo": "2025-2026", "sintesi": "Fronte unitario con i movimenti studenteschi e pacifisti contro la militarizzazione dei bilanci statali."}
        ],
        "punti_forza": "Coerenza storica con i valori sindacali e dei diritti del lavoro subordinato.",
        "criticita": "L'adeguamento automatico della scala mobile è classificato da ISTAT e Banca d'Italia come generatore di spirali inflazionistiche salario-prezzi."
    },
    "Potere al Popolo": {
        "identita": "Sinistra radicale di classe, internazionalismo, conflittualità sociale e anticapitalismo",
        "ruolo_legislatura": "Movimento popolare guidato da Marta Collot e Giuliano Granato.",
        "visione_economica": "Salario minimo a 10 euro netti orari, stop agli sfratti e alle dismissioni del patrimonio residenziale pubblico, blocco delle spese militari e nazionalizzazione delle grandi industrie in crisi.",
        "battaglie_chiave": [
            "Salario minimo legale a 10 euro netti all'ora agganciato all'inflazione per tutti i comparti",
            "Piano straordinario per 500.000 alloggi di edilizia residenziale pubblica a canone sociale",
            "Tassazione al 100% degli extraprofitti farmaceutici e dell'industria degli armamenti",
            "Abrogazione integrale dei decreti sicurezza e regolarizzazione generalizzata di tutti i migranti"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022-2024", "sintesi": "Raccolta firme per il salario minimo a 10 euro netti e sportelli sociali di mutuo soccorso nelle periferie."},
            {"periodo": "2025-2026", "sintesi": "Mobilitazione nelle vertenze territoriali sulla casa, logistica e contro il carovita."}
        ],
        "punti_forza": "Presenza militante diretta sui luoghi di lavoro, nella logistica e nelle vertenze abitative periferiche.",
        "criticita": "Le coperture da confisca totale di extraprofitti non garantiscono stabilità pluriennale ai capitoli di spesa del bilancio dello Stato."
    },
    "Radicali Italiani": {
        "identita": "Libertarismo, transnazionalismo, laicità dello Stato e diritti umani inviolabili",
        "ruolo_legislatura": "Movimento politico guidato da Matteo Hallissey.",
        "visione_economica": "Legalizzazione e tassazione trasparente dei mercati underground (cannabis, prostituzione), de-carcerizzazione, efficienza della giustizia e rispetto dello Stato di Diritto europeo.",
        "battaglie_chiave": [
            "Legalizzazione della produzione e vendita della cannabis con regime di monopolio fiscale controllato",
            "Amnistia, indulto e piano d'emergenza contro il sovraffollamento carcerario e i suicidi in cella",
            "Legge sul fine vita e riconoscimento della maternità surrogata solidale e altruistica",
            "Abolizione del concordato Stato-Chiesa e revoca delle esenzioni fiscali IMU per gli immobili religiosi commerciali"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022-2024", "sintesi": "Iniziative nonviolente e monitoraggio continuo nelle carceri italiane con dossier per la Corte di Strasburgo."},
            {"periodo": "2025-2026", "sintesi": "Referendum popolari sui diritti civili, digitalizzazione delle firme e denunce contro i monopoli corporativi."}
        ],
        "punti_forza": "Riconoscimento storico di avanguardia nell'elaborazione e approvazione delle grandi riforme civili italiane.",
        "criticita": "Struttura d'opinione focalizzata sui diritti civili con minore elaborazione sulle politiche macroeconomiche di finanza pubblica."
    },
    "Südtiroler Volkspartei": {
        "identita": "Autonomismo regionale, tutela delle minoranze linguistiche e democrazia cristiana territoriale",
        "ruolo_legislatura": "Partito di governo della Provincia Autonoma di Bolzano / Alto Adige guidato da Dieter Steger (3 deputati, 2 senatori).",
        "visione_economica": "Autonomia fiscale (90% dei tributi riscossi resta sul territorio provinciale), salvaguardia dell'agricoltura alpina, bilinguismo perfetto e gestione diretta della sanità.",
        "battaglie_chiave": [
            "Piena attuazione e ripristino delle competenze primarie dello Statuto Speciale di Autonomia del Trentino-Alto Adige",
            "Gestione provinciale esclusiva della sanità pubblica, della scuola bilingue e del trasporto locale",
            "Tutela speciale dell'agricoltura di montagna e contrasto alla proliferazione dei grandi carnivori (lupi/orsi)",
            "Sgravi fiscali specifici per i residenti montani e difesa delle clausole di proporzionale etnica"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022-2024", "sintesi": "Collaborazione istituzionale al Parlamento nazionale per la revisione delle norme di attuazione statutaria."},
            {"periodo": "2025-2026", "sintesi": "Difesa del modello di autonomia altoatesina rispetto alla riforma dell'autonomia differenziata ordinaria."}
        ],
        "punti_forza": "Eccezionale efficienza gestionale del bilancio provinciale e piena soddisfazione dei servizi per i cittadini altoatesini.",
        "criticita": "Ambito di rappresentanza rigorosamente circoscritto alla provincia di Bolzano senza mire sul piano nazionale generale."
    },
    "Sud chiama Nord": {
        "identita": "Autonomismo civico, federalismo solidale ed equità territoriale Nord-Sud",
        "ruolo_legislatura": "Movimento politico guidato da Cateno De Luca e Laura Castelli, con rappresentanza parlamentare alla Camera (on. Francesco Gallo) e all'ARS.",
        "visione_economica": "Riequilibrio delle disparità territoriali tra Nord e Sud, eliminazione della spesa storica nei trasferimenti statali ai Comuni, finanziamento integrale dei LEP prima di qualsiasi intesa di regionalismo differenziato e continuità territoriale garantita per le isole.",
        "battaglie_chiave": [
            "Finanziamento integrale dei LEP (Livelli Essenziali delle Prestazioni) ed eliminazione della spesa storica discriminatoria per il Sud",
            "Continuità territoriale aerea e marittima garantita con tariffe agevolate fisse tutto l'anno per residenti in Sicilia e Sardegna",
            "ZES Unica con decontribuzione al 100% per nuove assunzioni stabili di giovani e donne nel Mezzogiorno",
            "Sblocco delle infrastrutture idriche, completamento delle dighe e ristori alle aziende agricole colpite dalla siccità",
            "Rinegoziazione trentennale dei mutui CDP per i comuni in predissesto o dissesto finanziario senza penalità"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022 (Elezioni Politiche e Regionali)", "sintesi": "Elezione di parlamentari nazionali e radicamento come principale forza autonomista della Sicilia."},
            {"periodo": "2023-2024 (Lista Libertà)", "sintesi": "Costruzione del cartello elettorale Libertà per le Europee 2024 a tutela delle autonomie locali e del civismo territoriale."},
            {"periodo": "2025-2026 (Battaglie Parlamentari)", "sintesi": "Contrasto all'autonomia differenziata senza LEP e vertenze serrate per i trasporti e l'emergenza idrica in Sicilia."}
        ],
        "punti_forza": "Forte radicamento amministrativo nei territori comunali; difesa intransigente dell'equità nei servizi essenziali (sanità, trasporti, scuola) per il Meridione.",
        "criticita": "Concentrazione del consenso prevalente nel Sud e nelle Isole; necessità di costruire alleanze stabili sul piano nazionale."
    },
    "Pace Terra Dignità": {
        "identita": "Pacifismo radicale, ecologia costituzionale, antimilitarismo e diritti sociali",
        "ruolo_legislatura": "Movimento politico fondato da Michele Santoro e Raniero La Valle (2.2% dei consensi alle elezioni europee 2024).",
        "visione_economica": "Drastica riduzione delle spese militari e stop alla corsa al riarmo per finanziare la sanità pubblica e la transizione ecologica; tassazione straordinaria su colossi bellici ed energetici; salario minimo legale a 10 euro netti.",
        "battaglie_chiave": [
            "Cessate il fuoco immediato nei conflitti in Ucraina e Medio Oriente, stop all'invio di armi e neutralità attiva dell'Italia",
            "Aumento del Fondo Sanitario Nazionale ad almeno l'8% del PIL e piano di 40.000 assunzioni di medici e infermieri",
            "Salario minimo a 10 euro netti l'ora e riduzione dell'orario di lavoro a 32 ore a parità salariale",
            "Uscita rapida dalle fonti fossili, stop a nuovi rigassificatori e redistribuzione della ricchezza con patrimoniale progressiva",
            "Amnistia e depenalizzazione per reati minori per svuotare le carceri e tutelare la dignità umana"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2024 (Campagna Europee)", "sintesi": "Oltre 511.000 voti (2.2%) raccolti con una lista unitaria per la pace, la transizione verde e la giustizia sociale."},
            {"periodo": "2025-2026 (Mobilitazione permanente)", "sintesi": "Campagne contro il riarmo europeo, mobilitazioni studentesche e comitati territoriali per la sanità pubblica."}
        ],
        "punti_forza": "Riconoscibilità etica e mediatica di Michele Santoro; capacità di aggregare il voto pacifista, laico e di sinistra alternativa.",
        "criticita": "La rinuncia agli impegni atlantici e NATO pone forti tensioni con il quadro geopolitico occidentale e con le regole europee sui bilanci."
    },
    "Partito Socialista Italiano": {
        "identita": "Socialdemocrazia storica, riformismo laico, welfare universale e diritti del lavoro",
        "ruolo_legislatura": "Storico partito della sinistra democratica italiana guidato da Enzo Maraio (membro del Partito del Socialismo Europeo).",
        "visione_economica": "Economia sociale di mercato, investimento prioritario nella scuola e nella sanità pubblica, contrasto alla precarietà giovanile e piano nazionale di edilizia residenziale pubblica a canone calmierato.",
        "battaglie_chiave": [
            "Salario minimo legale legato alla contrattazione collettiva e superamento del precariato giovanile",
            "Piano Casa Nazionale con 100.000 alloggi di edilizia residenziale pubblica a canone sociale",
            "Potenziamento strutturale del Servizio Sanitario Nazionale e blocco dell'intramoenia a pagamento quando le liste d'attesa superano i limiti",
            "Legge quadro sul fine vita e riconoscimento del matrimonio egualitario",
            "Tempo pieno garantito nelle scuole primarie del Mezzogiorno con mensa scolastica gratuita"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2022-2024", "sintesi": "Partecipazione al cartello riformista ed europeista, radicamento nelle amministrazioni locali e tutela del lavoro dipendente."},
            {"periodo": "2025-2026", "sintesi": "Iniziativa per il piano casa giovanile e convergenza con l'opposizione democratica su sanità e salario minimo."}
        ],
        "punti_forza": "Centenaria tradizione politica socialdemocratica e solido raccordo con i partiti socialisti europei (SPD, PSOE).",
        "criticita": "Consenso elettorale contenuto a livello nazionale, che rende necessaria l'aggregazione in coalizioni di centrosinistra."
    },
    "Alternativa Popolare": {
        "identita": "Popolarismo europeo (PPE), liberalismo d'impresa, sussidiarietà e pragmatismo civico",
        "ruolo_legislatura": "Movimento politico guidato da Stefano Bandecchi (Sindaco di Terni) e Paolo Alli (Presidente AP e già Presidente dell'Assemblea Parlamentare NATO).",
        "visione_economica": "Sostegno concreto alla libera impresa e alle partite IVA, no tax area per i giovani fino a 15.000 euro, decontribuzione per nuove imprese e semplificazione burocratica per le opere pubbliche.",
        "battaglie_chiave": [
            "No tax area fino a 15.000 euro per lavoratori e partite IVA under 35",
            "Piano straordinario di 10.000 assunzioni nelle forze dell'ordine e sicurezza integrata nelle periferie e stazioni",
            "Sblocco rapido dei cantieri delle opere strategiche e accelerazione dell'Alta Velocità ferroviaria",
            "Assegno di natalità di 5.000 euro a fondo perduto nei comuni sotto i 20.000 abitanti a rischio spopolamento",
            "Apertura serale e nei weekend della diagnostica pubblica e accordi a tariffa sociale per azzerare le liste d'attesa"
        ],
        "evoluzione_2022_2026": [
            {"periodo": "2023-2024", "sintesi": "Vittoria al Comune di Terni con l'elezione di Bandecchi a Sindaco e corsa autonoma alle elezioni europee."},
            {"periodo": "2025-2026", "sintesi": "Crescita del radicamento civico nel Centro Italia e posizionamento come polo moderato e pragmatico nel PPE."}
        ],
        "punti_forza": "Forte leadership carismatica ed esecutiva; pragmatismo manageriale applicato all'amministrazione degli enti locali.",
        "criticita": "Profilo politico fortemente accentrato sulla figura del leader e polarizzazione comunicativa sui media."
    }
}

def generate_party_dossier(party: PoliticalParty, db: Session) -> Dict[str, Any]:
    """
    Synthesizes all gathered web data, official statements, and economic fact-checks
    into a comprehensive, structured AI Strategic Dossier for a political party.
    Combines the deep institutional knowledge base with live database records.
    """
    proposals = db.query(PoliticalProposal).filter(
        (PoliticalProposal.party_id == party.id) | (PoliticalProposal.partito.ilike(f"%{party.name}%"))
    ).order_by(PoliticalProposal.timestamp.desc()).all()

    # Economic benchmarks for comparison
    benchmarks = db.query(InstitutionalBenchmark).all()
    benchmarks_summary = {b.indicatore: f"{b.valore} {b.unita} ({b.fonte_istituzionale} {b.anno_riferimento})" for b in benchmarks}

    # Macro-topics grouping
    topic_groups: Dict[str, List[PoliticalProposal]] = {}
    for p in proposals:
        topic_groups.setdefault(p.macro_argomento, []).append(p)

    total_props = len(proposals)
    verified_count = sum(1 for p in proposals if p.fact_check_status == "Verificato")
    pending_coverage = sum(1 for p in proposals if p.fact_check_status == "In attesa di copertura")
    exaggerated_count = sum(1 for p in proposals if p.fact_check_status in ["Esagerato", "Fake / Infondato"])

    feasibility_score = round(sum(calculate_proposal_truthfulness_score(p.fact_check_status) for p in proposals) / total_props) if total_props > 0 else 80

    # Fetch Specialized Strategic Knowledge Profile for this party
    profile = PARTY_PROFILES_KNOWLEDGE_BASE.get(party.name, None)
    if not profile:
        for k, v in PARTY_PROFILES_KNOWLEDGE_BASE.items():
            if k.lower() in party.name.lower() or party.name.lower() in k.lower():
                profile = v
                break

    # 1. Articulate, Deep AI Strategic Synthesis
    if profile:
        sintesi_politica = (
            f"**Identità e Linea Strategica:** {party.name} si qualifica nell'arco politico italiano come espressione di {profile['identita'].lower()}. "
            f"{profile['ruolo_legislatura']} La visione economica fondamentale è imperniata su {profile['visione_economica'].lower()} "
            f"L'osservatorio indipendente ha censito nello storico persistente {total_props} atti parlamentari, disegni di legge e prese di posizione ufficiali rielaborate dal web. "
            f"I fronti programmatici prioritari risultano essere: {', '.join(list(topic_groups.keys())[:5]) if topic_groups else 'Fisco, Lavoro, Sanità, Istituzioni'}."
        )
        evoluzione_storica = list(profile.get("evoluzione_2022_2026", []))
        punti_forza = profile.get("punti_forza", "Presidio dei temi identitari di schieramento.")
        criticita_osservatorio = profile.get("criticita", "Necessità di quantificare le coperture strutturali di bilancio pluriennali.")
    else:
        sintesi_politica = (
            f"{party.name} ({party.coalition}), sotto la guida di {party.leader or 'Segreteria collegiale'}, "
            f"articola la propria azione politica su {len(topic_groups)} macro-aree tematiche monitorate 24/7. "
            f"L'osservatorio ha censito {total_props} posizioni formalizzate tra atti depositati e dichiarazioni pubbliche. "
            f"I dossier tematici prioritari risultano essere: {', '.join(list(topic_groups.keys())[:4]) if topic_groups else 'Riforme generali'}."
        )
        evoluzione_storica = [
            {"periodo": "2022 (Campagna elettorale)", "sintesi": f"Deposito dei programmi elettorali per la XIX Legislatura da parte di {party.name}."},
            {"periodo": "2023-2024 (Attività)", "sintesi": "Presentazione di atti parlamentari, ordini del giorno e contromanovre sui singoli dossier di spesa."},
            {"periodo": "2025-2026 (Consolidamento)", "sintesi": "Aggiornamento delle priorità su lavoro, fisco e tutela dei bilanci pubblici."}
        ]
        punti_forza = "Continuità nelle prese di posizione sul territorio."
        criticita_osservatorio = "Necessità di quantificazione finanziaria formale nei disegni di legge."

    # Dynamic Evolution Extension: incorporate real newly-ingested proposals for future years
    current_year = datetime.datetime.utcnow().year
    future_props = [p for p in proposals if p.timestamp and p.timestamp.year >= 2025]
    if future_props:
        by_year_map = {}
        for p in sorted(future_props, key=lambda x: x.timestamp or datetime.datetime.min):
            by_year_map.setdefault(p.timestamp.year, []).append(p)
        for yr, p_list in by_year_map.items():
            if yr >= 2026:
                label = f"{yr} (Sviluppi & Iniziative Recenti)" if yr <= current_year else f"{yr} (Proiezioni & DDL Futuri)"
                if not any(str(yr) in ev.get("periodo", "") for ev in evoluzione_storica):
                    summaries = " • ".join([f"[{p.macro_argomento}] {p.dichiarazione_sintesi[:80]}" for p in p_list[:2]])
                    evoluzione_storica.append({
                        "periodo": label,
                        "sintesi": f"Aggiornamento programmatico dinamico: {summaries}"
                    })

    # 2. Key Pillars Synthesis with Clear, Reformulated Prose (All distinct proposals per topic)
    pillars = []
    for topic, props in topic_groups.items():
        for item in props[:4]:
            sintesi_chiara = item.dichiarazione_sintesi
            if len(sintesi_chiara) > 0 and sintesi_chiara[0].islower():
                sintesi_chiara = sintesi_chiara[0].upper() + sintesi_chiara[1:]

            cost_str = item.costo_stimato or ""
            cov_str = item.coperture_dichiarate or ""
            if not cost_str or cost_str == "Non quantificato" or not any(c.isdigit() for c in cost_str) or not cov_str or cov_str == "Non specificate":
                f_calc = calculate_fiscal_impact_and_coverage(
                    partito=party.name,
                    macro_argomento=topic,
                    sintesi=sintesi_chiara,
                    costo_stimato=cost_str,
                    coperture_dichiarate=cov_str
                )
                cost_final = f_calc["costo_stimato"]
                cov_final = f_calc["coperture_dichiarate"]
                status_final = f_calc["fact_check_status"]
                mot_final = f_calc["fact_check_motivazione"]
            else:
                cost_final = cost_str
                cov_final = cov_str
                status_final = item.fact_check_status or "Verificato"
                mot_final = item.fact_check_motivazione or item.fattibilita_finanziaria or "Valutazione oggettiva basata su parametri MEF/ISTAT."

            pillars.append({
                "tema": topic,
                "proposta_chiave": sintesi_chiara,
                "tipo_azione": item.tipo_azione or "Dichiarazione programmatica",
                "costo": cost_final,
                "coperture": cov_final,
                "status_verifica": status_final,
                "motivazione": mot_final,
                "fonte_url": item.fonte_url,
                "fonte_testata": item.fonte_testata or "Fonti Istituzionali / Stampa Nazionale"
            })

    # 3. Macroeconomic Cost Computation and Financial Audit
    quantified_costs_numeric = []
    for p in proposals:
        if p.costo_stimato and p.costo_stimato != "Non quantificato":
            m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:miliardi|mld)", p.costo_stimato, re.I)
            if m:
                val = float(m.group(1).replace(",", "."))
                quantified_costs_numeric.append(val)

    totale_mld_stimato = round(sum(quantified_costs_numeric), 1) if quantified_costs_numeric else None
    spesa_str = f"~{totale_mld_stimato} Mld €" if totale_mld_stimato else "Quantificata per singoli capitoli di spesa"

    valutazione_finanziaria = {
        "score_fattibilita": f"{feasibility_score}%",
        "atti_quantificati": f"{len(quantified_costs_numeric)} su {total_props} posizioni censite",
        "impegno_economico_stimato": spesa_str,
        "analisi_coperture": (
            f"Dall'analisi delle proposte rilevate e catalogate dall'AI, {party.name} presenta {verified_count} misure "
            f"pienamente compatibili con i vincoli di finanza pubblica certificati da MEF, ISTAT e Corte dei Conti. "
            f"Al contempo, {pending_coverage} proposte risultano in attesa di dettagli operativi o dipendono da tagli di spesa/maggiori entrate tributarie. "
            f"L'osservatorio parametrizza ogni programma rispetto ai vincoli macroeconomici dello Stato: PIL nominale (~2.120 Mld €), "
            f"Debito Pubblico al 137,3% e capienza ordinaria della Legge di Bilancio fissata a circa 30 Mld € annui."
        )
    }

    # 4. Recent Verified Web News
    recent_quotes = []
    for p in proposals[:6]:
        recent_quotes.append({
            "data": p.timestamp.strftime("%d/%m/%Y") if p.timestamp else datetime.datetime.utcnow().strftime("%d/%m/%Y"),
            "titolo": p.fonte_titolo or p.dichiarazione_sintesi[:80] + "...",
            "dichiarazione": p.dichiarazione_sintesi,
            "fonte": p.fonte_testata or "Stampa Nazionale & Istituzioni",
            "url": p.fonte_url
        })

    dossier = {
        "partito_nome": party.name,
        "partito_codice": party.code,
        "coalizione": party.coalition,
        "leader": party.leader,
        "sintesi_strategica": sintesi_politica,
        "evoluzione_storica_legislatura": evoluzione_storica,
        "punti_di_forza": punti_forza,
        "criticita_osservatorio": criticita_osservatorio,
        "score_affidabilita": f"{feasibility_score}%",
        "statistiche_atti": {
            "totale_atti": total_props,
            "verificati": verified_count,
            "in_attesa_copertura": pending_coverage,
            "esagerati_o_non_quantificati": exaggerated_count
        },
        "pilastri_programmatici": pillars,
        "valutazione_finanziaria": valutazione_finanziaria,
        "dichiarazioni_recenti_web": recent_quotes,
        "parametri_macro_confronto": benchmarks_summary,
        "ultimo_aggiornamento_web": datetime.datetime.utcnow().strftime("%d/%m/%Y ore %H:%M UTC")
    }

    return dossier

def update_all_party_dossiers(db: Session):
    """
    Iterates over all political parties and generates updated AI Dossiers from gathered web data.
    Also synchronizes truthfulness_score and financial_reliability_score.
    """
    parties = db.query(PoliticalParty).all()
    for party in parties:
        try:
            dossier_data = generate_party_dossier(party, db)
            party.dossier_ai = json.dumps(dossier_data, ensure_ascii=False)

            proposals = db.query(PoliticalProposal).filter(
                (PoliticalProposal.party_id == party.id) | (PoliticalProposal.partito.ilike(f"%{party.name}%"))
            ).all()
            if proposals:
                party.truthfulness_score = round(sum(calculate_proposal_truthfulness_score(p.fact_check_status) for p in proposals) / len(proposals), 1)
                party.financial_reliability_score = round(sum(calculate_financial_coverage_percentage(p.costo_stimato, p.coperture_dichiarate, p.dichiarazione_sintesi) for p in proposals) / len(proposals), 1)
        except Exception as e:
            print(f"[DossierGenerator] Error updating dossier for {party.name}: {e}")
    db.commit()
    print(f"[DossierGenerator] Successfully updated enhanced AI dossiers and metrics for {len(parties)} parties.")
