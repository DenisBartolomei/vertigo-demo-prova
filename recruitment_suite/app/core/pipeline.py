# File: app/core/pipeline.py
# Scopo: Contiene la logica principale per lo screening dei candidati contro un'offerta di lavoro.

import json
import time
import math
import openai
import numpy as np
import torch
from pydantic import ValidationError
from sentence_transformers import util
from tqdm import tqdm
from interviewer.llm_service import get_structured_llm_response
from recruitment_suite.app.models.schemas import EvaluationResponse
from recruitment_suite.config import settings
from recruitment_suite.app.core.shared_embedding_model import get_shared_embedding_model
from recruitment_suite.app.core.cloud_optimizer import log_memory_usage, cleanup_tensors, monitor_memory_usage, get_dynamic_chunk_size
from recruitment_suite.app.core.benchmark_cache import (
    get_candidate_embedding_from_cache,
    save_candidate_embedding_to_cache,
    get_candidate_embeddings_batch_from_cache,
    bulk_save_candidate_embeddings_to_cache
)

def profile_ram(stage=""):
    """Stampa l'utilizzo di RAM attuale del processo in MB."""
    log_memory_usage(stage)

class RecruitmentPipeline:
    def __init__(self):
        print("Inizializzazione della Recruitment Pipeline...")
        self.offer_embedding = None
        # Usa il modello condiviso invece di creare una nuova istanza
        self.embedding_model = get_shared_embedding_model(device="cpu")
        
    def _calculate_affinity_score(self, candidate_exp_text: str) -> float:
        if self.offer_embedding is None or not candidate_exp_text: return 0.0
        candidate_embedding = self.embedding_model.encode(candidate_exp_text, convert_to_tensor=True)
        
        # Normalizza entrambi a float32 per consistenza dtype
        offer_emb = self.offer_embedding.to(torch.float32) if self.offer_embedding.dtype != torch.float32 else self.offer_embedding
        candidate_emb = candidate_embedding.to(torch.float32) if candidate_embedding.dtype != torch.float32 else candidate_embedding
        
        return util.cos_sim(offer_emb, candidate_emb).item()

    def _get_llm_evaluation_for_batch(self, offer_title: str, offer_desc: str, batch_dossiers: list[dict]) -> list[dict]:
        profiles_text = "".join([
            f"\n--- CANDIDATO {c['original_index']+1} ---\nID: {c['id']}\nSCORE: {c['score']:.4f}\n"
            f"POSIZIONE: {c['current_position']}\nDESCRIZIONE: {c['enriched_description']}\n-----------------------\n"
            for c in batch_dossiers
        ])

        system_prompt = "Sei un recruiter esperto. Analizza i CANDIDATI per l'OFFERTA DI LAVORO. Rispondi SOLO con un oggetto JSON con una chiave 'results', contenente una lista di valutazioni."
        user_prompt = (
            f"**OFFERTA DI LAVORO**\nTitolo: {offer_title}\nDescrizione: {offer_desc}\n\n"
            f"**CANDIDATI DA VALUTARE**\n{profiles_text}\n\n"
            f"**ISTRUZIONI**\nAnalizza ogni candidato e produci un JSON. La chiave 'results' deve contenere una lista di oggetti, uno per ogni candidato. "
            f"Ogni oggetto deve avere i campi 'ID' (intero), 'scartato' (boolean) e 'motivazione' (stringa max 20 parole)."
        )

        try:
            structured = get_structured_llm_response(
                prompt=user_prompt,
                model=settings.LLM_MODEL,
                system_prompt=system_prompt,
                tool_name="save_evaluations",
                tool_schema=EvaluationResponse.model_json_schema(),
                temperature=0.2, 
                max_tokens=30000
            )
            if not structured:
                return []
            parsed = json.loads(structured)
            return parsed.get("results", [])
        except Exception as e:
            print(f"ERRORE durante la chiamata LLM per un batch: {e}. Il batch sarà saltato.")
            return []

    def run_full_pipeline(self, offer_title: str, offer_desc: str, candidates_data: list[dict]):
        # --- PROFILING INIZIALE ---
        profile_ram("Inizio Pipeline")

        offer_full_text = f"{offer_title} {offer_desc}".strip()
        print("Creazione embedding per l'offerta di lavoro...")
        self.offer_embedding = self.embedding_model.encode(offer_full_text, convert_to_tensor=True)
        
        # Normalizza a float32 per consistenza dtype (evita mismatch con embedding candidati)
        if self.offer_embedding is not None:
            self.offer_embedding = self.offer_embedding.to(torch.float32)

        profile_ram("Dopo Embedding Offerta")

        # --- FASE 1 OTTIMIZZATA: Calcolo affinità in CHUNK (Cloud Optimized) ---
        print("\n--- FASE 1: Calcolo affinità (in chunk efficienti in RAM) ---")

        # Usa chunk size dinamico basato su memoria disponibile
        CHUNK_SIZE = get_dynamic_chunk_size(base_chunk_size=settings.CLOUD_CHUNK_SIZE, max_chunk_size=16)
        print(f"Chunk size dinamico: {CHUNK_SIZE}")

        all_scores = []
        num_chunks = math.ceil(len(candidates_data) / CHUNK_SIZE)
        
        # Pre-carica embedding candidati dalla cache se disponibili
        profile_ids = [p.get(settings.ID_COLUMN) for p in candidates_data]
        cached_embeddings = get_candidate_embeddings_batch_from_cache(profile_ids, candidates_data)
        print(f"Caricati {len(cached_embeddings)} embedding candidati dalla cache")

        # Batch per salvare embedding calcolati in cache
        embeddings_to_cache = []

        for i in tqdm(range(num_chunks), desc="Calcolo Affinità a Chunk"):
            # Monitora memoria prima di ogni chunk
            is_safe, mem_percent = monitor_memory_usage(settings.CLOUD_MEMORY_THRESHOLD)
            if not is_safe:
                print(f"ATTENZIONE: Memoria elevata ({mem_percent:.1f}%). Eseguo cleanup...")
                cleanup_tensors()
            
            start_index = i * CHUNK_SIZE
            end_index = start_index + CHUNK_SIZE
            chunk_data = candidates_data[start_index:end_index]

            chunk_texts = [p.get('normalized_experiences', [{}])[0].get("llm_enriched_text", "") for p in chunk_data]
            chunk_profile_ids = [p.get(settings.ID_COLUMN) for p in chunk_data]

            # Carica embedding dalla cache o calcola
            chunk_embeddings_list = []
            for j, profile_id in enumerate(chunk_profile_ids):
                if profile_id in cached_embeddings:
                    # Usa embedding dalla cache
                    chunk_embeddings_list.append(cached_embeddings[profile_id])
                else:
                    # Calcola embedding
                    candidate_embedding = self.embedding_model.encode(
                        chunk_texts[j], convert_to_tensor=False, show_progress_bar=False
                    )
                    # Normalizza a float32 per consistenza dtype
                    candidate_embedding_float32 = np.array(candidate_embedding, dtype=np.float32)
                    chunk_embeddings_list.append(candidate_embedding_float32)
                    # Salva per cache (aggiungeremo al batch)
                    embeddings_to_cache.append((profile_id, candidate_embedding_float32, chunk_data[j]))
            
            # Converti lista a tensore per calcolo similarità
            # Assicurati che tutti gli embedding siano float32 prima di creare il tensore
            chunk_embeddings_array = np.array(chunk_embeddings_list, dtype=np.float32)
            chunk_embeddings_tensor = torch.tensor(chunk_embeddings_array, dtype=torch.float32)
            
            # Assicurati che offer_embedding sia anche float32 per consistenza
            if self.offer_embedding.dtype != torch.float32:
                self.offer_embedding = self.offer_embedding.to(torch.float32)
            
            cos_scores = util.cos_sim(self.offer_embedding, chunk_embeddings_tensor)[0]

            chunk_scores = [{'id': p[settings.ID_COLUMN], 'score': score.item(), 'profile_data': p} for p, score in zip(chunk_data, cos_scores)]
            all_scores.extend(chunk_scores)

            # Salva embedding in cache in batch periodici
            if len(embeddings_to_cache) >= settings.CLOUD_BATCH_SIZE:
                bulk_save_candidate_embeddings_to_cache(embeddings_to_cache)
                embeddings_to_cache = []

            # Cleanup tensori dopo ogni chunk
            del chunk_embeddings_tensor
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Stampa il profilo RAM periodicamente per monitorare
            if (i % 10 == 0) or (i == num_chunks - 1):
                 profile_ram(f"Fine Chunk {i+1}/{num_chunks}")

        # Salva eventuali embedding rimanenti in cache
        if embeddings_to_cache:
            bulk_save_candidate_embeddings_to_cache(embeddings_to_cache)
        
        # Cleanup finale
        cleanup_tensors()

        scores = all_scores

        print(f"\n--- FASE 2: Filtro per soglia di affinità (>{settings.AFFINITY_THRESHOLD}) ---")
        candidates_for_llm = [c for c in scores if c['score'] >= settings.AFFINITY_THRESHOLD]
        print(f"{len(candidates_for_llm)} candidati superano la soglia e saranno inviati all'LLM.")
        if not candidates_for_llm: return [], []

        print("\n--- FASE 3: Valutazione LLM in BATCH ---")
        # Questa parte era già efficiente e rimane invariata
        dossiers_for_llm = [{'id': c['id'], 'score': c['score'], 'current_position': c['profile_data'].get('current_position', 'N/D'), 'enriched_description': c['profile_data']['normalized_experiences'][0].get('llm_enriched_text', ''), 'original_index': i} for i, c in enumerate(candidates_for_llm)]

        all_llm_results = []
        num_batches = math.ceil(len(dossiers_for_llm) / settings.BATCH_SIZE)
        for i in range(num_batches):
            start_index, end_index = i * settings.BATCH_SIZE, (i + 1) * settings.BATCH_SIZE
            batch = dossiers_for_llm[start_index:end_index]
            print(f"--> Processando batch {i+1} di {num_batches} (candidati da {start_index + 1} a {min(end_index, len(dossiers_for_llm))})...")
            batch_results = self._get_llm_evaluation_for_batch(offer_title, offer_desc, batch)
            if batch_results: all_llm_results.extend(batch_results)
            print(f"<-- Batch {i+1} completato. Valutazioni totali finora: {len(all_llm_results)}")
            if i < num_batches - 1: time.sleep(1)

        print(f"\nElaborazione LLM completata. Totale valutazioni ricevute: {len(all_llm_results)} su {len(candidates_for_llm)} inviati.")
        if all_llm_results:
            try:
                with open(settings.OUTPUT_LLM_FILE, 'w', encoding='utf-8') as f: json.dump(all_llm_results, f, indent=2, ensure_ascii=False)
                print(f"Valutazione LLM salvata in '{settings.OUTPUT_LLM_FILE}'")
            except Exception as e: print(f"Errore durante il salvataggio: {e}")

        profile_ram("Fine Pipeline")

        return all_llm_results, candidates_for_llm