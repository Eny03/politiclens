# Configuration of monitored political RSS feeds, official institutions, media sources and social channels

MONITORED_FEEDS = [
    # --- Agenzie di Stampa e Istituzioni ---
    {
        "name": "ANSA Politica & Istituzioni",
        "url": "https://www.ansa.it/sito/notizie/politica/politica_rss.xml",
        "category": "Agenzia Nazionale",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "ANSA Economia & Finanza Pubblica",
        "url": "https://www.ansa.it/sito/notizie/economia/economia_rss.xml",
        "category": "Economia & Fisco",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Il Sole 24 Ore - Politica & Riforme",
        "url": "https://www.ilsole24ore.com/rss/italia--politica.xml",
        "category": "Economia & Istituzioni",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Corriere della Sera - Politica",
        "url": "https://xml2.corriereobjects.it/rss/politica.xml",
        "category": "Quotidiano Nazionale",
        "reliability": "Alta",
        "is_active": True
    },
    {
        "name": "La Repubblica - Politica",
        "url": "https://www.repubblica.it/rss/politica/rss2.0.xml",
        "category": "Quotidiano Nazionale",
        "reliability": "Alta",
        "is_active": True
    },
    {
        "name": "Open - Fact-Checking & Politica",
        "url": "https://www.open.online/feed/",
        "category": "Fact-Checking & Web",
        "reliability": "Alta",
        "is_active": True
    },
    {
        "name": "Google News - Politica & Parlamento Live",
        "url": "https://news.google.com/rss/search?q=governo+politica+camera+senato+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Aggregatore Nazionale",
        "reliability": "Massima",
        "is_active": True
    },
    # --- Live Web Search AI Crawler (Scansione Web Nazionale per Partito) ---
    {
        "name": "Live Web Search - Fratelli d'Italia & Governo",
        "url": "https://news.google.com/rss/search?q=Fratelli+d%27Italia+Meloni+governo+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Partito Democratico & Schlein",
        "url": "https://news.google.com/rss/search?q=Partito+Democratico+Schlein+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Movimento 5 Stelle & Conte",
        "url": "https://news.google.com/rss/search?q=Movimento+5+Stelle+Giuseppe+Conte+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Lega & Salvini",
        "url": "https://news.google.com/rss/search?q=Lega+Salvini+proposte+riforme&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Forza Italia & Tajani",
        "url": "https://news.google.com/rss/search?q=Forza+Italia+Antonio+Tajani+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Alleanza Verdi e Sinistra",
        "url": "https://news.google.com/rss/search?q=Alleanza+Verdi+Sinistra+Bonelli+Fratoianni&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Azione & Calenda",
        "url": "https://news.google.com/rss/search?q=Azione+Carlo+Calenda+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Italia Viva & Renzi",
        "url": "https://news.google.com/rss/search?q=Italia+Viva+Matteo+Renzi+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - +Europa & Magi",
        "url": "https://news.google.com/rss/search?q=Piu+Europa+Riccardo+Magi+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Noi Moderati & Lupi",
        "url": "https://news.google.com/rss/search?q=Noi+Moderati+Maurizio+Lupi+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Manovra Economica & Fisco",
        "url": "https://news.google.com/rss/search?q=governo+opposizione+manovra+fisco+proposte+mef&hl=it&gl=IT&ceid=IT:it",
        "category": "Economia & Finanza Pubblica",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Lavoro, Salari & Pensioni",
        "url": "https://news.google.com/rss/search?q=partiti+salario+minimo+pensioni+quota+41+lavoro&hl=it&gl=IT&ceid=IT:it",
        "category": "Lavoro & Welfare",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Sanità Pubblica & Liste d'Attesa",
        "url": "https://news.google.com/rss/search?q=sanita+fondi+ospedali+liste+attesa+partiti+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Sanità & Servizi",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Partito Liberal Democratico & Marattin",
        "url": "https://news.google.com/rss/search?q=Partito+Liberal+Democratico+Marattin+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Futuro Nazionale & Vannacci",
        "url": "https://news.google.com/rss/search?q=Futuro+Nazionale+Roberto+Vannacci+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Movimento ORA!",
        "url": "https://news.google.com/rss/search?q=Movimento+ORA+proposte+riforme&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Radicali Italiani",
        "url": "https://news.google.com/rss/search?q=Radicali+Italiani+Hallissey+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Rifondazione Comunista & Acerbo",
        "url": "https://news.google.com/rss/search?q=Rifondazione+Comunista+Maurizio+Acerbo+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Potere al Popolo",
        "url": "https://news.google.com/rss/search?q=Potere+al+Popolo+Granato+Collot+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Democrazia Sovrana Popolare & Rizzo",
        "url": "https://news.google.com/rss/search?q=Democrazia+Sovrana+Popolare+Marco+Rizzo+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Südtiroler Volkspartei & Steger",
        "url": "https://news.google.com/rss/search?q=S%C3%BCdtiroler+Volkspartei+Dieter+Steger+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Sud chiama Nord & Cateno De Luca",
        "url": "https://news.google.com/rss/search?q=Sud+chiama+Nord+Cateno+De+Luca+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Pace Terra Dignità & Michele Santoro",
        "url": "https://news.google.com/rss/search?q=Pace+Terra+Dignita+Michele+Santoro+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Partito Socialista Italiano & Enzo Maraio",
        "url": "https://news.google.com/rss/search?q=Partito+Socialista+Italiano+Maraio+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Alternativa Popolare & Stefano Bandecchi",
        "url": "https://news.google.com/rss/search?q=Alternativa+Popolare+Stefano+Bandecchi+proposte&hl=it&gl=IT&ceid=IT:it",
        "category": "Ricerca Web AI",
        "reliability": "Massima",
        "is_active": True
    },
    {
        "name": "Live Web Search - Senato & Camera dei Deputati",
        "url": "https://news.google.com/rss/search?q=Parlamento+Camera+Senato+disegno+di+legge+approvato&hl=it&gl=IT&ceid=IT:it",
        "category": "Atti Parlamentari",
        "reliability": "Massima",
        "is_active": True
    }
]

