import re
from typing import Optional

DISALLOWED_ENDINGS = (
    '...', '..', '…', ' -', ' --', ':', ';', ',', 
    ' lo', ' la', ' il', ' le', ' i', ' gli', ' un', ' uno', ' una', 
    ' pr', ' di', ' a', ' da', ' in', ' con', ' su', ' per', ' tra', ' fra', 
    ' del', ' dello', ' della', ' dei', ' degli', ' delle', 
    ' ed', ' ad', ' e', ' o', ' ma', ' se', ' che', 
    ' al', ' allo', ' alla', ' ai', ' agli', ' alle', 
    ' dal', ' dallo', ' dalla', ' dai', ' dagli', ' dalle', 
    ' nel', ' nello', ' nella', ' nei', ' negli', ' nelle', 
    ' sul', ' sullo', ' sulla', ' sui', ' sugli', ' sulle'
)

ALLOWED_UPPERCASE_ACRONYMS = {
    "UE", "PIL", "SSN", "SMR", "DDL", "CSM", "LEP", "UPB", "IVA", "TFR", 
    "PA", "FSN", "MEF", "CIPE", "CIPESS", "INPS", "ISTAT", "AI", "CER", "LSU", "LPU"
}

MEDIA_SOURCE_SUFFIXES = [
    r"\s*[-–—|:]\s*(?:https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.(?:it|com|org|net|eu|info|gov))\s*$",
    r"\s*[-–—|:]\s*(?:quotidiano sanit[àa]|panorama della sanit[àa]|orizzonte scuola(?:\s+notizie)?|il sole 24 ore|ansa|adn?kronos|corriere(?:\s+della sera)?|la repubblica|repubblica|la stampa|il giornale|il fatto quotidiano|il messaggero|open|fanpage|tgcom24|sky tg24|fisac cgil(?:\s+nazionale)?|cgil nazionale|cgil|cisl|uil|confindustria|rainews(?:\s*24)?|agi|adnkronos|askanews|dire|forbes|huffpost|affaritaliani|today|wired|linkiesta|editorialedomani)\s*$",
    r"\s*[-–—|:]\s*[a-zA-Z0-9\s]{2,25}(?:notizie|news|quotidiano|online|sanit[àa]|today|tg|post|forbes|magazine)\s*$",
    r"\s*[-–—|:]\s*[a-zA-Z0-9-]+\.[a-z]{2,4}\s*$"
]

NON_POLITICAL_ACTORS = [
    # Sindacati dei lavoratori
    r"\b(?:anaao|assomed|cgil|cisl|uil|fisac|anief|cobas|usb|flc|snals|gilda|anp|siulp|sap|coisp|sim carabinieri|uap|unisin|fabi)\b",
    # Associazioni datoriali e ordini professionali
    r"\b(?:confindustria|confcommercio|confesercenti|coldiretti|confagricoltura|cia|confartigianato|cna|abi|ania|federfarma|fnopi|ordine dei medici|consiglio nazionale forense|anm)\b",
    # Associazioni consumatori e terze parti
    r"\b(?:codacons|altroconsumo|federconsumatori|assoutenti|unione nazionale consumatori|legambiente|greenpeace|wwf|amnesty)\b"
]

NON_POLICY_HEADLINE_PATTERNS = [
    r"al centro della puntata\b",
    r"al centro del dibattito\b",
    r"al centro dell'attenzione\b",
    r"al centro della mobilitazione\b",
    r"al centro della protesta\b",
    r"al centro della piazza\b",
    r"in cento piazze\b",
    r"in piazza per\b",
    r"scende in piazza\b",
    r"raccolta firme\b",
    r"raccolta di firme\b",
    r"campagna di tesseramento\b",
    r"gazebo informativi\b",
    r"volantinaggio\b",
    r"porta le sue proposte in\b",
    r"porta le proposte in\b",
    r"al centro dell'iniziativa\b",
    r"manifestazione nazionale\b",
    r"sit-in\b",
    r"corteo\b",
    r"^[«\"']?\s*(?:è|e')\s+ora\s+di\s+cambiare\b",
    r"^[«\"']?\s*troppi cittadini costretti a\b",
    r"annuncia emendamento per pdl\b",
    r"ecco cosa cambia\b",
    r"tutto quello che c'è da sapere\b",
    r"cosa prevede la bozza\b",
    r"la puntata di\b",
    r"guida completa\b",
    r"^i programmi dei (?:principali )?partiti\b",
    r"^cosa propongono i partiti\b"
]

