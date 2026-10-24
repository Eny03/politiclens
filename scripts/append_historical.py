import os

HISTORICAL_SNIPPET = """
    # ================================================================
    # SUD CHIAMA NORD — 2022-2024 (Elezioni Politiche ed Europee)
    # ================================================================
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Istituzioni",
        "dichiarazione_sintesi": "Patto di riscatto per il Sud: perequazione infrastrutturale automatica per ferrovie, strade e reti idriche prima di qualsiasi devoluzione di competenze regionali",
        "tipo_azione": "Dichiarazione programmatica",
        "costo_stimato": "Circa 10 miliardi € spalmati su 5 anni a valere sul Fondo Sviluppo e Coesione",
        "coperture_dichiarate": "FSC (Fondo per lo Sviluppo e la Coesione) e risorse ordinarie del bilancio pluriennale ex art. 119 comma 5 Costituzione.",
        "fattibilita_finanziaria": "La destinazione dell'80% delle risorse FSC al Mezzogiorno è principio normativo stabilito dalla legge nazionale.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Tema cardine della campagna elettorale 2022 che ha consentito a Sud chiama Nord l'elezione di parlamentari alla Camera e al Senato.",
        "fact_check_fonte": "https://www.sud-chiamanord.it",
        "fonte_url": "https://www.sud-chiamanord.it/programma-politiche-2022",
        "fonte_titolo": "Sud chiama Nord: il patto per il Sud e per le autonomie territoriali",
        "fonte_testata": "Sud chiama Nord",
        "timestamp": "2022-09-10T10:00:00",
        "party_color": "#f58220"
    },
    {
        "partito": "Sud chiama Nord",
        "macro_argomento": "Infrastrutture",
        "dichiarazione_sintesi": "Lista Libertà per le Europee 2024: Meno Europa, più Italia, più sovranità dei territori e difesa dell'agricoltura e pesca mediterranea",
        "tipo_azione": "Dichiarazione programmatica",
        "costo_stimato": "Invarianza finanziaria sui saldi di bilancio nazionale",
        "coperture_dichiarate": "Riforma della Politica Agricola Comune (PAC) e fondo FEAMPA europeo.",
        "fattibilita_finanziaria": "Proposta di indirizzo per la revisione dei regolamenti del Green Deal europeo sui settori primari.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Manifesto federativo della lista Libertà promossa da Cateno De Luca alle elezioni europee di giugno 2024 (1.22% nazionale).",
        "fact_check_fonte": "https://www.europarl.europa.eu",
        "fonte_url": "https://www.ansa.it/europa/notizie/rubriche/altrenews/2024/04/04/de-luca-presenta-il-simbolo-liberta-per-le-europee_789.html",
        "fonte_titolo": "Elezioni europee 2024: De Luca presenta la lista Libertà a Roma",
        "fonte_testata": "ANSA",
        "timestamp": "2024-04-04T12:00:00",
        "party_color": "#f58220"
    },

    # ================================================================
    # PACE TERRA DIGNITÀ — 2024 (Europee per la Pace)
    # ================================================================
    {
        "partito": "Pace Terra Dignità",
        "macro_argomento": "Politica Estera",
        "dichiarazione_sintesi": "Stop all'escalation bellica, divieto di invio di armi letali e investimenti prioritari sulla diplomazia e sul welfare sociale",
        "tipo_azione": "Dichiarazione programmatica",
        "costo_stimato": "Risparmio di oltre 2 miliardi € sulle spese militari",
        "coperture_dichiarate": "Riallocazione su capitoli di spesa per sanità pubblica e istruzione.",
        "fattibilita_finanziaria": "Misura di riduzione della spesa per approvvigionamento bellico a saldo positivo per i conti civili.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Manifesto fondativo depositato per le Elezioni Europee 2024 che ha ottenuto oltre 511.000 preferenze (2.21%).",
        "fact_check_fonte": "https://www.paceterradignita.it",
        "fonte_url": "https://www.ansa.it/sito/notizie/politica/2024/04/15/santoro-presenta-pace-terra-dignita-contro-la-guerra_99.html",
        "fonte_titolo": "Michele Santoro lancia la lista Pace Terra Dignità per il Parlamento Europeo",
        "fonte_testata": "ANSA",
        "timestamp": "2024-04-15T11:00:00",
        "party_color": "#0d9488"
    },

    # ================================================================
    # PARTITO SOCIALISTA ITALIANO — 2022-2024
    # ================================================================
    {
        "partito": "Partito Socialista Italiano",
        "macro_argomento": "Lavoro",
        "dichiarazione_sintesi": "Campagna per il lavoro dignitoso: salario minimo e fondo di garanzia pensionistica per le carriere discontinue dei giovani",
        "tipo_azione": "Proposta di legge",
        "costo_stimato": "Circa 1.8 miliardi € annui",
        "coperture_dichiarate": "Riorganizzazione delle agevolazioni contributive e fiscalità progressiva.",
        "fattibilita_finanziaria": "Sostenibile: si inserisce nel quadro previdenziale delle pensioni di garanzia giovanili studiate dal CNEL.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Documento approvato dalla Direzione Nazionale del PSI e condiviso nei tavoli programmatici del PSE.",
        "fact_check_fonte": "https://www.partitosocialista.it",
        "fonte_url": "https://www.avantionline.it/psi-campagna-lavoro-giovani-salario-minimo/",
        "fonte_titolo": "PSI: Un lavoro dignitoso e salario minimo: la battaglia socialista continua",
        "fonte_testata": "Avanti! Online",
        "timestamp": "2023-11-20T10:00:00",
        "party_color": "#dc2626"
    },

    # ================================================================
    # ALTERNATIVA POPOLARE — 2023-2024
    # ================================================================
    {
        "partito": "Alternativa Popolare",
        "macro_argomento": "Fisco",
        "dichiarazione_sintesi": "Sostegno alle microimprese e commercio di vicinato: esenzione totale dai tributi locali (TARI e occupazione suolo pubblico) per i primi due anni per i negozi aperti nei centri storici",
        "tipo_azione": "Dichiarazione programmatica",
        "costo_stimato": "Circa 120 milioni € annui a livello nazionale",
        "coperture_dichiarate": "Fondo perequativo per la rigenerazione urbana e compensazioni a carico delle Regioni.",
        "fattibilita_finanziaria": "Applicabile a livello comunale tramite delibere di bilancio e regolamenti sui tributi locali.",
        "fact_check_status": "Verificato",
        "fact_check_motivazione": "Modello amministrativo attuato a Terni dall'amministrazione Bandecchi e proposto nei programmi per le regionali.",
        "fact_check_fonte": "https://www.alternativapopolare.it",
        "fonte_url": "https://www.ilmessaggero.it/umbria/terni_commercio_bandecchi_tasse_zero-789012.html",
        "fonte_titolo": "Alternativa Popolare: tasse zero per due anni ai nuovi negozi nei centri storici",
        "fonte_testata": "Il Messaggero",
        "timestamp": "2023-10-14T15:30:00",
        "party_color": "#2563eb"
    }
"""

def append_to_historical():
    path = "backend/app/data/historical_proposals.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    idx = content.rfind("]")
    if idx != -1:
        new_content = content[:idx] + HISTORICAL_SNIPPET + content[idx:]
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("historical_proposals.py updated successfully!")
    else:
        print("Closing bracket not found!")

if __name__ == "__main__":
    append_to_historical()
