import re
import json
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import PoliticalProposal, PoliticalParty
from app.schemas import (
    ComparisonMatrixResponse,
    TopicComparisonRow,
    ComparisonCell,
    PoliticalPartySchema,
    PoliticalProposalDetail,
    HeadToHeadSynthesisRequest,
    HeadToHeadSynthesisResponse
)
from app.ai.llm_provider import llm_provider
from app.ai.extractor import normalize_macro_topic

router = APIRouter(prefix="/api/comparison", tags=["Manifesto Dinamico & Comparatore"])

MACRO_ARGOMENTI_DEFAULT = [
    "Fisco",
    "Lavoro",
    "Sanità",
    "Pensioni",
    "Energia",
    "Istituzioni",
    "Immigrazione",
    "Istruzione",
    "Infrastrutture",
    "Politica Estera",
    "Diritti Civili"
]


@router.get("/matrix", response_model=ComparisonMatrixResponse)
def get_comparison_matrix(db: Session = Depends(get_db)):
    """
    Builds the Dynamic Comparative Manifesto (Manifesto Dinamico).
    Generates a clean 2D matrix of the 11 canonical Macro-Topics vs Political Parties.
    """
    parties = db.query(PoliticalParty).order_by(PoliticalParty.poll_percentage.desc(), PoliticalParty.name).all()
    proposals = db.query(PoliticalProposal).order_by(PoliticalProposal.timestamp.desc()).all()

    party_by_id = {p.id: p for p in parties}
    party_by_name_low = {p.name.lower(): p for p in parties}

    grid_map: Dict[str, Dict[str, List[PoliticalProposal]]] = {
        topic: {p.name: [] for p in parties} for topic in MACRO_ARGOMENTI_DEFAULT
    }

    for prop in proposals:
        topic = normalize_macro_topic(prop.macro_argomento, prop.dichiarazione_sintesi)
        if topic not in grid_map:
            grid_map[topic] = {p.name: [] for p in parties}

        matched_party = party_by_id.get(prop.party_id) or party_by_name_low.get((prop.partito or "").lower())
        if not matched_party:
            for party in parties:
                if party.name.lower() == (prop.partito or "").lower():
                    matched_party = party
                    break
        if matched_party:
            grid_map[topic][matched_party.name].append(prop)

    rows: List[TopicComparisonRow] = []

    for topic in grid_map.keys():
        party_cells: Dict[str, ComparisonCell] = {}
        for party in parties:
            p_list = grid_map[topic].get(party.name, [])

            stance = "In attesa di posizione depositata"
            synthesis = "Nessun atto o dichiarazione formale censita di recente su questo macro-tema."

            if p_list:
                latest = p_list[0]
                if len(p_list) == 1:
                    synthesis = latest.dichiarazione_sintesi
                else:
                    synthesis = " • ".join([p.dichiarazione_sintesi for p in p_list[:3]])

                if all(p.tipo_azione == "Opposizione" for p in p_list):
                    stance = "Contrario / Opposizione"
                elif any(p.tipo_azione == "Opposizione" for p in p_list) and len(p_list) == 1:
                    stance = "Contrario / Opposizione"
                elif any("legge" in (p.tipo_azione or "").lower() or "ddl" in (p.tipo_azione or "").lower() for p in p_list):
                    stance = "1 proposta / Riforma" if len(p_list) == 1 else f"{len(p_list)} proposte / Riforme"
                else:
                    stance = "1 posizione censita" if len(p_list) == 1 else f"{len(p_list)} posizioni censite"

            details = [PoliticalProposalDetail.model_validate(p) for p in p_list]
            for d in details:
                d.party_color = party.color

            party_cells[party.name] = ComparisonCell(
                partito=party.name,
                party_color=party.color,
                proposals=details,
                sintesi_posizione=synthesis,
                stance_type=stance
            )

        rows.append(TopicComparisonRow(
            macro_argomento=topic,
            argomento_dettaglio=f"Quadro comparativo delle posizioni sul tema {topic}",
            parties=party_cells
        ))

    return ComparisonMatrixResponse(
        macro_argomenti=list(grid_map.keys()),
        partiti=[PoliticalPartySchema.model_validate(p) for p in parties],
        matrix=rows
    )


