# File: feedback_generator/market_integration.py
import os
import sys
import hashlib

# Aggiunge la root del progetto al PYTHONPATH (cartella padre di 'feedback_generator')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from recruitment_suite.config import settings
from recruitment_suite.app.core.pipeline import RecruitmentPipeline
from recruitment_suite.app.core.normalizer import CVNormalizer
from recruitment_suite.app.reporting.analysis import visualize_results, create_dossiers_for_promoted
from recruitment_suite.app.utils.esco_fetcher import EscoSkillFetcher
from recruitment_suite.app.reporting.qualitative import generate_qualitative_llm_report
from recruitment_suite.app.core.benchmark_cache import (
    load_offer_benchmark_from_cache,
    check_offer_benchmark_exists,
    save_offer_benchmark_to_cache
)
from services.data_manager import db
from services.language_detector import detect_language, validate_language
from services.text_translation import (
    translate_to_italian,
    translate_to_italian_async,
)
import asyncio
import numpy as np



def run_market_benchmark_from_text(
    job_description_text: str,
    parsed_experiences: str,
    offer_title: str,
    position_id: str = None,
    tenant_id: str = None,
    job_language: str | None = None
) -> tuple[str | None, str | None, list[str] | None]:
    """
    Esegue la recruitment suite usando JD e testo del CV.
    Usa benchmark pre-calcolato se disponibile, altrimenti calcola.
    Ritorna: (testo_qualitativo, grafico_categorie_base64, lista_delle_skill_piu_comuni)
    """
    original_job_description_text = job_description_text or ""
    normalized_language = (
        validate_language(job_language)
        if job_language
        else detect_language(original_job_description_text)
    )
    benchmark_job_description = original_job_description_text
    translated_for_benchmark = False

    if normalized_language == "en":
        translated_text = translate_to_italian(
            original_job_description_text,
            source_language="en",
        )
        if translated_text and translated_text.strip():
            if translated_text.strip() != original_job_description_text.strip():
                benchmark_job_description = translated_text
                translated_for_benchmark = True
                print("🌐 [Benchmark] Traduzione EN→IT applicata per la job description (sync).")
            else:
                print("ℹ️ [Benchmark] Traduzione EN→IT identica all'originale, uso testo originale (sync).")
        else:
            print("⚠ [Benchmark] Traduzione EN→IT fallita, uso job description originale (sync).")
    else:
        normalized_language = "it"

    benchmark_job_description_hash = hashlib.sha256(
        benchmark_job_description.encode("utf-8")
    ).hexdigest()
    
    # --- 1. Prova a caricare benchmark pre-calcolato se position_id disponibile ---
    market_df = None
    chart_cat_base64 = None
    market_skills_list = None
    cached_benchmark = None  # Inizializza per uso dopo
    market_json_from_cache = None  # Track se abbiamo market_json dalla cache
    
    if position_id:
        print(f"🔍 Ricerca benchmark in cache per position_id: {position_id}, tenant_id: {tenant_id}")
        cached_benchmark = load_offer_benchmark_from_cache(position_id, tenant_id=tenant_id)
        if cached_benchmark:
            cache_key = f"{tenant_id}_{position_id}" if tenant_id else position_id
            print(f"✓ CACHE HIT: Benchmark pre-calcolato trovato per posizione: {cache_key}")
            market_df = cached_benchmark.get("market_df")
            chart_cat_base64 = cached_benchmark.get("chart_cat_base64")
            market_skills_list = cached_benchmark.get("market_skills_list")
            market_json_from_cache = cached_benchmark.get("market_json")
            if cached_benchmark.get("translated_for_benchmark"):
                print("   ↳ Il benchmark in cache è stato generato con traduzione EN→IT.")
            if market_json_from_cache:
                print(f"✓ market_json presente nella cache con {len(market_json_from_cache)} categorie.")
            else:
                print(f"⚠ market_json NON presente nella cache (sarà generato da market_df).")
        else:
            print(f"✗ CACHE MISS: Benchmark non trovato per position_id: {position_id}, tenant_id: {tenant_id}")
    
    # --- 2. Se NON abbiamo market_json dalla cache E non abbiamo market_df, calcola il benchmark (backward compatibility) ---
    # IMPORTANTE: Se abbiamo market_json dalla cache, NON ricalcolare, anche se market_df è None!
    if market_json_from_cache is None and market_df is None:
        print("CACHE MISS: Benchmark pre-calcolato non trovato. Eseguo calcolo completo...")
        try:
            collection_name = settings.MONGO_COLLECTION_BENCHMARK_CANDIDATES
            candidates_data_full = list(db[collection_name].find({}))
            print(f"Caricati {len(candidates_data_full)} candidati benchmark da MongoDB.")
        except Exception as e:
            print(f"ERRORE CRITICO: Impossibile caricare i candidati benchmark. {e}")
            candidates_data_full = []

        candidates_data_filtered = [p for p in candidates_data_full if p.get('normalized_experiences')]
        pipeline = RecruitmentPipeline()
        
        llm_analysis, _ = pipeline.run_full_pipeline(
            offer_title,
            benchmark_job_description,
            candidates_data_filtered
        )

        if llm_analysis:
            promossi_llm = [p for p in llm_analysis if not p.get('scartato')]
            if promossi_llm:
                promoted_ids = {p['ID'] for p in promossi_llm}
                skill_fetcher = EscoSkillFetcher()
                final_dossiers = create_dossiers_for_promoted(promoted_ids, candidates_data_full, skill_fetcher)
                if final_dossiers:
                    # --- MODIFICA CHIAVE: Cattura i 3 valori restituiti ---
                    market_df, chart_cat_base64, market_skills_list = visualize_results(final_dossiers)
                    
                    # Salva in cache se position_id disponibile per uso futuro
                    if position_id and market_df is not None:
                        offer_embedding = pipeline.offer_embedding
                        if offer_embedding is not None:
                            # Converti tensore a numpy array se necessario e normalizza a float32
                            if hasattr(offer_embedding, 'cpu'):
                                offer_embedding = offer_embedding.cpu().numpy().astype(np.float32)
                            elif hasattr(offer_embedding, 'numpy'):
                                offer_embedding = offer_embedding.numpy().astype(np.float32)
                            else:
                                offer_embedding = np.array(offer_embedding, dtype=np.float32)
                            save_offer_benchmark_to_cache(
                                position_id,
                                offer_embedding,  # Già float32
                                market_df,
                                chart_cat_base64,
                                market_skills_list,
                                tenant_id=tenant_id,
                                job_language=normalized_language,
                                translated_for_benchmark=translated_for_benchmark,
                                job_description_hash=benchmark_job_description_hash,
                            )
    
    # La logica che usa chart_path è stata rimossa, non serve più.

    # --- 2. Normalizzazione del CV della sessione (aggiornata) ---
    candidate_json = {}
    try:
        normalizer = CVNormalizer()
        normalized_candidate_data = normalizer.run_normalization(
            parsed_experiences=parsed_experiences,
            profile_id="current_candidate"
        )
        if normalized_candidate_data and normalized_candidate_data[0].get('normalized_experiences'):
            candidate_past_experiences = normalized_candidate_data[0]['normalized_experiences'][:]
            candidate_json = {
                exp['original_title']: {
                    "durata_mesi": exp['duration_months'],
                    "mansioni_esco": [m.get('esco_title') for m in exp.get('esco_matches', [])]
                }
                for exp in candidate_past_experiences
            }
    except Exception as e:
        print(f"ERRORE durante la normalizzazione del CV (da testo): {e}")

    # --- 3. JSON di mercato per il report qualitativo ---
    # PRIORITÀ: Usa market_json dalla cache se disponibile (NON ricalcolare!)
    market_json = {}
    if market_json_from_cache:
        # Usa market_json direttamente dalla cache (più efficiente, evitiamo ricalcolo)
        market_json = market_json_from_cache
        print(f"✓ Usato market_json dalla cache pre-calcolata con {len(market_json)} categorie.")
        # Debug: verifica struttura
        if isinstance(market_json, dict) and market_json:
            sample_key = list(market_json.keys())[0]
            sample_value = market_json[sample_key]
            print(f"  - Esempio: '{sample_key}' = {sample_value} (tipo: {type(sample_value).__name__})")
        else:
            print(f"⚠ ATTENZIONE: market_json non è un dizionario valido: {type(market_json)}")
    elif market_df is not None and not market_df.empty:
        # Fallback: genera da market_df se non disponibile in cache (backward compatibility)
        # Converti i valori numpy a tipi Python nativi per serializzazione
        try:
            market_json_raw = market_df.head(10).round(0).astype(int).to_dict()
            market_json = {str(k): int(v) for k, v in market_json_raw.items()}
            print("⚠ Generato market_json da market_df (backward compatibility).")
        except Exception as e:
            print(f"⚠ ERRORE generazione market_json da market_df: {e}")
            market_json = {}
    else:
        print("⚠ ATTENZIONE: market_json vuoto. Il report qualitativo potrebbe essere incompleto.")

    # --- 4. Generazione testo qualitativo ---
    # Verifica che abbiamo i dati necessari per il confronto
    if not candidate_json:
        print("⚠ ATTENZIONE: candidate_json vuoto. Il report qualitativo potrebbe essere incompleto.")
    else:
        print(f"✓ candidate_json caricato con {len(candidate_json)} esperienze del candidato.")
    
    if not market_json:
        print("⚠ ATTENZIONE: market_json vuoto. Il report qualitativo non avrà confronto con trend di mercato.")
    else:
        print(f"✓ market_json caricato con {len(market_json)} categorie professionali.")
        print(f"  - Preparazione per LLM: market_json è un {type(market_json).__name__} con {len(market_json)} chiavi")
    
    # DEBUG: Verifica che market_json sia pronto per il JSON serialization
    try:
        import json
        market_json_str = json.dumps(market_json, indent=2, ensure_ascii=False)
        print(f"✓ market_json è serializzabile in JSON (lunghezza: {len(market_json_str)} caratteri)")
    except Exception as e:
        print(f"✗ ERRORE: market_json non è serializzabile in JSON: {e}")
    
    qualitative_text = generate_qualitative_llm_report(
        candidate_json=candidate_json,
        market_json=market_json,
        job_offer_text=original_job_description_text,
        language=normalized_language
    )
    
    if qualitative_text:
        print(f"✓ Report qualitativo generato con successo (lunghezza: {len(qualitative_text)} caratteri)")
    else:
        print(f"⚠ ATTENZIONE: Report qualitativo vuoto o None")

    # --- 5. Restituzione dei risultati pronti per MongoDB ---
    return qualitative_text, chart_cat_base64, market_skills_list 

