"""
Gestore per avviare e spegnere la VM GPU su Google Cloud Compute Engine
"""
import os
import subprocess
import logging
import time
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", os.getenv("PROJECT_ID", "poetic-orb-474016-q7"))
ZONE = os.getenv("GCP_ZONE", os.getenv("ZONE", "europe-west8-a"))
VM_NAME = os.getenv("GPU_VM_NAME", "vertigo-gpu-service")


class VMStatus(Enum):
    """Stati possibili della VM"""
    RUNNING = "RUNNING"
    STOPPED = "TERMINATED"
    STOPPING = "STOPPING"
    STARTING = "STARTING"
    UNKNOWN = "UNKNOWN"


def get_vm_status() -> Tuple[VMStatus, Optional[str]]:
    """
    Ottiene lo stato corrente della VM.
    
    Returns:
        Tuple di (VMStatus, IP esterno o None)
    """
    try:
        result = subprocess.run(
            [
                "gcloud", "compute", "instances", "describe", VM_NAME,
                "--zone", ZONE,
                "--project", PROJECT_ID,
                "--format", "value(status,networkInterfaces[0].accessConfigs[0].natIP)"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning(f"Impossibile ottenere stato VM: {result.stderr}")
            return VMStatus.UNKNOWN, None
        
        output = result.stdout.strip()
        if not output:
            return VMStatus.UNKNOWN, None
        
        parts = output.split("\t")
        status_str = parts[0] if parts else ""
        ip = parts[1] if len(parts) > 1 and parts[1] else None
        
        # Mappa gli stati GCP agli enum
        status_map = {
            "RUNNING": VMStatus.RUNNING,
            "TERMINATED": VMStatus.STOPPED,
            "STOPPING": VMStatus.STOPPING,
            "STARTING": VMStatus.STARTING,
        }
        
        status = status_map.get(status_str, VMStatus.UNKNOWN)
        return status, ip
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout durante il controllo dello stato della VM")
        return VMStatus.UNKNOWN, None
    except Exception as e:
        logger.error(f"Errore durante il controllo dello stato della VM: {e}")
        return VMStatus.UNKNOWN, None


def start_vm() -> Tuple[bool, Optional[str]]:
    """
    Avvia la VM se è spenta.
    
    Returns:
        Tuple di (successo, IP esterno o None)
    """
    status, ip = get_vm_status()
    
    if status == VMStatus.RUNNING:
        logger.info(f"VM già in esecuzione, IP: {ip}")
        return True, ip
    
    if status == VMStatus.STARTING:
        logger.info("VM già in avvio, attendo...")
        # Attendi che la VM si avvii
        max_wait = 120  # 2 minuti max
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(5)
            wait_time += 5
            status, ip = get_vm_status()
            if status == VMStatus.RUNNING:
                logger.info(f"VM avviata, IP: {ip}")
                return True, ip
            elif status == VMStatus.STOPPED:
                logger.warning("VM si è fermata durante l'avvio")
                break
        
        logger.error("Timeout durante l'avvio della VM")
        return False, None
    
    if status == VMStatus.STOPPED:
        logger.info(f"Avvio VM {VM_NAME}...")
        try:
            result = subprocess.run(
                [
                    "gcloud", "compute", "instances", "start", VM_NAME,
                    "--zone", ZONE,
                    "--project", PROJECT_ID
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Errore durante l'avvio della VM: {result.stderr}")
                return False, None
            
            # Attendi che la VM si avvii completamente
            logger.info("Attesa che la VM si avvii...")
            max_wait = 120  # 2 minuti max
            wait_time = 0
            while wait_time < max_wait:
                time.sleep(5)
                wait_time += 5
                status, ip = get_vm_status()
                if status == VMStatus.RUNNING:
                    logger.info(f"✅ VM avviata con successo, IP: {ip}")
                    return True, ip
                elif status == VMStatus.STOPPED:
                    logger.error("VM si è fermata durante l'avvio")
                    return False, None
            
            logger.error("Timeout durante l'avvio della VM")
            return False, None
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout durante il comando di avvio della VM")
            return False, None
        except Exception as e:
            logger.error(f"Errore durante l'avvio della VM: {e}")
            return False, None
    
    logger.warning(f"Stato VM non gestibile: {status}")
    return False, None


def stop_vm() -> bool:
    """
    Spegne la VM se è in esecuzione.
    
    Returns:
        True se lo spegnimento è riuscito o la VM era già spenta
    """
    status, _ = get_vm_status()
    
    if status == VMStatus.STOPPED:
        logger.info("VM già spenta")
        return True
    
    if status == VMStatus.STOPPING:
        logger.info("VM già in spegnimento, attendo...")
        # Attendi che la VM si spenga
        max_wait = 60  # 1 minuto max
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(5)
            wait_time += 5
            status, _ = get_vm_status()
            if status == VMStatus.STOPPED:
                logger.info("VM spenta")
                return True
        
        logger.warning("Timeout durante lo spegnimento della VM")
        return False
    
    if status == VMStatus.RUNNING:
        logger.info(f"Spegnimento VM {VM_NAME}...")
        try:
            result = subprocess.run(
                [
                    "gcloud", "compute", "instances", "stop", VM_NAME,
                    "--zone", ZONE,
                    "--project", PROJECT_ID
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                logger.error(f"Errore durante lo spegnimento della VM: {result.stderr}")
                return False
            
            logger.info("✅ VM spenta con successo")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout durante il comando di spegnimento della VM")
            return False
        except Exception as e:
            logger.error(f"Errore durante lo spegnimento della VM: {e}")
            return False
    
    logger.warning(f"Stato VM non gestibile per lo spegnimento: {status}")
    return False


def ensure_vm_running() -> Tuple[bool, Optional[str]]:
    """
    Assicura che la VM sia in esecuzione, avviandola se necessario.
    
    Returns:
        Tuple di (successo, IP esterno o None)
    """
    return start_vm()

