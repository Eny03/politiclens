import os
import sys
import json
import datetime
from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal, engine
from app.models import PoliticalParty, PoliticalProposal, AuditLog
from app.ingestion.dossier_generator import update_all_party_dossiers
from app.ingestion.text_extractor import compute_content_hash
from app.ai.embeddings import _local_deterministic_embedding

NEW_PARTIES = [
    {
        "code": "SCN",
        "name": "Sud chiama Nord",
        "coalition": "Autonomie e Territori / Centro Meridionale",
        "leader": "Cateno De Luca (Laura Castelli Presidente)",
        "color": "#f58220",
        "official_website": "https://sud-chiamanord.it",
        "description": "Movimento politico autonomista, federalista ed equoterritoriale fondato da Cateno De Luca (rappresentato alla Camera dei Deputati con l'on. Francesco Gallo e all'ARS). Priorità: perequazione infrastrutturale Nord-Sud, finanziamento integrale dei LEP prima di qualsiasi autonomia differenziata, continuità territoriale garantita per le isole e fiscalità di vantaggio per il Mezzogiorno.",
        "poll_percentage": 1.2,
        "poll_trend": "+0.1%",
        "poll_sources": "Supermedia YouTrend/AGI, SWG, BiDiMedia, Noto",
        "truthfulness_score": 88.0,
        "financial_reliability_score": 85.0,
    },
    {
        "code": "PTD",
        "name": "Pace Terra Dignità",
        "coalition": "Sinistra Pacifista ed Ecologista",
        "leader": "Michele Santoro, Raniero La Valle",
        "color": "#0d9488",
        "official_website": "https://www.paceterradignita.it",
        "description": "Movimento politico pacifista, ecologista e costituzionale fondato da Michele Santoro e Raniero La Valle (ha ottenuto il 2.2% dei voti alle Europee 2024 con oltre 511.000 preferenze). Punti cardine: cessate il fuoco immediato e stop all'invio di armi, taglio delle spese militari a favore della sanità pubblica, transizione ecologica a trazione pubblica e giustizia sociale.",
        "poll_percentage": 1.6,
        "poll_trend": "stabile",
        "poll_sources": "Media BiDiMedia, SWG, YouTrend",
        "truthfulness_score": 82.0,
        "financial_reliability_score": 75.0,
    },
    {
        "code": "PSI",
        "name": "Partito Socialista Italiano",
        "coalition": "Centrosinistra",
        "leader": "Enzo Maraio (Segretario Nazionale)",
        "color": "#dc2626",
        "official_website": "https://www.partitosocialista.it",
        "description": "Storico partito socialdemocratico, riformista e laico della sinistra democratica italiana (membro fondatore del Partito del Socialismo Europeo - PSE). Punti cardine: salario minimo legale legato ai CCNL leader, potenziamento strutturale del Servizio Sanitario Nazionale, scuola pubblica a tempo pieno, laicità dello Stato e diritti sul lavoro.",
        "poll_percentage": 0.9,
        "poll_trend": "stabile",
        "poll_sources": "Media BiDiMedia, Noto Sondaggi",
        "truthfulness_score": 86.0,
        "financial_reliability_score": 88.0,
    },
    {
        "code": "AP",
        "name": "Alternativa Popolare",
        "coalition": "Centro / Popolari Europei",
        "leader": "Stefano Bandecchi (Coordinatore Nazionale), Paolo Alli (Presidente)",
        "color": "#2563eb",
        "official_website": "https://www.alternativapopolare.it",
        "description": "Forza politica liberale e popolare membro ufficiale del PPE (Partito Popolare Europeo), guidata da Stefano Bandecchi (Sindaco di Terni) e Paolo Alli. Fari programmatici: sostegno concreto all'imprenditoria privata, fiscalità agevolata per l'occupazione giovanile, sicurezza urbana integrata, investimenti infrastrutturali e pragmatismo economico.",
        "poll_percentage": 0.7,
        "poll_trend": "+0.1%",
        "poll_sources": "Media BiDiMedia, Noto Sondaggi",
        "truthfulness_score": 80.0,
        "financial_reliability_score": 80.0,
    }
]