import pandas as pd
from pymongo.database import Database
import datetime
from recruitment_suite.app.reporting.qualitative import generate_qualitative_llm_report_async

async def run_market_benchmark_from_text_async(
    job_description_text: str,
    parsed_experiences: str,
    offer_title: str,
    db: Database,
    position_id: str = None,
    tenant_id: str = None,
    job_language: str | None = None
) -> tuple[str | None, str | None, list[str] | None]:
    
    from backend.app import recruitment_pipeline_instance, cv_normalizer_instance

    if db is None:
        print("ERRORE CRITICO: Oggetto Database non fornito.")
        return None, None, None

    original_job_description_text = job_description_text or ""
    normalized_language = (
        validate_language(job_language)
        if job_language
        else detect_language(original_job_description_text)
    )
    benchmark_job_description = original_job_description_text
    translated_for_benchmark = False

    if normalized_language == "en":
        translated_text = await translate_to_italian_async(
            original_job_description_text,
            source_language="en",
        )
        if translated_text and translated_text.strip():
            if translated_text.strip() != original_job_description_text.strip():
                benchmark_job_description = translated_text
                translated_for_benchmark = True
                print("🌐 [Benchmark] Traduzione EN→IT applicata per la job description (async).")
            else:
                print("ℹ️ [Benchmark] Traduzione EN→IT identica all'originale, uso testo originale (async).")
        else:
            print("⚠ [Benchmark] Traduzione EN→IT fallita, uso job description originale (async).")
    else:
        normalized_language = "it"

    benchmark_job_description_hash = hashlib.sha256(
        benchmark_job_description.encode("utf-8")
    ).hexdigest()

    # --- 1. Prova a caricare benchmark pre-calcolato se position_id disponibile ---
    market_df = None
    chart_cat_base64 = None
    market_skills_list = None
    cached_benchmark = None  # Inizializza per uso dopo
    market_json_from_cache_async = None  # Track se abbiamo market_json dalla cache
    
    if position_id:
        print(f"🔍 Ricerca benchmark in cache (async) per position_id: {position_id}, tenant_id: {tenant_id}")
        cached_benchmark = load_offer_benchmark_from_cache(position_id, tenant_id=tenant_id)
        if cached_benchmark:
            cache_key = f"{tenant_id}_{position_id}" if tenant_id else position_id
            print(f"✓ CACHE HIT (async): Benchmark pre-calcolato trovato per posizione: {cache_key}")
            market_df = cached_benchmark.get("market_df")
            chart_cat_base64 = cached_benchmark.get("chart_cat_base64")
            market_skills_list = cached_benchmark.get("market_skills_list")
            market_json_from_cache_async = cached_benchmark.get("market_json")
            if cached_benchmark.get("translated_for_benchmark"):
                print("   ↳ Il benchmark cached era stato generato con traduzione EN→IT (async).")
            if market_json_from_cache_async:
                print(f"✓ market_json presente nella cache (async) con {len(market_json_from_cache_async)} categorie.")
            else:
                print(f"⚠ market_json NON presente nella cache (sarà generato da market_df) (async).")
        else:
            print(f"✗ CACHE MISS (async): Benchmark non trovato per position_id: {position_id}, tenant_id: {tenant_id}")
    
    # --- 2. Se non trovato, fallback al vecchio sistema con hash JD (backward compatibility) ---
    if market_df is None:
        print("CACHE MISS: Benchmark pre-calcolato non trovato. Provo cache per hash JD...")
        jd_hash = benchmark_job_description_hash
        cache_collection = db["market_benchmark_cache"]
        cached_data = cache_collection.find_one({"_id": jd_hash})
        
        if cached_data:
            print(f"CACHE HIT per la JD hash: {jd_hash}. Salto il pipeline di mercato.")
            try:
                market_df = pd.DataFrame.from_records(cached_data["market_data"])
                chart_cat_base64 = cached_data.get("chart_cat_base64")
                market_skills_list = cached_data.get("market_skills_list")
            except Exception as e:
                print(f"Errore ricostruzione cache: {e}. Ricalcolo.")
                cached_data = None 
    
    # --- 3. Se ancora non trovato E non abbiamo market_json dalla cache, calcola il benchmark completo ---
    # IMPORTANTE: Se abbiamo market_json_from_cache_async, NON ricalcolare, anche se market_df è None!
    if market_json_from_cache_async is None and market_df is None:
        print("CACHE MISS: Eseguo il pipeline completo.")
        
        try:
            collection_name = settings.MONGO_COLLECTION_BENCHMARK_CANDIDATES
            projection = {"profile_id": 1, "ID": 1, "normalized_experiences": 1, "_id": 0}
            candidates_data_full = list(db[collection_name].find({}, projection))
        except Exception as e:
            print(f"ERRORE CRITICO caricamento candidati benchmark: {e}")
            return None, None, None

        candidates_data_filtered = [p for p in candidates_data_full if p.get('normalized_experiences')]
        
        pipeline = recruitment_pipeline_instance
        if pipeline is None:
            raise RuntimeError("Recruitment Pipeline non è stato inizializzato.")
        
        loop = asyncio.get_running_loop()
        llm_analysis, _ = await loop.run_in_executor(
            None,
            pipeline.run_full_pipeline,
            offer_title,
            benchmark_job_description,
            candidates_data_filtered,
        )

        if llm_analysis:
            promossi_llm = [p for p in llm_analysis if not p.get('scartato')]
            if promossi_llm:
                # Fix: usare 'ID' (maiuscolo) come restituito dall'LLM, non settings.ID_COLUMN
                promoted_ids = {p.get('ID') for p in promossi_llm if p.get('ID')}
                skill_fetcher = EscoSkillFetcher()
                final_dossiers = create_dossiers_for_promoted(promoted_ids, candidates_data_full, skill_fetcher)
                if final_dossiers:
                    market_df, chart_cat_base64, market_skills_list = visualize_results(final_dossiers)
                    
                    # Genera market_json da market_df per uso diretto nel report qualitativo
                    # Converti i valori numpy a tipi Python nativi per serializzazione MongoDB
                    market_json_temp = None
                    if market_df is not None and not market_df.empty:
                        market_json_raw = market_df.head(10).round(0).astype(int).to_dict()
                        # Converti valori numpy a int Python nativi
                        market_json_temp = {str(k): int(v) for k, v in market_json_raw.items()}
                    
                    # Salva in cache se position_id disponibile
                    if position_id:
                        offer_embedding = pipeline.offer_embedding
                        if offer_embedding is not None:
                            # Converti tensore a numpy array se necessario e normalizza a float32
                            if hasattr(offer_embedding, 'cpu'):
                                offer_embedding = offer_embedding.cpu().numpy().astype(np.float32)
                            elif hasattr(offer_embedding, 'numpy'):
                                offer_embedding = offer_embedding.numpy().astype(np.float32)
                            else:
                                offer_embedding = np.array(offer_embedding, dtype=np.float32)
                            save_offer_benchmark_to_cache(
                                position_id,
                                offer_embedding,  # Già float32
                                market_df,
                                chart_cat_base64,
                                market_skills_list,
                                tenant_id=tenant_id,
                                market_json=market_json_temp,  # Passa market_json per evitare ricalcolo
                                job_language=normalized_language,
                                translated_for_benchmark=translated_for_benchmark,
                                job_description_hash=benchmark_job_description_hash,
                            )
        
        # Fallback: salva anche nel vecchio sistema con hash JD per backward compatibility
        if market_df is not None:
            jd_hash = benchmark_job_description_hash
            cache_collection = db["market_benchmark_cache"]
            cache_payload = {
                "_id": jd_hash,
                "market_data": market_df.to_dict('records'),
                "chart_cat_base64": chart_cat_base64,
                "market_skills_list": market_skills_list,
                "created_at": datetime.utcnow(),
                "job_language": normalized_language,
                "translated_for_benchmark": translated_for_benchmark,
                "benchmark_job_description_hash": benchmark_job_description_hash,
            }
            cache_collection.replace_one({"_id": jd_hash}, cache_payload, upsert=True)
            print(f"Dati di mercato salvati in cache per JD hash: {jd_hash}")

    candidate_json = {}
    try:
        normalizer = cv_normalizer_instance
        if normalizer is None:
            raise RuntimeError("CV Normalizer non è stato inizializzato.")
            
        # Anche la normalizzazione è CPU-bound, eseguiamola in un thread
        loop = asyncio.get_running_loop()
        normalized_candidate_data = await loop.run_in_executor(
            None,
            normalizer.run_normalization,    # Il nuovo metodo
            parsed_experiences,              # Il nuovo argomento
            "current_candidate"              # Il profile_id
        )

        if normalized_candidate_data and normalized_candidate_data[0].get('normalized_experiences'):
            candidate_past_experiences = normalized_candidate_data[0]['normalized_experiences'][:]
            candidate_json = {
                exp['original_title']: {
                    "durata_mesi": exp['duration_months'],
                    "mansioni_esco": [m.get('esco_title') for m in exp.get('esco_matches', [])]
                }
                for exp in candidate_past_experiences
            }
    except Exception as e:
        print(f"ERRORE durante la normalizzazione del CV: {e}")

    # Usa market_json dalla cache se disponibile, altrimenti genera da market_df (backward compatibility)
    market_json = {}
    if market_json_from_cache_async:
        # Usa market_json direttamente dalla cache (più efficiente, evitiamo ricalcolo)
        market_json = market_json_from_cache_async
        print(f"✓ Usato market_json dalla cache pre-calcolata (async) con {len(market_json)} categorie.")
    elif market_df is not None and not market_df.empty:
        # Fallback: genera da market_df se non disponibile in cache (backward compatibility)
        # Converti i valori numpy a tipi Python nativi per serializzazione
        try:
            market_json_raw = market_df.head(10).round(0).astype(int).to_dict()
            market_json = {str(k): int(v) for k, v in market_json_raw.items()}
            print("⚠ Generato market_json da market_df (backward compatibility, async).")
        except Exception as e:
            print(f"⚠ ERRORE generazione market_json da market_df (async): {e}")
            market_json = {}
    else:
        print("⚠ ATTENZIONE: market_json vuoto. Il report qualitativo potrebbe essere incompleto (async).")

    # Verifica che abbiamo i dati necessari per il confronto
    if not candidate_json:
        print("⚠ ATTENZIONE: candidate_json vuoto. Il report qualitativo potrebbe essere incompleto (async).")
    
    if not market_json:
        print("⚠ ATTENZIONE: market_json vuoto. Il report qualitativo non avrà confronto con trend di mercato (async).")
    else:
        print(f"✓ market_json caricato con {len(market_json)} categorie professionali (async).")
    
    qualitative_text = await generate_qualitative_llm_report_async(
        candidate_json=candidate_json,
        market_json=market_json,
        job_offer_text=original_job_description_text,
        language=normalized_language
    )

    return qualitative_text, chart_cat_base64, market_skills_list