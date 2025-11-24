"""
WhatsApp service for tenant-aware configuration and phone mapping
"""
from typing import Optional, Dict, Any
from datetime import datetime
from backend.models.whatsapp import (
    WhatsappConfig,
    PhoneTenantMap,
    WhatsappStatus,
    ChatMessage,
    KnockoutRule
)
from services.data_manager import db


def get_whatsapp_config(tenant_id: str) -> Optional[WhatsappConfig]:
    """Recupera configurazione WhatsApp per tenant"""
    if db is None:
        return None
    
    collection = db["whatsapp_configs"]
    config_data = collection.find_one({"tenant_id": tenant_id})
    
    if config_data:
        config_data.pop("_id", None)  # Rimuovi ObjectId
        # Converti datetime strings se necessario
        if isinstance(config_data.get("created_at"), str):
            config_data["created_at"] = datetime.fromisoformat(config_data["created_at"].replace("Z", "+00:00"))
        if isinstance(config_data.get("updated_at"), str):
            config_data["updated_at"] = datetime.fromisoformat(config_data["updated_at"].replace("Z", "+00:00"))
        return WhatsappConfig(**config_data)
    
    return None


def save_whatsapp_config(config: WhatsappConfig) -> bool:
    """Salva configurazione WhatsApp per tenant"""
    if db is None:
        return False
    
    collection = db["whatsapp_configs"]
    
    # Aggiorna timestamp
    config.updated_at = datetime.utcnow()
    
    # Converti model in dict per MongoDB
    config_dict = config.model_dump()
    
    # Upsert: aggiorna se esiste, crea se non esiste
    result = collection.replace_one(
        {"tenant_id": config.tenant_id},
        config_dict,
        upsert=True
    )
    
    return result.acknowledged


def create_default_whatsapp_config(tenant_id: str) -> WhatsappConfig:
    """Crea configurazione di default per un nuovo tenant"""
    return WhatsappConfig(
        tenant_id=tenant_id,
        bot_name="Recruiter AI",
        tone="friendly",
        language="it",
        knockout_rules=[],
        screening_questions=[],
        knowledge_base={}
    )


def get_whatsapp_config_or_default(tenant_id: str) -> WhatsappConfig:
    """Recupera configurazione o crea default se non esiste"""
    config = get_whatsapp_config(tenant_id)
    if not config:
        config = create_default_whatsapp_config(tenant_id)
        save_whatsapp_config(config)
    return config


# Phone-Tenant Mapping (Global collection)
def save_phone_tenant_mapping(phone_number: str, tenant_id: str, session_id: str) -> bool:
    """Salva mappatura telefono -> tenant per risoluzione webhook"""
    if db is None:
        return False
    
    collection = db["phone_tenant_map"]
    
    mapping = PhoneTenantMap(
        phone_number=phone_number,
        tenant_id=tenant_id,
        session_id=session_id
    )
    
    # Usa phone_number come _id per lookup veloce
    result = collection.replace_one(
        {"_id": phone_number},
        {**mapping.model_dump(), "_id": phone_number},
        upsert=True
    )
    
    return result.acknowledged


def get_tenant_from_phone(phone_number: str) -> Optional[Dict[str, str]]:
    """Recupera tenant_id e session_id da numero di telefono"""
    if db is None:
        return None
    
    collection = db["phone_tenant_map"]
    mapping = collection.find_one({"_id": phone_number})
    
    if mapping:
        return {
            "tenant_id": mapping.get("tenant_id"),
            "session_id": mapping.get("session_id")
        }
    
    return None


def update_session_whatsapp_status(
    session_id: str,
    tenant_id: str,
    status: WhatsappStatus,
    chat_message: Optional[ChatMessage] = None
) -> bool:
    """Aggiorna lo stato WhatsApp di una sessione e aggiunge messaggio al log se presente"""
    if db is None:
        return False
    
    from services.tenant_service import get_tenant_collections
    collections = get_tenant_collections(tenant_id)
    sessions_collection = db[collections["sessions"]]
    
    update_data = {
        "whatsapp_status": status.value,
        "whatsapp_updated_at": datetime.utcnow()
    }
    
    # Se c'è un messaggio, aggiungilo al log
    if chat_message:
        update_data["$push"] = {
            "whatsapp_chat_log": chat_message.model_dump()
        }
    
    result = sessions_collection.update_one(
        {"_id": session_id},
        {"$set": update_data} if not chat_message else {
            "$set": {k: v for k, v in update_data.items() if k != "$push"},
            "$push": update_data["$push"]
        }
    )
    
    return result.modified_count > 0 or result.matched_count > 0


def get_session_whatsapp_data(session_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Recupera dati WhatsApp di una sessione"""
    if db is None:
        return None
    
    from services.tenant_service import get_tenant_collections
    collections = get_tenant_collections(tenant_id)
    sessions_collection = db[collections["sessions"]]
    
    session = sessions_collection.find_one({"_id": session_id})
    
    if session:
        return {
            "whatsapp_status": session.get("whatsapp_status", "ready"),
            "whatsapp_chat_log": session.get("whatsapp_chat_log", []),
            "phone_number": session.get("candidate_contact", {}).get("phone_number")
        }
    
    return None

