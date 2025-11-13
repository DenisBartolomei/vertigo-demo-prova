# File: app/core/benchmark_cache.py
# Scopo: Gestione cache per benchmark pre-calcolati e embedding candidati

import hashlib
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any, Union
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo import UpdateOne

from recruitment_suite.config import settings
from recruitment_suite.app.core.cloud_optimizer import log_memory_usage, cleanup_tensors, monitor_memory_usage
from services.data_manager import db

def get_candidate_text_hash(candidate_data: dict) -> str:
    """
    Calcola l'hash del testo dell'esperienza del candidato per validazione cache.
    
    Args:
        candidate_data: Dizionario con dati candidato
    
    Returns:
        Hash SHA256 del testo dell'esperienza
    """
    exp_text = candidate_data.get('normalized_experiences', [{}])[0].get("llm_enriched_text", "")
    return hashlib.sha256(exp_text.encode('utf-8')).hexdigest()

def get_candidate_embedding_from_cache(profile_id: str, candidate_data: dict) -> Optional[np.ndarray]:
    """
    Carica l'embedding di un candidato dalla cache se esiste e valido.
    
    Args:
        profile_id: ID del profilo candidato
        candidate_data: Dati candidato per validazione hash
    
    Returns:
        Embedding numpy array o None se non trovato/invalido
    """
    if db is None:
        return None
    
    try:
        collection = db[settings.MONGO_COLLECTION_CANDIDATE_VECTORS]
        cached_doc = collection.find_one({"_id": profile_id})
        
        if cached_doc:
            # Backward compatibility: supporta sia "vector" (vecchia struttura) che "embedding" (nuova struttura)
            embedding_data = cached_doc.get("embedding") or cached_doc.get("vector")
            if not embedding_data:
                return None
            
            # Valida hash del testo per assicurarsi che sia ancora valido (se presente)
            current_hash = get_candidate_text_hash(candidate_data)
            cached_hash = cached_doc.get("text_hash") or cached_doc.get("offer_text_hash")
            
            # Se non c'è hash, accetta comunque (per backward compatibility con dati vecchi)
            if cached_hash and cached_hash != current_hash:
                # Hash diverso, embedding non più valido
                print(f"Cache embedding candidato {profile_id} non valido (hash cambiato).")
                return None
            
            # Converti a numpy array e normalizza a float32
            embedding_array = np.array(embedding_data, dtype=np.float32)
            return embedding_array
        
        return None
    except Exception as e:
        print(f"Errore caricamento embedding candidato da cache: {e}")
        return None

def save_candidate_embedding_to_cache(profile_id: str, embedding: np.ndarray, candidate_data: dict):
    """
    Salva l'embedding di un candidato nella cache.
    
    Args:
        profile_id: ID del profilo candidato
        embedding: Embedding numpy array
        candidate_data: Dati candidato per hash validazione
    """
    if db is None:
        return
    
    try:
        collection = db[settings.MONGO_COLLECTION_CANDIDATE_VECTORS]
        text_hash = get_candidate_text_hash(candidate_data)
        
        # Normalizza a float32 prima di salvare (più efficiente e consistente)
        embedding_float32 = embedding.astype(np.float32) if isinstance(embedding, np.ndarray) else np.array(embedding, dtype=np.float32)
        
        doc = {
            "_id": profile_id,
            "embedding": embedding_float32.tolist(),  # Converti numpy array a lista (float32)
            "text_hash": text_hash,
            "created_at": datetime.utcnow()
        }
        
        collection.replace_one({"_id": profile_id}, doc, upsert=True)
    except Exception as e:
        print(f"Errore salvataggio embedding candidato in cache: {e}")

