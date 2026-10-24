import sys
import os
import datetime
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal, engine
from app.models import PoliticalParty, PoliticalProposal, IngestionLog, AuditLog
from app.ai.fiscal_calculator import calculate_fiscal_impact_and_coverage
from app.ai.embeddings import _local_deterministic_embedding
from app.ingestion.dossier_generator import update_all_party_dossiers

NEW_PROPOSALS = [
    # PSI (7 proposals)
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Pensioni",
        "tipo_azione": "Disegno di legge depositato",
        "sintesi": "Superamento della Legge Fornero con quota 41 pulita senza penalizzazioni di calcolo e istituzione di una pensione di garanzia da 1.000 euro per giovani precari.",
        "costo_stimato": "Circa 4,5 miliardi € annui",
        "coperture_dichiarate": "Rimodulazione progressiva delle detrazioni fiscali per redditi superiori a 100.000 euro e contributo di solidarietà sui trattamenti pensionistici d'oro.",
        "fattibilita_finanziaria": "Proposta previdenziale asseverata dai centri studi del lavoro ma dipendente dall'introduzione di correttivi strutturali sulle pensioni retributive elevate.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Disegno di legge depositato dal PSI a tutela della flessibilità in uscita per mansioni gravose e giovani discontinui.",
        "fonte_titolo": "Programma Nazionale PSI: riforma previdenziale e pensione di garanzia",
        "fonte_url": "https://www.partitosocialista.it/programma/pensioni-giovani",
        "fonte_testata": "Ufficio Stampa PSI"
    },
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Energia",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Piano straordinario per la transizione verde tramite comunità energetiche rinnovabili pubbliche e incentivi al fotovoltaico diffuso per famiglie e PMI.",
        "costo_stimato": "Circa 1,5 miliardi € annui",
        "coperture_dichiarate": "Proventi delle aste europee ETS sulle quote di CO2 e prelievo di scopo sugli extraprofitti delle multinazionali dei combustibili fossili.",
        "fattibilita_finanziaria": "Intervento conforme agli obiettivi europei Fit for 55 con coperture da aste verdi ETS.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Posizione ufficiale del Partito Socialista a sostegno della decarbonizzazione e dell'autonomia energetica pulita.",
        "fonte_titolo": "PSI: transizione ecologica e comunità energetiche rinnovabili",
        "fonte_url": "https://www.partitosocialista.it/programma/energia-ambiente",
        "fonte_testata": "Partito Socialista Italiano"
    },
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Istruzione",
        "tipo_azione": "Disegno di legge depositato",
        "sintesi": "Estensione del tempo pieno obbligatorio nelle scuole elementari su tutto il territorio nazionale e incremento graduale degli stipendi dei docenti alla media OCSE.",
        "costo_stimato": "Circa 3 miliardi € annui a regime",
        "coperture_dichiarate": "Riassegnazione di capitoli di spesa del Ministero dell'Istruzione e utilizzo dei fondi FSE+ per il diritto allo studio.",
        "fattibilita_finanziaria": "In attesa di copertura strutturale completa per l'organico aggiuntivo del tempo pieno al Sud.",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "L'estensione del tempo pieno richiede assunzioni stabili di decine di migliaia di docenti la cui copertura non è ancora asseverata dal MEF.",
        "fonte_titolo": "Proposta PSI per la scuola pubblica: tempo pieno e adeguamento stipendiale",
        "fonte_url": "https://www.partitosocialista.it/programma/scuola-tempo-pieno",
        "fonte_testata": "Avanti! Online"
    },
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Istituzioni",
        "tipo_azione": "Atto di indirizzo parlamentare",
        "sintesi": "Difesa della Costituzione repubblicana antifascista, contrarietà al premierato e abrogazione della legge sull'autonomia differenziata a salvaguardia della coesione nazionale.",
        "costo_stimato": "Invarianza finanziaria (0 €)",
        "coperture_dichiarate": "Clausola di invarianza finanziaria ex art. 81 Costituzione.",
        "fattibilita_finanziaria": "Riforma di carattere costituzionale e istituzionale senza oneri a carico della finanza pubblica.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Posizione di opposizione istituzionale confermata nei documenti programmatici approvati dalla Direzione Nazionale PSI.",
        "fonte_titolo": "PSI: Mozione per l'unità della Repubblica contro autonomia differenziata e premierato",
        "fonte_url": "https://www.partitosocialista.it/programma/istituzioni-costituzione",
        "fonte_testata": "Partito Socialista Italiano"
    },
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Immigrazione",
        "tipo_azione": "Disegno di legge depositato",
        "sintesi": "Abolizione della legge Bossi-Fini, canali regolari d'ingresso per lavoro concordati con le parti sociali e riconoscimento dello Ius Scholae per minori integrati.",
        "costo_stimato": "Circa 150 milioni € annui",
        "coperture_dichiarate": "Fondi del Ministero dell'Interno per le politiche di integrazione e riprogrammazione del Fondo Asilo, Migrazione e Integrazione (FAMI).",
        "fattibilita_finanziaria": "Spesa per l'integrazione e la regolarizzazione compensata dal gettito fiscale e contributivo generato dai nuovi lavoratori regolari.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Proposta di legge sostenuta dal PSI in Parlamento per la riforma organica del Testo Unico sull'Immigrazione.",
        "fonte_titolo": "Riforma del Testo Unico Immigrazione e Ius Scholae: la posizione socialista",
        "fonte_url": "https://www.partitosocialista.it/programma/immigrazione-diritti",
        "fonte_testata": "Avanti! Online"
    },
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Politica Estera",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Costruzione degli Stati Uniti d'Europa con debito comune (Eurobond) per sanità e infrastrutture, difesa diplomatica e multilateralismo ONU.",
        "costo_stimato": "Invarianza finanziaria per il bilancio statale",
        "coperture_dichiarate": "Emissione di titoli di debito sovrannazionale garantiti dal bilancio dell'Unione Europea.",
        "fattibilita_finanziaria": "Proposta europea coordinata con il Partito del Socialismo Europeo (PSE) compatibile con i trattati comunitari.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Manifesto approvato dal PSI per il rafforzamento dell'integrazione europea e della diplomazia preventiva.",
        "fonte_titolo": "Manifesto PSI per gli Stati Uniti d'Europa e investimenti sociali comuni",
        "fonte_url": "https://www.partitosocialista.it/programma/europa-politica-estera",
        "fonte_testata": "Ufficio Stampa PSI"
    },
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Infrastrutture",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Piano straordinario per la manutenzione delle reti idriche contro la dispersione e messa in sicurezza dei versanti montani dal dissesto idrogeologico.",
        "costo_stimato": "Circa 2,5 miliardi € annui",
        "coperture_dichiarate": "Fondi di Sviluppo e Coesione (FSC) e riassegnazione quota residua del Piano Nazionale di Ripresa e Resilienza (PNRR).",
        "fattibilita_finanziaria": "Interventi finanziabili tramite linee di finanziamento europeo già allocate nel Piano per le infrastrutture idriche.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Programma di investimenti territoriali prioritari per fermare il 42% di perdite negli acquedotti del Paese.",
        "fonte_titolo": "PSI: Piano Idrico Nazionale e contrasto al dissesto geologico",
        "fonte_url": "https://www.partitosocialista.it/programma/infrastrutture-acqua",
        "fonte_testata": "Partito Socialista Italiano"
    },

    # Alternativa Popolare (7 proposals)
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Lavoro",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Decontribuzione totale al 100% per 3 anni per le imprese che assumono giovani under 35 e donne a tempo indeterminato, con salario netto defiscalizzato.",
        "costo_stimato": "Circa 2,8 miliardi € annui",
        "coperture_dichiarate": "Taglio delle agevolazioni fiscali a pioggia e recupero di gettito da contrasto al sommerso.",
        "fattibilita_finanziaria": "In attesa di copertura formale (La decontribuzione totale triennale richiede stanziamenti di bilancio asseverati dalla RGS).",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "Proposta programmatica di Stefano Bandecchi per lo shock occupazionale giovanile priva di disegno di legge con copertura MEF.",
        "fonte_titolo": "Programma Alternativa Popolare: decontribuzione giovani e rilancio imprese",
        "fonte_url": "https://www.alternativapopolare.it/programma-lavoro",
        "fonte_testata": "Alternativa Popolare"
    },
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Pensioni",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Pensione minima a 1.000 euro netti al mese per tutti gli anziani over 70 con indicizzazione automatica all'inflazione reale del carrello della spesa.",
        "costo_stimato": "Circa 5,2 miliardi € annui",
        "coperture_dichiarate": "In attesa di copertura (Revisione generale della spesa assistenziale e lotta all'evasione previdenziale).",
        "fattibilita_finanziaria": "Onere finanziario rilevante non coperto da capitoli asseverati dalla Ragioneria Generale dello Stato.",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "Promessa elettorale per la dignità degli anziani priva di relazione tecnica di bilancio ex art. 81 Cost.",
        "fonte_titolo": "Alternativa Popolare: pensione minima a 1000 euro per over 70",
        "fonte_url": "https://www.alternativapopolare.it/programma-pensioni",
        "fonte_testata": "Alternativa Popolare"
    },
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Energia",
        "tipo_azione": "Atto di indirizzo politico",
        "sintesi": "Ritorno immediato all'energia nucleare pulita di ultima generazione tramite Mini Reattori Modulari (SMR) per abbattere i costi industriali del 40%.",
        "costo_stimato": "Non quantificato",
        "coperture_dichiarate": "Project financing pubblico-privato con consorzi industriali energivori e prestiti della Banca Europea per gli Investimenti (BEI).",
        "fattibilita_finanziaria": "In attesa di quadro normativo primario e piano finanziario pluriennale depositato.",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "Proposta politica di reintroduzione del nucleare civile a bassa emissione in attesa di DDL legislativo.",
        "fonte_titolo": "Bandecchi: nucleare pulito SMR per salvare le nostre aziende energivore",
        "fonte_url": "https://www.alternativapopolare.it/programma-energia",
        "fonte_testata": "Alternativa Popolare"
    },
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Istruzione",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Riorganizzazione degli Istituti Tecnici Superiori con docenze aziendali e borse di studio a copertura integrale per facoltà scientifiche.",
        "costo_stimato": "Circa 800 milioni € annui",
        "coperture_dichiarate": "Cofinanziamento con il fondo bilaterale per la formazione continua delle imprese e fondi PNRR istruzione.",
        "fattibilita_finanziaria": "Sostenibile tramite l'integrazione di fondi interprofessionali privati e incentivi statali.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Proposta orientata a colmare il mismatch tra domanda e offerta di lavoro nel comparto manifatturiero.",
        "fonte_titolo": "Alternativa Popolare: rivoluzione negli istituti tecnici e sinergia con le imprese",
        "fonte_url": "https://www.alternativapopolare.it/programma-istruzione",
        "fonte_testata": "Alternativa Popolare"
    },
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Immigrazione",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Presidio navale rafforzato delle frontiere marittime, espulsioni immediate dei migranti irregolari che commettono reati e visti lavoro gestiti all'estero.",
        "costo_stimato": "Circa 350 milioni € annui",
        "coperture_dichiarate": "Stanziamenti per la sicurezza del Ministero dell'Interno e fondi Frontex.",
        "fattibilita_finanziaria": "Le misure di sicurezza rientrano nei capitoli ordinari di bilancio per l'ordine pubblico.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Posizione di Alternativa Popolare in tema di sicurezza dei confini e legalità dell'immigrazione.",
        "fonte_titolo": "Linea Bandecchi su immigrazione: sicurezza dei confini e rimpatri immediati",
        "fonte_url": "https://www.alternativapopolare.it/programma-immigrazione",
        "fonte_testata": "Alternativa Popolare"
    },
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Politica Estera",
        "tipo_azione": "Risoluzione politica",
        "sintesi": "Lealtà assoluta all'Alleanza Atlantica, appartenenza organica alla famiglia del Partito Popolare Europeo e sostegno alle spese di difesa fino al 2% PIL.",
        "costo_stimato": "Circa 5 miliardi € annui a regime per il target NATO",
        "coperture_dichiarate": "In attesa di copertura (Programmazione pluriennale del bilancio della Difesa statale).",
        "fattibilita_finanziaria": "L'incremento strutturale della spesa militare richiede coperture compatibili con il patto di stabilità europeo.",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "Adesione ai target NATO approvati dai vertici internazionali dell'Alleanza ma ancora in fase di adeguamento finanziario.",
        "fonte_titolo": "Alternativa Popolare: lealtà NATO e linea atlantista nel Partito Popolare Europeo",
        "fonte_url": "https://www.alternativapopolare.it/programma-esteri",
        "fonte_testata": "Alternativa Popolare"
    },
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Diritti Civili",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Introduzione del quoziente familiare fiscale per azzerare l'IRPEF per i nuclei con almeno tre figli e sostegno economico diretto ai caregiver familiari.",
        "costo_stimato": "Circa 3,4 miliardi € annui",
        "coperture_dichiarate": "In attesa di copertura (Rimodulazione generale delle detrazioni e assegno unico universale).",
        "fattibilita_finanziaria": "Il quoziente familiare fiscale per i grandi nuclei comporta una forte contrazione di gettito IRPEF.",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "Proposta a sostegno della natalità in attesa di relazione tecnica RGS per la compensazione di gettito.",
        "fonte_titolo": "Alternativa Popolare per la famiglia: quoziente familiare e assegno per i caregiver",
        "fonte_url": "https://www.alternativapopolare.it/programma-famiglia",
        "fonte_testata": "Alternativa Popolare"
    },

    # Pace Terra Dignità (6 proposals)
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Fisco",
        "tipo_azione": "Disegno di legge depositato",
        "sintesi": "Imposta straordinaria del 50% su tutti gli extraprofitti delle industrie belliche, delle grandi banche commerciali e delle piattaforme Big Tech per finanziare sanità e scuola.",
        "costo_stimato": "Gettito aggiuntivo stimato in oltre 7 miliardi € annui",
        "coperture_dichiarate": "Prelievo erariale straordinario d'imposta vincolato a Fondi per il Servizio Sanitario e la Scuola Pubblica.",
        "fattibilita_finanziaria": "Proposta tributaria con saldi positivi ma soggetta a rischi di contenzioso tributario e costituzionale ex art. 53 Cost.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Proposta cardine del programma di Michele Santoro depositata in occasione delle elezioni europee e politiche.",
        "fonte_titolo": "Pace Terra Dignità: tassa al 50% sugli extraprofitti delle armi e delle banche",
        "fonte_url": "https://www.paceterradignita.it/programma/fisco-extraprofitti",
        "fonte_testata": "Pace Terra Dignità"
    },
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Pensioni",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Abolizione integrale della Legge Fornero con diritto alla pensione a 60 anni o 35 anni di contributi, e pensione minima universale a 1.000 euro per tutti.",
        "costo_stimato": "Circa 9,5 miliardi € annui",
        "coperture_dichiarate": "In attesa di copertura (Finanziata mediante tassazione dei grandi patrimoni e stop alle spese militari).",
        "fattibilita_finanziaria": "Costo economico elevatissimo privo di relazione tecnica asseverata dalla Ragioneria Generale dello Stato.",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "Obiettivo programmatico di rottura del sistema previdenziale privo di DDL formalmente incardinato.",
        "fonte_titolo": "Pace Terra Dignità: pensione a 60 anni e 1000 euro per tutti",
        "fonte_url": "https://www.paceterradignita.it/programma/pensioni-diritti",
        "fonte_testata": "Pace Terra Dignità"
    },
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Istruzione",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Gratuità totale dell'istruzione pubblica dall'asilo all'università, abolizione di ogni tassa universitaria per redditi fino a 40.000 euro ISEE e gratuità dei libri scolastici.",
        "costo_stimato": "Circa 4,2 miliardi € annui",
        "coperture_dichiarate": "In attesa di copertura (Riconversione dei fondi della difesa militare verso il Ministero dell'Istruzione).",
        "fattibilita_finanziaria": "La copertura tramite taglio delle spese militari richiede modifiche agli impegni internazionali dello Stato.",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "Proposta programmatica della lista di sinistra pacifista a sostegno del diritto allo studio universale.",
        "fonte_titolo": "Pace Terra Dignità: scuola e università gratuite per tutti senza tasse",
        "fonte_url": "https://www.paceterradignita.it/programma/istruzione-gratuita",
        "fonte_testata": "Pace Terra Dignità"
    },
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Istituzioni",
        "tipo_azione": "Proposta referendaria e di legge",
        "sintesi": "Abrogazione immediata dell'autonomia differenziata per tutelare l'uguaglianza dei cittadini e ripristino della legge elettorale proporzionale pura con voto di preferenza.",
        "costo_stimato": "Invarianza finanziaria (0 €)",
        "coperture_dichiarate": "Clausola di invarianza finanziaria ex art. 81 Costituzione.",
        "fattibilita_finanziaria": "Proposta istituzionale a costo zero per le casse pubbliche.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Sostegno attivo al referendum contro l'autonomia differenziata e deposito di proposta proporzionale.",
        "fonte_titolo": "Pace Terra Dignità: referendum contro autonomia differenziata e proporzionale puro",
        "fonte_url": "https://www.paceterradignita.it/programma/democrazia-istituzioni",
        "fonte_testata": "Pace Terra Dignità"
    },
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Immigrazione",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Chiusura immediata di tutti i Centri di Permanenza per i Rimpatri (CPR), canali umanitari legali europei e diritto di cittadinanza per chi nasce in Italia.",
        "costo_stimato": "Circa 600 milioni € annui",
        "coperture_dichiarate": "Risparmio di spesa derivante dalla chiusura dei contratti di appalto dei CPR e fondi europei per l'accoglienza diffusa.",
        "fattibilita_finanziaria": "La riallocazione dei fondi della detenzione amministrativa verso l'accoglienza diffusa rende l'intervento fattibile.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Posizione di principio di Michele Santoro e Raniero La Valle per il superamento della detenzione amministrativa dei migranti.",
        "fonte_titolo": "Pace Terra Dignità: stop ai CPR e accoglienza solidale diffusa",
        "fonte_url": "https://www.paceterradignita.it/programma/immigrazione-accoglienza",
        "fonte_testata": "Pace Terra Dignità"
    },
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Infrastrutture",
        "tipo_azione": "Atto di indirizzo parlamentare",
        "sintesi": "Cancellazione definitiva dell'appalto del Ponte sullo Stretto di Messina e destinazione vincolata dei 14 miliardi al raddoppio ferroviario della Sicilia e Calabria.",
        "costo_stimato": "Riallocazione di 14 miliardi € già stanziati",
        "coperture_dichiarate": "Storno integrale dei fondi iscritti a bilancio pluriennale per il Ponte sullo Stretto verso il contratto di programma RFI.",
        "fattibilita_finanziaria": "Riallocazione di risorse già presenti a legislazione vigente nella legge di bilancio.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Proposta di riconversione economica delle grandi opere verso la sicurezza idrogeologica e la rete ferroviaria pendolare.",
        "fonte_titolo": "Pace Terra Dignità: no al Ponte sullo Stretto, 14 miliardi ai treni di Sicilia e Calabria",
        "fonte_url": "https://www.paceterradignita.it/programma/infrastrutture-ponte",
        "fonte_testata": "Pace Terra Dignità"
    },

    # Sud chiama Nord (6 proposals)
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Lavoro",
        "tipo_azione": "Disegno di legge depositato",
        "sintesi": "Decontribuzione al 100% permanente per tutte le micro e piccole imprese del Sud Italia che assumono personale locale e accordi territoriali per salari adeguati al costo della vita.",
        "costo_stimato": "Circa 3,8 miliardi € annui",
        "coperture_dichiarate": "Risorse del Fondo di Sviluppo e Coesione (FSC) e proroga strutturale dell'incentivo Decontribuzione Sud.",
        "fattibilita_finanziaria": "In attesa di copertura permanente (La decontribuzione Sud è attualmente soggetta a proroghe temporanee e autorizzazioni UE sugli aiuti di Stato).",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "Proposta parlamentare del deputato Cateno De Luca per il lavoro stabile nel Meridione in attesa di accordo stabile con la Commissione UE.",
        "fonte_titolo": "Sud chiama Nord: decontribuzione totale per le imprese del Mezzogiorno",
        "fonte_url": "https://www.sud-chiamanord.it/programma/lavoro-sud",
        "fonte_testata": "Sud chiama Nord Ufficio Stampa"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Pensioni",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Anticipo pensionistico dedicato di 3 anni senza penalizzazioni di calcolo per tutti i residenti nelle regioni del Sud Italia e lavoratori di settori a forte usura fisica.",
        "costo_stimato": "Circa 2,1 miliardi € annui",
        "coperture_dichiarate": "In attesa di copertura (Fondi per il riequilibrio previdenziale territoriale).",
        "fattibilita_finanziaria": "Proposta di differenziazione territoriale previdenziale priva di quantificazione congiunta INPS/MEF.",
        "fact_check_status": "In attesa di copertura",
        "fact_check_motivazione": "Promessa elettorale di Cateno De Luca per l'uscita anticipata al Sud priva di copertura asseverata ex art. 81 Cost.",
        "fonte_titolo": "De Luca: pensione anticipata di 3 anni per i lavoratori del Meridione",
        "fonte_url": "https://www.sud-chiamanord.it/programma/pensioni-mezzogiorno",
        "fonte_testata": "Sud chiama Nord"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Istruzione",
        "tipo_azione": "Disegno di legge regionale e nazionale",
        "sintesi": "Assegnazione prioritaria con indennità economica di insularità e montanità per i docenti nelle scuole del Sud e garanzia del tempo pieno e della mensa gratuita al 100%.",
        "costo_stimato": "Circa 900 milioni € annui",
        "coperture_dichiarate": "Fondi perequativi territoriali del Piano per il Sud e stanziamenti PNRR per la lotta alla dispersione scolastica.",
        "fattibilita_finanziaria": "Misura compatibile con i vincoli di coesione territoriale finanziabile tramite il Fondo Perequativo Nazionale.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Iniziativa legislativa presentata da Sud chiama Nord per frenare l'abbandono scolastico al Sud e valorizzare i docenti.",
        "fonte_titolo": "Sud chiama Nord: indennità per i docenti al Sud e tempo pieno garantito",
        "fonte_url": "https://www.sud-chiamanord.it/programma/scuola-istruzione",
        "fonte_testata": "Sud chiama Nord"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Immigrazione",
        "tipo_azione": "Risoluzione parlamentare",
        "sintesi": "Dichiarazione della Sicilia e delle Isole Minori quale confine strategico europeo con indennizzo economico automatico ai Comuni e presidio navale UE.",
        "costo_stimato": "Circa 250 milioni € annui",
        "coperture_dichiarate": "Fondi europei del programma AMIF (Asylum, Migration and Integration Fund) e compensazioni straordinarie del bilancio dello Stato.",
        "fattibilita_finanziaria": "Finanziabile attraverso i fondi di solidarietà per i Paesi di primo approdo previsti dal Patto Europeo Migrazione e Asilo.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Atto parlamentare depositato da Sud chiama Nord a tutela dei territori di frontiera come Lampedusa e Pozzallo.",
        "fonte_titolo": "Risoluzione De Luca: la Sicilia non sia l'hotspot d'Europa, indennizzi ai Comuni",
        "fonte_url": "https://www.sud-chiamanord.it/programma/immigrazione-isole",
        "fonte_testata": "Sud chiama Nord"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Politica Estera",
        "tipo_azione": "Dichiarazione programmatica",
        "sintesi": "Piano Strategico Euromediterraneo per rendere i porti siciliani di Augusta, Palermo e Catania il centro logistico ed energetico degli scambi nel Mediterraneo.",
        "costo_stimato": "Circa 1,2 miliardi € ripartiti in 5 anni",
        "coperture_dichiarate": "Fondi delle reti transeuropee di trasporto TEN-T e cofinanziamento con la Banca Europea per gli Investimenti (BEI).",
        "fattibilita_finanziaria": "Progetto di cooperazione logistica e marittima coerente con i corridoi europei Scandinavo-Mediterraneo.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Proposta programmatica di Laura Castelli e Cateno De Luca per la valorizzazione geostrategica della Sicilia nel Mediterraneo.",
        "fonte_titolo": "Sud chiama Nord: la Sicilia hub logistico ed energetico del Mediterraneo",
        "fonte_url": "https://www.sud-chiamanord.it/programma/mediterraneo-logistica",
        "fonte_testata": "Sud chiama Nord"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Diritti Civili",
        "tipo_azione": "Disegno di legge depositato",
        "sintesi": "Piena applicazione del principio costituzionale di insularità (art. 119 Cost.) con continuità territoriale aerea e marittima a tariffa sociale garantita per i residenti.",
        "costo_stimato": "Circa 450 milioni € annui",
        "coperture_dichiarate": "Fondo nazionale per la continuità territoriale e risorse del Ministero delle Infrastrutture e dei Trasporti.",
        "fattibilita_finanziaria": "Proposta conforme all'art. 119 Cost. introdotto dalla riforma costituzionale sull'insularità con capitoli di bilancio ordinario.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Battaglia storica di Sud chiama Nord contro il caro-voli e per il diritto alla mobilità dei cittadini delle isole.",
        "fonte_titolo": "Continuità territoriale e stop al caro-voli: il DDL di Sud chiama Nord",
        "fonte_url": "https://www.sud-chiamanord.it/programma/continuita-territoriale",
        "fonte_testata": "Sud chiama Nord Ufficio Stampa"
    }
]

