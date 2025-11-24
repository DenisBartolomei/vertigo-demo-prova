"""
WhatsApp router for FastAPI
"""
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from services.whatsapp_service import (
    get_whatsapp_config,
    save_whatsapp_config,
    get_whatsapp_config_or_default,
    save_phone_tenant_mapping,
    get_tenant_from_phone,
    update_session_whatsapp_status,
    get_session_whatsapp_data
)
from services.whatsapp_ai import process_whatsapp_message
from services.whatsapp_client import WhatsAppClient
from services.auth_service import verify_jwt
from services.tenant_service import get_tenant_collections
from backend.models.whatsapp import (
    WhatsappConfig,
    WhatsappStatus,
    ChatMessage,
    KnockoutRule
)
from datetime import datetime

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def get_tenant_from_auth(authorization: str | None = Header(default=None)):
    """Helper per estrarre tenant_id dal token JWT"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = authorization.split(" ", 1)[1]
    auth_data = verify_jwt(token)
    tenant_id = auth_data.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing tenant_id")
    
    return tenant_id


# ========== CONFIGURAZIONE ENDPOINTS ==========

@router.get("/config")
async def get_config(tenant_id: str = Depends(get_tenant_from_auth)):
    """Recupera configurazione WhatsApp per il tenant corrente"""
    config = get_whatsapp_config_or_default(tenant_id)
    return config.model_dump()


@router.put("/config")
async def update_config(
    config: WhatsappConfig,
    tenant_id: str = Depends(get_tenant_from_auth)
):
    """Aggiorna configurazione WhatsApp per il tenant corrente"""
    # Forza il tenant_id dal token (sicurezza)
    config.tenant_id = tenant_id
    
    success = save_whatsapp_config(config)
    if not success:
        raise HTTPException(status_code=500, detail="Errore nel salvataggio configurazione")
    
    return {"message": "Configurazione salvata con successo", "config": config.model_dump()}


@router.get("/config/validate-credentials")
async def validate_credentials(tenant_id: str = Depends(get_tenant_from_auth)):
    """Valida che le credenziali WhatsApp siano corrette"""
    try:
        client = WhatsAppClient()
        is_valid = client.validate_credentials()
        return {"valid": is_valid}
    except Exception as e:
        return {"valid": False, "error": str(e)}


# ========== INGAGGIO CANDIDATO ==========

class EngageCandidateRequest(BaseModel):
    """Request per ingaggiare un candidato via WhatsApp"""
    session_id: str
    phone_number: str  # Formato internazionale senza +


@router.post("/engage")
async def engage_candidate(
    request: EngageCandidateRequest,
    tenant_id: str = Depends(get_tenant_from_auth)
):
    """
    Invia il Template Message iniziale a un candidato
    Questo è il primo messaggio (a pagamento)
    """
    # Verifica che la sessione appartenga al tenant
    collections = get_tenant_collections(tenant_id)
    from services.data_manager import db
    session = db[collections["sessions"]].find_one({"_id": request.session_id})
    
    if not session:
        raise HTTPException(status_code=404, detail="Sessione non trovata")
    
    # Carica configurazione
    config = get_whatsapp_config_or_default(tenant_id)
    
    if not config.template_name:
        raise HTTPException(
            status_code=400,
            detail="Template message non configurato. Configura un template nella pagina WhatsApp Setup."
        )
    
    # Prepara il numero (rimuovi + se presente, aggiungi se manca)
    phone = request.phone_number.replace("+", "").strip()
    if not phone.startswith("39"):  # Assumiamo numeri italiani per default
        # Potresti voler gestire altri paesi
        pass
    
    try:
        # Invia template message
        client = WhatsAppClient()
        
        # Estrai nome candidato se disponibile
        candidate_name = session.get("candidate_name", "Candidato")
        components = [{
            "type": "body",
            "parameters": [
                {
                    "type": "text",
                    "text": candidate_name.split()[0] if candidate_name else "Candidato"
                }
            ]
        }] if candidate_name else None
        
        response = client.send_template_message(
            to=phone,
            template_name=config.template_name,
            language_code=config.language,
            components=components
        )
        
        # Salva mappatura telefono -> tenant
        save_phone_tenant_mapping(phone, tenant_id, request.session_id)
        
        # Aggiorna stato sessione
        update_session_whatsapp_status(
            request.session_id,
            tenant_id,
            WhatsappStatus.SENT
        )
        
        # Salva messaggio inviato nel log
        bot_message = ChatMessage(
            sender="bot",
            text=f"[Template: {config.template_name}]",
            message_id=response.get("messages", [{}])[0].get("id") if response.get("messages") else None
        )
        update_session_whatsapp_status(
            request.session_id,
            tenant_id,
            WhatsappStatus.SENT,
            bot_message
        )
        
        return {
            "message": "Messaggio inviato con successo",
            "message_id": response.get("messages", [{}])[0].get("id") if response.get("messages") else None
        }
        
    except Exception as e:
        print(f"Errore invio messaggio WhatsApp: {e}")
        raise HTTPException(status_code=500, detail=f"Errore invio messaggio: {str(e)}")


# ========== WEBHOOK ENDPOINTS ==========

@router.get("/webhook")
async def webhook_verify(
    hub_mode: str,
    hub_verify_token: str,
    hub_challenge: str
):
    """
    Endpoint per la verifica del webhook da parte di Meta
    Meta chiama questo endpoint quando configuri il webhook nella dashboard
    """
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return int(hub_challenge)
    else:
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def webhook_receive(request: Request):
    """
    Endpoint per ricevere messaggi e status da Meta
    Questo è chiamato ogni volta che arriva un messaggio o cambia lo status
    """
    try:
        payload = await request.json()
        
        # Meta invia notifiche in questo formato
        entry = payload.get("entry", [])
        if not entry:
            return {"status": "ok"}
        
        for entry_item in entry:
            changes = entry_item.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                
                # Gestione messaggi in arrivo
                messages = value.get("messages", [])
                for message in messages:
                    await handle_incoming_message(message, value)
                
                # Gestione status (opzionale, per tracking delivery)
                statuses = value.get("statuses", [])
                for status in statuses:
                    await handle_status_update(status)
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"Errore webhook WhatsApp: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


async def handle_incoming_message(message: Dict[str, Any], value: Dict[str, Any]):
    """Gestisce un messaggio in arrivo dal candidato"""
    from_phone = message.get("from")
    message_id = message.get("id")
    text = message.get("text", {}).get("body")
    timestamp = message.get("timestamp")
    
    if not text or not from_phone:
        return
    
    # Rimuovi prefisso + se presente
    from_phone = from_phone.replace("+", "")
    
    # Trova tenant e sessione dal numero
    mapping = get_tenant_from_phone(from_phone)
    if not mapping:
        print(f"⚠️ Messaggio da numero sconosciuto: {from_phone}")
        return
    
    tenant_id = mapping["tenant_id"]
    session_id = mapping["session_id"]
    
    # Carica configurazione tenant
    config = get_whatsapp_config_or_default(tenant_id)
    
    # Recupera storia conversazione dalla sessione
    from services.data_manager import db
    from services.tenant_service import get_tenant_collections
    collections = get_tenant_collections(tenant_id)
    session = db[collections["sessions"]].find_one({"_id": session_id})
    
    conversation_history = session.get("whatsapp_chat_log", []) if session else []
    candidate_name = session.get("candidate_name", "Candidato") if session else "Candidato"
    
    # Salva messaggio utente nel log
    user_message = ChatMessage(
        sender="user",
        text=text,
        message_id=message_id,
        timestamp=datetime.fromtimestamp(int(timestamp)) if timestamp else datetime.utcnow()
    )
    update_session_whatsapp_status(
        session_id,
        tenant_id,
        WhatsappStatus.ACTIVE,
        user_message
    )
    
    # Aggiungi alla storia per l'AI
    conversation_history.append({
        "sender": "user",
        "text": text,
        "timestamp": user_message.timestamp.isoformat()
    })
    
    # Processa messaggio con AI
    try:
        response_text, new_status, is_qualified = process_whatsapp_message(
            config=config,
            user_message=text,
            conversation_history=conversation_history,
            candidate_name=candidate_name
        )
        
        # Invia risposta
        client = WhatsAppClient()
        response_data = client.send_text_message(to=from_phone, text=response_text)
        response_message_id = response_data.get("messages", [{}])[0].get("id") if response_data.get("messages") else None
        
        # Salva risposta bot nel log
        bot_message = ChatMessage(
            sender="bot",
            text=response_text,
            message_id=response_message_id
        )
        
        # Aggiorna stato se necessario
        final_status = new_status if new_status else WhatsappStatus.ACTIVE
        update_session_whatsapp_status(
            session_id,
            tenant_id,
            final_status,
            bot_message
        )
        
        # Se qualificato o squalificato, salva il risultato nella sessione
        if is_qualified is not None:
            db[collections["sessions"]].update_one(
                {"_id": session_id},
                {"$set": {
                    "whatsapp_screening_result": "qualified" if is_qualified else "disqualified",
                    "whatsapp_screening_completed_at": datetime.utcnow()
                }}
            )
        
    except Exception as e:
        print(f"Errore processamento messaggio WhatsApp: {e}")
        import traceback
        traceback.print_exc()
        
        # Invia messaggio di errore generico
        try:
            client = WhatsAppClient()
            error_response = "Mi scuso, c'è stato un problema tecnico. Puoi ripetere la tua domanda?"
            client.send_text_message(to=from_phone, text=error_response)
        except:
            pass


async def handle_status_update(status: Dict[str, Any]):
    """Gestisce aggiornamenti di status (sent, delivered, read, failed)"""
    # Per ora solo log, potremmo salvare nel DB se necessario
    message_id = status.get("id")
    status_value = status.get("status")
    print(f"📊 Status update per {message_id}: {status_value}")


# ========== UTILITY ENDPOINTS ==========

@router.get("/session/{session_id}")
async def get_session_chat(
    session_id: str,
    tenant_id: str = Depends(get_tenant_from_auth)
):
    """Recupera lo storico chat WhatsApp di una sessione"""
    data = get_session_whatsapp_data(session_id, tenant_id)
    if not data:
        raise HTTPException(status_code=404, detail="Sessione non trovata")
    return data

