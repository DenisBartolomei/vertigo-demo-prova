# File: app/core/llm_cache.py
# Scopo: Caching intelligente per risposte LLM basato su hash del prompt

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional
from services.data_manager import db
from recruitment_suite.config import settings

# Configurazione cache
LLM_CACHE_COLLECTION = "suite_llm_cache"
LLM_CACHE_ENABLED = getattr(settings, 'LLM_CACHE_ENABLED', True)
LLM_CACHE_TTL_DAYS = getattr(settings, 'LLM_CACHE_TTL_DAYS', 7)

def get_prompt_hash(prompt: str, system_prompt: str = "", **kwargs) -> str:
    """
    Genera un hash univoco per un prompt LLM.
    
    Args:
        prompt: Prompt principale
        system_prompt: System prompt
        **kwargs: Parametri aggiuntivi (temperature, max_tokens, ecc.)
    
    Returns:
        Hash SHA256 del prompt
    """
    # Normalizza il prompt (rimuovi spazi extra, lowercase per case-insensitive)
    normalized_prompt = prompt.strip().lower()
    normalized_system = system_prompt.strip().lower()
    
    # Crea un dict con tutti i parametri rilevanti per il cache key
    cache_key_data = {
        "prompt": normalized_prompt,
        "system_prompt": normalized_system,
        # Include solo parametri che influenzano la risposta
        "temperature": kwargs.get("temperature"),
        "max_tokens": kwargs.get("max_tokens"),
    }
    
    # Serializza in JSON e genera hash
    cache_key_str = json.dumps(cache_key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(cache_key_str.encode('utf-8')).hexdigest()

def get_cached_llm_response(prompt_hash: str) -> Optional[str]:
    """
    Recupera una risposta LLM dalla cache se disponibile e non scaduta.
    
    Args:
        prompt_hash: Hash del prompt
    
    Returns:
        Risposta cached o None se non trovata/scaduta
    """
    if not LLM_CACHE_ENABLED or db is None:
        return None
    
    try:
        collection = db[LLM_CACHE_COLLECTION]
        cached_doc = collection.find_one({"_id": prompt_hash})
        
        if not cached_doc:
            return None
        
        # Verifica se la cache è scaduta
        expires_at = cached_doc.get("expires_at")
        if expires_at:
            if datetime.utcnow() > expires_at:
                # Cache scaduta, rimuovila
                collection.delete_one({"_id": prompt_hash})
                return None
        
        response = cached_doc.get("response")
        if response:
            print(f"✓ Cache HIT per prompt hash: {prompt_hash[:8]}...")
            return response
        
        return None
    except Exception as e:
        print(f"⚠ Errore recupero cache LLM: {e}")
        return None

def save_cached_llm_response(prompt_hash: str, response: str) -> bool:
    """
    Salva una risposta LLM nella cache.
    
    Args:
        prompt_hash: Hash del prompt
        response: Risposta LLM da cacheare
    
    Returns:
        True se salvato con successo, False altrimenti
    """
    if not LLM_CACHE_ENABLED or db is None:
        return False
    
    try:
        collection = db[LLM_CACHE_COLLECTION]
        expires_at = datetime.utcnow() + timedelta(days=LLM_CACHE_TTL_DAYS)
        
        doc = {
            "_id": prompt_hash,
            "response": response,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at
        }
        
        collection.replace_one({"_id": prompt_hash}, doc, upsert=True)
        print(f"✓ Cache SAVED per prompt hash: {prompt_hash[:8]}... (expires in {LLM_CACHE_TTL_DAYS} days)")
        return True
    except Exception as e:
        print(f"⚠ Errore salvataggio cache LLM: {e}")
        return False

def clear_expired_cache() -> int:
    """
    Rimuove tutte le entry di cache scadute.
    
    Returns:
        Numero di entry rimosse
    """
    if db is None:
        return 0
    
    try:
        collection = db[LLM_CACHE_COLLECTION]
        result = collection.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
        deleted_count = result.deleted_count
        if deleted_count > 0:
            print(f"✓ Rimossi {deleted_count} entry di cache LLM scadute")
        return deleted_count
    except Exception as e:
        print(f"⚠ Errore pulizia cache LLM: {e}")
        return 0






