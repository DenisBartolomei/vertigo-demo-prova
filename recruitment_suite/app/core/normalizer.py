# File: app/core/normalizer.py
# Scopo: Contiene la logica per estrarre, parsare e normalizzare le esperienze da un singolo file CV (PDF).

import os
import json
import fitz  # PyMuPDF
import numpy as np
import pandas as pd
import torch
import openai
import asyncio
import hashlib
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as universal_date_parser
from sentence_transformers import util
from tqdm import tqdm
from interviewer.llm_service import get_llm_response, get_llm_response_async

from recruitment_suite.config import settings
from recruitment_suite.app.core.shared_embedding_model import get_shared_embedding_model
from services.gpu_embedding_client import get_gpu_embedding_client
from recruitment_suite.app.core.llm_cache import get_prompt_hash, get_cached_llm_response, save_cached_llm_response
from recruitment_suite.app.core.benchmark_cache import get_candidate_embedding_from_cache, save_candidate_embedding_to_cache

class CVNormalizer:
    def __init__(self):
        print("Inizializzazione del Normalizzatore CV...")
        # Non si valida più la chiave localmente: viene gestita da llm_service
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Usa GPU client invece del modello locale
        self.gpu_client = get_gpu_embedding_client()
        print(f"  - GPU Service disponibile: {self.gpu_client.is_gpu_available()}")
        # Mantieni embedding_model per backward compatibility (fallback)
        self.embedding_model = get_shared_embedding_model(device=self.device)
        print(f"Normalizzazione CV: Modello '{settings.EMBEDDING_MODEL_NAME}' disponibile (device richiesto: {self.device.upper()}).")

        self._prepare_esco_data()

        self.load_data_from_mongo()
    
    def load_data_from_mongo(self):
        """Carica tutti i dati necessari da MongoDB e li imposta come attributi."""
        from services.data_manager import db # Importa la connessione
    
        try:
            # Carica il DataFrame delle professioni filtrate
            collection_name_filtered = settings.MONGO_COLLECTION_OCCUPATIONS_FILTERED
            data_list = list(db[collection_name_filtered].find({}))
            self.occupations_df = pd.DataFrame(data_list)
            print(f"Caricato DataFrame 'occupations_filtered' ({len(self.occupations_df)} righe).")
    
            # Carica la gerarchia ESCO
            collection_name_hierarchy = settings.MONGO_COLLECTION_ESCO_HIERARCHY
            self.hierarchy_map = db[collection_name_hierarchy].find_one({})
            if self.hierarchy_map and '_id' in self.hierarchy_map:
                del self.hierarchy_map['_id']
            print("Caricata gerarchia ESCO.")
    
            # Carica e riassembla gli Embeddings
            collection_name_embeddings = settings.MONGO_COLLECTION_EMBEDDINGS
            embedding_id = 'embeddings'
            chunks = list(db[collection_name_embeddings].find({"embedding_id": embedding_id}).sort("chunk_index", 1))
            if not chunks:
                raise ValueError(f"Nessun embedding trovato per id '{embedding_id}'")
            
            full_list = []
            for chunk in chunks:
                full_list.extend(chunk['embeddings'])
                
            # Assegna l'array all'attributo corretto!
            self.esco_embeddings_matrix = np.array(full_list)
            print(f"Embeddings riassemblati. Shape finale: {self.esco_embeddings_matrix.shape}")
            
            # TASK 2: Pre-conversione matrice ESCO in tensor (una volta sola)
            self.esco_embeddings_tensor = torch.tensor(
                self.esco_embeddings_matrix, 
                device=self.device, 
                dtype=torch.float32
            )
            print(f"✓ Matrice ESCO pre-convertita in tensor su {self.device.upper()}")
    
        except Exception as e:
            raise RuntimeError(f"ERRORE CRITICO nel caricamento dei dati da MongoDB per CVNormalizer: {e}")

    # NUOVO CODICE per il metodo _prepare_esco_data
    def _prepare_esco_data(self):
        """
        Verifica se la collezione ESCO filtrata esiste su MongoDB.
        Se non esiste, la crea a partire dalla collezione grezza.
        """
        # Import necessari all'interno del metodo se non sono a livello di modulo
        import pandas as pd
        from recruitment_suite.config import settings
        from services.data_manager import db

        try:
            raw_collection_name = settings.MONGO_COLLECTION_OCCUPATIONS_RAW
            filtered_collection_name = settings.MONGO_COLLECTION_OCCUPATIONS_FILTERED

            # 1. Controlla se la collezione di destinazione esiste già e non è vuota
            if db[filtered_collection_name].count_documents({}) > 0:
                print(f"La collezione '{filtered_collection_name}' esiste già. Salto la preparazione.")
                return # Il lavoro è già fatto, esci dal metodo

            print(f"Collezione '{filtered_collection_name}' non trovata o vuota. Inizio preparazione dati ESCO...")

            # 2. Carica i dati dalla collezione grezza
            raw_data_list = list(db[raw_collection_name].find({}))
            if not raw_data_list:
                raise ValueError(f"La collezione sorgente '{raw_collection_name}' è vuota.")

            df = pd.DataFrame(raw_data_list)

            # 3. Applica la logica di filtro
            df.dropna(subset=['Description_it'], inplace=True)

            # 4. Salva il risultato nella collezione filtrata
            print(f"Salvataggio di {len(df)} documenti filtrati su '{filtered_collection_name}'...")
            db[filtered_collection_name].delete_many({}) # Pulisci prima di inserire
            filtered_records = df.to_dict('records')
            db[filtered_collection_name].insert_many(filtered_records)
            print("Preparazione dati ESCO su MongoDB completata.")
        except Exception as e:
            print(f"Si è verificato un errore: {e}")

    def _parse_and_filter_experiences(self, experiences: list) -> list:
        """Filtra le esperienze per parole chiave e durata minima."""
        
        valid_experiences = []
        for pos in experiences:
            title = pos.get('title', '')
            if not title or any(keyword in title.lower() for keyword in settings.NON_JOB_KEYWORDS_NORM):
                continue
            try:
                start_date = universal_date_parser(pos['start_date'])
                end_date_str = pos.get('end_date', 'present')
                end_date = datetime.now() if 'present' in end_date_str.lower() or 'oggi' in end_date_str.lower() else universal_date_parser(end_date_str)
                duration = relativedelta(end_date, start_date).years * 12 + relativedelta(end_date, start_date).months
                if duration >= settings.MIN_EXPERIENCE_MONTHS_NORM:
                    valid_experiences.append({
                        'title': title,
                        'description': pos.get('description', ''),
                        'duration_months': duration
                    })
            except (ValueError, TypeError, KeyError):
                continue # Salta se le date sono malformate
        return valid_experiences    

    def _normalize_experiences(self, valid_experiences: list) -> list:
        """
        Versione sincrona mantenuta per backward compatibility.
        Usa la versione async internamente.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._normalize_experiences_async(valid_experiences))
    
    async def _normalize_experiences_async(self, valid_experiences: list) -> list:
        """
        TASK 1: Versione ASINCRONA e PARALLELA della normalizzazione.
        Parallelizza le chiamate LLM per processare più esperienze contemporaneamente.
        """
        print("3. Normalizzazione di ogni esperienza valida (PARALLELA)...")
        print(f"   Processando {len(valid_experiences)} esperienze in parallelo...")
        
        async def normalize_single_experience(exp: dict) -> dict | None:
            """Normalizza una singola esperienza (async)"""
            print(f"  > Normalizzando '{exp['title']}'...")
            prompt = settings.LLM_PROMPT_ENRICHMENT_IT_NORM.format(
                title=exp['title'], description=exp['description']
            )
            system_prompt = "Sei un esperto di semantica HR."
            
            try:
                # TASK 3: Caching LLM responses
                prompt_hash = get_prompt_hash(prompt, system_prompt, temperature=0.15, max_tokens=800)
                raw = get_cached_llm_response(prompt_hash)
                
                if not raw:
                    # TASK 1: Chiamata LLM async (parallelizzata) - solo se non in cache
                    raw = await get_llm_response_async(
                        prompt=prompt,
                        model=settings.LLM_MODEL,
                        system_prompt=system_prompt,
                        temperature=0.15,
                        max_tokens=800
                    )
                    # Salva in cache
                    if raw and not raw.startswith("Errore"):
                        save_cached_llm_response(prompt_hash, raw)
                enriched_text = json.loads(raw).get("enriched_text")
                if enriched_text:
                    # TASK 4: Caching Embedding Esperienze
                    # Crea hash del testo arricchito per cache embedding
                    text_hash = hashlib.sha256(enriched_text.encode('utf-8')).hexdigest()
                    candidate_data_for_cache = {"normalized_experiences": [{"llm_enriched_text": enriched_text}]}
                    cached_embedding = get_candidate_embedding_from_cache(text_hash, candidate_data_for_cache)
                    
                    embedding_from_cache = False
                    if cached_embedding is not None:
                        # Usa embedding dalla cache
                        query_embedding = torch.tensor(
                            cached_embedding, 
                            device=self.device, 
                            dtype=torch.float32
                        )
                        print(f"    -> Embedding da cache")
                        embedding_from_cache = True
                    else:
                        # TASK 6: Non fare encoding qui, sarà fatto in batch dopo
                        # Segna che questo testo deve essere processato in batch
                        pass
                    
                    # TASK 2: Usa matrice ESCO pre-convertita (non convertirla ogni volta!)
                    # Nota: Se embedding_from_cache, calcola subito. Altrimenti sarà fatto in batch.
                    if embedding_from_cache:
                        cos_scores = util.cos_sim(
                            query_embedding.to(dtype=torch.float32), 
                            self.esco_embeddings_tensor
                        )[0]
                        top_results = torch.topk(cos_scores, k=settings.TOP_N_MATCHES_NORM)
                        matches = [
                            {'esco_title': self.occupations_df.iloc[idx.item()]['Title'], 'similarity': f"{score.item():.4f}"}
                            for score, idx in zip(top_results.values, top_results.indices)
                        ]
                    else:
                        # Matches verranno calcolati dopo batch encoding
                        matches = []
                    
                    result = {
                        "original_title": exp['title'],
                        "duration_months": exp['duration_months'],
                        "esco_matches": matches,
                        "enriched_text": enriched_text,  # Salva per batch encoding
                        "embedding_from_cache": embedding_from_cache  # Flag per batch processing
                    }
                    if embedding_from_cache:
                        print(f"    -> Match trovato (da cache).")
                    else:
                        print(f"    -> Arricchito, in attesa batch encoding...")
                    return result
                else:
                    print(f"    -> Arricchimento saltato (testo nullo dall'LLM).")
                    return None
            except Exception as e:
                print(f"  - ERRORE durante l'arricchimento/matching per '{exp['title']}': {e}")
                return None
        
        # TASK 1: Parallelizza tutte le chiamate LLM
        tasks = [normalize_single_experience(exp) for exp in valid_experiences]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtra risultati validi (rimuovi None ed eccezioni)
        normalized_list = []
        enriched_texts_for_batch = []  # Per TASK 6: Batch encoding
        result_indices = []  # Per mappare embeddings batch ai risultati
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  - ERRORE durante normalizzazione esperienza {i+1}: {result}")
            elif result is not None:
                # TASK 6: Raccogli testi arricchiti per batch encoding (se non già in cache)
                if result.get("enriched_text") and not result.get("embedding_from_cache"):
                    enriched_texts_for_batch.append(result["enriched_text"])
                    result_indices.append(len(normalized_list))
                
                normalized_list.append(result)
        
        # TASK 6: Batch encoding transformer (se ci sono testi da processare)
        if enriched_texts_for_batch:
            print(f"  → Encoding batch transformer per {len(enriched_texts_for_batch)} esperienze...")
            try:
                # Usa GPU client per encoding batch (più efficiente)
                embeddings_batch = self.gpu_client.embed_batch(
                    enriched_texts_for_batch,
                    model_name=settings.EMBEDDING_MODEL_NAME,
                    normalize=True,
                    batch_size=16
                )
                
                # Converti a tensore per calcolo similarità
                batch_embeddings = torch.tensor(
                    np.array(embeddings_batch, dtype=np.float32),
                    device=self.device,
                    dtype=torch.float32
                )
                
                # Mappa embeddings batch ai risultati
                for batch_idx, result_idx in enumerate(result_indices):
                    if result_idx < len(normalized_list):
                        result = normalized_list[result_idx]
                        enriched_text = result["enriched_text"]
                        
                        # Ottieni embedding dal batch (gestisci dimensioni correttamente)
                        if batch_embeddings.dim() == 2:
                            # Batch di embeddings: shape [batch_size, embedding_dim]
                            query_embedding = batch_embeddings[batch_idx:batch_idx+1]  # [1, embedding_dim]
                        else:
                            # Singolo embedding: shape [embedding_dim]
                            query_embedding = batch_embeddings[batch_idx].unsqueeze(0)  # [1, embedding_dim]
                        
                        # Assicura float32
                        query_embedding = query_embedding.to(dtype=torch.float32)
                        
                        # Calcola cosine similarity con ESCO
                        cos_scores = util.cos_sim(
                            query_embedding, 
                            self.esco_embeddings_tensor
                        )[0]
                        top_results = torch.topk(cos_scores, k=settings.TOP_N_MATCHES_NORM)
                        matches = [
                            {'esco_title': self.occupations_df.iloc[idx.item()]['Title'], 'similarity': f"{score.item():.4f}"}
                            for score, idx in zip(top_results.values, top_results.indices)
                        ]
                        
                        # Aggiorna risultato con matches
                        normalized_list[result_idx]["esco_matches"] = matches
                        
                        # Salva embedding in cache per riutilizzo futuro
                        text_hash = hashlib.sha256(enriched_text.encode('utf-8')).hexdigest()
                        # Estrai embedding come numpy array (rimuovi dimensione batch)
                        if query_embedding.dim() > 1:
                            embedding_array = query_embedding.squeeze(0).cpu().numpy().astype(np.float32)
                        else:
                            embedding_array = query_embedding.cpu().numpy().astype(np.float32)
                        candidate_data_for_cache = {"normalized_experiences": [{"llm_enriched_text": enriched_text}]}
                        save_candidate_embedding_to_cache(
                            profile_id=text_hash,
                            embedding=embedding_array,
                            candidate_data=candidate_data_for_cache
                        )
                
                print(f"    ✓ Batch encoding completato per {len(enriched_texts_for_batch)} esperienze")
            except Exception as e:
                print(f"    ⚠ Errore batch encoding: {e}, continuo con encoding sequenziale")
                # Fallback: encoding sequenziale già fatto in normalize_single_experience
        
        print(f"✓ Normalizzazione completata: {len(normalized_list)}/{len(valid_experiences)} esperienze processate con successo")
        return normalized_list

    def run_normalization(self, parsed_experiences: list, profile_id: str = "cv_profile") -> list | None:
        """
        Esegue la normalizzazione partendo da una lista di esperienze lavorative
        già estratte e parsate.

        Args:
            parsed_experiences (list): Lista di dizionari, ognuno rappresentante un'esperienza.
                                       Formato atteso: [{'title': '...', 'start_date': '...', ...}]
            profile_id (str): Un identificatore per il profilo del candidato (es. session_id).
        """
        print("\n" + "="*60 + f"\n--- ESECUZIONE NORMALIZZAZIONE PER PROFILO: {profile_id} ---\n" + "="*60)
        
        if not parsed_experiences:
            print("ERRORE: La lista di esperienze fornita è vuota.")
            return None

        # Il vecchio metodo run_normalization_from_text non serve più, 
        # perché questo metodo fa già tutto partendo dai dati.
        
        # 3. La logica di parsing e filtraggio ora lavora sui dati in input
        valid_experiences = self._parse_and_filter_experiences(parsed_experiences)
        
        if not valid_experiences:
            print("ERRORE: Nessuna esperienza lavorativa valida trovata dopo il filtraggio.")
            return None
        print(f"Trovate {len(valid_experiences)} esperienze valide da normalizzare.")

        # 4. La normalizzazione (ora async/parallela)
        normalized_experiences_list = self._normalize_experiences(valid_experiences)

        # 5. Costruisce il risultato finale
        final_result = [{"profile_id": profile_id, "normalized_experiences": normalized_experiences_list}]
        
        print(f"\nNormalizzazione completata per il profilo {profile_id}.")
        # Opzionale: puoi rimuovere il salvataggio su file se non è più necessario
        try:
            output_file = f"temp_normalization_{profile_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f: 
                json.dump(final_result, f, ensure_ascii=False, indent=2)
            print(f"Risultato di debug salvato in '{output_file}'.")
        except Exception as e:
            print(f"Errore durante il salvataggio del file di normalizzazione: {e}")

        return final_result