def bulk_save_candidate_embeddings_to_cache(embeddings_batch: List[Tuple[str, np.ndarray, dict]]):
    """
    Salva un batch di embedding candidati nella cache usando bulk_write.
    
    Args:
        embeddings_batch: Lista di tuple (profile_id, embedding, candidate_data)
    """
    if db is None or not embeddings_batch:
        return
    
    try:
        collection = db[settings.MONGO_COLLECTION_CANDIDATE_VECTORS]
        operations = []
        
        for profile_id, embedding, candidate_data in embeddings_batch:
            text_hash = get_candidate_text_hash(candidate_data)
            # Normalizza a float32 prima di salvare
            embedding_float32 = embedding.astype(np.float32) if isinstance(embedding, np.ndarray) else np.array(embedding, dtype=np.float32)
            
            doc = {
                "_id": profile_id,
                "embedding": embedding_float32.tolist(),  # Converti a lista (float32)
                "text_hash": text_hash,
                "created_at": datetime.utcnow()
            }
            operations.append(UpdateOne({"_id": profile_id}, {"$set": doc}, upsert=True))
        
        if operations:
            collection.bulk_write(operations, ordered=False)
            print(f"Salvati {len(operations)} embedding candidati in cache (bulk write).")
    except Exception as e:
        print(f"Errore bulk save embedding candidati in cache: {e}")

