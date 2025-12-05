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
    ChatMessage
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
    import os
    
    # Verifica prima se le variabili d'ambiente sono settate
    api_token = os.getenv("WHATSAPP_API_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    
    if not api_token or not phone_number_id:
        missing = []
        if not api_token:
            missing.append("WHATSAPP_API_TOKEN")
        if not phone_number_id:
            missing.append("WHATSAPP_PHONE_NUMBER_ID")
        return {
            "valid": False,
            "error": f"Variabili d'ambiente mancanti: {', '.join(missing)}. Configurale su Cloud Run."
        }
    
    try:
        client = WhatsAppClient()
        is_valid = client.validate_credentials()
        if not is_valid:
            return {
                "valid": False,
                "error": "Credenziali non valide. Verifica che WHATSAPP_API_TOKEN e WHATSAPP_PHONE_NUMBER_ID siano corretti."
            }
        return {"valid": True}
    except ValueError as e:
        return {"valid": False, "error": str(e)}
    except Exception as e:
        return {"valid": False, "error": f"Errore validazione: {str(e)}"}


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
    
    # Recupera dati per le variabili del template
    raw_candidate_name = session.get("candidate_name") or ""
    position_id = session.get("position_id")
    
    # Estrai primo nome del candidato (con fallback sicuro)
    candidate_first_name = "Candidato"
    if raw_candidate_name and raw_candidate_name.strip():
        parts = raw_candidate_name.strip().split()
        if parts and parts[0]:
            candidate_first_name = parts[0]
    
    # Recupera nome posizione reale dalla collection positions_data
    position_name = "la posizione"
    if position_id:
        from services.tenant_data_manager import get_single_position_data_tenant
        position_data = get_single_position_data_tenant(position_id, collections["positions"])
        # Nei documenti posizione il campo standard è "position_name"
        if position_data:
            pos_name = (
                position_data.get("position_name")
                or position_data.get("name")  # fallback legacy
            )
            if pos_name and isinstance(pos_name, str) and pos_name.strip():
                position_name = pos_name.strip()
    
    # Recupera nome azienda dal tenant
    from services.tenant_service import get_tenant_by_id
    tenant_data = get_tenant_by_id(tenant_id)
    company_name = "l'azienda"
    if tenant_data:
        comp_name = tenant_data.get("company_name")
        if comp_name and comp_name.strip():
            company_name = comp_name.strip()
    
    # Log per debug
    print(f"📱 Template vars: candidate='{candidate_first_name}', company='{company_name}', position='{position_name}'")
    
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
        
        # Costruisci components con le 3 variabili NOMINATE del template
        # Template usa: {{nome_candidato}}, {{nome_azienda}}, {{posizione}}
        components = [{
            "type": "body",
            "parameters": [
                {"type": "text", "parameter_name": "nome_candidato", "text": candidate_first_name},
                {"type": "text", "parameter_name": "nome_azienda", "text": company_name},
                {"type": "text", "parameter_name": "posizione", "text": position_name}
            ]
        }]
        
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
async def webhook_verify(request: Request):
    """
    Endpoint per la verifica del webhook da parte di Meta
    Meta chiama questo endpoint quando configuri il webhook nella dashboard
    """
    # Meta usa parametri con il punto: hub.mode, hub.verify_token, hub.challenge
    hub_mode = request.query_params.get("hub.mode")
    hub_verify_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")
    
    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    
    print(f"Webhook verify request: mode={hub_mode}, token_match={hub_verify_token == verify_token}")
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        # Restituisci la challenge come testo semplice (non JSON)
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=hub_challenge)
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
    
    # CONTROLLO: Se il candidato è interrotto, blocca il messaggio e invia risposta automatica
    if session:
        whatsapp_status = session.get("whatsapp_status")
        whatsapp_screening_result = session.get("whatsapp_screening_result")
        
        if whatsapp_status == "interrupted" or whatsapp_screening_result == "interrupted":
            print(f"🚫 Messaggio bloccato: candidato {session_id} è interrotto")
            
            # Messaggio automatico
            auto_message = "Ci dispiace, ma il processo di selezione per questa posizione è stato interrotto. Ti aspettiamo per una prossima candidatura! 👋"
            
            # Invia messaggio automatico
            try:
                client = WhatsAppClient()
                response_data = client.send_text_message(to=from_phone, text=auto_message)
                response_message_id = response_data.get("messages", [{}])[0].get("id") if response_data.get("messages") else None
                
                # Salva messaggio automatico nel log
                bot_message = ChatMessage(
                    sender="bot",
                    text=auto_message,
                    message_id=response_message_id
                )
                update_session_whatsapp_status(
                    session_id,
                    tenant_id,
                    WhatsappStatus.INTERRUPTED,  # Mantieni stato interrupted
                    bot_message
                )
                
                print(f"✅ Messaggio automatico inviato a candidato interrotto")
                return  # NON processare con AI
            except Exception as e:
                print(f"Errore invio messaggio automatico per candidato interrotto: {e}")
                return
    
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
        # Recupera dati dalla sessione
        stages = session.get("stages", {}) if session else {}
        interview_token = stages.get("interview_token")
        position_id = session.get("position_id") if session else None
        cv_text = stages.get("uploaded_cv_text")  # Testo originale del CV
        # NOTA: cv_analysis_report rimosso per risparmio token
        
        # Carica dati posizione se disponibile
        position_data = None
        if position_id:
            from services.tenant_data_manager import get_single_position_data_tenant
            position_data = get_single_position_data_tenant(position_id, collections["positions"])
        
        response_text, new_status, is_qualified, interruption_reason = process_whatsapp_message(
            config=config,
            user_message=text,
            conversation_history=conversation_history,
            candidate_name=candidate_name,
            interview_token=interview_token,
            position_id=position_id,
            tenant_id=tenant_id,
            cv_text=cv_text,  # Testo CV per conversazione naturale
            position_data=position_data,
            session_data=session  # Passa session_data per verificare stato qualificato/interrotto
            session_data=session  # Passa i dati della sessione per verificare flag ritiro
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
        
        # Se qualificato, squalificato o interrotto, salva il risultato nella sessione
        if is_qualified is not None or final_status == WhatsappStatus.INTERRUPTED:
            update_data = {
                "whatsapp_screening_completed_at": datetime.utcnow()
            }
            
            if final_status == WhatsappStatus.INTERRUPTED:
                update_data["whatsapp_screening_result"] = "interrupted"
                update_data["interruption_reason"] = interruption_reason or "unknown"
                # Allinea whatsapp_status con il risultato
                update_data["whatsapp_status"] = "interrupted"
                
                # Se è un ritiro volontario (inizia con "ritiro:" o è "ritiro_candidato"), salva il flag
                if interruption_reason and (interruption_reason.startswith("ritiro:") or interruption_reason == "ritiro_candidato"):
                    if interruption_reason == "ritiro_candidato":
                        # Ritiro appena iniziato, flag in corso
                        update_data["_withdrawal_in_progress"] = True
                    else:
                        # Motivazione ricevuta, ritiro completato
                        update_data["_withdrawal_in_progress"] = False
            elif is_qualified is not None:
                update_data["whatsapp_screening_result"] = "qualified" if is_qualified else "disqualified"
                
                # ALLINEA whatsapp_status con il risultato dello screening
                if is_qualified:
                    # Se qualificato, aggiorna whatsapp_status a "qualified"
                    update_data["whatsapp_status"] = "qualified"
                    # Aggiorna anche lo stato tramite la funzione dedicata per coerenza
                    update_session_whatsapp_status(
                        session_id,
                        tenant_id,
                        WhatsappStatus.QUALIFIED,
                        None  # Nessun nuovo messaggio da aggiungere
                    )
                else:
                    # Se disqualified, aggiorna whatsapp_status
                    update_data["whatsapp_status"] = "disqualified"
                    update_session_whatsapp_status(
                        session_id,
                        tenant_id,
                        WhatsappStatus.DISQUALIFIED,
                        None
                    )
                
                # Se qualificato, marca automaticamente il token come inviato (l'agente lo ha mandato autonomamente)
                if is_qualified:
                    update_data["downloaded_at"] = datetime.utcnow().isoformat()
                    update_data["downloaded_by"] = "whatsapp_agent"
                    update_data["downloaded_by_name"] = "WhatsApp Agent"
                    print(f"✅ Token marcato come inviato automaticamente per sessione {session_id} (qualificato via WhatsApp)")
            
            db[collections["sessions"]].update_one(
                {"_id": session_id},
                {"$set": update_data}
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

