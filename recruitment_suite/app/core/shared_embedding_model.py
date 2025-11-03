# File: recruitment_suite/app/core/shared_embedding_model.py
# Scopo: Fornisce un servizio singleton per condividere l'istanza del modello di embedding
# tra RecruitmentPipeline e CVNormalizer, evitando duplicazione di memoria (~450MB)

from sentence_transformers import SentenceTransformer
from recruitment_suite.config import settings

# Cache globale per l'istanza del modello condivisa
_shared_model_instance = None
_model_device = None


def get_shared_embedding_model(device="cpu"):
    """
    Restituisce un'istanza singleton del modello di embedding condiviso.
    
    Args:
        device (str): Dispositivo su cui caricare il modello ("cpu" o "cuda").
                     Il primo chiamante determina il device usato.
                     Default: "cpu" per compatibilità Cloud Run.
    
    Returns:
        SentenceTransformer: Istanza condivisa del modello di embedding.
    """
    global _shared_model_instance, _model_device
    
    # Se il modello non è ancora stato caricato, lo carica
    if _shared_model_instance is None:
        print(f"📦 [SHARED MODEL] Caricamento modello '{settings.EMBEDDING_MODEL_NAME}' su {device.upper()}...")
        _shared_model_instance = SentenceTransformer(
            settings.EMBEDDING_MODEL_NAME,
            device=device
        )
        _model_device = device
        print(f"✅ [SHARED MODEL] Modello '{settings.EMBEDDING_MODEL_NAME}' caricato e pronto (device: {device.upper()})")
    else:
        # Il modello è già caricato, verifica che il device richiesto sia compatibile
        if device != _model_device:
            print(f"⚠️  [SHARED MODEL] Richiesto device '{device}' ma modello già caricato su '{_model_device}'. Usando istanza esistente.")
    
    return _shared_model_instance

