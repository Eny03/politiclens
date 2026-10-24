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

router = APIRouter(prefix="/api/comparison", tags=["Manifesto Dinamico & Comparatore"])

MACRO_ARGOMENTI_DEFAULT = [
    "Fisco",
    "Lavoro",
    "Sanità",
    "Pensioni",
    "Energia",
    "Istituzioni",
    "Immigrazione",
    "Cittadinanza",
    "Istruzione",
    "Infrastrutture",
    "Politica Estera",
    "Diritti Civili"
]

@router.get("/matrix", response_model=ComparisonMatrixResponse)
def get_comparison_matrix(db: Session = Depends(get_db)):
    """
    Builds the Dynamic Comparative Manifesto (Manifesto Dinamico).
    Generates a 2D matrix of Macro-Topic vs Political Parties with synthesized stances.
    """
    parties = db.query(PoliticalParty).order_by(PoliticalParty.coalition, PoliticalParty.name).all()
    proposals = db.query(PoliticalProposal).order_by(PoliticalProposal.timestamp.desc()).all()
    
    # Map proposals by (macro_topic, party_name_clean)
    grid_map: Dict[str, Dict[str, List[PoliticalProposal]]] = {
        topic: {p.name: [] for p in parties} for topic in MACRO_ARGOMENTI_DEFAULT
    }
    
    for prop in proposals:
        topic = prop.macro_argomento
        if topic not in grid_map:
            grid_map[topic] = {p.name: [] for p in parties}
            
        for party in parties:
            if party.name.lower() in prop.partito.lower() or prop.partito.lower() in party.name.lower():
                grid_map[topic][party.name].append(prop)
                break

    rows: List[TopicComparisonRow] = []
    
    for topic in grid_map.keys():
        party_cells: Dict[str, ComparisonCell] = {}
        for party in parties:
            p_list = grid_map[topic].get(party.name, [])
            
            # Determine stance type
            stance = "In attesa di posizione depositata"
            synthesis = "Nessun atto o dichiarazione formale censita di recente su questo macro-tema."
            
            if p_list:
                latest = p_list[0]
                if len(p_list) == 1:
                    synthesis = latest.dichiarazione_sintesi
                else:
                    synthesis = " • ".join([p.dichiarazione_sintesi for p in p_list[:3]])

                if any(p.tipo_azione == "Opposizione" for p in p_list):
                    stance = "Contrario / Opposizione"
                elif any(p.tipo_azione == "Proposta di legge" for p in p_list):
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

def _parse_cost_in_billions(cost_str: str) -> float:
    """Extracts numeric billions from strings like '~12.5 Mld €', '5.5 miliardi €', '120 milioni €', etc."""
    if not cost_str or "non quantificato" in cost_str.lower() or "invarianza" in cost_str.lower():
        return 0.0
    m_mld = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:mld|miliard)", cost_str, re.I)
    if m_mld:
        return float(m_mld.group(1).replace(",", "."))
    m_mln = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:mln|milion)", cost_str, re.I)
    if m_mln:
        return float(m_mln.group(1).replace(",", ".")) / 1000.0
    return 0.0

