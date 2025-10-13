# services/interview_config_service.py

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import os
from datetime import datetime

from .data_manager import db

class InterviewConfig(BaseModel):
    """Configurazione intervista per tenant"""
    tenant_id: str
    reasoning_steps: int = Field(default=4, ge=2, le=6, description="Numero di reasoning steps (da 2 a 6)")
    max_attempts: int = Field(default=5, ge=2, le=5, description="Numero massimo di tentativi per step (da 2 a 5)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def estimated_duration_minutes(self) -> int:
        """Stima durata massima in minuti (1.5 minuti per attempt)"""
        return int((self.reasoning_steps * self.max_attempts * 1.5) + 5)  # +5 minuti per setup
    
    @property
    def max_questions(self) -> int:
        """Calcola numero massimo di domande basato sulla configurazione"""
        # Formula: 2 domande per reasoning step + 3 domande base
        return (self.reasoning_steps * 2) + 3

def get_interview_config(tenant_id: str) -> Optional[InterviewConfig]:
    """Recupera configurazione intervista per tenant"""
    if db is None:
        return None
    
    collection = db["interview_configs"]
    config_data = collection.find_one({"tenant_id": tenant_id})
    
    if config_data:
        config_data.pop("_id", None)  # Rimuovi ObjectId
        return InterviewConfig(**config_data)
    
    return None

def save_interview_config(config: InterviewConfig) -> bool:
    """Salva configurazione intervista per tenant"""
    if db is None:
        return False
    
    collection = db["interview_configs"]
    
    # Aggiorna timestamp
    config.updated_at = datetime.utcnow()
    
    # Upsert: aggiorna se esiste, crea se non esiste
    result = collection.replace_one(
        {"tenant_id": config.tenant_id},
        config.model_dump(),
        upsert=True
    )
    
    return result.acknowledged

def create_default_config(tenant_id: str) -> InterviewConfig:
    """Crea configurazione di default per un nuovo tenant"""
    return InterviewConfig(
        tenant_id=tenant_id,
        reasoning_steps=4,
        max_attempts=5
    )

def get_interview_config_or_default(tenant_id: str) -> InterviewConfig:
    """Recupera configurazione o crea default se non esiste"""
    config = get_interview_config(tenant_id)
    if not config:
        config = create_default_config(tenant_id)
        save_interview_config(config)
    return config
