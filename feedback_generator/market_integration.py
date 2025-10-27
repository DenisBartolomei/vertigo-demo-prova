# File: feedback_generator/market_integration.py
import os
import sys

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
from services.data_manager import db
import asyncio



def run_market_benchmark_from_text(
    job_description_text: str,
    parsed_experiences: str,
    offer_title: str
) -> tuple[str | None, str | None, list[str] | None]:
    """
    Esegue la recruitment suite usando JD e testo del CV.
    Ritorna: (testo_qualitativo, grafico_categorie_base64, lista_delle_skill_piu_comuni)
    """
    
    # --- 1. Screening massivo per generare i dati di mercato e i grafici ---
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
        job_description_text,
        candidates_data_filtered
    )

    market_df = None
    chart_cat_base64 = None
    market_skills_list  = None

    if llm_analysis:
        promossi_llm = [p for p in llm_analysis if not p.get('scartato')]
        if promossi_llm:
            promoted_ids = {p['ID'] for p in promossi_llm}
            skill_fetcher = EscoSkillFetcher()
            final_dossiers = create_dossiers_for_promoted(promoted_ids, candidates_data_full, skill_fetcher)
            if final_dossiers:
                # --- MODIFICA CHIAVE: Cattura i 3 valori restituiti ---
                market_df, chart_cat_base64, market_skills_list  = visualize_results(final_dossiers)
    
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

    # --- 3. JSON di mercato per il report qualitativo (invariata) ---
    market_json = {}
    if market_df is not None and not market_df.empty:
        market_json = market_df.head(10).round(0).astype(int).to_dict()

    # --- 4. Generazione testo qualitativo (invariata) ---
    qualitative_text = generate_qualitative_llm_report(
    candidate_json=candidate_json,
    market_json=market_json,
    job_offer_text=job_description_text
)

    # --- 5. Restituzione dei risultati pronti per MongoDB ---
    return qualitative_text, chart_cat_base64, market_skills_list 

import hashlib
import pandas as pd
from pymongo.database import Database
import datetime
from recruitment_suite.app.reporting.qualitative import generate_qualitative_llm_report_async

async def run_market_benchmark_from_text_async(
    job_description_text: str,
    parsed_experiences: str,
    offer_title: str,
    db: Database
) -> tuple[str | None, str | None, list[str] | None]:
    
    from backend.app import recruitment_pipeline_instance, cv_normalizer_instance

    if db is None:
        print("ERRORE CRITICO: Oggetto Database non fornito.")
        return None, None, None

    jd_hash = hashlib.sha256(job_description_text.encode('utf-8')).hexdigest()
    cache_collection = db["market_benchmark_cache"]
    cached_data = cache_collection.find_one({"_id": jd_hash})
    
    market_df, chart_cat_base64, market_skills_list = None, None, None

    if cached_data:
        print(f"CACHE HIT per la JD hash: {jd_hash}. Salto il pipeline di mercato.")
        try:
            market_df = pd.DataFrame.from_records(cached_data["market_data"])
            chart_cat_base64 = cached_data.get("chart_cat_base64")
            market_skills_list = cached_data.get("market_skills_list")
        except Exception as e:
            print(f"Errore ricostruzione cache: {e}. Ricalcolo.")
            cached_data = None 
    
    if not cached_data:
        print(f"CACHE MISS per la JD hash: {jd_hash}. Eseguo il pipeline completo.")
        
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
            None, pipeline.run_full_pipeline, offer_title, job_description_text, candidates_data_filtered
        )

        if llm_analysis:
            promossi_llm = [p for p in llm_analysis if not p.get('scartato')]
            if promossi_llm:
                # Usa il nome della colonna ID dalle impostazioni per coerenza
                id_column = settings.ID_COLUMN
                promoted_ids = {p.get(id_column) for p in promossi_llm if p.get(id_column)}
                skill_fetcher = EscoSkillFetcher()
                final_dossiers = create_dossiers_for_promoted(promoted_ids, candidates_data_full, skill_fetcher)
                if final_dossiers:
                    market_df, chart_cat_base64, market_skills_list = visualize_results(final_dossiers)
        
        if market_df is not None:
            cache_payload = {
                "_id": jd_hash, "market_data": market_df.to_dict('records'),
                "chart_cat_base64": chart_cat_base64, "market_skills_list": market_skills_list,
                "created_at": datetime.utcnow()
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

    market_json = {}
    if market_df is not None and not market_df.empty:
        market_json = market_df.head(10).round(0).astype(int).to_dict()

    qualitative_text = await generate_qualitative_llm_report_async(
        candidate_json=candidate_json, market_json=market_json, job_offer_text=job_description_text
    )

    return qualitative_text, chart_cat_base64, market_skills_list