# Canali ufficiali e monitoraggio social media/web dei partiti politici
PARTY_OFFICIAL_CHANNELS = {
    "Fratelli d'Italia": {
        "website": "https://www.fratelli-italia.it",
        "social_handles": ["@GiorgiaMeloni", "@FratellidItalia", "facebook.com/fratelliditalia"],
        "rss": "https://www.fratelli-italia.it/feed/"
    },
    "Partito Democratico": {
        "website": "https://www.partitodemocratico.it",
        "social_handles": ["@ellyesse", "@pdnetwork", "facebook.com/partitodemocratico"],
        "rss": "https://www.partitodemocratico.it/feed/"
    },
    "Movimento 5 Stelle": {
        "website": "https://www.movimento5stelle.eu",
        "social_handles": ["@GiuseppeConteIT", "@M5S_Europa", "facebook.com/movimentocinquestelle"],
        "rss": "https://www.movimento5stelle.eu/feed/"
    },
    "Lega - Salvini Premier": {
        "website": "https://www.legaonline.it",
        "social_handles": ["@matteosalvinimi", "@LegaSalvini", "facebook.com/salviniofficial"],
        "rss": "https://www.legaonline.it/feed/"
    },
    "Forza Italia": {
        "website": "https://www.forzaitalia.it",
        "social_handles": ["@Antonio_Tajani", "@forza_italia", "facebook.com/forzaitalia"],
        "rss": "https://www.forzaitalia.it/feed/"
    },
    "Alleanza Verdi e Sinistra": {
        "website": "https://verdisinistra.it",
        "social_handles": ["@AngeloBonelli1", "@NFratoianni", "@VerdiSinistra"],
        "rss": "https://verdisinistra.it/feed/"
    },
    "Azione": {
        "website": "https://www.azione.it",
        "social_handles": ["@CarloCalenda", "@Azione_it", "facebook.com/AzioneIT"],
        "rss": "https://www.azione.it/feed/"
    },
    "Italia Viva": {
        "website": "https://www.italiaviva.it",
        "social_handles": ["@matteorenzi", "@ItaliaViva", "facebook.com/ItaliaViva"],
        "rss": "https://www.italiaviva.it/feed/"
    },
    "+Europa": {
        "website": "https://www.piueuropa.eu",
        "social_handles": ["@riccardomagi", "@Piu_Europa", "facebook.com/piueuropa"],
        "rss": "https://www.piueuropa.eu/feed/"
    },
    "Noi Moderati": {
        "website": "https://www.noimoderati.it",
        "social_handles": ["@Maurizio_Lupi", "@NoiModerati", "facebook.com/noimoderati"],
        "rss": "https://www.noimoderati.it/feed/"
    },
    "Partito Liberal Democratico": {
        "website": "https://partitoliberaldemocratico.com",
        "social_handles": ["@marattin", "@LibDem_IT", "@OrizzontiLib"],
        "rss": "https://partitoliberaldemocratico.com/feed/"
    },
    "Futuro Nazionale": {
        "website": "https://futuronazionale.it",
        "social_handles": ["@RobertoVannacci", "@FuturoNaz", "@simoni_m"],
        "rss": "https://futuronazionale.it/feed/"
    },
    "ORA!": {
        "website": "https://ora-italia.it",
        "social_handles": ["@Ora_Italia", "@micheleboldrin", "@forchielli"],
        "rss": "https://ora-italia.it/feed/"
    },
    "Radicali Italiani": {
        "website": "https://www.radicali.it",
        "social_handles": ["@radicali", "@m_hallissey"],
        "rss": "https://www.radicali.it/feed/"
    },
    "Rifondazione Comunista": {
        "website": "https://www.rifondazione.it",
        "social_handles": ["@RifondazioneSin", "@maurizioacerbo"],
        "rss": "https://www.rifondazione.it/feed/"
    },
    "Potere al Popolo": {
        "website": "https://poterealpopolo.org",
        "social_handles": ["@potere_alpopolo", "@GiulianoGranato"],
        "rss": "https://poterealpopolo.org/feed/"
    },
    "Democrazia Sovrana Popolare": {
        "website": "https://democraziasovranapopolare.it",
        "social_handles": ["@MarcoRizzo", "@DSP_Italia"],
        "rss": "https://democraziasovranapopolare.it/feed/"
    },
    "Südtiroler Volkspartei": {
        "website": "https://www.svp.eu",
        "social_handles": ["@svp_online"],
        "rss": "https://www.svp.eu/feed/"
    },
    "Sud chiama Nord": {
        "website": "https://sud-chiamanord.it",
        "social_handles": ["@CatenoDeLuca", "@SudChiamaNord", "@CastelliLaura"],
        "rss": "https://sud-chiamanord.it/feed/"
    },
    "Pace Terra Dignità": {
        "website": "https://www.paceterradignita.it",
        "social_handles": ["@michelesantorotv", "@PaceTerraDignita"],
        "rss": "https://www.paceterradignita.it/feed/"
    },
    "Partito Socialista Italiano": {
        "website": "https://www.partitosocialista.it",
        "social_handles": ["@EnzoMaraio", "@PSI_Socialisti"],
        "rss": "https://www.partitosocialista.it/feed/"
    },
    "Alternativa Popolare": {
        "website": "https://www.alternativapopolare.it",
        "social_handles": ["@StefanoBandecchi", "@Alt_Popolare"],
        "rss": "https://www.alternativapopolare.it/feed/"
    }
}

