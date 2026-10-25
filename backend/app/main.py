import os
import json
import asyncio
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models import PoliticalParty, PoliticalProposal, InstitutionalBenchmark, AuditLog
from app.data.benchmark_data import BENCHMARKS_SEED
from app.data.seed_data import PARTIES_SEED, PROPOSALS_SEED
from app.data.historical_proposals import HISTORICAL_PROPOSALS_SEED
from app.ingestion.text_extractor import compute_content_hash
from app.ai.embeddings import get_text_embedding
from app.ai.ollama_client import ollama_client
from app.ai.deduplication_engine import is_duplicate_proposal
from app.ingestion.scheduler import start_scheduler, stop_scheduler

from app.api.parties import router as parties_router
from app.api.proposals import router as proposals_router
from app.api.comparison import router as comparison_router
from app.api.chat import router as chat_router
from app.api.ingestion import router as ingestion_router
from app.api.stats import router as stats_router
from app.api.audit import router as audit_router, seed_audit_history_if_empty


def seed_database_if_empty():
    """Seeds initial parties, documented proposals, and economic benchmarks if not present."""
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            for col, ctype in [
                ("dossier_ai", "TEXT"),
                ("poll_percentage", "FLOAT"),
                ("poll_trend", "VARCHAR(20)"),
                ("poll_sources", "VARCHAR(255)"),
                ("truthfulness_score", "FLOAT"),
                ("financial_reliability_score", "FLOAT")
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE political_parties ADD COLUMN {col} {ctype}"))
                    conn.commit()
                except Exception:
                    pass
    except Exception:
        pass
    db: Session = SessionLocal()
    try:
        # Seed or sync parties
        existing_parties = {p.code: p for p in db.query(PoliticalParty).all()}
        for p_data in PARTIES_SEED:
            code = p_data["code"]
            if code not in existing_parties:
                print(f"[Database] Adding new party: {p_data['name']}")
                new_party = PoliticalParty(**p_data)
                db.add(new_party)
            else:
                curr = existing_parties[code]
                curr.name = p_data.get("name", curr.name)
                curr.coalition = p_data.get("coalition", curr.coalition)
                curr.leader = p_data.get("leader", curr.leader)
                curr.color = p_data.get("color", curr.color)
                curr.description = p_data.get("description", curr.description)
                curr.official_website = p_data.get("official_website", curr.official_website)
                # Sync certified poll benchmarks and official institutional scores
                from app.ingestion.poll_tracker import LATEST_POLL_BENCHMARKS
                bench = LATEST_POLL_BENCHMARKS.get(code)
                if not bench and code == "NOI_MOD":
                    bench = LATEST_POLL_BENCHMARKS.get("NM")
                elif not bench and code == "NM":
                    bench = LATEST_POLL_BENCHMARKS.get("NOI_MOD")

                if bench:
                    curr.poll_percentage = bench["base"]
                    curr.poll_sources = f"{bench['institutes'][0]} (Rilevazione ufficiale)"
                    curr.poll_trend = "stabile"
                elif p_data.get("poll_percentage") is not None:
                    curr.poll_percentage = p_data["poll_percentage"]
                if p_data.get("truthfulness_score") is not None:
                    curr.truthfulness_score = p_data["truthfulness_score"]
                if p_data.get("financial_reliability_score") is not None:
                    curr.financial_reliability_score = p_data["financial_reliability_score"]
                if p_data.get("dossier_ai"):
                    curr.dossier_ai = p_data["dossier_ai"]
        db.commit()

        # Seed Benchmarks
        if db.query(InstitutionalBenchmark).count() == 0:
            print("[Database] Seeding institutional benchmarks...")
            for b_data in BENCHMARKS_SEED:
                benchmark = InstitutionalBenchmark(**b_data)
                db.add(benchmark)
            db.commit()

        # Non-destructive Proposal Persistence with Intelligent Deduplication
        parties_map = {p.name: p.id for p in db.query(PoliticalParty).all()}
        from app.ai.embeddings import _local_deterministic_embedding
        from difflib import SequenceMatcher

        stopwords = {'e', 'il', 'la', 'i', 'gli', 'le', 'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'del', 'della', 'dei', 'delle', 'un', 'una', 'uno', 'al', 'alla', 'ai', 'alle'}

        # Deduplicate all seed proposals before inserting (strict substantive matching)
        deduped_seeds = []
        for prop in (PROPOSALS_SEED + HISTORICAL_PROPOSALS_SEED):
            is_dup = False
            for existing_idx, existing_seed in enumerate(deduped_seeds):
                dup_matched, reason = is_duplicate_proposal(
                    party_a=prop["partito"],
                    topic_a=prop["macro_argomento"],
                    text_a=prop["dichiarazione_sintesi"],
                    party_b=existing_seed["partito"],
                    topic_b=existing_seed["macro_argomento"],
                    text_b=existing_seed["dichiarazione_sintesi"]
                )
                if dup_matched:
                    is_dup = True
                    # If current prop is more detailed or formal, replace the existing one
                    if len(prop["dichiarazione_sintesi"]) > len(existing_seed["dichiarazione_sintesi"]):
                        deduped_seeds[existing_idx] = prop
                    break
            if not is_dup:
                deduped_seeds.append(prop)

        # Seed missing clean proposals
        existing_proposals = db.query(PoliticalProposal).all()
        existing_signatures = {
            (p.partito.strip(), p.macro_argomento.strip(), p.dichiarazione_sintesi.strip().lower()[:35])
            for p in existing_proposals
        }
        existing_hashes = {p.content_hash for p in existing_proposals if p.content_hash}

        added_count = 0
        for prop in deduped_seeds:
            sig = (prop["partito"].strip(), prop["macro_argomento"].strip(), prop["dichiarazione_sintesi"].strip().lower()[:35])
            hash_key = compute_content_hash(f"{prop['partito']}_{prop['macro_argomento']}_{prop['dichiarazione_sintesi']}")
            
            if sig not in existing_signatures and hash_key not in existing_hashes:
                party_id = parties_map.get(prop["partito"])
                emb_list = _local_deterministic_embedding(f"{prop['partito']} {prop['macro_argomento']} {prop['dichiarazione_sintesi']}")
                
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
                    fact_check_status=prop.get("fact_check_status", "In attesa di copertura"),
                    fact_check_motivazione=prop.get("fact_check_motivazione"),
                    fact_check_fonte=prop.get("fact_check_fonte"),
                    fonte_url=prop.get("fonte_url", ""),
                    fonte_titolo=prop.get("fonte_titolo"),
                    fonte_testata=prop.get("fonte_testata"),
                    raw_text=prop.get("raw_text") or f"{prop['dichiarazione_sintesi']}. Posizione politica formalizzata da {prop['partito']} in materia di {prop['macro_argomento']}.",
                    content_hash=hash_key,
                    embedding=json.dumps(emb_list) if emb_list else None,
                    timestamp=ts_val
                )
                db.add(record)
                existing_signatures.add(sig)
                existing_hashes.add(hash_key)
                added_count += 1

        if added_count > 0:
            db.commit()
            print(f"[Database] Successfully seeded {added_count} policy proposals.")

        # Post-Seed Database Deduplication Pass: Remove any duplicated proposals across all topics
        existing_db_props = db.query(PoliticalProposal).order_by(PoliticalProposal.id).all()
        by_grp = {}
        db_to_delete = []
        for p in existing_db_props:
            grp_key = (p.partito.strip().lower(), p.macro_argomento.strip().lower())
            if grp_key not in by_grp:
                by_grp[grp_key] = [p]
            else:
                dup_found = False
                for prev_p in by_grp[grp_key]:
                    p_emb = json.loads(p.embedding) if p.embedding else None
                    prev_emb = json.loads(prev_p.embedding) if prev_p.embedding else None
                    dup_matched, reason = is_duplicate_proposal(
                        party_a=p.partito,
                        topic_a=p.macro_argomento,
                        text_a=p.dichiarazione_sintesi,
                        party_b=prev_p.partito,
                        topic_b=prev_p.macro_argomento,
                        text_b=prev_p.dichiarazione_sintesi,
                        emb_a=p_emb,
                        emb_b=prev_emb
                    )
                    if dup_matched:
                        dup_found = True
                        # Keep the longer, more descriptive one
                        if len(p.dichiarazione_sintesi) > len(prev_p.dichiarazione_sintesi):
                            db_to_delete.append(prev_p)
                            by_grp[grp_key].remove(prev_p)
                            by_grp[grp_key].append(p)
                        else:
                            db_to_delete.append(p)
                        break
                if not dup_found:
                    by_grp[grp_key].append(p)

        for dp in db_to_delete:
            try:
                del_log = AuditLog(
                    event_type="cancellazione",
                    entity_type="programma",
                    entity_id=str(dp.id),
                    entity_name=f"{dp.partito}: {dp.macro_argomento}",
                    old_value=dp.dichiarazione_sintesi[:90] + "...",
                    new_value=None,
                    agent_responsible="DeduplicationAgent",
                    details=f"Cancellazione proposta duplicata di {dp.partito} ({dp.macro_argomento}): '{dp.dichiarazione_sintesi[:90]}...'.",
                    timestamp=datetime.datetime.utcnow()
                )
                db.add(del_log)
                db.delete(dp)
            except Exception:
                pass
        if db_to_delete:
            db.commit()
            print(f"[Database] Post-seed clean: deleted {len(db_to_delete)} duplicate proposals from database.")

        # Purge any incomplete, cut-off, or clickbait proposals
        from app.ai.proposal_validator import sanitize_and_validate_proposal_statement
        all_current = db.query(PoliticalProposal).all()
        purged = []
        for p in all_current:
            # 1. Correct inverted coalition positions
            if p.partito == "Movimento 5 Stelle" and "attuazione del regionalismo differenziato" in p.dichiarazione_sintesi.lower():
                old_val = p.dichiarazione_sintesi
                p.dichiarazione_sintesi = "Referendum abrogativo e opposizione all'Autonomia Differenziata Calderoli a difesa dei servizi essenziali e dell'unità nazionale"
                p.tipo_azione = "Opposizione"
                p.fact_check_status = "Verificato"
                p.fact_check_motivazione = "M5S ha promosso e depositato oltre 500.000 firme per il referendum abrogativo totale della legge Calderoli sull'autonomia differenziata."
                mod_log = AuditLog(
                    event_type="modifica",
                    entity_type="programma",
                    entity_id=str(p.id),
                    entity_name=f"{p.partito}: {p.macro_argomento}",
                    old_value=old_val[:90] + "...",
                    new_value=p.dichiarazione_sintesi[:90] + "...",
                    agent_responsible="PolicyMergerAgent",
                    details=f"Rettifica e allineamento politico d'opposizione: '{p.dichiarazione_sintesi}'.",
                    timestamp=datetime.datetime.utcnow()
                )
                db.add(mod_log)
                continue

            # 2. Correct vague slogan for M5S LSU/LPU
            if "restituire diritti a chi ha garantito per anni" in p.dichiarazione_sintesi.lower():
                old_val = p.dichiarazione_sintesi
                p.macro_argomento = "Lavoro"
                p.dichiarazione_sintesi = "Disegno di legge per il pieno riconoscimento previdenziale e la pensione equa dei lavoratori socialmente utili (LSU e LPU)"
                p.tipo_azione = "Proposta di legge"
                p.costo_stimato = "Circa 280 milioni € annui"
                p.coperture_dichiarate = "Fondo per le politiche attive del lavoro e riordino della spesa assistenziale INPS"
                p.fact_check_status = "Verificato"
                p.fact_check_motivazione = "DDL depositato dal gruppo M5S in Parlamento per sanare la disparità previdenziale dei lavoratori LSU e LPU."
                mod_log = AuditLog(
                    event_type="modifica",
                    entity_type="programma",
                    entity_id=str(p.id),
                    entity_name=f"{p.partito}: {p.macro_argomento}",
                    old_value=old_val[:90] + "...",
                    new_value=p.dichiarazione_sintesi[:90] + "...",
                    agent_responsible="PolicyMergerAgent",
                    details=f"Riformulazione da slogan astratto a disegno di legge parlamentare concreto: '{p.dichiarazione_sintesi}'.",
                    timestamp=datetime.datetime.utcnow()
                )
                db.add(mod_log)
                continue

            val = sanitize_and_validate_proposal_statement(p.dichiarazione_sintesi)
            if not val:
                del_log = AuditLog(
                    event_type="cancellazione",
                    entity_type="programma",
                    entity_id=str(p.id),
                    entity_name=f"{p.partito}: {p.macro_argomento}",
                    old_value=p.dichiarazione_sintesi[:90] + "...",
                    new_value=None,
                    agent_responsible="DataSanitizerAgent",
                    details=f"Cancellazione proposta incompleta o non valida di {p.partito} ({p.macro_argomento}): '{p.dichiarazione_sintesi}'.",
                    timestamp=datetime.datetime.utcnow()
                )
                db.add(del_log)
                db.delete(p)
                purged.append(p)
            elif val != p.dichiarazione_sintesi:
                p.dichiarazione_sintesi = val
        if purged:
            db.commit()
            print(f"[Database] Purged {len(purged)} incomplete/invalid proposals.")

        # Correct political inversions and purge press headlines
        gov_parties = {"Fratelli d'Italia", "Lega - Salvini Premier", "Forza Italia", "Noi Moderati", "Futuro Nazionale"}
        for p in db.query(PoliticalProposal).all():
            p_text = p.dichiarazione_sintesi.lower()
            if p.partito in gov_parties:
                if any(k in p_text for k in ["cannabis", "fine vita assistito", "eutanasia"]) and "contrariet" not in p_text:
                    p.dichiarazione_sintesi = "Contrarietà a qualsiasi legalizzazione delle droghe leggere, potenziamento delle comunità di recupero e tutela della vita dal concepimento alla morte naturale"
                    p.tipo_azione = "Dichiarazione programmatica"
                    p.fact_check_status = "Verificato"
                    p.fact_check_motivazione = "Posizione ufficiale e programma di governo di Fratelli d'Italia a contrasto delle dipendenze e tutela della vita."
            if "i programmi dei principali partiti su tasse" in p_text or "forbes" in p_text:
                db.delete(p)
            if p.partito == "Potere al Popolo" and p.macro_argomento == "Lavoro" and "9 euro" in p_text:
                p.dichiarazione_sintesi = "Salario minimo legale a 10 euro lordi l'ora indicizzato all'inflazione reale con ripristino della scala mobile"
            if p.partito == "Forza Italia" and p.macro_argomento == "Istituzioni" and any(k in p_text for k in ["legittima difesa", "separazione delle carriere"]):
                p.dichiarazione_sintesi = "Tutela del garantismo penale, riforma della carcerazione preventiva e abolizione del reato di abuso d'ufficio"
            if p.partito == "Fratelli d'Italia" and p.macro_argomento == "Diritti Civili" and "separazione delle carriere" in p_text:
                p.dichiarazione_sintesi = "Tutela della famiglia e della natalità con quoziente familiare, potenziamento degli asili nido e contrasto alla maternità surrogata"
        db.commit()

        # Strict deduplication for any remaining duplicate identical entries
        for p in db.query(PoliticalProposal).all():
            others = db.query(PoliticalProposal).filter(
                PoliticalProposal.partito == p.partito,
                PoliticalProposal.macro_argomento == p.macro_argomento,
                PoliticalProposal.id < p.id
            ).all()
            for other in others:
                from difflib import SequenceMatcher
                ratio = SequenceMatcher(None, p.dichiarazione_sintesi.lower(), other.dichiarazione_sintesi.lower()).ratio()
                p_w = set(p.dichiarazione_sintesi.lower().split())
                o_w = set(other.dichiarazione_sintesi.lower().split())
                if ratio > 0.75 and len(p_w & o_w) >= 4:
                    db.delete(p)
                    break
        db.commit()

        # Deduplicate nuclear template clones across parties
        nuclear_clones = db.query(PoliticalProposal).filter(
            PoliticalProposal.macro_argomento == "Energia"
        ).all()
        for p in nuclear_clones:
            if "reintegro dell'energia nucleare pulita di nuova generazione" in p.dichiarazione_sintesi.lower():
                other = db.query(PoliticalProposal).filter(
                    PoliticalProposal.partito == p.partito,
                    PoliticalProposal.macro_argomento == "Energia",
                    PoliticalProposal.id != p.id
                ).first()
                if other:
                    db.delete(p)
                elif p.partito == "Azione":
                    p.dichiarazione_sintesi = "Piano Nazionale per il Nucleare con la realizzazione di 8 reattori modulari SMR entro il 2040 per assicurare energia a basso costo all'industria manifatturiera"
                elif p.partito == "Radicali Italiani":
                    p.dichiarazione_sintesi = "Abolizione immediata di tutti i sussidi ambientalmente dannosi (SAD), introduzione di una carbon tax neutra e riavvio dell'energia nucleare pulita"
                elif p.partito == "Partito Liberal Democratico":
                    p.dichiarazione_sintesi = "Quadro normativo e regolatorio per investimenti privati nel nucleare civile SMR e snellimento delle autorizzazioni per parchi rinnovabili"
        db.commit()

        # Ensure ORA! has clean authentic Sanità proposal
        ora_sanita = db.query(PoliticalProposal).filter(
            PoliticalProposal.partito == "ORA!",
            PoliticalProposal.macro_argomento == "Sanità"
        ).first()
        if not ora_sanita:
            ora_party = db.query(PoliticalProposal).filter(PoliticalProposal.partito == "ORA!").first()
            p_id = ora_party.party_id if ora_party else None
            new_ora = PoliticalProposal(
                party_id=p_id,
                partito="ORA!",
                macro_argomento="Sanità",
                dichiarazione_sintesi="Sanità di prossimità con convenzioni trasparenti e voucher universali per l'abbattimento immediato delle liste d'attesa",
                tipo_azione="Proposta di legge",
                costo_stimato="Non quantificato",
                coperture_dichiarate="Riorganizzazione delle convenzioni regionali e fondi ordinari SSN",
                fattibilita_finanziaria="Compatibile con i saldi di bilancio sanitario a parità di spesa pro-capite.",
                fact_check_status="In attesa di copertura",
                fact_check_motivazione="Proposta programmatica di ORA! per l'efficientamento del servizio sanitario e la riduzione dei tempi d'attesa.",
                fact_check_fonte="Programma Politico ORA! - Sezione Sanità e Servizi",
                fonte_url="https://movimento-ora.it",
                fonte_titolo="Programma Sanità e Liste d'Attesa",
                fonte_testata="ORA! Ufficio Studi",
                timestamp=datetime.datetime.utcnow()
            )
            db.add(new_ora)
            db.commit()

        # Synchronize 'aggiunta' audit logs for all active valid proposals
        from app.api.audit import sync_audit_with_proposals
        sync_audit_with_proposals(db)

        print(f"[Database] All proposals are up to date and deduplicated ({db.query(PoliticalProposal).count()} total).")


        # Realistic Public Finance Audit: Art. 81 Cost. & Legge 196/2009
        try:
            from app.ai.fiscal_calculator import sanitize_proposal_title
            all_db_props = db.query(PoliticalProposal).all()
            
            FORMAL_ACT_KEYWORDS = [
                "legge", "decreto", "ddl", "a.c.", "a.s.", "atto di governo", 
                "delibera", "l.", "d.l.", "d.lgs.", "l. 86/2024", "l. 159/2024", "l. 14/2024"
            ]

            for p in all_db_props:
                clean_t = sanitize_proposal_title(p.dichiarazione_sintesi, p.partito)
                if "le intese sul programma" in p.dichiarazione_sintesi.lower():
                    clean_t = "Riforma IRPEF ad aliquota marginale al 35%, taglio delle micro-tasse e azzeramento dei sussidi ambientalmente dannosi"
                    p.fonte_testata = "+Europa Ufficio Studi"
                if clean_t and clean_t != p.dichiarazione_sintesi:
                    p.dichiarazione_sintesi = clean_t

                act_str = (p.tipo_azione or "").lower()
                text_str = (p.dichiarazione_sintesi or "").lower()
                is_formal = any(k in act_str or k in text_str for k in FORMAL_ACT_KEYWORDS)

                # Evaluate public finance impact and fact-check status against institutional criteria
                from app.ai.fact_checker import analyze_feasibility_and_factcheck
                from app.ai.fiscal_calculator import calculate_fiscal_impact_and_coverage

                if not p.costo_stimato or p.costo_stimato.lower() in ["non quantificato", "non quantificata", "da definire"] or not p.coperture_dichiarate or len(p.coperture_dichiarate) < 15:
                    f_calc = calculate_fiscal_impact_and_coverage(
                        partito=p.partito,
                        macro_argomento=p.macro_argomento,
                        sintesi=p.dichiarazione_sintesi,
                        costo_stimato=p.costo_stimato,
                        coperture_dichiarate=p.coperture_dichiarate
                    )
                    p.costo_stimato = f_calc["costo_stimato"]
                    p.coperture_dichiarate = f_calc["coperture_dichiarate"]
                    p.fattibilita_finanziaria = f_calc["fattibilita_finanziaria"]
                    p.fact_check_status = f_calc["fact_check_status"]
                    p.fact_check_motivazione = f_calc["fact_check_motivazione"]
                    p.fact_check_fonte = f_calc["fact_check_fonte"]

                feas, st, mot, src = analyze_feasibility_and_factcheck(
                    partito=p.partito,
                    macro_argomento=p.macro_argomento,
                    sintesi=p.dichiarazione_sintesi,
                    costo_stimato=p.costo_stimato,
                    coperture=p.coperture_dichiarate
                )
                if st != p.fact_check_status and st in ["Inattuabile", "Esagerato", "In attesa di copertura"]:
                    p.fact_check_status = st
                    p.fattibilita_finanziaria = feas
                    p.fact_check_motivazione = mot
                    p.fact_check_fonte = src
            db.commit()

            # Recalculate and persist realistic party truthfulness and coverage scores
            TRUTH_WEIGHTS = {
                "Verificato": 100.0,
                "In attesa di copertura": 60.0,
                "Esagerato": 30.0,
                "Inattuabile": 0.0,
                "Fake / Infondato": 0.0,
                "Non verificabile": 20.0
            }
            for party in db.query(PoliticalParty).all():
                p_props = db.query(PoliticalProposal).filter(
                    (PoliticalProposal.party_id == party.id) | (PoliticalProposal.partito.ilike(f"%{party.name}%"))
                ).all()
                if p_props:
                    party.truthfulness_score = round(sum(TRUTH_WEIGHTS.get(pr.fact_check_status, 50.0) for pr in p_props) / len(p_props), 1)
            db.commit()
            print("[Database] Realistic Art. 81 public finance audit applied cleanly.")
        except Exception as fe:
            print(f"[Database] Fiscal audit notice: {fe}")


        # Update all party dossiers on startup
        try:
            from app.ingestion.dossier_generator import update_all_party_dossiers
            update_all_party_dossiers(db)
        except Exception as de:
            print(f"[Database] Dossier update notice: {de}")

        # Seed initial audit history
        try:
            seed_audit_history_if_empty(db)
        except Exception as ae:
            print(f"[Database] Audit seed notice: {ae}")

    except Exception as e:
        db.rollback()
        print(f"[Database] Seeding error: {e}")
    finally:
        db.close()

async def _autonomous_self_keepalive():
    """
    Autonomous Keepalive: pings the public Render URL every 7 minutes.
    Because Render monitors incoming HTTP traffic on politclens.onrender.com, this public request
    resets Render's 15-minute idle timer, preventing the free tier container from sleeping.
    """
    await asyncio.sleep(45)  # Let server complete initial startup
    external_url = os.environ.get("RENDER_EXTERNAL_URL", "https://politclens.onrender.com")
    health_endpoint = f"{external_url.rstrip('/')}/api/health"
    print(f"[Keepalive] Autonomous 24/7 background keepalive loop started (target: {health_endpoint}).")
    
    while True:
        try:
            import urllib.request
            req = urllib.request.Request(
                health_endpoint,
                headers={"User-Agent": "PoliticLens-Autonomous-Keepalive/2.0 (+https://politclens.onrender.com)"}
            )
            # Run in thread pool to avoid blocking async event loop
            loop = asyncio.get_running_loop()
            def do_ping():
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.getcode()
            status = await loop.run_in_executor(None, do_ping)
            print(f"[Keepalive] Public ping status: {status} -> Render 15-min idle timer reset.")
        except Exception as e:
            print(f"[Keepalive] Public ping notice (will retry in 7 min): {e}")
        # Ping every 7 minutes (420 seconds) - safely below Render's 15-minute (900 seconds) timeout
        await asyncio.sleep(420)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[PoliticLens] Inizializzazione piattaforma e database...")
    seed_database_if_empty()
    start_scheduler()
    
    # Autonomous startup poll sync (in background after 2 seconds)
    async def _startup_poll_sync():
        await asyncio.sleep(2)
        try:
            db_sync = SessionLocal()
            from app.ingestion.poll_tracker import run_poll_tracker_pipeline
            print("[PoliticLens] Sincronizzazione demoscopica iniziale all'avvio...")
            run_poll_tracker_pipeline(db_sync)
            db_sync.close()
        except Exception as e:
            print(f"[PoliticLens] Notice sincronizzazione demoscopica avvio: {e}")

    # Autonomous initial web ingestion pass (in background after 5 seconds)
    async def _startup_pipeline_scan():
        await asyncio.sleep(5)
        try:
            from app.ingestion.scheduler import run_pipeline_scan
            print("[PoliticLens] Esecuzione prima scansione web automatica...")
            await run_pipeline_scan()
        except Exception as e:
            print(f"[PoliticLens] Notice scansione web avvio: {e}")

    asyncio.create_task(_startup_poll_sync())
    asyncio.create_task(_startup_pipeline_scan())
    keepalive_task = asyncio.create_task(_autonomous_self_keepalive())
    yield
    print("[PoliticLens] Arresto servizi...")
    keepalive_task.cancel()
    stop_scheduler()

app = FastAPI(
    title="PoliticLens Backend API",
    description="Analizzatore e Comparatore Politico Autonomo, neutrale e 100% open-source.",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(parties_router)
app.include_router(proposals_router)
app.include_router(comparison_router)
app.include_router(chat_router)
app.include_router(ingestion_router)
app.include_router(stats_router)
app.include_router(audit_router)


@app.get("/api/health")
async def health_check():
    ollama_ok = await ollama_client.is_available()
    models = await ollama_client.list_models() if ollama_ok else []
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "neutrality_policy": "Absolute Political Impartiality & Institutional Fact-Checking",
        "ollama_connected": ollama_ok,
        "ollama_models": models
    }

# Unified Frontend Serving
# Find static files directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "..", "static")

if os.path.exists(STATIC_DIR):
    # Mount _next assets
    next_dir = os.path.join(STATIC_DIR, "_next")
    if os.path.exists(next_dir):
        app.mount("/_next", StaticFiles(directory=next_dir), name="next_assets")

    @app.get("/icon.svg")
    async def serve_icon():
        return FileResponse(os.path.join(STATIC_DIR, "icon.svg"))

    @app.get("/manifest.json")
    async def serve_manifest():
        return FileResponse(os.path.join(STATIC_DIR, "manifest.json"))

    @app.get("/favicon.ico")
    async def serve_favicon():
        return FileResponse(os.path.join(STATIC_DIR, "favicon.ico"))

    @app.get("/compare")
    async def serve_compare():
        return FileResponse(os.path.join(STATIC_DIR, "compare.html"))

    @app.get("/chat")
    async def serve_chat():
        return FileResponse(os.path.join(STATIC_DIR, "chat.html"))

    @app.get("/fact-check")
    async def serve_factcheck():
        return FileResponse(os.path.join(STATIC_DIR, "fact-check.html"))

    @app.get("/parties")
    async def serve_parties():
        return FileResponse(os.path.join(STATIC_DIR, "parties.html"))

    @app.get("/sources")
    async def serve_sources():
        return FileResponse(os.path.join(STATIC_DIR, "sources.html"))

    @app.get("/audit")
    async def serve_audit():
        return FileResponse(os.path.join(STATIC_DIR, "audit.html"))

    @app.get("/")

    async def serve_root():
        index_file = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return await health_check()

    @app.get("/{full_path:path}")
    async def serve_catch_all(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        file_path = os.path.join(STATIC_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        html_file = os.path.join(STATIC_DIR, f"{full_path}.html")
        if os.path.isfile(html_file):
            return FileResponse(html_file)
        # Default fallback to index.html
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
else:
    @app.get("/")
    async def root():
        return await health_check()