def _parse_cost_in_billions(cost_str: Optional[str]) -> float:
    """
    Extracts numeric spending cost in billions of € from cost strings.
    Explicitly returns 0.0 for neutral/invarianza, savings ('risparmio'), and tax revenue ('gettito', 'saldo positivo').
    Accurately computes midpoints for ranges (e.g. '1.5 - 2.5 miliardi' -> 2.0).
    """
    if not cost_str:
        return 0.0
    cs_low = cost_str.lower()
    if any(w in cs_low for w in [
        "non quantificat", "invarianza", "saldo neutro", "risparmio", "gettito",
        "saldo positivo", "zero costi", "costi nulli", "incalcolabile", "non quantificabile"
    ]):
        return 0.0
    m_b_range = re.search(r"(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:mld|miliard)", cs_low)
    if m_b_range:
        return (float(m_b_range.group(1).replace(",", ".")) + float(m_b_range.group(2).replace(",", "."))) / 2.0
    m_mld = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:mld|miliard)", cs_low)
    if m_mld:
        return float(m_mld.group(1).replace(",", "."))
    m_m_range = re.search(r"(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:mln|milion)", cs_low)
    if m_m_range:
        return ((float(m_m_range.group(1).replace(",", ".")) + float(m_m_range.group(2).replace(",", "."))) / 2.0) / 1000.0
    m_mln = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:mln|milion)", cs_low)
    if m_mln:
        return float(m_mln.group(1).replace(",", ".")) / 1000.0
    return 0.0


def _detect_party_stance(props: List[PoliticalProposal], positive_kws: List[str], negative_kws: List[str]) -> Optional[str]:
    """
    Determines a party's actual stance ('pro', 'contra', or None) on a specific policy theme
    by inspecting ONLY that party's proposals (preventing false divergences between allies!).
    """
    for p in props:
        s = (p.dichiarazione_sintesi or "").lower()
        act = (p.tipo_azione or "").lower()
        is_neg_text = act == "opposizione" or any(w in s for w in ["contrariet", "opposizione", "contrario", "stop ", "blocco ", "cancellazione", "abrogazione", "no a", "no al", "moratoria"])
        if any(kw in s for kw in negative_kws):
            return "contra"
        if any(kw in s for kw in positive_kws):
            return "contra" if is_neg_text else "pro"
    return None