# Party detection aliases to accurately map textual mentions to normalized party codes
PARTY_ALIASES = {
    "Fratelli d'Italia": ["fratelli d'italia", "fdi", "giorgia meloni", "meloni", "crosetto", "lollobrigida", "donzelli", "fitto", "fazzolari", "bignami"],
    "Partito Democratico": ["partito democratico", "pd", "elly schlein", "schlein", "provenzano", "boccia", "braga", "misiani", "orlando", "gualtieri"],
    "Movimento 5 Stelle": ["movimento 5 stelle", "m5s", "giuseppe conte", "conte", "cinquestelle", "5 stelle", "appendino", "patuanelli", "todde", "traversi"],
    "Lega - Salvini Premier": ["lega", "lega - salvini premier", "lega nord", "matteo salvini", "salvini", "giorgetti", "calderoli", "crippa", "fedriga", "zaia", "borghi", "bagnai"],
    "Forza Italia": ["forza italia", "antonio tajani", "tajani", "barelli", "ronzulli", "gasparri", "berlusconi", "occhipinti", "cannizzaro", "roberto occhiuto"],
    "Alleanza Verdi e Sinistra": ["alleanza verdi e sinistra", "alleanza verdi sinistra", "avs", "verdi e sinistra", "angelo bonelli", "nicola fratoianni", "bonelli", "fratoianni", "europa verde", "sinistra italiana", "salis"],
    "Azione": ["partito azione", "azione - calenda", "carlo calenda", "calenda", "gruppo azione", "azione under 30", "fabrizio benzoni", "elena bonetti", "giulia pastorella"],
    "Italia Viva": ["italia viva", "iv", "matteo renzi", "renzi", "boschi", "faraone", "bellanova", "delbono"],
    "+Europa": ["+europa", "più europa", "piu europa", "riccardo magi", "magi", "emma bonino", "bonino", "della vedova"],
    "Noi Moderati": ["noi moderati", "maurizio lupi", "saverio romano", "pino bicchielli", "alessandro colucci", "mara carfagna", "mariastella gelmini"],
    "Partito Liberal Democratico": ["partito liberal democratico", "partito liberaldemocratico", "pld", "liberal democratici", "libdem", "orizzonti liberali", "luigi marattin", "marattin", "andrea marcucci"],
    "Futuro Nazionale": ["futuro nazionale", "fnv", "roberto vannacci", "vannacci", "massimiliano simoni"],
    "ORA!": ["movimento ora", "partito ora", "comitato ora", "ora italia", "ora-italia", "alberto forchielli", "forchielli", "michele boldrin", "boldrin", "drin drin"],
    "Radicali Italiani": ["radicali italiani", "radicali", "matteo hallissey", "hallissey", "giulia crivellini", "maurizio turco", "partito radicale"],
    "Rifondazione Comunista": ["rifondazione comunista", "prc", "maurizio acerbo", "acerbo", "sinistra europea"],
    "Potere al Popolo": ["potere al popolo", "pap", "giuliano granato", "marta collot", "unione popolare"],
    "Democrazia Sovrana Popolare": ["democrazia sovrana popolare", "dsp", "marco rizzo", "francesco toscano", "sovrana popolare"],
    "Südtiroler Volkspartei": ["südtiroler volkspartei", "svp", "dieter steger", "steger", "herbert dorfmann"],
    "Sud chiama Nord": ["sud chiama nord", "scn", "cateno de luca", "de luca cateno", "laura castelli", "francesco gallo", "dafne musolino", "libertà de luca"],
    "Pace Terra Dignità": ["pace terra dignità", "pace terra e dignità", "pace terra e dignita", "ptd", "michele santoro", "santoro", "raniero la valle"],
    "Partito Socialista Italiano": ["partito socialista italiano", "partito socialista", "psi", "enzo maraio", "maraio", "socialisti italiani"],
    "Alternativa Popolare": ["alternativa popolare", "ap", "stefano bandecchi", "bandecchi", "paolo alli"]
}

