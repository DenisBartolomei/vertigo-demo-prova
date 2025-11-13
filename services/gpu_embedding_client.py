"""
Client library per chiamare il GPU Embedding Service
Con fallback automatico a CPU locale se il servizio non è disponibile
"""
import os
import logging
import time
import hashlib
import json
from typing import List, Optional, Union, Dict, Any
from functools import lru_cache
import requests
from sentence_transformers import SentenceTransformer
import numpy as np
import torch

logger = logging.getLogger(__name__)

# Configuration
GPU_SERVICE_URL = os.getenv("GPU_SERVICE_URL", "")
GPU_SERVICE_TIMEOUT = int(os.getenv("GPU_SERVICE_TIMEOUT", "30"))
GPU_SERVICE_RETRY_ATTEMPTS = int(os.getenv("GPU_SERVICE_RETRY_ATTEMPTS", "3"))
GPU_SERVICE_RETRY_DELAY = float(os.getenv("GPU_SERVICE_RETRY_DELAY", "1.0"))
ENABLE_GPU_SERVICE = os.getenv("ENABLE_GPU_SERVICE", "true").lower() == "true"

# Cache locale per embeddings (evita chiamate duplicate)
_embedding_cache: Dict[str, np.ndarray] = {}
CACHE_MAX_SIZE = int(os.getenv("GPU_EMBEDDING_CACHE_SIZE", "1000"))