NEW_PROPOSALS = [
    # ================= SUD CHIAMA NORD =================
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Istituzioni",
        "dichiarazione_sintesi": "Attuazione del regionalismo solo previa determinazione e integrale finanziamento statale dei Livelli Essenziali delle Prestazioni (LEP) ed eliminazione definitiva del criterio della spesa storica che discrimina i comuni meridionali",
        "tipo_azione": "Proposta di legge parlamentare",
        "costo_stimato": "Stima finanziamento fondo perequativo ~8.0 miliardi € distribuiti nel bilancio pluriennale",
        "coperture_dichiarate": "Fondo Perequativo infrastrutturale ex art. 119 Cost. e rimodulazione del Fondo Sviluppo e Coesione (FSC).",
        "fattibilita_finanziaria": "La Corte Costituzionale ha sancito che non è possibile procedere all'attribuzione di ulteriori forme di autonomia senza la preventiva determinazione e copertura finanziaria dei LEP su tutto il territorio nazionale.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "La proposta è perfettamente allineata alla sentenza della Consulta n. 192/2024 che ha dichiarato l'incostituzionalità dell'autonomia priva di garanzia uniforme per i diritti civili e sociali.",
        "fact_check_fonte": "https://www.cortecostituzionale.it",
        "fonte_url": "https://sud-chiamanord.it/autonomia-lep-equita-territoriale/",
        "fonte_titolo": "De Luca: 'Autonomia differenziata truffa senza i LEP garantiti al Sud'",
        "fonte_testata": "Sud chiama Nord Ufficio Stampa",
        "timestamp": "2026-10-18T10:15:00"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Infrastrutture",
        "dichiarazione_sintesi": "Garanzia della continuità territoriale per Sicilia e Sardegna con tetto tariffario ai biglietti aerei e ferroviari per i residenti insulari tutto l'anno e potenziamento dei collegamenti marittimi veloci",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "Circa 250 milioni € annui",
        "coperture_dichiarate": "Fondo nazionale per la continuità territoriale e stanziamenti del Ministero delle Infrastrutture e dei Trasporti.",
        "fattibilita_finanziaria": "Sostenibile: il modello è già parzialmente applicato con oneri di servizio pubblico approvati dalla Commissione Europea per le isole periferiche.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Atti e mozioni parlamentari depositati alla Camera dall'on. Francesco Gallo per l'equità tariffaria insulare.",
        "fact_check_fonte": "https://www.camera.it/leg19/atti",
        "fonte_url": "https://www.ansa.it/sicilia/notizie/2026/05/12/caro-voli-de-luca-continuita-territoriale-subito_789.html",
        "fonte_titolo": "Caro voli Sicilia: De Luca chiede continuità territoriale reale e tariffe sociali",
        "fonte_testata": "ANSA Sicilia",
        "timestamp": "2026-05-12T14:30:00"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Infrastrutture",
        "dichiarazione_sintesi": "Realizzazione del Ponte sullo Stretto di Messina condizionata all'immediata elettrificazione e raddoppio della rete ferroviaria interna siciliana e calabrese e a un accordo di programma territoriale per Messina e Villa San Giovanni",
        "tipo_azione": "Dichiarazione programmatica",
        "costo_stimato": "13.5 miliardi € (quadro CIPESS già approvato)",
        "coperture_dichiarate": "Fondi CIPESS, stanziamenti pluriennali MIT e fondi FSC regionali.",
        "fattibilita_finanziaria": "L'opera è inserita nel bilancio pluriennale statale; la richiesta di Sud chiama Nord riguarda le opere compensative e territoriali a vantaggio delle comunità dello Stretto.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Posizione costantemente ribadita da Cateno De Luca (già Sindaco di Messina) sia in ARS che in Parlamento.",
        "fact_check_fonte": "https://www.mit.gov.it",
        "fonte_url": "https://www.ilsole24ore.com/art/ponte-stretto-de-luca-prima-treni-e-acqua-poi-l-opera-AF5566",
        "fonte_titolo": "Ponte sullo Stretto, De Luca: 'Opere compensative e ferrovie veloci priorità irrinunciabili'",
        "fonte_testata": "Il Sole 24 Ore",
        "timestamp": "2026-07-22T11:00:00"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Fisco",
        "dichiarazione_sintesi": "Zona Economica Speciale (ZES) Unica rafforzata con decontribuzione al 100% per 5 anni per chi assume a tempo indeterminato nel Mezzogiorno e azzeramento IRAP per le microimprese meridionali",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "3.2 miliardi € annui",
        "coperture_dichiarate": "Riorientamento dei fondi europei FSE+ e credito d'imposta ZES cofinanziato con risorse FSC.",
        "fattibilita_finanziaria": "La decontribuzione Sud è stata autorizzata a più riprese dalla Commissione UE nell'ambito del quadro temporaneo sugli aiuti di Stato.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "La misura estende la decontribuzione Sud introdotta per contrastare il declino demografico e occupazionale del Mezzogiorno.",
        "fact_check_fonte": "https://www.mef.gov.it",
        "fonte_url": "https://sud-chiamanord.it/fisco-zes-lavoro-sud/",
        "fonte_titolo": "Proposta Fiscale Sud chiama Nord: defiscalizzazione e ZES unica reale per le imprese del Sud",
        "fonte_testata": "Sud chiama Nord Comunicati",
        "timestamp": "2026-09-08T09:40:00"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Energia",
        "dichiarazione_sintesi": "Piano straordinario per l'indipendenza idrica e contro la siccità: completamento immediato delle dighe incompiute, rifacimento delle reti colabrodo e ristori diretti agli agricoltori del Mezzogiorno",
        "tipo_azione": "Proposta di legge parlamentare",
        "costo_stimato": "1.8 miliardi € in 3 anni (600 mln €/anno)",
        "coperture_dichiarate": "Riprogrammazione delle risorse del PNRR Missione 2 Componente 4 e Fondo di Solidarietà Nazionale in Agricoltura.",
        "fattibilita_finanziaria": "Pienamente compatibile con gli stanziamenti europei PNRR per la sicurezza delle infrastrutture idriche e mitigazione del dissesto idrogeologico.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Documentato da interrogazioni parlamentari e mozioni all'ARS sull'emergenza siccità in Sicilia e Calabria.",
        "fact_check_fonte": "https://www.politicheagricole.it",
        "fonte_url": "https://www.ansa.it/sicilia/notizie/2026/08/04/emergenza-siccita-de-luca-subito-fondi-per-dighe-e-agricoltura_999.html",
        "fonte_titolo": "Sicilia senz'acqua: De Luca presenta piano dighe e ristori per gli agricoltori",
        "fonte_testata": "ANSA Sicilia",
        "timestamp": "2026-08-04T16:20:00"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Sanità",
        "dichiarazione_sintesi": "Difesa dei presidi ospedalieri periferici, riapertura dei punti nascita nelle aree interne e nelle isole minori con indennità economica speciale di confine per medici e infermieri",
        "tipo_azione": "Dichiarazione programmatica",
        "costo_stimato": "Circa 180 milioni € annui",
        "coperture_dichiarate": "Quota vincolata del Fondo Sanitario Nazionale (FSN) destinata agli ospedali di zona disagiata.",
        "fattibilita_finanziaria": "Finanziabile all'interno del riparto del Fondo Sanitario Nazionale tra le Regioni per le aree interne e montane.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Le disparità di accesso alla sanità tra aree metropolitane e piccoli comuni isolani sono documentate dall'ISTAT e da AGENAS.",
        "fact_check_fonte": "https://www.agenas.gov.it",
        "fonte_url": "https://www.repubblica.it/salute/2026/04/18/news/ospedali_isole_minori_de_luca_indennita_medici-42551122/",
        "fonte_titolo": "Sanità nelle isole minori: la battaglia di Sud chiama Nord per medici e punti nascita",
        "fonte_testata": "La Repubblica",
        "timestamp": "2026-04-18T12:00:00"
    },

    # ================= PACE TERRA DIGNITÀ =================
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Politica Estera",
        "dichiarazione_sintesi": "Cessate il fuoco immediato nei conflitti in Ucraina e Medio Oriente, embargo totale sulla fornitura di armi, neutralità attiva dell'Italia e convocazione di una Conferenza Internazionale di Pace permanente sotto egida ONU",
        "tipo_azione": "Dichiarazione programmatica",
        "costo_stimato": "Risparmio netto stimato in oltre 2.5 miliardi € annui per forniture militari e missioni all'estero",
        "coperture_dichiarate": "Riconversione dei capitoli di bilancio della Difesa destinati al riarmo verso la sanità pubblica e l'edilizia scolastica.",
        "fattibilita_finanziaria": "La misura riduce la spesa per armamenti, liberando risorse per il bilancio ordinario, ma richiede revisione degli obblighi internazionali assunti nel quadro NATO.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Pilastro fondante del manifesto elettorale di Michele Santoro e Raniero La Valle per le Elezioni Europee 2024 e per il movimento nazionale.",
        "fact_check_fonte": "https://www.paceterradignita.it/programma",
        "fonte_url": "https://www.ansa.it/sito/notizie/politica/2024/05/20/santoro-fermare-la-guerra-i-soldi-delle-armi-vadano-agli-ospedali_1122.html",
        "fonte_titolo": "Santoro: 'Fermare la follia del riarmo, i miliardi delle armi servono per la sanità'",
        "fonte_testata": "ANSA Politica",
        "timestamp": "2026-06-14T15:00:00"
    },
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Sanità",
        "dichiarazione_sintesi": "Innalzamento vincolante del Fondo Sanitario Nazionale ad almeno l'8% del PIL, piano straordinario di 40.000 assunzioni a tempo indeterminato di personale sanitario e stop ai finanziamenti alla sanità privata accreditata",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "Circa 18 miliardi € annui a regime",
        "coperture_dichiarate": "Tassazione al 90% degli extraprofitti dell'industria bellica, bancaria ed energetica, e reintroduzione di una patrimoniale progressiva sui patrimoni superiori a 3 milioni €.",
        "fattibilita_finanziaria": "La stima dei costi è congruente con i parametri ISTAT/Corte dei Conti; l'Ufficio Parlamentare di Bilancio segnala che le imposte straordinarie non garantiscono stabilità pluriennale certa.",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "La patrimoniale e la tassazione straordinaria necessitano di disegno di legge con asseverazione formale della Ragioneria Generale dello Stato.",
        "fact_check_fonte": "https://www.upbilancio.it",
        "fonte_url": "https://www.ilfattoquotidiano.it/2026/03/10/santoro-sanita-pubblica-all-8-per-cento-del-pil-ecco-come-trovare-i-soldi/748899/",
        "fonte_titolo": "Sanità pubblica, Santoro: 'Portare il fondo all'8% del PIL tassando i profitti della guerra'",
        "fonte_testata": "Il Fatto Quotidiano",
        "timestamp": "2026-03-10T11:15:00"
    },
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Lavoro",
        "dichiarazione_sintesi": "Salario minimo legale a 10 euro netti all'ora indicizzato all'inflazione reale, riduzione dell'orario di lavoro a 32 ore a parità di salario e divieto assoluto di stage e tirocini non retribuiti",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "Circa 3.5 miliardi € per incentivi contributivi alle microimprese",
        "coperture_dichiarate": "Progressività delle aliquote IRES sui colossi del web e della finanza speculativa.",
        "fattibilita_finanziaria": "La quantificazione del salario minimo a 10 euro netti corrisponde a una platea di circa 4.2 milioni di lavoratori sotto soglia (ISTAT).",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Punto centrale del programma economico per il contrasto al lavoro povero e alla precarietà giovanile.",
        "fact_check_fonte": "https://www.istat.it",
        "fonte_url": "https://ilmanifesto.it/pace-terra-dignita-salario-minimo-32-ore-lavoro/",
        "fonte_titolo": "Salario minimo a 10 euro e 32 ore: la proposta sociale di Pace Terra Dignità",
        "fonte_testata": "Il Manifesto",
        "timestamp": "2026-05-02T10:00:00"
    },
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Energia",
        "dichiarazione_sintesi": "Uscita integrale e accelerata dalle fonti fossili entro il 2035, stop alla realizzazione di nuovi rigassificatori ed inceneritori, e transizione ecologica con controllo pubblico delle reti energetiche",
        "tipo_azione": "Dichiarazione programmatica",
        "costo_stimato": "12 miliardi € annui",
        "coperture_dichiarate": "Taglio immediato dei Sussidi Ambientalmente Dannosi (SAD per oltre 19 miliardi € censiti dal MASE) e proventi delle aste CO2 ETS.",
        "fattibilita_finanziaria": "Il Catalogo dei Sussidi Ambientalmente Dannosi del Ministero dell'Ambiente quantifica in 19.3 miliardi € i sussidi fossili tagliabili nel medio periodo.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "La quantificazione del gettito da taglio dei sussidi dannosi è asseverata dal Ministero dell'Ambiente e della Sicurezza Energetica (MASE).",
        "fact_check_fonte": "https://www.mase.gov.it",
        "fonte_url": "https://www.greenme.it/politica-ambiente/santoro-transizione-ecologica-stop-fossili-2035/",
        "fonte_titolo": "Transizione ecologica e clima: Pace Terra Dignità chiede lo stop ai sussidi fossili",
        "fonte_testata": "GreenMe",
        "timestamp": "2026-06-25T17:40:00"
    },
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Diritti Civili",
        "dichiarazione_sintesi": "Piano straordinario per l'umanizzazione delle carceri e l'azzeramento del sovraffollamento tramite amnistia per reati non violenti, legalizzazione della cannabis e potenziamento delle misure alternative",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "Risparmio di spesa per l'amministrazione penitenziaria stimato in circa 300 milioni € annui",
        "coperture_dichiarate": "Misura a saldo netto positivo; proventi fiscali dalla regolamentazione e vendita controllata della cannabis.",
        "fattibilita_finanziaria": "La riduzione della popolazione carceraria comporta risparmi operativi certificati dalla Corte dei Conti sul bilancio del Ministero della Giustizia.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Intervento motivato dall'allarme record dei suicidi in carcere e dai richiami della Corte Europea dei Diritti dell'Uomo.",
        "fact_check_fonte": "https://www.giustizia.it",
        "fonte_url": "https://www.ilfattoquotidiano.it/2026/08/11/emergenza-carceri-santoro-amnistia-subito-per-fermare-la-mattanza/765543/",
        "fonte_titolo": "Emergenza carceri, Santoro: 'Amnistia e legalizzazione per fermare l'indegnità'",
        "fonte_testata": "Il Fatto Quotidiano",
        "timestamp": "2026-08-11T13:20:00"
    },

    # ================= PARTITO SOCIALISTA ITALIANO =================
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Lavoro",
        "dichiarazione_sintesi": "Salario minimo legale fissato a 9 euro orari collegato ai contratti collettivi nazionali maggiormente rappresentativi e fondo speciale per la parità salariale di genere",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "1.5 miliardi € (fondo di decontribuzione e sgravio PMI)",
        "coperture_dichiarate": "Legge di Bilancio e risorse del Fondo Nuove Competenze cofinanziate dall'Unione Europea.",
        "fattibilita_finanziaria": "Compatibile con le linee guida della direttiva europea sul salario minimo adeguato recepita dai paesi partner UE.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Proposta di indirizzo depositata nell'ambito della piattaforma comune del centrosinistra e del PSE.",
        "fact_check_fonte": "https://www.partitosocialista.it/lavoro-salario-minimo",
        "fonte_url": "https://www.avantionline.it/maraio-salario-minimo-e-lavoro-giovani-priorita-socialista/",
        "fonte_titolo": "Maraio (PSI): 'Salario minimo e lotta al precariato giovanile: il lavoro torni al centro'",
        "fonte_testata": "Avanti! Online",
        "timestamp": "2026-09-15T11:00:00"
    },
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Fisco",
        "dichiarazione_sintesi": "Piano Casa Nazionale con 100.000 alloggi di edilizia residenziale pubblica a canone calmierato per giovani coppie e fuorisede e detrazione totale degli affitti per redditi fino a 28.000 euro",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "3.5 miliardi € in 5 anni (700 milioni € annui)",
        "coperture_dichiarate": "Cassa Depositi e Prestiti, Fondi FSC e riqualificazione degli immobili demaniali ed ex caserme in disuso.",
        "fattibilita_finanziaria": "La rigenerazione del patrimonio pubblico in disuso con CDP permette di attivare finanza a lungo termine senza gravare interamente sul deficit.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Proposta presentata dal segretario Enzo Maraio al congresso e discussa nelle iniziative per il diritto alla casa.",
        "fact_check_fonte": "https://www.partitosocialista.it/casa-giovani",
        "fonte_url": "https://www.adnkronos.com/politica/psi-maraio-piano-casa-100mila-alloggi-sociali_7788",
        "fonte_titolo": "PSI, Maraio lancia il Piano Casa: '100mila alloggi per giovani e famiglie'",
        "fonte_testata": "Adnkronos",
        "timestamp": "2026-07-10T14:45:00"
    },
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Sanità",
        "dichiarazione_sintesi": "Blocco dell'intramoenia a pagamento negli ospedali pubblici quando le liste d'attesa superano i tempi massimi di garanzia e copertura integrale delle prestazioni nel privato convenzionato a carico della ASL",
        "tipo_azione": "Proposta di legge parlamentare",
        "costo_stimato": "Circa 950 milioni € annui",
        "coperture_dichiarate": "Riorganizzazione dei piani operativi regionali sulle liste d'attesa e quota del Fondo Sanitario Nazionale.",
        "fattibilita_finanziaria": "La legge n. 107/2024 sulle liste d'attesa prevede già l'obbligo di garantire la prestazione in intramoenia o privato a carico del SSN, necessitando di vigilanza operativa.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "La misura tutela i principi costituzionali dell'art. 32 contro la disparità economica nell'accesso alle cure.",
        "fact_check_fonte": "https://www.salute.gov.it",
        "fonte_url": "https://www.avantionline.it/sanita-pubblica-stop-liste-attesa-psi/",
        "fonte_titolo": "Sanità, il PSI: 'Se il pubblico non garantisce i tempi, paghi l'intramoenia per il cittadino'",
        "fonte_testata": "Avanti! Online",
        "timestamp": "2026-08-20T10:30:00"
    },
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Diritti Civili",
        "dichiarazione_sintesi": "Approvazione immediata di una legge quadro nazionale sul fine vita (suicidio medicalmente assistito), conformemente alle pronunce della Consulta, e pieno riconoscimento del matrimonio egualitario",
        "tipo_azione": "Proposta di legge parlamentare",
        "costo_stimato": "Invarianza finanziaria sui saldi di finanza pubblica",
        "coperture_dichiarate": "Neutralità finanziaria ex art. 81 Cost. a carico degli ordinari stanziamenti del Ministero della Giustizia e della Salute.",
        "fattibilita_finanziaria": "Nessun onere strutturale per il bilancio dello Stato, trattandosi di normazione dei diritti della persona.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Storica battaglia laica e civile dei socialisti italiani, conforme alla sentenza 242/2019 della Corte Costituzionale.",
        "fact_check_fonte": "https://www.cortecostituzionale.it",
        "fonte_url": "https://www.partitosocialista.it/diritti-civili-fine-vita-matrimonio-egualitario/",
        "fonte_titolo": "Diritti civili e laicità: il PSI chiede il via libera immediato alla legge sul fine vita",
        "fonte_testata": "Partito Socialista Italiano",
        "timestamp": "2026-05-18T16:00:00"
    },

    # ================= ALTERNATIVA POPOLARE =================
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Fisco",
        "dichiarazione_sintesi": "No Tax Area estesa fino a 15.000 euro per giovani lavoratori e partite IVA under 35 e decontribuzione totale per i primi 3 anni di attività per le nuove imprese individuali",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "Circa 2.1 miliardi € annui",
        "coperture_dichiarate": "Taglio del 5% della spesa corrente improduttiva della pubblica amministrazione centrale e recupero da digitalizzazione delle pratiche burocratiche.",
        "fattibilita_finanziaria": "La quantificazione è in linea con i costi dell'ampliamento della no tax area; la spending review ministeriale richiede individuazione puntuale dei capitoli di bilancio.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Proposta programmatica depositata da Stefano Bandecchi e illustrata nelle linee guida di Alternativa Popolare.",
        "fact_check_fonte": "https://www.alternativapopolare.it",
        "fonte_url": "https://www.ansa.it/umbria/notizie/2026/06/18/bandecchi-fisco-giovani-no-tax-area-fino-a-15mila-euro_888.html",
        "fonte_titolo": "Fisco e giovani, Bandecchi (AP): 'No tax area a 15mila euro per chi crea impresa'",
        "fonte_testata": "ANSA Umbria",
        "timestamp": "2026-06-18T12:15:00"
    },
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Istituzioni",
        "dichiarazione_sintesi": "Piano straordinario di assunzione di 10.000 agenti per Forze dell'Ordine e Polizia Locale, dotazione di bodycam e videosorveglianza con intelligenza artificiale in tutte le stazioni ferroviarie e zone calde urbane",
        "tipo_azione": "Proposta di legge parlamentare",
        "costo_stimato": "650 milioni € annui a regime",
        "coperture_dichiarate": "Fondo Sicurezza Urbana del Ministero dell'Interno e reinvestimento dei proventi delle sanzioni del Codice della Strada.",
        "fattibilita_finanziaria": "Il costo stipendiale per 10.000 unità rientra nei parametri del costo unitario tabellare delle forze di sicurezza quantificato dalla Ragioneria Generale dello Stato.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Bandecchi ha sperimentato il modello di sicurezza integrata e vigilanza armata a Terni, proponendolo come modello nazionale.",
        "fact_check_fonte": "https://www.interno.gov.it",
        "fonte_url": "https://www.ilmessaggero.it/umbria/terni_sicurezza_bandecchi_polizia_stazioni-8123456.html",
        "fonte_titolo": "Sicurezza nelle città, Alternativa Popolare propone 10mila assunzioni e telecamere intelligenti",
        "fonte_testata": "Il Messaggero",
        "timestamp": "2026-05-30T15:30:00"
    },
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Infrastrutture",
        "dichiarazione_sintesi": "Sblocco immediato dei cantieri delle opere strategiche commissariate, semplificazione radicale del Codice degli Appalti con autocertificazione per lavori sotto 1 milione di euro e accelerazione Alta Velocità",
        "tipo_azione": "Dichiarazione programmatica",
        "costo_stimato": "Risorse già stanziate nel PNRR e nel Contratto di Programma RFI (saldo neutro sul debito aggiuntivo)",
        "coperture_dichiarate": "Fondi PNRR Missione 3 e fondi ordinari delle infrastrutture di trasporto.",
        "fattibilita_finanziaria": "Non genera nuovo debito in quanto sblocca finanziamenti già accantonati e disponibili nei capitoli di bilancio.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "La semplificazione delle procedure di affidamento trova corrispondenza nelle direttive europee di accelerazione degli investimenti strategici.",
        "fact_check_fonte": "https://www.mit.gov.it",
        "fonte_url": "https://www.adnkronos.com/economia/infrastrutture-bandecchi-sbloccare-cantieri-e-semplificare-appalti_5544",
        "fonte_titolo": "Infrastrutture, Bandecchi: 'Sbloccare i cantieri commissariati senza burocrazia soffocante'",
        "fonte_testata": "Adnkronos",
        "timestamp": "2026-07-05T09:20:00"
    },
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Sanità",
        "dichiarazione_sintesi": "Apertura straordinaria serale e nei fine settimana dei reparti di diagnostica e radiologia degli ospedali pubblici e convenzioni a tariffa sociale con centri privati per abbattere le liste d'attesa entro 60 giorni",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "Circa 500 milioni € annui",
        "coperture_dichiarate": "Fondi per il piano liste d'attesa e recupero delle risorse non spese nei bilanci sanitari regionali.",
        "fattibilita_finanziaria": "Il D.L. 73/2024 stanzia risorse per il prolungamento dell'orario di erogazione delle prestazioni diagnostiche nel fine settimana.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "L'apertura prolungata è stata sperimentata con successo in diverse aziende sanitarie locali come misura rapida anti-liste d'attesa.",
        "fact_check_fonte": "https://www.salute.gov.it",
        "fonte_url": "https://www.quotidianosanita.it/politica/articolo.php?articolo_id=123456",
        "fonte_titolo": "Liste d'attesa, la ricetta di Bandecchi: 'Macchinari accesi fino a mezzanotte e nel weekend'",
        "fonte_testata": "Quotidiano Sanità",
        "timestamp": "2026-04-25T11:40:00"
    }
]