def save_offer_benchmark_to_cache(
    position_id: str,
    offer_embedding: np.ndarray,
    market_df: Union[pd.DataFrame, pd.Series],
    chart_cat_base64: Optional[str],
    market_skills_list: Optional[List[str]],
    tenant_id: Optional[str] = None,
    market_json: Optional[dict] = None,
    job_language: Optional[str] = None,
    translated_for_benchmark: bool = False,
    job_description_hash: Optional[str] = None,
) -> bool:
    """
    Salva i risultati del benchmark di mercato per una posizione nella cache.
    
    Args:
        position_id: ID della posizione
        offer_embedding: Embedding dell'offerta
        market_df: DataFrame con risultati di mercato
        chart_cat_base64: Grafico base64 (opzionale)
        market_skills_list: Lista skill di mercato (opzionale)
        tenant_id: ID del tenant (opzionale, per multi-tenant)
        market_json: Dizionario market_json già formato (opzionale, per evitare ricalcolo)
        job_language: Lingua originale dell'annuncio
        translated_for_benchmark: True se l'annuncio è stato tradotto prima del benchmark
        job_description_hash: Hash SHA256 del testo usato per il benchmark
    
    Returns:
        True se salvato con successo, False altrimenti
    """
    if db is None:
        return False
    
    try:
        collection = db[settings.MONGO_COLLECTION_OFFER_VECTORS]
        
        # Crea chiave unica: tenant_id_position_id se tenant_id presente, altrimenti solo position_id
        cache_key = f"{tenant_id}_{position_id}" if tenant_id else position_id
        
        # Converti DataFrame o Series a dict per MongoDB
        # Se è una Series (come restituito da visualize_results), convertila in dict
        # Se è un DataFrame, convertila in records
        if market_df is not None:
            if isinstance(market_df, pd.Series):
                # Per Series, converti in dict semplice {chiave: valore}
                market_df_dict = {str(k): float(v) for k, v in market_df.to_dict().items()}
            elif not market_df.empty:
                market_df_dict = market_df.to_dict('records')
            else:
                market_df_dict = None
        else:
            market_df_dict = None
        
        # Normalizza a float32 prima di salvare
        if isinstance(offer_embedding, np.ndarray):
            offer_embedding_float32 = offer_embedding.astype(np.float32)
        else:
            offer_embedding_float32 = np.array(offer_embedding, dtype=np.float32)
        
        # Converti market_json per assicurarsi che tutti i valori siano tipi Python nativi
        market_json_serializable = None
        if market_json:
            # Assicurati che tutti i valori siano tipi Python nativi (int, float, str)
            market_json_serializable = {
                str(k): int(v) if isinstance(v, (int, np.integer)) else float(v) if isinstance(v, (float, np.floating)) else str(v)
                for k, v in market_json.items()
            }
        
        doc = {
            "_id": cache_key,
            "position_id": position_id,  # Mantieni anche position_id separato per query
            "tenant_id": tenant_id,  # Salva tenant_id per query
            "offer_embedding": offer_embedding_float32.tolist(),  # Converti a lista (float32)
            "market_df": market_df_dict,
            "market_json": market_json_serializable,  # Salva market_json per uso diretto (tipi Python nativi)
            "chart_cat_base64": chart_cat_base64,
            "market_skills_list": market_skills_list,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "job_language": job_language,
            "translated_for_benchmark": bool(translated_for_benchmark),
            "benchmark_job_description_hash": job_description_hash,
        }
        
        # Rimuovi eventuali campi None per evitare problemi con indici MongoDB
        # IMPORTANTE: Non salvare tenant_id come stringa "NULL" o "None", ma come None o non includerlo
        doc = {k: v for k, v in doc.items() if v is not None}
        
        # Verifica che tenant_id non sia una stringa "NULL" o "None" (converti a None)
        if "tenant_id" in doc and isinstance(doc["tenant_id"], str) and doc["tenant_id"].upper() in ("NULL", "NONE", ""):
            del doc["tenant_id"]
            print(f"⚠ ATTENZIONE: tenant_id era una stringa invalida, rimosso dal documento.")
        
        # Rimuovi eventuali indici problematici prima di salvare (es. job_title_1 che causa duplicate key error)
        try:
            existing_indexes = list(collection.list_indexes())
            for idx in existing_indexes:
                idx_name = idx.get('name', '')
                idx_key = idx.get('key', {})
                # Cerca indici unici su job_title
                if 'job_title' in idx_key and idx.get('unique', False):
                    print(f"⚠ Rimozione indice problematico '{idx_name}' su job_title (causa duplicate key error con null)")
                    try:
                        collection.drop_index(idx_name)
                        print(f"  ✓ Indice '{idx_name}' rimosso con successo")
                    except Exception as drop_err:
                        print(f"  ⚠ Errore durante rimozione indice '{idx_name}': {drop_err}")
        except Exception as idx_err:
            print(f"⚠ Errore durante verifica indici (non bloccante): {idx_err}")
        
        # Prova a salvare il documento
        try:
            collection.replace_one({"_id": cache_key}, doc, upsert=True)
            print(f"✓ Benchmark di mercato salvato in cache per posizione: {cache_key}")
            return True
        except Exception as save_err:
            # Se l'errore è ancora un duplicate key su job_title, prova a rimuovere l'indice e riprovare
            error_str = str(save_err)
            if "E11000" in error_str and "job_title" in error_str:
                print(f"⚠ Errore duplicate key su job_title rilevato. Tentativo rimozione indice e retry...")
                try:
                    # Prova a rimuovere tutti gli indici che contengono job_title
                    indexes_to_drop = []
                    for idx in collection.list_indexes():
                        idx_name = idx.get('name', '')
                        idx_key = idx.get('key', {})
                        if 'job_title' in idx_key:
                            indexes_to_drop.append(idx_name)
                    
                    for idx_name in indexes_to_drop:
                        try:
                            collection.drop_index(idx_name)
                            print(f"  ✓ Indice '{idx_name}' rimosso")
                        except Exception as e:
                            print(f"  ⚠ Impossibile rimuovere indice '{idx_name}': {e}")
                    
                    # Riprova il salvataggio dopo la rimozione degli indici
                    collection.replace_one({"_id": cache_key}, doc, upsert=True)
                    print(f"✓ Benchmark di mercato salvato in cache per posizione: {cache_key} (dopo rimozione indice)")
                    return True
                except Exception as retry_err:
                    print(f"✗ Errore persistente dopo rimozione indice: {retry_err}")
                    return False
            else:
                # Se è un altro tipo di errore, rilanciarlo
                raise save_err
    except Exception as e:
        print(f"✗ Errore salvataggio benchmark in cache: {e}")
        return False

