"""
Configurazione per il GPU Service
"""
import os
from typing import Optional

# Server Configuration
SERVER_HOST = os.getenv("GPU_SERVICE_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("GPU_SERVICE_PORT", "8080"))

# Model Configuration
EMBEDDING_MODELS = {
    "all-MiniLM-L6-v2": {
        "name": "all-MiniLM-L6-v2",
        "device": "cuda",
        "max_seq_length": 256,
        "description": "Modello leggero per RAG corsi"
    },
    "paraphrase-multilingual-mpnet-base-v2": {
        "name": "paraphrase-multilingual-mpnet-base-v2",
        "device": "cuda",
        "max_seq_length": 128,
        "description": "Modello multilingue per benchmark"
    }
}

# Default model per backward compatibility
DEFAULT_MODEL = os.getenv("GPU_SERVICE_DEFAULT_MODEL", "all-MiniLM-L6-v2")

# Batch Processing
MAX_BATCH_SIZE = int(os.getenv("GPU_SERVICE_MAX_BATCH_SIZE", "32"))
DEFAULT_BATCH_SIZE = int(os.getenv("GPU_SERVICE_DEFAULT_BATCH_SIZE", "16"))

# Performance Settings
GPU_MEMORY_FRACTION = float(os.getenv("GPU_SERVICE_MEMORY_FRACTION", "0.8"))
ENABLE_BATCH_PROCESSING = os.getenv("GPU_SERVICE_ENABLE_BATCH", "true").lower() == "true"

# Health Check
HEALTH_CHECK_INTERVAL = int(os.getenv("GPU_SERVICE_HEALTH_INTERVAL", "30"))

# Logging
LOG_LEVEL = os.getenv("GPU_SERVICE_LOG_LEVEL", "INFO")