JOURNALISTIC_CLICKBAIT_PATTERNS = [
    r"^perch[ée]\s+",
    r"^guida,?\s+esempi",
    r"^come funziona\b",
    r"^a chi spetta\b",
    r"^bonus e detrazioni\b",
    r"^\s*-\s*[a-zA-Z]",
    r"^uscita a \d+ anni con \d+ di contributi",
    r"^il programma di\b",
    r"^interrogazione al governo",
    r"^[«\"']?sanit[àa],?\s+\w+:\s*interrogazione",
    r"^[«\"']?fondo nazionale con contributo",
    r"^[«\"']?fisco:\s*presentata in cassazione",
    r"^emendamento per pdl\b",
    r"^emendamento per ddl\b",
    r"^i programmi dei (?:principali )?partiti\b",
    r"^tasse, rincari e bonus\b"
]

RHETORICAL_SLOGAN_PATTERNS = [
    r"^(?:restituire|dare)\s+diritti\s+a\s+chi\b",
    r"^(?:dare|vogliamo dare)\s+voce\s+a\b",
    r"^mettere\s+al\s+centro\b",
    r"^stare\s+vicino\s+a\b",
    r"^lottare\s+per\b",
    r"^combattere\s+per\b",
    r"^ascoltare\s+(?:i bisogni|la voce|il popolo)\b",
    r"^cambiare\s+passo\b",
    r"^dire\s+basta\s+a\b",
    r"^difendere\s+il\s+futuro\b",
    r"^nessuno\s+deve\s+rimanere\s+indietro\b",
    r"^un\s+nuovo\s+inizio\s+per\b",
    r"^la\s+nostra\s+priorit[àa]\s+(?:è|saranno)\s+i\s+cittadini\b",
    r"^governo\s+bocciato\b",
    r"^opposizione\s+senza\s+idee\b"
]

POLICY_DOMAIN_NOUNS = [
    # Lavoro & Previdenza
    r"\bpension", r"\bprevidenz", r"\bcontribut", r"\btfr\b", r"\bsalari", r"\bstipend",
    r"\bcuneo\b", r"\blsu\b", r"\blpu\b", r"\bcontratt", r"\blavorator", r"\bammortizzator",
    r"\blicenziament", r"\bcassa integrazione", r"\bprecari", r"\bassunzion", r"\btirocin",
    r"\bpmi\b", r"\bimpres", r"\bddl\b", r"\bdecreto\b", r"\blegge\b", r"\bdisegno di legge\b",
    r"\bemendament", r"\bmozione\b", r"\bordine del giorno\b", r"\borario di lavoro\b",
    r"\b32 ore\b", r"\bquota 41\b", r"\bopzione donna\b",
    # Fisco & Economia
    r"\birpef\b", r"\biva\b", r"\bires\b", r"\bimpost", r"\btass", r"\bdetrazion",
    r"\bdeduzion", r"\baliquot", r"\bno tax area\b", r"\bbonus\b", r"\bextraprofitt",
    r"\bevasion", r"\bconcordato\b", r"\bflat tax\b", r"\baccis", r"\bbilancio\b",
    r"\bdebito\b", r"\bpil\b", r"\bfondo\b", r"\bfinanziament", r"\bsovraindebitament",
    r"\bpignorament", r"\briscossion", r"\bspesa\b",
    # Sanità & Sociale
    r"\bsanit[àa]", r"\bssn\b", r"\bfsn\b", r"\bospedal", r"\bmedici\b", r"\binfermier",
    r"\bliste d'attesa", r"\bprestazioni sanitarie", r"\bfarmac", r"\brsa\b", r"\bdisabilit",
    r"\basili nido", r"\bconged", r"\bnatalit", r"\bassegno unico",
    # Istituzioni, Giustizia, Diritti
    r"\bgiustizia\b", r"\bmagistrat", r"\bcsm\b", r"\bcarcer", r"\bprocess", r"\bseparazione delle carriere",
    r"\bpremierato\b", r"\breferendum\b", r"\bautonomia\b", r"\blep\b", r"\bcostituzion",
    r"\bcittadinanz", r"\bius scholae\b", r"\bius soli\b", r"\bfine vita\b", r"\beutanasia\b",
    r"\bcannabis\b", r"\bimmigrazion", r"\bmigrant", r"\bfrontiere\b", r"\brimpatri\b", r"\bcpr\b",
    # Energia, Ambiente, Infrastrutture, Scuola, Esteri, Istituzioni, Società
    r"\benergi", r"\benerget", r"\bcarburant", r"\bbiocarburant", r"\bgreen deal\b", r"\bclima\b", r"\bclimatic", r"\bbollett", r"\belettric", r"\bnazionalizzazion", r"\btariff",
    r"\brinnovabil", r"\bnucleare\b", r"\bsmr\b", r"\bemission", r"\bfotovoltaic", r"\beolic", r"\bidroelettric", r"\bautosufficienz",
    r"\bidrogeologic", r"\brigenerazion", r"\btransizione\b", r"\brifiut", r"\bponte\b",
    r"\binfrastruttur", r"\bferrovi", r"\btrasport", r"\bautostrad", r"\brete idrica", r"\bacquedott", r"\bidric", r"\bsiccit", r"\boper[ae]", r"\bcommissar", r"\bzes\b", r"\bportual", r"\blogistic", r"\bpnrr\b",
    r"\bscuola\b", r"\buniversit", r"\bdocent", r"\bricerca\b", r"\bistruzion", r"\bstudent", r"\beducazion", r"\bformazion", r"\btecnic", r"\bits\b", r"\bcondotta\b", r"\bsuperior", r"\bliceo\b", r"\bdidattic", r"\bmerito\b", r"\bdispersion",
    r"\bester", r"\bdifesa\b", r"\barmamenti\b", r"\barm[ie]\b", r"\bnato\b", r"\bue\b", r"\bunione europea\b", r"\bucraina\b", r"\bdiplomazi", r"\bcooperazion",
    r"\bdiritt", r"\bmatrimoni", r"\bcoppie\b", r"\blibert", r"\bdiscriminazion", r"\bburocraz", r"\bminister", r"\bpa\b", r"\bpubblica amministrazione\b", r"\bdigital", r"\bcittadin",
    r"\briform", r"\bdecret", r"\bbicameralism", r"\belezion", r"\belettor", r"\bparlament", r"\bautonom", r"\bregion", r"\bupb\b", r"\basseverazion",
    r"\bdublino\b", r"\bricollocazion", r"\bumanitar", r"\basilo\b", r"\baccoglienz", r"\bespulsion", r"\bclandestin", r"\bong\b", r"\bdecreti sicurezza\b",
    r"\bbilinguism", r"\bminoranz", r"\boccupazion", r"\bdelocalizzazion", r"\bsfratt", r"\ballogg", r"\bcasa\b", r"\babitativ"
]