def load_offer_benchmark_from_cache(position_id: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Carica i risultati del benchmark di mercato dalla cache.
    
    Args:
        position_id: ID della posizione
        tenant_id: ID del tenant (opzionale, per multi-tenant)
    
    Returns:
        Dizionario con i risultati o None se non trovato
    """
    if db is None:
        return None
    
    try:
        collection = db[settings.MONGO_COLLECTION_OFFER_VECTORS]
        
        # Verifica che tenant_id non sia una stringa "NULL" o "None"
        if tenant_id and isinstance(tenant_id, str) and tenant_id.upper() in ("NULL", "NONE", ""):
            tenant_id = None
        
        # Crea chiave unica: tenant_id_position_id se tenant_id presente, altrimenti solo position_id
        cache_key = f"{tenant_id}_{position_id}" if tenant_id else position_id
        cached_doc = collection.find_one({"_id": cache_key})
        
        # Se non trovato con tenant_id, prova anche senza tenant_id (backward compatibility)
        if not cached_doc and tenant_id:
            print(f"⚠ Tentativo fallito con tenant_id, provo senza tenant_id (backward compatibility)...")
            cached_doc = collection.find_one({"_id": position_id})
        
        if cached_doc:
            print(f"✓ Documento trovato in MongoDB collection '{settings.MONGO_COLLECTION_OFFER_VECTORS}' con _id: {cache_key}")
            
            # VERIFICA PRIMA COSA: Estrai market_json dal documento MongoDB (PRIORITÀ ASSOLUTA)
            market_json_from_doc = cached_doc.get("market_json")
            
            if market_json_from_doc:
                print(f"✓ market_json estratto dal documento MongoDB con {len(market_json_from_doc)} categorie professionali")
                # Verifica che sia un dizionario con i tipi corretti
                if isinstance(market_json_from_doc, dict):
                    sample_keys = list(market_json_from_doc.keys())[:3]
                    sample_values = [market_json_from_doc.get(k) for k in sample_keys]
                    print(f"  - Esempio chiavi: {sample_keys}")
                    print(f"  - Esempio valori: {sample_values} (tipi: {[type(v).__name__ for v in sample_values]})")
                else:
                    print(f"⚠ ATTENZIONE: market_json non è un dizionario, è: {type(market_json_from_doc)}")
                    market_json_from_doc = None
            else:
                print(f"✗ market_json NON trovato nel documento MongoDB")
            
            # Verifica che il tenant_id salvato nel documento non sia una stringa "NULL"
            doc_tenant_id = cached_doc.get("tenant_id")
            if doc_tenant_id and isinstance(doc_tenant_id, str) and doc_tenant_id.upper() in ("NULL", "NONE", ""):
                print(f"⚠ ATTENZIONE: tenant_id salvato nel documento è una stringa invalida: {doc_tenant_id}")
            
            # Ricostruisci DataFrame solo se necessario (OPZIONALE - non bloccante per market_json)
            market_df = None
            market_df_data = cached_doc.get("market_df")
            if market_df_data:
                try:
                    # Se è un dizionario semplice (Series salvato come dict), convertilo in Series
                    if isinstance(market_df_data, dict):
                        # Controlla se è un dict semplice (chiave: valore) o un dict di record
                        if market_df_data and isinstance(list(market_df_data.values())[0], dict):
                            # È una lista di record (dict di dict)
                            market_df = pd.DataFrame.from_records(list(market_df_data.values()))
                        else:
                            # È un dict semplice (Series) -> converti in Series
                            market_df = pd.Series(market_df_data)
                    elif isinstance(market_df_data, list):
                        # È una lista di record
                        if market_df_data and isinstance(market_df_data[0], dict):
                            market_df = pd.DataFrame.from_records(market_df_data)
                        else:
                            # È una lista di valori scalari -> crea Series
                            market_df = pd.Series(market_df_data)
                    else:
                        print(f"⚠ ATTENZIONE: market_df ha tipo non riconosciuto: {type(market_df_data)}")
                except Exception as e:
                    print(f"⚠ ERRORE ricostruzione market_df (NON bloccante): {e}")
                    market_df = None  # Non bloccare il recupero di market_json
            
            # Backward compatibility: supporta sia "offer_embedding" (nuova struttura) che "vector" (vecchia struttura)
            offer_embedding_array = np.array([], dtype=np.float32)
            embedding_data = cached_doc.get("offer_embedding") or cached_doc.get("vector")
            if embedding_data:
                try:
                    # Converti a numpy array e normalizza a float32
                    offer_embedding_array = np.array(embedding_data, dtype=np.float32)
                except Exception as e:
                    print(f"⚠ ERRORE ricostruzione offer_embedding (NON bloccante): {e}")
            
            return {
                "offer_embedding": offer_embedding_array,
                "market_df": market_df,  # Può essere None, non è critico
                "market_json": market_json_from_doc,  # PRIORITÀ: Questo deve essere presente!
                "chart_cat_base64": cached_doc.get("chart_cat_base64"),
                "market_skills_list": cached_doc.get("market_skills_list"),
                "created_at": cached_doc.get("created_at"),
                "updated_at": cached_doc.get("updated_at"),
                "job_language": cached_doc.get("job_language"),
                "translated_for_benchmark": cached_doc.get("translated_for_benchmark", False),
                "benchmark_job_description_hash": cached_doc.get("benchmark_job_description_hash"),
            }
        
        return None
    except Exception as e:
        print(f"✗ ERRORE caricamento benchmark da MongoDB collection '{settings.MONGO_COLLECTION_OFFER_VECTORS}': {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return None

def check_offer_benchmark_exists(position_id: str, tenant_id: Optional[str] = None) -> bool:
    """
    Verifica se esiste un benchmark pre-calcolato per una posizione.
    
    Args:
        position_id: ID della posizione
        tenant_id: ID del tenant (opzionale, per multi-tenant)
    
    Returns:
        True se esiste, False altrimenti
    """
    if db is None:
        return False
    
    try:
        collection = db[settings.MONGO_COLLECTION_OFFER_VECTORS]
        cache_key = f"{tenant_id}_{position_id}" if tenant_id else position_id
        return collection.count_documents({"_id": cache_key}) > 0
    except Exception:
        return False

def get_candidate_embeddings_batch_from_cache(
    profile_ids: List[str],
    candidates_data: List[dict]
) -> Dict[str, np.ndarray]:
    """
    Carica un batch di embedding candidati dalla cache.
    
    Args:
        profile_ids: Lista di ID profili
        candidates_data: Lista di dati candidati per validazione
    
    Returns:
        Dizionario {profile_id: embedding} per i candidati trovati in cache
    """
    if db is None or not profile_ids:
        return {}
    
    try:
        collection = db[settings.MONGO_COLLECTION_CANDIDATE_VECTORS]
        cached_docs = list(collection.find({"_id": {"$in": profile_ids}}))
        
        result = {}
        for doc in cached_docs:
            profile_id = doc["_id"]
            # Trova i dati candidato corrispondenti
            candidate_data = next((c for c in candidates_data if c.get(settings.ID_COLUMN) == profile_id), None)
            
            if candidate_data:
                # Backward compatibility: supporta sia "embedding" (nuova struttura) che "vector" (vecchia struttura)
                embedding_data = doc.get("embedding") or doc.get("vector")
                if not embedding_data:
                    continue
                
                # Valida hash se presente (backward compatibility: alcuni vecchi documenti potrebbero non averlo)
                current_hash = get_candidate_text_hash(candidate_data)
                cached_hash = doc.get("text_hash") or doc.get("offer_text_hash")
                
                # Se non c'è hash, accetta comunque (per backward compatibility)
                if cached_hash and cached_hash != current_hash:
                    continue
                
                # Converti a numpy array e normalizza a float32
                result[profile_id] = np.array(embedding_data, dtype=np.float32)
        
        return result
    except Exception as e:
        print(f"Errore caricamento batch embedding candidati da cache: {e}")
        return {}

