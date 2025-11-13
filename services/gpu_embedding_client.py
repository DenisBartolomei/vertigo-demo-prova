"""
Client library per chiamare il GPU Embedding Service
Con fallback automatico a CPU locale se il servizio non è disponibile
Con auto-start/stop della VM GPU per risparmiare costi
"""
import os
import logging
import time
import hashlib
import json
import threading
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
ENABLE_VM_AUTO_MANAGEMENT = os.getenv("ENABLE_VM_AUTO_MANAGEMENT", "true").lower() == "true"
VM_IDLE_TIMEOUT = int(os.getenv("VM_IDLE_TIMEOUT", "120"))  # 2 minuti in secondi

# Cache locale per embeddings (evita chiamate duplicate)
_embedding_cache: Dict[str, np.ndarray] = {}
CACHE_MAX_SIZE = int(os.getenv("GPU_EMBEDDING_CACHE_SIZE", "1000"))

# VM Management
_vm_manager = None
_last_activity_time: Optional[float] = None
_auto_stop_thread: Optional[threading.Thread] = None
_auto_stop_lock = threading.Lock()
_stop_auto_stop = threading.Event()


def _get_vm_manager():
    """Lazy import del VM manager per evitare dipendenze circolari"""
    global _vm_manager
    if _vm_manager is None and ENABLE_VM_AUTO_MANAGEMENT:
        try:
            from gpu_service.vm_manager import ensure_vm_running, stop_vm, get_vm_status
            _vm_manager = {
                'ensure_running': ensure_vm_running,
                'stop': stop_vm,
                'get_status': get_vm_status
            }
            logger.info("VM Manager inizializzato")
        except ImportError as e:
            logger.warning(f"Impossibile importare VM Manager: {e}. Auto-management disabilitato.")
            _vm_manager = False
    return _vm_manager


def _update_activity_time():
    """Aggiorna il timestamp dell'ultima attività"""
    global _last_activity_time
    _last_activity_time = time.time()


def _auto_stop_worker():
    """Thread worker che controlla periodicamente e spegne la VM dopo inattività"""
    global _last_activity_time
    
    while not _stop_auto_stop.is_set():
        try:
            time.sleep(10)  # Controlla ogni 10 secondi
            
            if not ENABLE_VM_AUTO_MANAGEMENT:
                continue
            
            vm_manager = _get_vm_manager()
            if not vm_manager or vm_manager is False:
                continue
            
            with _auto_stop_lock:
                if _last_activity_time is None:
                    continue
                
                idle_time = time.time() - _last_activity_time
                
                if idle_time >= VM_IDLE_TIMEOUT:
                    # Verifica che la VM sia ancora in esecuzione
                    status, _ = vm_manager['get_status']()
                    if status.value == "RUNNING":
                        logger.info(f"VM inattiva da {idle_time:.0f} secondi, spegnimento automatico...")
                        success = vm_manager['stop']()
                        if success:
                            logger.info("✅ VM spenta automaticamente per risparmio costi")
                            _last_activity_time = None
                        else:
                            logger.warning("⚠️ Impossibile spegnere la VM automaticamente")
                
        except Exception as e:
            logger.error(f"Errore nel thread auto-stop: {e}")


