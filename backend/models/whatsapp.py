"""
Pydantic models for WhatsApp integration
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class BotTone(str, Enum):
    """Tono di voce del bot"""
    FORMAL = "formal"
    FRIENDLY = "friendly"
    ENTHUSIASTIC = "enthusiastic"


class KnockoutRule(BaseModel):
    """Regola knock-out: se il candidato non risponde correttamente, viene squalificato"""
    question: str = Field(..., description="Domanda da porre al candidato")
    expected_answer: str = Field(..., description="Risposta attesa (può essere una parola chiave o frase)")
    rejection_message: str = Field(..., description="Messaggio da inviare se la risposta non corrisponde")


class WhatsappConfig(BaseModel):
    """Configurazione WhatsApp per tenant"""
    tenant_id: str
    bot_name: str = Field(default="Recruiter AI", description="Nome del bot")
    tone: BotTone = Field(default=BotTone.FRIENDLY, description="Tono di voce del bot")
    language: str = Field(default="it", description="Lingua di default (it, en, ecc.)")
    
    # Template message name (deve essere approvato da Meta)
    template_name: Optional[str] = Field(default=None, description="Nome del template approvato da Meta")
    
    # Regole knock-out
    knockout_rules: List[KnockoutRule] = Field(default_factory=list, description="Domande obbligatorie che squalificano se fallite")
    
    # Domande di screening
    screening_questions: List[str] = Field(default_factory=list, description="Lista di domande aperte per lo screening")
    
    # Knowledge base per rispondere alle domande del candidato
    knowledge_base: Dict[str, Any] = Field(
        default_factory=dict,
        description="Informazioni utili (RAL, sede, smart working, ecc.) che l'AI può usare per rispondere"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class WhatsappStatus(str, Enum):
    """Stati possibili della conversazione WhatsApp"""
    READY = "ready"  # Numero presente, mai contattato
    SENT = "sent"  # Messaggio inviato, in attesa risposta
    ACTIVE = "active"  # Conversazione in corso (finestra 24h aperta)
    QUALIFIED = "qualified"  # Screening superato
    DISQUALIFIED = "disqualified"  # Screening fallito
    EXPIRED = "expired"  # Nessuna risposta entro 24h


class ChatMessage(BaseModel):
    """Singolo messaggio nella conversazione"""
    sender: str = Field(..., description="'bot' o 'user'")
    text: str = Field(..., description="Contenuto del messaggio")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_id: Optional[str] = Field(default=None, description="ID messaggio da Meta (wamid)")


class PhoneTenantMap(BaseModel):
    """Mappatura globale telefono -> tenant per risolvere il tenant dal webhook"""
    phone_number: str = Field(..., description="Numero di telefono (formato internazionale)")
    tenant_id: str = Field(..., description="ID del tenant")
    session_id: str = Field(..., description="ID della sessione candidato")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        # Usa phone_number come _id per lookup veloce
        pass


# Models per i payload Meta API
class MetaWebhookMessage(BaseModel):
    """Payload del webhook Meta per messaggi in arrivo"""
    from_number: str
    message_id: str
    text: Optional[str] = None
    timestamp: str


class MetaWebhookStatus(BaseModel):
    """Payload del webhook Meta per status delivery"""
    message_id: str
    status: str  # sent, delivered, read, failed
    timestamp: str