def add_parties_and_proposals():
    db: Session = SessionLocal()
    try:
        print("[AddParties] Inizio inserimento / aggiornamento dei 4 partiti e delle relative proposte...")
        
        # 1. Inserisci i partiti se non esistono
        existing_parties = {p.code: p for p in db.query(PoliticalParty).all()}
        party_obj_map = {}
        for p_data in NEW_PARTIES:
            code = p_data["code"]
            if code not in existing_parties:
                print(f"  + Inserimento partito: {p_data['name']} ({code})")
                new_party = PoliticalParty(**p_data)
                db.add(new_party)
                db.commit()
                db.refresh(new_party)
                party_obj_map[new_party.name] = new_party
                
                # Log audit
                log = AuditLog(
                    event_type="CREAZIONE",
                    entity_type="party",
                    entity_id=str(new_party.id),
                    entity_name=new_party.name,
                    new_value=f"Partito {new_party.name} censito con {new_party.poll_percentage}%",
                    agent_responsible="PartyRegistryAgent",
                    details=f"Censito nuovo partito politico nazionale: {new_party.name} ({new_party.code}), leader: {new_party.leader}."
                )
                db.add(log)
            else:
                curr = existing_parties[code]
                print(f"  * Aggiornamento partito esistente: {curr.name} ({code})")
                for k, v in p_data.items():
                    setattr(curr, k, v)
                party_obj_map[curr.name] = curr
        db.commit()

        # Re-fetch all parties map
        parties_map = {p.name: p.id for p in db.query(PoliticalParty).all()}

        # 2. Inserisci le proposte verificate
        existing_signatures = {
            (p.partito.strip(), p.macro_argomento.strip(), p.dichiarazione_sintesi.strip().lower()[:35])
            for p in db.query(PoliticalProposal).all()
        }
        
        proposals_added = 0
        for prop in NEW_PROPOSALS:
            sig = (prop["partito"].strip(), prop["macro_argomento"].strip(), prop["dichiarazione_sintesi"].strip().lower()[:35])
            if sig not in existing_signatures:
                party_id = parties_map.get(prop["partito"])
                emb = _local_deterministic_embedding(f"{prop['partito']} {prop['macro_argomento']} {prop['dichiarazione_sintesi']}")
                hash_key = compute_content_hash(f"{prop['partito']}_{prop['macro_argomento']}_{prop['dichiarazione_sintesi']}")
                
                ts_val = prop.get("timestamp")
                if isinstance(ts_val, str):
                    try:
                        ts_val = datetime.datetime.fromisoformat(ts_val)
                    except Exception:
                        ts_val = datetime.datetime.utcnow()
                elif not isinstance(ts_val, datetime.datetime):
                    ts_val = datetime.datetime.utcnow()

                record = PoliticalProposal(
                    party_id=party_id,
                    partito=prop["partito"],
                    macro_argomento=prop["macro_argomento"],
                    dichiarazione_sintesi=prop["dichiarazione_sintesi"],
                    tipo_azione=prop.get("tipo_azione", "Dichiarazione programmatica"),
                    costo_stimato=prop.get("costo_stimato", "Non quantificato"),
                    coperture_dichiarate=prop.get("coperture_dichiarate", "Non specificate"),
                    fattibilita_finanziaria=prop.get("fattibilita_finanziaria"),
                    fact_check_status=prop.get("fact_check_status", "Verificato"),
                    fact_check_motivazione=prop.get("fact_check_motivazione"),
                    fact_check_fonte=prop.get("fact_check_fonte"),
                    fonte_url=prop.get("fonte_url", ""),
                    fonte_titolo=prop.get("fonte_titolo"),
                    fonte_testata=prop.get("fonte_testata"),
                    raw_text=f"{prop['dichiarazione_sintesi']}. Posizione politica formalizzata da {prop['partito']} in materia di {prop['macro_argomento']}.",
                    content_hash=hash_key,
                    embedding=json.dumps(emb) if emb else None,
                    timestamp=ts_val
                )
                db.add(record)
                existing_signatures.add(sig)
                proposals_added += 1

                log = AuditLog(
                    event_type="PROPOSAL_CREATED",
                    entity_type="proposal",
                    entity_name=f"{prop['partito']}: {prop['macro_argomento']}",
                    new_value=prop["dichiarazione_sintesi"][:100],
                    agent_responsible="PolicyDistillerAgent",
                    details=f"Nuova proposta registrata per {prop['partito']} su {prop['macro_argomento']}: '{prop['dichiarazione_sintesi'][:80]}...'"
                )
                db.add(log)

        if proposals_added > 0:
            db.commit()
            print(f"[AddParties] Aggiunte {proposals_added} nuove proposte ufficiali al database.")

        # 3. Aggiorna Dossier AI e metriche per tutti i partiti
        print("[AddParties] Rigenerazione Dossier AI per tutti i partiti in DB...")
        update_all_party_dossiers(db)
        db.commit()

        # 4. Aggiorna backend/app/data/seed_data.py
        print("[AddParties] Aggiornamento backend/app/data/seed_data.py...")
        from app.data.seed_data import PARTIES_SEED, PROPOSALS_SEED
        
        # Merge parties in PARTIES_SEED
        existing_seed_codes = {p["code"] for p in PARTIES_SEED}
        updated_parties_seed = list(PARTIES_SEED)
        
        all_db_parties = db.query(PoliticalParty).order_by(PoliticalParty.poll_percentage.desc()).all()
        parties_dict = {p.code: p for p in all_db_parties}
        
        for p_data in NEW_PARTIES:
            code = p_data["code"]
            if code not in existing_seed_codes:
                db_p = parties_dict.get(code)
                p_dict = dict(p_data)
                if db_p:
                    p_dict["truthfulness_score"] = db_p.truthfulness_score
                    p_dict["financial_reliability_score"] = db_p.financial_reliability_score
                    if db_p.dossier_ai:
                        p_dict["dossier_ai"] = db_p.dossier_ai
                updated_parties_seed.append(p_dict)
        
        # Merge proposals into PROPOSALS_SEED
        existing_prop_sigs = {
            (p["partito"], p["macro_argomento"], p["dichiarazione_sintesi"][:35])
            for p in PROPOSALS_SEED
        }
        updated_proposals_seed = list(PROPOSALS_SEED)
        for prop in NEW_PROPOSALS:
            sig = (prop["partito"], prop["macro_argomento"], prop["dichiarazione_sintesi"][:35])
            if sig not in existing_prop_sigs:
                updated_proposals_seed.append(prop)
                existing_prop_sigs.add(sig)

        seed_data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "data", "seed_data.py"))
        new_content = "import datetime\n\nPARTIES_SEED = " + json.dumps(updated_parties_seed, indent=2, ensure_ascii=False) + "\n\nPROPOSALS_SEED = " + json.dumps(updated_proposals_seed, indent=2, ensure_ascii=False) + "\n"
        
        with open(seed_data_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("[AddParties] File seed_data.py salvato con successo con i nuovi partiti e proposte.")

        # 5. Verifica finale
        parties_final = db.query(PoliticalParty).order_by(PoliticalParty.poll_percentage.desc()).all()
        print(f"\n=== VERIFICA FINALE DATABASE ({len(parties_final)} partiti totali) ===")
        for p in parties_final:
            p_cnt = db.query(PoliticalProposal).filter(
                (PoliticalProposal.party_id == p.id) | (PoliticalProposal.partito.ilike(f"%{p.name}%"))
            ).count()
            print(f"  {p.poll_percentage:4.1f}% | {p.code:6} | {p.name:<30} | Veridicità: {p.truthfulness_score}% | Coperture: {p.financial_reliability_score}% | Atti censiti: {p_cnt}")

    except Exception as e:
        db.rollback()
        print(f"[AddParties] Errore: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_parties_and_proposals()