# Macro-topics detection keywords
MACRO_TOPICS_KEYWORDS = {
    "Lavoro": ["salario minimo", "lavoro", "occupazione", "cuneo fiscale", "contratti", "inps", "disoccupazione", "precariato", "stage", "settimana corta", "pensioni", "quota 41", "fornero", "sicurezza sul lavoro", "decontribuzione", "smart working"],
    "Economia": ["fisco", "tasse", "flat tax", "irpef", "iva", "manovra", "patrimoniale", "debito pubblico", "pil", "def", "extraprofitti", "privatizzazioni", "bilancio", "inflazione", "superbonus", "concordato preventivo", "rottamazione"],
    "Energia": ["nucleare", "rinnovabili", "eolico", "fotovoltaico", "gas", "smr", "bollette", "caro energia", "transizione energetica", "idrogeno", "mase", "trivelle", "nucleare pulito", "comunità energetiche"],
    "Ambiente": ["clima", "siccità", "inquinamento", "co2", "decarbonizzazione", "green deal", "dissesto idrogeologico", "sad", "biodiversità", "auto elettriche", "alluvioni", "case green"],
    "Sanità": ["sanità", "ssn", "medici", "infermieri", "ospedali", "liste d'attesa", "pronto soccorso", "fondo sanitario", "mes sanitario", "ticket", "carenza personale", "salute mentale"],
    "Istruzione": ["scuola", "università", "docenti", "insegnanti", "istruzione", "its", "ricerca", "stipendi docenti", "tempo pieno", "valditara", "maturità", "precari scuola", "edilizia scolastica"],
    "Diritti Civili": ["diritti civili", "giustizia", "magistrati", "csm", "separazione delle carriere", "ius scholae", "cittadinanza", "carceri", "fine vita", "matrimonio egualitario", "adozioni", "carriere alias", "ddl zan", "prescrizione"],
    "Esteri": ["ucraina", "russia", "medio oriente", "gaza", "israele", "nato", "spese militari", "difesa europea", "eurobond", "piano mattei", "europa", "ue", "politica estera", "armi ucraina", "migranti albania"]
}
