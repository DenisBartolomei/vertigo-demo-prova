# data_preparation/analyzer/run_production_pipeline.py

import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from .icp_generator.icp_creator import generate_and_extract_icp
from .case_guide_generator.guide_creator import generate_case_guide
from .kb_summarizer.kb_processor import summarize_knowledge_base
from .final_generator.case_creator import generate_final_cases
from .final_generator.criteria_creator import generate_final_criteria
from ..corrector.evaluation_criteria_generator.criteria_generator import generate_evaluation_criteria

from services.data_manager import db
from services.language_detector import validate_language
from services.text_translation import translate_to_italian
from recruitment_suite.app.core.pipeline import RecruitmentPipeline
from recruitment_suite.app.reporting.analysis import visualize_results, create_dossiers_for_promoted
from recruitment_suite.app.utils.esco_fetcher import EscoSkillFetcher
from recruitment_suite.app.core.benchmark_cache import save_offer_benchmark_to_cache
from recruitment_suite.config import settings
import numpy as np
import re
import hashlib

def extract_tenant_id_from_collection(collection_name: str) -> str | None:
    """
    Estrae tenant_id dal nome della collection.
    Formato: {tenant_id}_positions_data oppure semplicemente positions_data (senza tenant)
    """
    if collection_name == "positions_data":
        return None
    # Pattern: {tenant_id}_positions_data
    match = re.match(r'^(.+?)_positions_data$', collection_name)
    if match:
        return match.group(1)
    return None

