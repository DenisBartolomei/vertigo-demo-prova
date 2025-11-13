"""
GPU Service - Microservizio FastAPI per gestire embedding transformer su GPU
"""
import os
import sys
import logging
import torch
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
import numpy as np
from contextlib import asynccontextmanager

from .config import (
    EMBEDDING_MODELS,
    DEFAULT_MODEL,
    MAX_BATCH_SIZE,
    DEFAULT_BATCH_SIZE,
    SERVER_HOST,
    SERVER_PORT,
    LOG_LEVEL
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global model cache
_models_cache: Dict[str, SentenceTransformer] = {}


# Pydantic models for request/response
class EmbedRequest(BaseModel):
    text: str = Field(..., description="Testo da convertire in embedding")
    model_name: Optional[str] = Field(None, description="Nome del modello da usare (default: all-MiniLM-L6-v2)")
    normalize: bool = Field(True, description="Normalizza l'embedding")


class EmbedBatchRequest(BaseModel):
    texts: List[str] = Field(..., description="Lista di testi da convertire in embedding")
    model_name: Optional[str] = Field(None, description="Nome del modello da usare (default: all-MiniLM-L6-v2)")
    normalize: bool = Field(True, description="Normalizza gli embeddings")
    batch_size: Optional[int] = Field(None, description="Dimensione del batch (default: 16)")


class EmbedResponse(BaseModel):
    embedding: List[float] = Field(..., description="Vettore embedding")
    model_name: str = Field(..., description="Modello usato")
    dimension: int = Field(..., description="Dimensione dell'embedding")


class EmbedBatchResponse(BaseModel):
    embeddings: List[List[float]] = Field(..., description="Lista di vettori embedding")
    model_name: str = Field(..., description="Modello usato")
    dimension: int = Field(..., description="Dimensione degli embeddings")
    count: int = Field(..., description="Numero di embeddings generati")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Stato del servizio")
    gpu_available: bool = Field(..., description="GPU disponibile")
    models_loaded: List[str] = Field(..., description="Modelli caricati")
    gpu_memory: Optional[Dict[str, Any]] = Field(None, description="Informazioni memoria GPU")


def load_model(model_name: str) -> SentenceTransformer:
    """
    Carica un modello di embedding, usando la cache se disponibile.
    
    Args:
        model_name: Nome del modello da caricare
        
    Returns:
        SentenceTransformer: Istanza del modello caricato
    """
    global _models_cache
    
    if model_name in _models_cache:
        logger.info(f"Modello {model_name} già caricato in cache")
        return _models_cache[model_name]
    
    if model_name not in EMBEDDING_MODELS:
        raise ValueError(f"Modello {model_name} non supportato. Modelli disponibili: {list(EMBEDDING_MODELS.keys())}")
    
    model_config = EMBEDDING_MODELS[model_name]
    device = model_config["device"]
    
    # Verifica disponibilità GPU
    if device == "cuda" and not torch.cuda.is_available():
        logger.warning(f"GPU non disponibile, uso CPU per modello {model_name}")
        device = "cpu"
    
    logger.info(f"Caricamento modello {model_name} su {device.upper()}...")
    try:
        model = SentenceTransformer(model_config["name"], device=device)
        _models_cache[model_name] = model
        logger.info(f"✅ Modello {model_name} caricato con successo su {device.upper()}")
        return model
    except Exception as e:
        logger.error(f"Errore nel caricamento del modello {model_name}: {e}")
        raise


def get_gpu_info() -> Optional[Dict[str, Any]]:
    """Ottiene informazioni sulla GPU"""
    if not torch.cuda.is_available():
        return None
    
    try:
        return {
            "device_name": torch.cuda.get_device_name(0),
            "device_count": torch.cuda.device_count(),
            "memory_allocated_mb": torch.cuda.memory_allocated(0) / 1024**2,
            "memory_reserved_mb": torch.cuda.memory_reserved(0) / 1024**2,
            "memory_total_mb": torch.cuda.get_device_properties(0).total_memory / 1024**2
        }
    except Exception as e:
        logger.error(f"Errore nel recupero info GPU: {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager per startup/shutdown"""
    # Startup: Pre-carica il modello di default
    logger.info("🚀 Avvio GPU Service...")
    logger.info(f"CUDA disponibile: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    
    try:
        # Pre-carica il modello di default
        load_model(DEFAULT_MODEL)
        logger.info(f"✅ Modello di default {DEFAULT_MODEL} pre-caricato")
    except Exception as e:
        logger.error(f"⚠️ Errore nel pre-caricamento del modello di default: {e}")
    
    yield
    
    # Shutdown: Cleanup
    logger.info("🛑 Shutdown GPU Service...")
    _models_cache.clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# Inizializza FastAPI app
app = FastAPI(
    title="GPU Embedding Service",
    description="Microservizio per generare embeddings usando GPU",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione, specificare domini esatti
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    gpu_available = torch.cuda.is_available()
    models_loaded = list(_models_cache.keys())
    gpu_memory = get_gpu_info() if gpu_available else None
    
    return HealthResponse(
        status="healthy" if models_loaded else "degraded",
        gpu_available=gpu_available,
        models_loaded=models_loaded,
        gpu_memory=gpu_memory
    )


@app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """
    Genera embedding per un singolo testo.
    
    Args:
        request: Richiesta con testo e opzioni
        
    Returns:
        EmbedResponse: Embedding generato
    """
    try:
        model_name = request.model_name or DEFAULT_MODEL
        model = load_model(model_name)
        
        # Genera embedding
        embedding = model.encode(
            request.text,
            normalize_embeddings=request.normalize,
            convert_to_numpy=True
        )
        
        return EmbedResponse(
            embedding=embedding.tolist(),
            model_name=model_name,
            dimension=len(embedding)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Errore nella generazione embedding: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/embed-batch", response_model=EmbedBatchResponse)
async def embed_batch(request: EmbedBatchRequest):
    """
    Genera embeddings per un batch di testi.
    
    Args:
        request: Richiesta con lista di testi e opzioni
        
    Returns:
        EmbedBatchResponse: Lista di embeddings generati
    """
    try:
        if not request.texts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lista testi vuota"
            )
        
        if len(request.texts) > MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch size troppo grande. Massimo: {MAX_BATCH_SIZE}"
            )
        
        model_name = request.model_name or DEFAULT_MODEL
        model = load_model(model_name)
        batch_size = request.batch_size or DEFAULT_BATCH_SIZE
        
        # Genera embeddings in batch
        embeddings = model.encode(
            request.texts,
            normalize_embeddings=request.normalize,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        return EmbedBatchResponse(
            embeddings=[emb.tolist() for emb in embeddings],
            model_name=model_name,
            dimension=len(embeddings[0]) if len(embeddings) > 0 else 0,
            count=len(embeddings)
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Errore nella generazione batch embeddings: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GPU Embedding Service",
        "version": "1.0.0",
        "status": "running",
        "gpu_available": torch.cuda.is_available(),
        "models_available": list(EMBEDDING_MODELS.keys()),
        "models_loaded": list(_models_cache.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "gpu_service.main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level=LOG_LEVEL.lower()
    )