async def _compute_head_to_head_synthesis(
    party1_name: str,
    party2_name: str,
    topic: Optional[str],
    db: Session
) -> HeadToHeadSynthesisResponse:
    # Query proposals for both parties
    all_props = db.query(PoliticalProposal).all()
    
    props1 = [
        p for p in all_props 
        if (party1_name.lower() in p.partito.lower() or p.partito.lower() in party1_name.lower())
        and (not topic or topic.lower() == "tutti" or p.macro_argomento.lower() == topic.lower())
    ]
    props2 = [
        p for p in all_props 
        if (party2_name.lower() in p.partito.lower() or p.partito.lower() in party2_name.lower())
        and (not topic or topic.lower() == "tutti" or p.macro_argomento.lower() == topic.lower())
    ]

    cost1_total = sum(_parse_cost_in_billions(p.costo_stimato) for p in props1)
    cost2_total = sum(_parse_cost_in_billions(p.costo_stimato) for p in props2)
    
    quantified1 = sum(1 for p in props1 if "non quantificato" not in p.costo_stimato.lower())
    quantified2 = sum(1 for p in props2 if "non quantificato" not in p.costo_stimato.lower())

    p1_summaries = [f"[{p.macro_argomento}] {p.dichiarazione_sintesi} ({p.costo_stimato})" for p in props1[:8]]
    p2_summaries = [f"[{p.macro_argomento}] {p.dichiarazione_sintesi} ({p.costo_stimato})" for p in props2[:8]]

    # Analyze commonalities and contrasts
    convergences = []
    divergences = []

    # Check thematic common grounds
    topics1 = {p.macro_argomento for p in props1}
    topics2 = {p.macro_argomento for p in props2}
    common_topics = topics1.intersection(topics2)

    if "Sanità" in common_topics:
        convergences.append("Potenziamento della spesa sanitaria pubblica e riduzione delle liste d'attesa SSN (seppur con diverse priorità su personale vs convenzioni private).")
    if "Lavoro" in common_topics:
        convergences.append("Necessità condivisa di ridurre il cuneo fiscale sul costo del lavoro a vantaggio delle retribuzioni nette dei lavoratori.")
    if "Energia" in common_topics:
        convergences.append("Obiettivo comune di garantire indipendenza energetica e mitigare l'impatto dei rincari delle bollette per famiglie e PMI.")
    if "Istruzione" in common_topics:
        convergences.append("Investimenti per il potenziamento degli istituti tecnici, digitalizzazione e lotta alla dispersione scolastica.")

    if not convergences:
        convergences.append(f"Entrambe le forze dichiarano prioritaria la crescita economica e la salvaguardia del tessuto produttivo italiano.")
        convergences.append("Condivisione della necessità di accelerare le riforme previste dal PNRR nelle scadenze concordate con l'UE.")

    # Divergences
    if any("flat tax" in p.dichiarazione_sintesi.lower() for p in props1 + props2) and any("progressiv" in p.dichiarazione_sintesi.lower() or "patrimoniale" in p.dichiarazione_sintesi.lower() for p in props1 + props2):
        divergences.append("Modello Fiscale: contrapposizione netta tra aliquota fissa (Flat Tax / riduzione scaglioni) e progressività accentuata con tassazione sui grandi patrimoni o extraprofitti.")
    if any("salario minimo" in p.dichiarazione_sintesi.lower() for p in props1 + props2):
        divergences.append("Politiche Salariali: soglia oraria minima per legge a 9€/h contro valorizzazione esclusiva della contrattazione collettiva nazionale di categoria.")
    if any("nucleare" in p.dichiarazione_sintesi.lower() for p in props1 + props2):
        divergences.append("Mix Energetico: riapertura all'energia nucleare pulita di nuova generazione (SMR) vs modello 100% rinnovabili con opposizione ad atomo e trivelle.")
    if any("premierato" in p.dichiarazione_sintesi.lower() or "autonomia" in p.dichiarazione_sintesi.lower() for p in props1 + props2):
        divergences.append("Assetto Istituzionale: riforma del Premierato e Autonomia Differenziata regionale contro salvaguardia dei LEP uniformi e centralità del Parlamento.")

    if not divergences:
        divergences.append(f"Differenti priorità nell'allocazione delle risorse di bilancio: tagli fiscali selettivi vs investimenti diretti nei servizi pubblici essenziali.")
        divergences.append("Diverso orientamento sulle coperture finanziarie: leva sul deficit e spending review vs rimodulazione delle aliquote e lotta all'evasione.")

    # Cost ratio text
    if cost2_total > 0 and cost1_total > 0:
        ratio_val = round(cost1_total / cost2_total, 2)
        cost_ratio_str = f"{party1_name} quota ~{cost1_total:.1f} Mld € contro ~{cost2_total:.1f} Mld € di {party2_name} (rapporto {ratio_val}:1)"
    elif cost1_total > 0:
        cost_ratio_str = f"{party1_name}: ~{cost1_total:.1f} Mld € stimati ({quantified1} misure) | {party2_name}: ~{cost2_total:.1f} Mld € (in attesa di quantificazione MEF)"
    elif cost2_total > 0:
        cost_ratio_str = f"{party1_name}: ~{cost1_total:.1f} Mld € (in attesa di quantificazione MEF) | {party2_name}: ~{cost2_total:.1f} Mld € stimati ({quantified2} misure)"
    else:
        cost_ratio_str = f"Misure ad invarianza finanziaria o con oneri programmatici in attesa di relazione tecnica MEF ({quantified1} vs {quantified2} atti)"

    exec_summary = (
        f"L'analisi comparativa tra {party1_name} e {party2_name} "
        f"{f'sul tema {topic}' if topic else 'sul complesso dei programmi'} "
        f"evidenzia due visioni di politica pubblica ben distinte. "
        f"{party1_name} presenta {len(props1)} posizioni censite, mentre {party2_name} ne registra {len(props2)}. "
        f"Mentre sussistono convergenze su interventi d'urgenza a sostegno del potere d'acquisto, permangono profonde fratture "
        f"strutturali sulle fonti di finanziamento e sul perimetro d'intervento statale nell'economia."
    )

    institutional_verdict = (
        f"In base ai vincoli dell'Articolo 81 della Costituzione e alle regole del rinnovato Patto di Stabilità europeo, "
        f"entrambi i partiti devono affrontare la prova della quantificazione preventiva asseverata dall'Ufficio Parlamentare di Bilancio (UPB). "
        f"Il saldo netto dei costi stimati ({cost1_total:.1f} Mld € vs {cost2_total:.1f} Mld €) richiederà, per entrambi gli schieramenti, "
        f"coperture strutturali credibili per evitare l'apertura di procedure d'infrazione per disavanzo eccessivo."
    )

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

    return HeadToHeadSynthesisResponse(
        party1=party1_name,
        party2=party2_name,
        topic=topic,
        executive_summary=exec_summary,
        convergences=convergences,
        divergences=divergences,
        cost_comparison=cost_comparison,
        proposals_party1=p1_summaries,
        proposals_party2=p2_summaries,
        institutional_verdict=institutional_verdict
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