def run_full_generation_pipeline(position_id: str, reasoning_steps: int, collection_name: str = "positions_data", tenant_id: str | None = None) -> bool:
    """
    Orchestra l'intera pipeline di generazione dei dati per una nuova posizione.
    """
    print(f"--- [PIPELINE 'PRODUCTION'] Avvio per la posizione: {position_id} ---")

    # --- STEP 0: RECUPERO DELLA JOB DESCRIPTION ---
    print(f"\n[STEP 0/6] Recupero dati iniziali da MongoDB...")
    try:
        if db is None: raise ConnectionError("Connessione a MongoDB non disponibile.")
        positions_collection = db[collection_name]
        position_document = positions_collection.find_one({"_id": position_id})

        if not position_document:
            print(f"  - ERRORE: Documento non trovato per '{position_id}'.")
            return False

        jd_text = position_document.get("job_description")
        kb_docs = position_document.get("knowledge_base", [])
        seniority_level = position_document.get("seniority_level", "Mid-Level")
        hr_special_needs = position_document.get("hr_special_needs", "")
        language = validate_language(position_document.get("language", "it"))  # Get language, default to Italian

        if not jd_text:
            print(f"  - ERRORE: Campo 'job_description' non trovato per '{position_id}'.")
            return False
        print(f"  - Dati iniziali (JD, KB, Seniority, HR Needs, Language: {language}) recuperati con successo.")
    except Exception as e:
        print(f"  - ERRORE durante il recupero dei dati iniziali da MongoDB: {e}")
        return False

    # --- STEP 1: GENERAZIONE ICP ---
    print(f"\n[STEP 1/6] Generazione dell'Ideal Candidate Profile (ICP)...")
    from .icp_generator.icp_creator import extract_canonical_skills_from_icp
    
    icp_text, icp_structured = generate_and_extract_icp(job_description_text=jd_text, hr_special_needs=hr_special_needs, language=language)
    if not icp_text or not icp_structured:
        print("  - Fallimento nella generazione dell'ICP. Pipeline interrotta.")
        return False
    
    # Estrai la lista canonica delle skills (UNICA fonte di verità)
    canonical_skills = extract_canonical_skills_from_icp(icp_structured)
    
    # Salva ICP testuale (retrocompatibilità), ICP strutturato e canonical_skills
    update_data = {
        "icp": icp_text,
        "icp_structured": icp_structured.model_dump(),
        "canonical_skills": canonical_skills
    }
    positions_collection.update_one({"_id": position_id}, {"$set": update_data})
    print(f"  - ICP salvato con successo per '{position_id}'.")
    print(f"  - Canonical skills salvate: {len(canonical_skills)} skills totali.")

    # --- STEP 2: GENERAZIONE GUIDA AL CASO ---
    print(f"\n[STEP 2/6] Generazione della Guida alla Creazione dei Casi...")
    case_guide_text = generate_case_guide(icp_text=icp_text, seniority_level=seniority_level, hr_special_needs=hr_special_needs, language=language)
    if not case_guide_text:
        print("  - Fallimento nella generazione della Guida. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"case_guide": case_guide_text}})
    print(f"  - Guida salvata con successo per '{position_id}'.")

    # --- STEP 3: SINTESI KNOWLEDGE BASE ---
    print(f"\n[STEP 3/6] Sintesi della Knowledge Base...")
    kb_summary = summarize_knowledge_base(icp_text=icp_text, kb_documents=kb_docs, language=language)
    if not kb_summary:
        print("  - Fallimento nella sintesi della KB. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"kb_summary": kb_summary}})
    print(f"  - Sintesi KB salvata con successo per '{position_id}'.")

    # --- STEP 4: GENERAZIONE DEI CASI ---
    print(f"\n[STEP 4/6] Generazione finale dei casi strutturati...")
    case_collection = generate_final_cases(icp_text, case_guide_text, kb_summary, seniority_level, reasoning_steps, hr_special_needs, language, canonical_skills=canonical_skills)
    if not case_collection:
        print("  - Fallimento nella generazione dei Casi. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"all_cases": case_collection.model_dump()}})
    print(f"  - Casi salvati con successo per '{position_id}'.")

    # --- STEP 5: GENERAZIONE DEI CRITERI PER IL CHATBOT ---
    print(f"\n[STEP 5/6] Generazione dei criteri per il chatbot...")
    cases_json_str = case_collection.model_dump_json()
    criteria_collection = generate_final_criteria(icp_text, cases_json_str, seniority_level, hr_special_needs, language)
    if not criteria_collection:
        print("  - Fallimento nella generazione dei Criteri. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"all_criteria": criteria_collection.model_dump()}})
    print(f"  - Criteri per il chatbot salvati con successo per '{position_id}'.")

    # --- STEP 6: GENERAZIONE DEI CRITERI DI VALUTAZIONE FINALE ---
    print(f"\n[STEP 6/7] Generazione dei Criteri di Valutazione Finale...")
    eval_criteria_collection = generate_evaluation_criteria(icp_text, cases_json_str, seniority_level, hr_special_needs, language, canonical_skills=canonical_skills)
    if not eval_criteria_collection:
        print("  - Fallimento nella generazione dei Criteri di Valutazione. Pipeline interrotta.")
        return False
    positions_collection.update_one({"_id": position_id}, {"$set": {"evaluation_criteria": eval_criteria_collection.model_dump()}})
    print(f"  - Criteri di valutazione finale salvati con successo per '{position_id}'.")

    # --- STEP 7: PRE-CALCOLO BENCHMARK DI MERCATO (Cloud Optimized) ---
    print(f"\n[STEP 7/7] Pre-calcolo Benchmark di Mercato (Cloud Optimized)...")
    try:
        # Carica candidati benchmark da MongoDB (streaming/projection per efficienza)
        collection_name = settings.MONGO_COLLECTION_BENCHMARK_CANDIDATES
        projection = {"profile_id": 1, "ID": 1, "normalized_experiences": 1, "_id": 0}
        candidates_data_full = list(db[collection_name].find({}, projection))
        
        if not candidates_data_full:
            print("  - ATTENZIONE: Nessun candidato benchmark trovato. Salto pre-calcolo benchmark.")
        else:
            print(f"  - Caricati {len(candidates_data_full)} candidati benchmark.")
            candidates_data_filtered = [p for p in candidates_data_full if p.get('normalized_experiences')]
            
            if not candidates_data_filtered:
                print("  - ATTENZIONE: Nessun candidato con esperienze normalizzate. Salto pre-calcolo benchmark.")
            else:
                print(f"  - {len(candidates_data_filtered)} candidati validi per il benchmark.")
                
                # Usa il titolo della posizione o fallback al position_id
                position_name = position_document.get("position_name", position_id)
                
                benchmark_job_description = jd_text
                translated_for_benchmark = False

                if language == "en":
                    translated_text = translate_to_italian(jd_text, source_language="en")
                    if translated_text and translated_text.strip():
                        if translated_text.strip() != jd_text.strip():
                            benchmark_job_description = translated_text
                            translated_for_benchmark = True
                            print("  - Traduzione EN→IT applicata per il pre-calcolo del benchmark.")
                        else:
                            print("  - Traduzione EN→IT identica all'originale. Uso JD originale per il benchmark.")
                    else:
                        print("  - ATTENZIONE: Traduzione EN→IT fallita. Uso JD originale per il benchmark.")

                benchmark_job_description_hash = hashlib.sha256(
                    benchmark_job_description.encode("utf-8")
                ).hexdigest()

                # Crea pipeline e calcola benchmark
                pipeline = RecruitmentPipeline()
                llm_analysis, _ = pipeline.run_full_pipeline(
                    position_name,
                    benchmark_job_description,
                    candidates_data_filtered
                )
                
                # Genera risultati di mercato
                market_df = None
                chart_cat_base64 = None
                market_skills_list = None
                market_json = None
                
                if llm_analysis:
                    promossi_llm = [p for p in llm_analysis if not p.get('scartato')]
                    if promossi_llm:
                        # Fix: usare 'ID' (maiuscolo) come restituito dall'LLM, non settings.ID_COLUMN
                        promoted_ids = {p.get('ID') for p in promossi_llm if p.get('ID')}
                        print(f"  - {len(promoted_ids)} candidati promossi dall'LLM per il benchmark.")
                        skill_fetcher = EscoSkillFetcher()
                        final_dossiers = create_dossiers_for_promoted(promoted_ids, candidates_data_full, skill_fetcher)
                        print(f"  - {len(final_dossiers)} dossier creati per la generazione del market_json.")
                        if final_dossiers:
                            market_df, chart_cat_base64, market_skills_list = visualize_results(final_dossiers)
                            
                            # Genera market_json da market_df per uso diretto nel report qualitativo
                            # Converti i valori numpy a tipi Python nativi per serializzazione MongoDB
                            if market_df is not None and not market_df.empty:
                                market_json_raw = market_df.head(10).round(0).astype(int).to_dict()
                                # Converti valori numpy a int Python nativi
                                market_json = {str(k): int(v) for k, v in market_json_raw.items()}
                
                # Salva in cache per uso futuro
                if market_df is not None and pipeline.offer_embedding is not None:
                    offer_embedding = pipeline.offer_embedding
                    # Converti tensore a numpy array se necessario e normalizza a float32
                    if hasattr(offer_embedding, 'cpu'):
                        offer_embedding = offer_embedding.cpu().numpy().astype(np.float32)
                    elif hasattr(offer_embedding, 'numpy'):
                        offer_embedding = offer_embedding.numpy().astype(np.float32)
                    else:
                        offer_embedding = np.array(offer_embedding, dtype=np.float32)
                    
                    # Usa tenant_id passato esplicitamente, altrimenti prova a estrarlo dalla collection
                    if tenant_id is None:
                        tenant_id = extract_tenant_id_from_collection(collection_name)
                    
                    # Verifica che tenant_id non sia una stringa "NULL" o "None"
                    if tenant_id and isinstance(tenant_id, str) and tenant_id.upper() in ("NULL", "NONE", ""):
                        tenant_id = None
                    
                    if tenant_id:
                        print(f"  - tenant_id utilizzato per il benchmark: {tenant_id}")
                    else:
                        print(f"  - ATTENZIONE: tenant_id non disponibile, benchmark salvato senza tenant_id")
                    
                    save_offer_benchmark_to_cache(
                        position_id,
                        offer_embedding,  # Già float32
                        market_df,
                        chart_cat_base64,
                        market_skills_list,
                        tenant_id=tenant_id,
                        market_json=market_json,  # Passa market_json per evitare ricalcolo
                        job_language=language,
                        translated_for_benchmark=translated_for_benchmark,
                        job_description_hash=benchmark_job_description_hash,
                    )
                    cache_key = f"{tenant_id}_{position_id}" if tenant_id else position_id
                    print(f"  - Benchmark di mercato pre-calcolato e salvato in cache per '{cache_key}'.")
                else:
                    print("  - ATTENZIONE: Benchmark non generato correttamente. Non salvato in cache.")
    
    except Exception as e:
        print(f"  - ERRORE durante il pre-calcolo del benchmark: {e}")
        print("  - Continuo comunque la pipeline (benchmark opzionale).")

    print("\n--- [PIPELINE 'PRODUCTION'] Tutti i dati per la posizione sono stati generati e salvati su MongoDB. ---")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_position_id = sys.argv[1]
        run_full_generation_pipeline(test_position_id)
    else:
        print("Uso: python -m data_preparation.analyzer.run_production_pipeline \"<position_id_da_mongodb>\"")