def _get_cache_key(text: str, model_name: str, normalize: bool) -> str:
    """Genera una chiave di cache per un embedding"""
    key_str = f"{model_name}:{normalize}:{text}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _check_gpu_service_health(url: str) -> bool:
    """Verifica se il GPU service è disponibile"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.debug(f"GPU service health check failed: {e}")
        return False


class GPUEmbeddingClient:
    """
    Client per il GPU Embedding Service con fallback automatico a CPU.
    """
    
    def __init__(
        self,
        gpu_service_url: Optional[str] = None,
        enable_gpu: bool = True,
        fallback_device: str = "cpu"
    ):
        """
        Inizializza il client.
        
        Args:
            gpu_service_url: URL del GPU service (default: da env var)
            enable_gpu: Se True, prova a usare GPU service (default: True)
            fallback_device: Device da usare per fallback CPU (default: "cpu")
        """
        self.gpu_service_url = (gpu_service_url or GPU_SERVICE_URL).rstrip("/")
        self.enable_gpu = enable_gpu and ENABLE_GPU_SERVICE and bool(self.gpu_service_url)
        self.fallback_device = fallback_device
        self.use_gpu_service = False
        self._local_models: Dict[str, SentenceTransformer] = {}
        
        # Verifica disponibilità GPU service
        if self.enable_gpu and self.gpu_service_url:
            if _check_gpu_service_health(self.gpu_service_url):
                self.use_gpu_service = True
                logger.info(f"✅ GPU Service disponibile: {self.gpu_service_url}")
            else:
                logger.warning(f"⚠️ GPU Service non disponibile, uso fallback CPU: {self.gpu_service_url}")
        else:
            logger.info("ℹ️ GPU Service disabilitato o URL non configurato, uso CPU locale")
    
    def _get_local_model(self, model_name: str) -> SentenceTransformer:
        """Ottiene o carica un modello locale per fallback CPU"""
        if model_name not in self._local_models:
            logger.info(f"Caricamento modello locale {model_name} su {self.fallback_device}...")
            self._local_models[model_name] = SentenceTransformer(model_name, device=self.fallback_device)
        return self._local_models[model_name]
    
    def _call_gpu_service(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        retry: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Chiama il GPU service con retry logic.
        
        Args:
            endpoint: Endpoint da chiamare (es. "/embed" o "/embed-batch")
            payload: Payload della richiesta
            retry: Se True, riprova in caso di errore
            
        Returns:
            Risposta JSON o None se fallisce
        """
        if not self.use_gpu_service:
            return None
        
        url = f"{self.gpu_service_url}{endpoint}"
        attempts = GPU_SERVICE_RETRY_ATTEMPTS if retry else 1
        
        for attempt in range(attempts):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=GPU_SERVICE_TIMEOUT
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(
                        f"GPU service returned status {response.status_code}: {response.text}"
                    )
            except requests.exceptions.Timeout:
                logger.warning(f"GPU service timeout (attempt {attempt + 1}/{attempts})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"GPU service connection error (attempt {attempt + 1}/{attempts})")
                # Se c'è un errore di connessione, disabilita GPU service per questa sessione
                if attempt == attempts - 1:
                    self.use_gpu_service = False
                    logger.error("GPU service non raggiungibile, disabilitato per questa sessione")
            except Exception as e:
                logger.error(f"Errore nella chiamata GPU service: {e}")
            
            if attempt < attempts - 1:
                time.sleep(GPU_SERVICE_RETRY_DELAY * (2 ** attempt))  # Exponential backoff
        
        return None
    
    def embed(
        self,
        text: str,
        model_name: str = "all-MiniLM-L6-v2",
        normalize: bool = True,
        use_cache: bool = True
    ) -> np.ndarray:
        """
        Genera embedding per un singolo testo.
        
        Args:
            text: Testo da convertire in embedding
            model_name: Nome del modello da usare
            normalize: Se True, normalizza l'embedding
            use_cache: Se True, usa la cache locale
            
        Returns:
            Array numpy con l'embedding
        """
        # Controlla cache
        if use_cache:
            cache_key = _get_cache_key(text, model_name, normalize)
            if cache_key in _embedding_cache:
                logger.debug(f"Cache hit per embedding: {model_name}")
                return _embedding_cache[cache_key]
        
        # Prova GPU service
        if self.use_gpu_service:
            response = self._call_gpu_service("/embed", {
                "text": text,
                "model_name": model_name,
                "normalize": normalize
            })
            
            if response:
                embedding = np.array(response["embedding"], dtype=np.float32)
                # Salva in cache
                if use_cache:
                    cache_key = _get_cache_key(text, model_name, normalize)
                    if len(_embedding_cache) >= CACHE_MAX_SIZE:
                        # Rimuovi il primo elemento (FIFO)
                        _embedding_cache.pop(next(iter(_embedding_cache)))
                    _embedding_cache[cache_key] = embedding
                return embedding
        
        # Fallback a CPU locale
        logger.debug(f"Fallback CPU per embedding: {model_name}")
        model = self._get_local_model(model_name)
        embedding = model.encode(text, normalize_embeddings=normalize, convert_to_numpy=True)
        
        # Salva in cache
        if use_cache:
            cache_key = _get_cache_key(text, model_name, normalize)
            if len(_embedding_cache) >= CACHE_MAX_SIZE:
                _embedding_cache.pop(next(iter(_embedding_cache)))
            _embedding_cache[cache_key] = embedding
        
        return embedding
    
    def embed_batch(
        self,
        texts: List[str],
        model_name: str = "all-MiniLM-L6-v2",
        normalize: bool = True,
        batch_size: int = 16
    ) -> List[np.ndarray]:
        """
        Genera embeddings per un batch di testi.
        
        Args:
            texts: Lista di testi da convertire in embedding
            model_name: Nome del modello da usare
            normalize: Se True, normalizza gli embeddings
            batch_size: Dimensione del batch (per fallback CPU)
            
        Returns:
            Lista di array numpy con gli embeddings
        """
        if not texts:
            return []
        
        # Prova GPU service
        if self.use_gpu_service:
            response = self._call_gpu_service("/embed-batch", {
                "texts": texts,
                "model_name": model_name,
                "normalize": normalize,
                "batch_size": batch_size
            })
            
            if response:
                embeddings = [
                    np.array(emb, dtype=np.float32)
                    for emb in response["embeddings"]
                ]
                return embeddings
        
        # Fallback a CPU locale
        logger.debug(f"Fallback CPU per batch embedding: {model_name} ({len(texts)} testi)")
        model = self._get_local_model(model_name)
        embeddings = model.encode(
            texts,
            normalize_embeddings=normalize,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        return [emb for emb in embeddings]
    
    def is_gpu_available(self) -> bool:
        """Verifica se il GPU service è disponibile"""
        return self.use_gpu_service


# Singleton instance
_gpu_client_instance: Optional[GPUEmbeddingClient] = None


def get_gpu_embedding_client() -> GPUEmbeddingClient:
    """
    Ottiene l'istanza singleton del GPU embedding client.
    
    Returns:
        GPUEmbeddingClient: Istanza del client
    """
    global _gpu_client_instance
    if _gpu_client_instance is None:
        _gpu_client_instance = GPUEmbeddingClient()
    return _gpu_client_instance


def clear_embedding_cache():
    """Pulisce la cache degli embeddings"""
    global _embedding_cache
    _embedding_cache.clear()
    logger.info("Cache embeddings pulita")