def strip_media_source_suffix(text: Optional[str]) -> str:
    """
    Cleans media outlet suffixes, broadcast mentions and trailing quotes from proposal statements.
    E.g. "Proposta sanità - Quotidiano Sanità" -> "Proposta sanità"
    """
    if not text:
        return ""
    cleaned = text.strip()
    # Strip leading quotes
    cleaned = re.sub(r'^[«"\'“\s]+', '', cleaned)
    # Strip repeated trailing source tags
    for _ in range(3):
        prev = cleaned
        for pat in MEDIA_SOURCE_SUFFIXES:
            cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'[«"\'”\s\-\–—]+$', '', cleaned).strip()
        if cleaned == prev:
            break
    # Strip repetitive internal newspaper mentions
    cleaned = re.sub(r'\s*[-–—]\s*(?:Orizzonte Scuola Notizie|Quotidiano Sanità|Panorama della Sanità)\s*', ' ', cleaned, flags=re.IGNORECASE)
    # Strip any trailing or inline URLs and website domains
    cleaned = re.sub(r'[-–—|:]?\s*(?:https?://\S+|www\.\S+|[a-zA-Z0-9-]+\.(?:it|com|org|net|eu))\b', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def sanitize_and_validate_proposal_statement(text: Optional[str]) -> Optional[str]:
    """
    Rigorously validates and cleans a political proposal statement.
    Returns the clean, complete statement, or None if the statement is incomplete,
    truncated, a vague political slogan, attributed to non-political actors (unions),
    contains website URLs, rally event titles, or non-policy journalistic noise.
    """
    if not text:
        return None

    cleaned = strip_media_source_suffix(text)
    
    # 1. Fix stuck quotation marks without space (e.g. '"30%"epartiranno' -> '"30%" e partiranno')
    cleaned = re.sub(r'([”"»])([a-zA-ZÀ-ÿ])', r'\1 \2', cleaned)
    cleaned = re.sub(r'([a-zA-ZÀ-ÿ])([“"«])', r'\1 \2', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Reject if still contains web addresses, URLs, or domains
    if re.search(r'www\.|\.it\b|\.com\b|https?://', cleaned, re.IGNORECASE):
        return None

    cleaned_lower = cleaned.lower()

    # Reject rally, protest, or party mobilization slogans
    if re.search(r'\b(?:mobilitazione|in cento piazze|raccolta firme|sit-in|volantinaggio|tesseramento)\b', cleaned_lower):
        return None

    # 2. Check minimum length for a complete policy proposal
    if len(cleaned) < 30:
        return None

    cleaned_lower = cleaned.lower()

    # 3. Discard if attributed primarily to non-political actors (unions, employer guilds, medical orders)
    for actor_pat in NON_POLITICAL_ACTORS:
        # If text starts with or has subject as the union/guild (e.g. "anaao assomed lancia", "cgil chiede", etc.)
        if re.search(r'^(?:' + actor_pat + r')\b', cleaned_lower):
            return None
        if re.search(r'^(?:la|il|lo|l\')\s*(?:' + actor_pat + r')\s+(?:chiede|lancia|propone|annuncia|boccia)\b', cleaned_lower):
            return None
        if re.search(r'\b(?:anaao assomed|fisac cgil|anief|cobas|ordine dei medici)\b', cleaned_lower):
            return None

    # 4. Discard non-policy headlines, media broadcasts, or rhetorical laments
    for pat in NON_POLICY_HEADLINE_PATTERNS:
        if re.search(pat, cleaned_lower):
            return None

    # 5. Discard if contains ellipsis or suspension dots
    if '...' in cleaned or '…' in cleaned or '..' in cleaned:
        return None

    # 6. Discard if ends with dangling prepositions, articles, conjunctions or punctuation
    for ending in DISALLOWED_ENDINGS:
        if cleaned_lower.endswith(ending):
            return None

    # 7. Discard if ends with cut-off word or dangling single/double letters
    if re.search(r'\s[a-zA-Z]{1,2}$', cleaned):
        last_word = cleaned.split()[-1].strip(".,;:?!'\"")
        if not (last_word.isupper() and last_word in ALLOWED_UPPERCASE_ACRONYMS):
            return None

    # 8. Discard journalistic clickbait or article headlines
    for pat in JOURNALISTIC_CLICKBAIT_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return None

    # 9. Discard purely rhetorical or empty campaign slogans
    for pat in RHETORICAL_SLOGAN_PATTERNS:
        if re.search(pat, cleaned, re.IGNORECASE):
            return None

    # 10. Must contain at least ONE concrete public policy concept / domain noun
    has_policy_noun = any(re.search(pat, cleaned_lower) for pat in POLICY_DOMAIN_NOUNS)
    if not has_policy_noun:
        return None

    # 11. Discard if ends with colon, semicolon, comma or dash
    if cleaned.endswith((':', ';', ',', '-', '–', '—', '/', '\\')):
        return None

    return cleaned

def purge_and_audit_invalid_proposals(db) -> dict:
    """
    Autonomous AI Quality Auditor:
    Scans the database for invalid proposals (slogans, event titles, web URLs, or unvalidatable phrases).
    Either cleans/reformulates them or deletes them, recording an audit log entry for transparency.
    """
    import datetime
    from app.models import PoliticalProposal, AuditLog

    all_proposals = db.query(PoliticalProposal).all()
    deleted = []
    cleaned = []

    for p in all_proposals:
        stmt = (p.dichiarazione_sintesi or "").strip()
        val_stmt = sanitize_and_validate_proposal_statement(stmt)
        
        has_url = bool(re.search(r"www\.|\.it\b|\.com\b|https?://", stmt, re.I))
        has_rally = bool(re.search(r"\b(mobilitazione|in cento piazze|raccolta firme|sit-in|volantinaggio|tesseramento)\b", stmt, re.I))

        if not val_stmt or has_url or has_rally:
            deleted.append({"id": p.id, "partito": p.partito, "sintesi": stmt})
            db.add(AuditLog(
                event_type="cancellazione",
                entity_type="programma",
                entity_id=str(p.id),
                entity_name=f"{p.partito}: {p.macro_argomento}",
                old_value=stmt[:90] + "..." if len(stmt) > 90 else stmt,
                new_value=None,
                agent_responsible="QualityGatekeeperAgent",
                details=f"Cancellata proposta non conforme alle linee guida di policy: titolo di evento/comunicato stampa con dominio web o slogan non formalizzato ('{stmt}').",
                timestamp=datetime.datetime.utcnow()
            ))
            db.delete(p)
        elif val_stmt != stmt:
            cleaned.append({"id": p.id, "old": stmt, "new": val_stmt})
            p.dichiarazione_sintesi = val_stmt

    if deleted or cleaned:
        db.commit()

    return {
        "deleted_count": len(deleted),
        "deleted": deleted,
        "cleaned_count": len(cleaned),
        "cleaned": cleaned
    }