def main():
    db = SessionLocal()
    parties = {p.name: p for p in db.query(PoliticalParty).all()}
    
    print(f"Loaded {len(parties)} parties from DB.")
    added_count = 0
    
    for item in NEW_PROPOSALS:
        p_name = item["partito"]
        party = parties.get(p_name)
        if not party:
            print(f"Party {p_name} not found!")
            continue
            
        # Check if identical synthesis already exists
        existing = db.query(PoliticalProposal).filter(
            PoliticalProposal.partito == p_name,
            PoliticalProposal.macro_argomento == item["macro_argomento"]
        ).first()
        
        # If there's already a proposal for that topic, let's verify if exact synthesis exists
        exact = db.query(PoliticalProposal).filter(
            PoliticalProposal.partito == p_name,
            PoliticalProposal.dichiarazione_sintesi == item["sintesi"]
        ).first()
        
        if exact:
            print(f"Skipping already existing: {p_name} | {item['macro_argomento']}")
            continue
            
        emb = _local_deterministic_embedding(f"{p_name} {item['macro_argomento']} {item['sintesi']}")
        
        emb_str = json.dumps(emb)
        
        prop = PoliticalProposal(
            party_id=party.id,
            partito=p_name,
            macro_argomento=item["macro_argomento"],
            dichiarazione_sintesi=item["sintesi"],
            tipo_azione=item["tipo_azione"],
            costo_stimato=item["costo_stimato"],
            coperture_dichiarate=item["coperture_dichiarate"],
            fattibilita_finanziaria=item["fattibilita_finanziaria"],
            fact_check_status=item["fact_check_status"],
            fact_check_motivazione=item["fact_check_motivazione"],
            fact_check_fonte=item["fonte_url"],
            fonte_url=item["fonte_url"],
            fonte_titolo=item["fonte_titolo"],
            fonte_testata=item["fonte_testata"],
            raw_text=f"{item['sintesi']} Atto politico promosso da {p_name} in materia di {item['macro_argomento']}.",
            embedding=emb_str,
            timestamp=datetime.datetime.utcnow(),
            created_at=datetime.datetime.utcnow()
        )
        db.add(prop)
        added_count += 1
        print(f"Added: {p_name} | {item['macro_argomento']}")
        
    db.commit()
    print(f"\nSuccessfully added {added_count} new proposals.")
    db.close()
    
    # Run the comprehensive audit and recalculation engine to sync seed_data.py and dossiers
    from recalculate_and_audit import audit_and_recalculate_all
    audit_and_recalculate_all()
    print("All tasks completed.")

if __name__ == "__main__":
    main()