def _start_auto_stop_thread():
    """Avvia il thread di auto-stop se non è già in esecuzione"""
    global _auto_stop_thread
    
    if _auto_stop_thread is None or not _auto_stop_thread.is_alive():
        _stop_auto_stop.clear()
        _auto_stop_thread = threading.Thread(target=_auto_stop_worker, daemon=True)
        _auto_stop_thread.start()
        logger.debug("Thread auto-stop avviato")


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
        # Se l'URL non è fornito ma l'auto-management è abilitato, usa un placeholder
        # L'URL verrà aggiornato dinamicamente quando la VM viene avviata
        base_url = (gpu_service_url or GPU_SERVICE_URL).rstrip("/")
        if not base_url and ENABLE_VM_AUTO_MANAGEMENT:
            # Usa un placeholder, l'IP verrà recuperato quando la VM viene avviata
            base_url = "http://PLACEHOLDER:8080"
        
        self.gpu_service_url = base_url
        self.enable_gpu = enable_gpu and ENABLE_GPU_SERVICE
        self.fallback_device = fallback_device
        self.use_gpu_service = False
        self._local_models: Dict[str, SentenceTransformer] = {}
        self._base_gpu_url = base_url  # URL base (senza IP dinamico)
        
        # Avvia thread auto-stop se abilitato
        if ENABLE_VM_AUTO_MANAGEMENT:
            _start_auto_stop_thread()
        
        # Verifica disponibilità GPU service (senza avviare la VM qui)
        # Se l'auto-management è abilitato, non verifichiamo subito perché la VM potrebbe essere spenta
        if self.enable_gpu:
            if ENABLE_VM_AUTO_MANAGEMENT:
                logger.info("ℹ️ GPU Service con auto-management abilitato (VM verrà avviata on-demand)")
            elif self.gpu_service_url and "PLACEHOLDER" not in self.gpu_service_url:
                if _check_gpu_service_health(self.gpu_service_url):
                    self.use_gpu_service = True
                    logger.info(f"✅ GPU Service disponibile: {self.gpu_service_url}")
                else:
                    logger.debug(f"GPU Service non raggiungibile al momento: {self.gpu_service_url}")
            else:
                logger.info("ℹ️ GPU Service URL non configurato, uso CPU locale")
        else:
            logger.info("ℹ️ GPU Service disabilitato, uso CPU locale")
    
    def _get_local_model(self, model_name: str) -> SentenceTransformer:
        """Ottiene o carica un modello locale per fallback CPU"""
        if model_name not in self._local_models:
            logger.info(f"Caricamento modello locale {model_name} su {self.fallback_device}...")
            self._local_models[model_name] = SentenceTransformer(model_name, device=self.fallback_device)
        return self._local_models[model_name]
    
    def _ensure_vm_running(self) -> bool:
        """
        Assicura che la VM GPU sia in esecuzione, avviandola se necessario.
        
        Returns:
            True se la VM è in esecuzione o è stata avviata con successo
        """
        if not ENABLE_VM_AUTO_MANAGEMENT:
            return True  # Se auto-management è disabilitato, assume che la VM sia sempre accesa
        
        vm_manager = _get_vm_manager()
        if not vm_manager or vm_manager is False:
            return True  # Se il VM manager non è disponibile, continua comunque
        
        try:
            success, ip = vm_manager['ensure_running']()
            if success and ip:
                # Aggiorna l'URL del GPU service con l'IP corrente
                if ip:
                    # Estrai la porta dall'URL originale o usa default 8080
                    port = "8080"
                    if self._base_gpu_url:
                        # Prova a estrarre la porta dall'URL originale
                        if ":" in self._base_gpu_url:
                            parts = self._base_gpu_url.split(":")
                            if len(parts) > 2:
                                port = parts[-1].rstrip("/")
                    self.gpu_service_url = f"http://{ip}:{port}"
                    logger.info(f"GPU Service URL aggiornato: {self.gpu_service_url}")
                return True
            else:
                logger.warning("Impossibile avviare la VM GPU")
                return False
        except Exception as e:
            logger.error(f"Errore durante l'avvio della VM: {e}")
            return False
    
    def _call_gpu_service(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        retry: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Chiama il GPU service con retry logic e auto-start della VM.
        
        Args:
            endpoint: Endpoint da chiamare (es. "/embed" o "/embed-batch")
            payload: Payload della richiesta
            retry: Se True, riprova in caso di errore
            
        Returns:
            Risposta JSON o None se fallisce
        """
        if not self.enable_gpu:
            return None
        
        # Assicura che la VM sia in esecuzione
        if not self._ensure_vm_running():
            logger.warning("VM non disponibile, uso fallback CPU")
            return None
        
        # Aggiorna timestamp attività
        _update_activity_time()
        
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
                    # Aggiorna timestamp attività dopo successo
                    _update_activity_time()
                    self.use_gpu_service = True
                    return response.json()
                else:
                    logger.warning(
                        f"GPU service returned status {response.status_code}: {response.text}"
                    )
            except requests.exceptions.Timeout:
                logger.warning(f"GPU service timeout (attempt {attempt + 1}/{attempts})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"GPU service connection error (attempt {attempt + 1}/{attempts})")
                # Se c'è un errore di connessione dopo aver provato ad avviare la VM, disabilita per questa sessione
                if attempt == attempts - 1:
                    self.use_gpu_service = False
                    logger.error("GPU service non raggiungibile dopo avvio VM, disabilitato per questa sessione")
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