async def _compute_head_to_head_synthesis(
    party1_name: str,
    party2_name: str,
    topic: Optional[str],
    db: Session
) -> HeadToHeadSynthesisResponse:
    p1_obj = db.query(PoliticalParty).filter(PoliticalParty.name.ilike(party1_name)).first()
    p2_obj = db.query(PoliticalParty).filter(PoliticalParty.name.ilike(party2_name)).first()

    all_props = db.query(PoliticalProposal).order_by(PoliticalProposal.timestamp.desc()).all()

    def _matches_party(prop: PoliticalProposal, target_name: str, target_obj: Optional[PoliticalParty]) -> bool:
        if target_obj and prop.party_id == target_obj.id:
            return True
        return prop.partito.lower() == target_name.lower()

    norm_topic = normalize_macro_topic(topic) if (topic and topic.lower() != "tutti") else None

    props1 = [
        p for p in all_props
        if _matches_party(p, party1_name, p1_obj)
        and (not norm_topic or normalize_macro_topic(p.macro_argomento, p.dichiarazione_sintesi).lower() == norm_topic.lower())
    ]
    props2 = [
        p for p in all_props
        if _matches_party(p, party2_name, p2_obj)
        and (not norm_topic or normalize_macro_topic(p.macro_argomento, p.dichiarazione_sintesi).lower() == norm_topic.lower())
    ]

    cost1_total = sum(_parse_cost_in_billions(p.costo_stimato) for p in props1)
    cost2_total = sum(_parse_cost_in_billions(p.costo_stimato) for p in props2)

    quantified1 = sum(1 for p in props1 if _parse_cost_in_billions(p.costo_stimato) > 0)
    quantified2 = sum(1 for p in props2 if _parse_cost_in_billions(p.costo_stimato) > 0)

    p1_summaries = [f"[{p.macro_argomento}] {p.dichiarazione_sintesi} ({p.costo_stimato})" for p in props1[:8]]
    p2_summaries = [f"[{p.macro_argomento}] {p.dichiarazione_sintesi} ({p.costo_stimato})" for p in props2[:8]]

    # True stance-aware convergence & divergence analysis (checks Party 1 vs Party 2 independently!)
    convergences: List[str] = []
    divergences: List[str] = []

    THEMES = [
        (
            "Salario Minimo",
            ["salario minimo legale", "salario minimo a 9", "salario minimo a 10", "salario minimo fissato"],
            ["alternativa al salario minimo", "contrattazione aziendale", "contrattazione collettiva di settore", "abolizione dei contratti"],
            "Entrambe le forze convergono sul modello di determinazione salariale (entrambe favorevoli o entrambe orientate alla contrattazione collettiva).",
            "Politiche Salariali: divergenza netta tra introduzione del salario minimo legale orario e rafforzamento esclusivo della contrattazione collettiva/aziendale."
        ),
        (
            "Nucleare Civile (SMR)",
            ["nucleare", "smr", "reattori modulari", "microreattori"],
            ["contrarietà al riavvio del nucleare", "moratoria totale sul nucleare", "100% energie rinnovabili", "uscita integrale"],
            "Energia & Mix Elettrico: convergenza strategica sul ruolo dell'energia nucleare di nuova generazione (SMR) / transizione decarbonizzata.",
            "Mix Energetico: contrapposizione tra ritorno al nucleare civile di quarta generazione (SMR) e modello basato esclusivamente su fonti rinnovabili."
        ),
        (
            "Fisco & Patrimoniale",
            ["flat tax", "riduzione del secondo scaglione", "taglio irpef", "contrarietà a qualsiasi forma di imposta patrimoniale"],
            ["imposta patrimoniale", "imposta straordinaria e progressiva sui patrimoni", "grandi patrimoni", "next generation tax", "extraprofitti"],
            "Orientamento Fiscale: visione affine sul livello di pressione fiscale e sugli strumenti tributari prioritari.",
            "Modello Fiscale: divergenza strutturale tra riduzione delle aliquote/Flat Tax e maggiore progressività con imposte sui grandi patrimoni o extraprofitti."
        ),
        (
            "Ponte sullo Stretto",
            ["realizzazione del ponte sullo stretto", "avanzamento del cantiere del ponte"],
            ["stop immediato al ponte", "cancellazione definitiva", "blocco definitivo del progetto del ponte"],
            "Grandi Infrastrutture: convergenza sull'orientamento relativo al Ponte sullo Stretto di Messina e alle priorità infrastrutturali.",
            "Grandi Opere: contrapposizione netta sulla realizzazione del Ponte sullo Stretto rispetto al dirottamento dei fondi su ferrovie regionali e rete idrica."
        ),
        (
            "Autonomia Differenziata & Premierato",
            ["attuazione del regionalismo", "legge sull'autonomia differenziata", "riforma costituzionale del premierato", "sindaco d'italia"],
            ["opposizione all'autonomia", "abrogazione immediata dell'autonomia", "opposizione alla riforma costituzionale del premierato", "referendum abrogativo"],
            "Assetto Istituzionale: allineamento sugli indirizzi di riforma costituzionale e del regionalismo.",
            "Assetto Istituzionale: frattura tra riforma del Premierato / Autonomia Differenziata e difesa della centralità parlamentare e dei LEP uniformi."
        ),
        (
            "Difesa & Politica Estera",
            ["nato", "alleanza atlantica", "difesa comune europea", "sostegno incondizionato all'ucraina", "spesa militare nato al 2%"],
            ["uscita immediata dell'italia dalla nato", "uscita dell'italia dalla nato", "stop all'invio di armi", "blocco dell'invio di ulteriori armamenti", "cessate il fuoco immediato"],
            "Politica Estera & Sicurezza: posizionamento convergente sul quadro delle alleanze internazionali e della difesa.",
            "Politica Estera & Difesa: divergenza netta tra aderenza agli impegni NATO/UE (target 2% PIL) e richiesta di stop alle forniture militari o neutralità."
        ),
        (
            "Diritti Civili & Cittadinanza",
            ["ius scholae", "ius soli", "fine vita", "matrimonio egualitario", "legalizzazione della cannabis"],
            ["tutela della famiglia naturale", "contrarietà alla modifica della legge sulla cittadinanza", "revoca della cittadinanza", "reato universale"],
            "Diritti Civili: sensibilità convergente sul perimetro dei diritti individuali e delle norme sulla cittadinanza.",
            "Diritti Civili & Cittadinanza: visioni contrapposte su riforma della cittadinanza (Ius Scholae/Soli), fine vita e politiche familiari."
        )
    ]

    matched_axes = 0
    converged_axes = 0
    for _theme_name, pro_kws, contra_kws, conv_msg, div_msg in THEMES:
        s1 = _detect_party_stance(props1, pro_kws, contra_kws)
        s2 = _detect_party_stance(props2, pro_kws, contra_kws)
        if s1 and s2:
            matched_axes += 1
            if s1 == s2:
                converged_axes += 1
                convergences.append(conv_msg)
            else:
                divergences.append(div_msg)

    common_topics = {p.macro_argomento for p in props1} & {p.macro_argomento for p in props2}
    if not convergences:
        if "Sanità" in common_topics:
            convergences.append("Entrambe le forze riconoscono la priorità di abbattere le liste d'attesa e potenziare i presidi del Servizio Sanitario Nazionale (con strumenti attuativi differenti).")
        if "Istruzione" in common_topics:
            convergences.append("Attenzione condivisa verso l'ammodernamento della filiera educativa, la formazione tecnica e il sostegno agli studenti.")
        if not convergences:
            convergences.append(f"Entrambe le forze presentano proposte concrete sui temi prioritari dell'agenda parlamentare ({', '.join(sorted(common_topics)[:4]) or 'riforme nazionali'}).")

    if not divergences:
        same_coal = p1_obj and p2_obj and p1_obj.coalition == p2_obj.coalition
        if same_coal:
            divergences.append(f"Pur appartenendo alla stessa area ({p1_obj.coalition}), {party1_name} e {party2_name} differiscono per accentuazione tematica e priorità di spesa sui singoli capitoli di bilancio.")
        else:
            divergences.append("Differenti priorità nell'allocazione delle risorse pubbliche e nella scelta degli strumenti fiscali e normativi.")

    # Cost ratio text
    if cost2_total > 0 and cost1_total > 0:
        ratio_val = round(cost1_total / cost2_total, 2)
        cost_ratio_str = f"{party1_name} stima ~{cost1_total:.1f} Mld € ({quantified1} atti con onere) vs ~{cost2_total:.1f} Mld € di {party2_name} ({quantified2} atti) • rapporto {ratio_val}:1"
    elif cost1_total > 0:
        cost_ratio_str = f"{party1_name}: ~{cost1_total:.1f} Mld € stimati ({quantified1} atti) | {party2_name}: misure prevalenti a saldo neutro o in attesa di quantificazione"
    elif cost2_total > 0:
        cost_ratio_str = f"{party1_name}: misure prevalenti a saldo neutro o in attesa di quantificazione | {party2_name}: ~{cost2_total:.1f} Mld € stimati ({quantified2} atti)"
    else:
        cost_ratio_str = "Misure prevalenti ad invarianza finanziaria, a saldo neutro o con risparmio netto per l'Erario"

    same_coalition = bool(p1_obj and p2_obj and p1_obj.coalition.split("/")[0].strip().lower() == p2_obj.coalition.split("/")[0].strip().lower())
    relation_desc = (
        f"un'affinità di area ({p1_obj.coalition}) accompagnata da distinte priorità programmatiche"
        if same_coalition else
        "due visioni di politica pubblica ben distinte"
    )
    exec_summary = (
        f"L'analisi comparativa tra {party1_name} e {party2_name} "
        f"{f'sul tema {norm_topic}' if norm_topic else 'sul complesso dei programmi'} "
        f"evidenzia {relation_desc}. "
        f"{party1_name} presenta {len(props1)} posizioni censite (oneri di spesa stimati: ~{cost1_total:.1f} Mld €), "
        f"mentre {party2_name} ne registra {len(props2)} (~{cost2_total:.1f} Mld €)."
    )

    institutional_verdict = (
        f"In base all'Articolo 81 della Costituzione e alle regole del Patto di Stabilità europeo, "
        f"le misure a maggiore onere ({cost1_total:.1f} Mld € vs {cost2_total:.1f} Mld €) richiedono "
        f"coperture strutturali certificate dall'Ufficio Parlamentare di Bilancio (UPB) e dalla Ragioneria Generale dello Stato."
    )

    # Optional LLM enrichment when an external/local LLM provider is active
    provider_info = await llm_provider.get_active_provider_info()
    if provider_info["provider"] != "deterministic" and (props1 or props2):
        try:
            prompt = (
                f"Confronta in modo neutrale e rigoroso {party1_name} e {party2_name}"
                f"{f' sul tema {norm_topic}' if norm_topic else ''}.\n"
                f"PROPOSTE {party1_name}:\n" + "\n".join(p1_summaries[:6]) + "\n\n"
                f"PROPOSTE {party2_name}:\n" + "\n".join(p2_summaries[:6]) + "\n\n"
                "Restituisci ESCLUSIVAMENTE un oggetto JSON con chiavi: "
                "executive_summary (stringa), convergences (lista 2-3 stringhe), divergences (lista 2-3 stringhe), institutional_verdict (stringa)."
            )
            raw_ai, used_p = await llm_provider.generate_chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="Sei PoliticLens AI, analista parlamentare neutrale. Rispondi solo con JSON valido in italiano.",
                temperature=0.15,
                format_json=True
            )
            if used_p != "deterministic" and raw_ai:
                m_json = re.search(r"\{.*\}", raw_ai, re.DOTALL)
                if m_json:
                    parsed = json.loads(m_json.group(0))
                    if isinstance(parsed.get("executive_summary"), str) and len(parsed["executive_summary"]) > 30:
                        exec_summary = parsed["executive_summary"]
                    if isinstance(parsed.get("convergences"), list) and parsed["convergences"]:
                        convergences = [str(x) for x in parsed["convergences"][:4]]
                    if isinstance(parsed.get("divergences"), list) and parsed["divergences"]:
                        divergences = [str(x) for x in parsed["divergences"][:4]]
                    if isinstance(parsed.get("institutional_verdict"), str) and len(parsed["institutional_verdict"]) > 30:
                        institutional_verdict = parsed["institutional_verdict"]
        except Exception as e:
            print(f"[Comparison] LLM synthesis notice (using deterministic): {e}")

    cost_comparison = {
        "party1_name": party1_name,
        "party1_total_mld": round(cost1_total, 2),
        "party1_quantified_count": quantified1,
        "party2_name": party2_name,
        "party2_total_mld": round(cost2_total, 2),
        "party2_quantified_count": quantified2,
        "ratio_summary": cost_ratio_str,
        "compliance_mef": "Entrambi i programmi richiedono clausole di salvaguardia finanziaria ex L. 196/2009."
    }

    def _build_party_metrics(p_obj: Optional[PoliticalParty], p_name: str, p_list: List[PoliticalProposal]) -> Dict[str, Any]:
        verified = sum(1 for pr in p_list if (pr.fact_check_status or "").lower() in ("verificato", "parzialmente verificato"))
        critical = sum(1 for pr in p_list if any(k in (pr.fact_check_status or "").lower() for k in ("esagerat", "inattuabile", "fake")))
        return {
            "name": p_obj.name if p_obj else p_name,
            "code": p_obj.code if p_obj else p_name[:4].upper(),
            "color": p_obj.color if p_obj else "#3b82f6",
            "coalition": p_obj.coalition if p_obj else "Altro",
            "leader": p_obj.leader if p_obj else None,
            "poll_percentage": round(float(p_obj.poll_percentage or 0.0), 1) if p_obj else 0.0,
            "truthfulness_score": round(float(p_obj.truthfulness_score or 75.0), 1) if p_obj else 75.0,
            "financial_reliability_score": round(float(p_obj.financial_reliability_score or 70.0), 1) if p_obj else 70.0,
            "proposals_count": len(p_list),
            "verified_count": verified,
            "critical_count": critical,
        }

    # Alignment index (0-100%) grounded directly on shared programmatic axes
    if matched_axes > 0:
        alignment_index = int(round((converged_axes / matched_axes) * 100))
    else:
        alignment_index = 68 if same_coalition else 35

    return HeadToHeadSynthesisResponse(
        party1=party1_name,
        party2=party2_name,
        topic=norm_topic or topic,
        executive_summary=exec_summary,
        convergences=convergences,
        divergences=divergences,
        cost_comparison=cost_comparison,
        proposals_party1=p1_summaries,
        proposals_party2=p2_summaries,
        institutional_verdict=institutional_verdict,
        party1_metrics=_build_party_metrics(p1_obj, party1_name, props1),
        party2_metrics=_build_party_metrics(p2_obj, party2_name, props2),
        alignment_index=alignment_index,
    )


@router.post("/head-to-head-synthesis", response_model=HeadToHeadSynthesisResponse)
async def get_head_to_head_synthesis_post(req: HeadToHeadSynthesisRequest, db: Session = Depends(get_db)):
    """AI Head-to-Head synthesis between two political forces."""
    return await _compute_head_to_head_synthesis(req.party1, req.party2, req.topic, db)


@router.get("/head-to-head-synthesis", response_model=HeadToHeadSynthesisResponse)
async def get_head_to_head_synthesis_get(
    party1: str = Query(..., description="Primo partito da confrontare"),
    party2: str = Query(..., description="Secondo partito da confrontare"),
    topic: Optional[str] = Query(None, description="Macro-argomento opzionale"),
    db: Session = Depends(get_db)
):
    """AI Head-to-Head synthesis (GET query method)."""
    return await _compute_head_to_head_synthesis(party1, party2, topic, db)
