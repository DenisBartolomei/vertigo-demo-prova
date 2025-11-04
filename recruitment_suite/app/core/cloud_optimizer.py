# File: app/core/cloud_optimizer.py
# Scopo: Utility per ottimizzazioni cloud-specific: monitoraggio memoria, cleanup tensori, batch processing dinamico

import psutil
import os
import torch
import gc
from typing import Optional, Tuple
import time

def get_memory_usage_mb() -> float:
    """Restituisce l'uso di RAM in MB per il processo corrente."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss / 1024 ** 2

def get_memory_usage_percent() -> float:
    """Restituisce l'uso di RAM come percentuale della RAM totale disponibile."""
    process = psutil.Process(os.getpid())
    return process.memory_percent()

def check_memory_threshold(threshold_percent: float = 80.0) -> bool:
    """
    Verifica se l'uso di memoria supera la soglia specificata.
    
    Args:
        threshold_percent: Soglia percentuale (default 80%)
    
    Returns:
        True se la memoria è sotto la soglia, False altrimenti
    """
    usage_percent = get_memory_usage_percent()
    return usage_percent < threshold_percent

def log_memory_usage(stage: str = ""):
    """Logga l'uso di memoria corrente."""
    usage_mb = get_memory_usage_mb()
    usage_percent = get_memory_usage_percent()
    print(f"[{stage}] Utilizzo RAM: {usage_mb:.2f} MB ({usage_percent:.1f}%)")

def cleanup_tensors():
    """Pulisce esplicitamente i tensori PyTorch dalla memoria."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

def cleanup_and_log(stage: str = ""):
    """Esegue cleanup e logga l'uso di memoria."""
    cleanup_tensors()
    log_memory_usage(stage)

def get_dynamic_chunk_size(base_chunk_size: int = 16, max_chunk_size: int = 32) -> int:
    """
    Calcola un chunk size dinamico basato sulla memoria disponibile.
    Ottimizzato per cloud con 6GB RAM: chunk più grandi per migliorare throughput.
    
    Args:
        base_chunk_size: Chunk size minimo (default 16, aumentato per cloud)
        max_chunk_size: Chunk size massimo (default 32, aumentato per cloud)
    
    Returns:
        Chunk size ottimale basato sulla memoria disponibile
    """
    usage_percent = get_memory_usage_percent()
    
    if usage_percent < 40:
        # Memoria abbondante (< 40%), possiamo usare chunk più grandi
        return max_chunk_size
    elif usage_percent < 65:
        # Memoria media (40-65%), chunk medio
        return (base_chunk_size + max_chunk_size) // 2
    elif usage_percent < 85:
        # Memoria in uso (65-85%), chunk base
        return base_chunk_size
    else:
        # Memoria critica (> 85%), chunk ridotto
        return max(8, base_chunk_size // 2)

def safe_operation(operation, max_retries: int = 3, retry_delay: float = 1.0):
    """
    Esegue un'operazione con retry logic e gestione errori.
    
    Args:
        operation: Funzione da eseguire
        max_retries: Numero massimo di tentativi
        retry_delay: Delay tra i tentativi in secondi
    
    Returns:
        Risultato dell'operazione o None se fallisce
    """
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Tentativo {attempt + 1} fallito: {e}. Retry tra {retry_delay}s...")
                time.sleep(retry_delay)
                cleanup_tensors()  # Pulisci memoria prima di retry
            else:
                print(f"Operazione fallita dopo {max_retries} tentativi: {e}")
                raise
    return None

def monitor_memory_usage(threshold_percent: float = 80.0) -> Tuple[bool, float]:
    """
    Monitora l'uso di memoria e verifica se è sotto la soglia.
    
    Args:
        threshold_percent: Soglia percentuale (default 80%)
    
    Returns:
        Tuple (is_safe, usage_percent): True se sicuro, percentuale uso
    """
    usage_percent = get_memory_usage_percent()
    is_safe = usage_percent < threshold_percent
    
    if not is_safe:
        print(f"ATTENZIONE: Uso memoria elevato ({usage_percent:.1f}%). Eseguo cleanup...")
        cleanup_tensors()
        usage_percent = get_memory_usage_percent()
        is_safe = usage_percent < threshold_percent
    
    return is_safe, usage_percent

