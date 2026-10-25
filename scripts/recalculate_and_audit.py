import os
import sys
import json
import datetime
from sqlalchemy.orm import Session

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database import SessionLocal, engine
from app.models import PoliticalParty, PoliticalProposal, AuditLog
from app.ai.fiscal_calculator import calculate_fiscal_impact_and_coverage, calculate_financial_coverage_percentage
from app.ai.fact_checker import analyze_feasibility_and_factcheck, calculate_proposal_truthfulness_score
from app.ingestion.dossier_generator import update_all_party_dossiers
from app.ingestion.poll_tracker import PollTrackerAgent

def audit_and_recalculate_all():
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE political_proposals ADD COLUMN truth_score FLOAT"))
            conn.commit()
    except Exception:
        pass
    db: Session = SessionLocal()
    try:
        print("[AuditEngine] Avvio verifica analitica di tutte le proposte nel database...")
        proposals = db.query(PoliticalProposal).all()
        print(f"  Totale proposte da verificare: {len(proposals)}")
        
        updated_proposals = 0
        for p in proposals:
            sintesi = (p.dichiarazione_sintesi or "").strip()
            costo = (p.costo_stimato or "").strip()
            coperture = (p.coperture_dichiarate or "").strip()
            
            # Controlla se la proposta necessita di quantificazione o copertura asseverata
            needs_audit = (
                not costo or
                costo.lower() in ["non quantificato", "non quantificata", "da definire"] or
                not coperture or
                coperture.lower() in ["non specificate", "non specificata", "da definire", "nessuna", "none", ""] or
                not p.fattibilita_finanziaria or
                len(coperture) < 15
            )
            
            if needs_audit:
                f_calc = calculate_fiscal_impact_and_coverage(
                    partito=p.partito,
                    macro_argomento=p.macro_argomento,
                    sintesi=sintesi,
                    costo_stimato=costo,
                    coperture_dichiarate=coperture
                )
                p.costo_stimato = f_calc["costo_stimato"]
                p.coperture_dichiarate = f_calc["coperture_dichiarate"]
                p.fattibilita_finanziaria = f_calc["fattibilita_finanziaria"]
                updated_proposals += 1

            # Controllo di accuratezza fattuale indipendente dalle coperture economiche con voto al 5%
            feas_data = analyze_feasibility_and_factcheck(
                partito=p.partito,
                macro_argomento=p.macro_argomento,
                sintesi=sintesi,
                costo_stimato=p.costo_stimato,
                coperture=p.coperture_dichiarate,
                raw_text=p.raw_text or ""
            )
            feas, st, mot, src = feas_data[:4]
            t_vote = feas_data[4] if len(feas_data) > 4 else 75.0
            p.fact_check_status = st
            p.fact_check_motivazione = mot
            p.fact_check_fonte = src
            p.truth_score = t_vote
            updated_proposals += 1

        db.commit()
        print(f"  Aggiornate e armonizzate {updated_proposals} proposte con parametri MEF/ISTAT/UPB/IPCC e voto di veridicità a salti del 5%.")

        # 2. Ricalcolo sondaggi multi-istituto guidato dall'AI Poll Tracker
        print("\n[AuditEngine] Aggregazione sondaggi multi-istituto (SWG, Ipsos, Tecnè, BiDiMedia, Noto) con Futuro Nazionale al ~6.0%...")
        poll_agent = PollTrackerAgent(db)
        poll_results = poll_agent.update_all_party_polls()
        print(f"  Aggiornati sondaggi per {len(poll_results)} partiti.")

        # 3. Ricalcolo metriche analitiche Veridicità e Coperture per tutti i 22 partiti
        print("\n[AuditEngine] Ricalcolo metriche analitiche Veridicità (fattuale) e Coperture (matematica %)...")
        parties = db.query(PoliticalParty).all()
        
        for party in parties:
            p_props = db.query(PoliticalProposal).filter(
                (PoliticalProposal.party_id == party.id) | (PoliticalProposal.partito.ilike(f"%{party.name}%"))
            ).all()
            total_n = len(p_props)
            if total_n > 0:
                t_score = round(sum((pr.truth_score if hasattr(pr, 'truth_score') and pr.truth_score is not None else calculate_proposal_truthfulness_score(pr.fact_check_status)) for pr in p_props) / total_n, 1)
                c_score = round(sum(calculate_financial_coverage_percentage(pr.costo_stimato, pr.coperture_dichiarate, pr.dichiarazione_sintesi) for pr in p_props) / total_n, 1)
                party.truthfulness_score = t_score
                party.financial_reliability_score = c_score
            else:
                party.truthfulness_score = 75.0
                party.financial_reliability_score = 70.0
                
        db.commit()

        # 3. Rigenerazione Dossier AI per tutti i partiti
        print("[AuditEngine] Rigenerazione Dossier AI e SWOT istituzionali...")
        update_all_party_dossiers(db)
        db.commit()

        # 4. Aggiornamento seed_data.py
        print("[AuditEngine] Allineamento di backend/app/data/seed_data.py...")
        from app.data.seed_data import PARTIES_SEED, PROPOSALS_SEED
        
        parties_db_map = {p.code: p for p in db.query(PoliticalParty).all()}
        updated_parties_seed = []
        for p_seed in PARTIES_SEED:
            code = p_seed["code"]
            db_p = parties_db_map.get(code)
            p_copy = dict(p_seed)
            if db_p:
                p_copy["poll_percentage"] = db_p.poll_percentage
                p_copy["poll_trend"] = db_p.poll_trend
                p_copy["poll_sources"] = db_p.poll_sources
                p_copy["truthfulness_score"] = db_p.truthfulness_score
                p_copy["financial_reliability_score"] = db_p.financial_reliability_score
                if db_p.dossier_ai:
                    p_copy["dossier_ai"] = db_p.dossier_ai
            updated_parties_seed.append(p_copy)
            
        # Update proposals seed with cleaned values
        all_proposals_db = db.query(PoliticalProposal).all()
        db_prop_map = {
            (pr.partito.strip(), pr.macro_argomento.strip(), pr.dichiarazione_sintesi.strip()[:35]): pr
            for pr in all_proposals_db
        }
        
        updated_proposals_seed = []
        for prop in PROPOSALS_SEED:
            key = (prop["partito"].strip(), prop["macro_argomento"].strip(), prop["dichiarazione_sintesi"].strip()[:35])
            p_obj = db_prop_map.get(key)
            prop_copy = dict(prop)
            if p_obj:
                prop_copy["costo_stimato"] = p_obj.costo_stimato
                prop_copy["coperture_dichiarate"] = p_obj.coperture_dichiarate
                prop_copy["fattibilita_finanziaria"] = p_obj.fattibilita_finanziaria
                prop_copy["fact_check_status"] = p_obj.fact_check_status
                prop_copy["fact_check_motivazione"] = p_obj.fact_check_motivazione
                prop_copy["fact_check_fonte"] = p_obj.fact_check_fonte
                prop_copy["truth_score"] = getattr(p_obj, "truth_score", 75.0)
            updated_proposals_seed.append(prop_copy)

        seed_data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "data", "seed_data.py"))
        new_content = "import datetime\n\nPARTIES_SEED = " + json.dumps(updated_parties_seed, indent=2, ensure_ascii=False) + "\n\nPROPOSALS_SEED = " + json.dumps(updated_proposals_seed, indent=2, ensure_ascii=False) + "\n"
        with open(seed_data_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("  File seed_data.py aggiornato con successo.")

        # 5. Stampa riepilogo verificato
        print("\n" + "="*80)
        print("RIEPILOGO FINALE VERIFICATO: 22 PARTITI (ISTAT / MEF / UPB 2026)")
        print("="*80)
        final_parties = db.query(PoliticalParty).order_by(PoliticalParty.poll_percentage.desc()).all()
        for p in final_parties:
            cnt = db.query(PoliticalProposal).filter(
                (PoliticalProposal.party_id == p.id) | (PoliticalProposal.partito.ilike(f"%{p.name}%"))
            ).count()
            print(f"  {p.poll_percentage:4.1f}% | {p.code:6} | {p.name:<30} | Veridicità: {p.truthfulness_score:5.1f}% | Coperture: {p.financial_reliability_score:5.1f}% | Proposte: {cnt:2d}")
        print("="*80)

    except Exception as e:
        db.rollback()
        print(f"[AuditEngine] Errore: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    audit_and_recalculate_all()
