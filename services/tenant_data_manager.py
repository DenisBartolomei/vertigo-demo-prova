"""
Tenant-aware data manager functions
"""
import os
from services.data_manager import db

# ============================================
# NUOVA NOMENCLATURA STATI SESSIONI
# ============================================
# Codice DB         | Label UI            | Condizione
# ------------------|---------------------|------------------------------------------
# cv_analyzed       | CV analizzato       | CV processato, no WhatsApp
# engaged           | Ingaggiato          | WhatsApp inviato, conversazione attiva
# interrupted       | Interrotto          | Knockout fallito o ritiro
# qualified         | Qualificato         | Pre-screening OK
# interviewed       | Colloquiato         | Colloquio AI completato
# feedback_in_progress | Feedback in elaborazione | Generazione feedback avviata
# feedback_ready    | Feedback pronto     | PDF generato
# feedback_downloaded| Feedback scaricato | PDF scaricato
# ============================================

SESSION_STATUS = {
    # Nuovi stati standardizzati
    "CV_ANALYZED": "CV analizzato",
    "ENGAGED": "Ingaggiato", 
    "INTERRUPTED": "Interrotto",
    "QUALIFIED": "Qualificato",
    "INTERVIEWED": "Colloquiato",
    "FEEDBACK_IN_PROGRESS": "Feedback in elaborazione",
    "FEEDBACK_BATCH_PENDING": "Feedback in coda batch (può richiedere fino a 24h)",  # NUOVO: stato specifico per batch
    "FEEDBACK_READY": "Feedback pronto",
    "FEEDBACK_DOWNLOADED": "Feedback scaricato",
    
    # Stati legacy (per backward compatibility durante transizione)
    "CREATED": "CV analizzato",  # Mappato al nuovo
    "PREPARED": "Qualificato",   # Mappato al nuovo
    "INTERVIEW_STARTED": "Qualificato",  # Rimane qualificato finché non completa
    "INTERVIEW_COMPLETED": "Colloquiato",
    "EVALUATION_COMPLETED": "Colloquiato",
    "FEEDBACK_GENERATION_IN_PROGRESS": "Feedback in elaborazione",  # Mappato al nuovo stato
    "FEEDBACK_PENDING": "Feedback in coda batch (può richiedere fino a 24h)",  # Mappato allo stato batch per backward compatibility
    "FEEDBACK_GENERATION_FAILED": "Colloquiato"  # Errore = torna a colloquiato
}

# Codici DB per i nuovi stati (usare questi nei confronti)
SESSION_STATUS_CODES = {
    "cv_analyzed": "CV analizzato",
    "engaged": "Ingaggiato",
    "interrupted": "Interrotto",
    "qualified": "Qualificato", 
    "interviewed": "Colloquiato",
    "feedback_in_progress": "Feedback in elaborazione",
    "feedback_ready": "Feedback pronto",
    "feedback_downloaded": "Feedback scaricato"
}


def create_or_update_position_tenant(position_id: str, payload: dict, collection_name: str) -> bool:
    """Create or update position in tenant-specific collection"""
    if db is None:
        print("DB not available for create_or_update_position_tenant")
        return False
    try:
        collection = db[collection_name]
        payload = payload.copy()
        payload["_id"] = position_id
        collection.update_one({"_id": position_id}, {"$set": payload}, upsert=True)
        print(f"📄 Position upserted in tenant collection: {collection_name} with ID: {position_id}")
        return True
    except Exception as e:
        print(f"Error during position upsert {position_id}: {e}")
        return False


def create_new_session_tenant(session_id: str, position_id: str, candidate_name: str, collection_name: str, candidate_email: str = None) -> bool:
    """Create new session in tenant-specific collection"""
    if db is None:
        return False
    try:
        collection = db[collection_name]
        new_document = {
            "_id": session_id, 
            "position_id": position_id, 
            "candidate_name": candidate_name, 
            "candidate_email": candidate_email,
            "status": "initialized", 
            "stages": {}
        }
        collection.insert_one(new_document)
        print(f"📄 Session created in tenant collection: {collection_name} with ID: {session_id}")
        return True
    except Exception as e:
        print(f"Error during session creation {session_id}: {e}")
        return False


def save_stage_output_tenant(session_id: str, stage_name: str, data_content: dict | str, collection_name: str):
    """Save stage output in tenant-specific collection"""
    if db is None:
        return
    try:
        collection = db[collection_name]
        
        # Convert ObjectId objects to strings if present in data_content
        if isinstance(data_content, dict):
            data_content = _convert_objectids_to_strings(data_content)
        
        update_query = {"$set": {f"stages.{stage_name}": data_content}}
        collection.update_one({"_id": session_id}, update_query)
        print(f"💾 Stage '{stage_name}' data saved for session {session_id} in tenant collection: {collection_name}")
    except Exception as e:
        print(f"Error saving stage '{stage_name}': {e}")


def save_pdf_report_tenant(pdf_bytes: bytes, session_id: str, collection_name: str) -> str:
    """
    Save PDF feedback report for a session in tenant-specific directory structure.
    
    Args:
        pdf_bytes: The PDF file content as bytes
        session_id: The session ID
        collection_name: The tenant collection name (e.g., "tenant_id_sessions")
    
    Returns:
        The file path where the PDF was saved
    """
    try:
        # Estrai tenant_id dal nome della collection
        tenant_id = collection_name.replace("_sessions", "")
        
        # Crea directory tenant-specific per i PDF
        output_dir = os.path.join("data", "sessions", tenant_id, session_id)
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, "Report_Feedback_Candidato.pdf")
        
        # Salva il PDF
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"📄 PDF salvato in: {file_path}")
        return file_path
        
    except Exception as e:
        print(f"❌ Errore nel salvataggio del PDF per sessione {session_id}: {e}")
        import traceback
        traceback.print_exc()
        return ""


def _convert_objectids_to_strings(obj):
    """Recursively convert ObjectId objects to strings in nested dictionaries and lists"""
    from bson import ObjectId
    
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: _convert_objectids_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_objectids_to_strings(item) for item in obj]
    else:
        return obj


def get_session_data_tenant(session_id: str, collection_name: str) -> dict | None:
    """Get session data from tenant-specific collection"""
    if db is None:
        return None
    try:
        collection = db[collection_name]
        return collection.find_one({"_id": session_id})
    except Exception as e:
        print(f"Error retrieving session {session_id}: {e}")
        return None


def get_available_positions_tenant(collection_name: str):
    """Get available positions from tenant-specific collection"""
    if db is None:
        print("DB not available for get_available_positions_tenant")
        return []
    try:
        collection = db[collection_name]
        positions = list(collection.find({}, {"_id": 1, "position_name": 1}))
        return sorted(positions, key=lambda p: p['position_name'])
    except Exception as e:
        print(f"Error retrieving positions from tenant collection: {e}")
        return []


def get_single_position_data_tenant(position_id: str, collection_name: str):
    """Get single position data from tenant-specific collection"""
    if db is None:
        print(f"DB not available for get_single_position_data_tenant for ID: {position_id}")
        return None
    try:
        collection = db[collection_name]
        return collection.find_one({"_id": position_id})
    except Exception as e:
        print(f"Error retrieving position {position_id}: {e}")
        return None


def list_sessions_tenant(collection_name: str):
    """List sessions from tenant-specific collection with status logic"""
    if db is None:
        return []
    try:
        collection = db[collection_name]
        sessions = list(collection.find({}, {
            "_id": 1, 
            "candidate_name": 1, 
            "position_id": 1,
            "stages.cv_analysis_status": 1,
            "stages.conversation": 1
        }))
        
        # Get position names
        positions_collection = db[collection_name.replace("_sessions", "_positions_data")]
        results = []
        for s in sessions:
            pid = s.get("position_id")
            pname = None
            if pid:
                p = positions_collection.find_one({"_id": pid}, {"position_name": 1})
                pname = (p or {}).get("position_name")
            
            # Determine status based on cv_analysis_status and conversation
            stages = s.get("stages", {})
            cv_status = stages.get("cv_analysis_status")
            conversation = stages.get("conversation")
            
            status = "initialized"
            if cv_status == "Completed":
                if conversation:
                    # Both present - interview completed, don't show in dashboard
                    continue
                else:
                    # CV done but no conversation - interview pending
                    status = "Colloquio da completare"
            elif cv_status == "Failed":
                status = "CV analysis failed"
            
                results.append({
                    "session_id": s.get("_id"),
                    "candidate_name": s.get("candidate_name"),
                    "position_id": pid,
                    "position_name": pname,
                    "status": status,
                    "interview_token": s.get("interview_token"),  # Include interview token
                })
        return results
    except Exception as e:
        print(f"Error listing sessions from tenant collection: {e}")
        return []


def list_completed_sessions_tenant(collection_name: str) -> list:
    """List sessions that are ready for the HR report page, with robust status detection.
    
    Include:
    - Sessioni che hanno completato il colloquio (case_evaluation_report exists)
    - Sessioni interrotte via WhatsApp (whatsapp_status = interrupted)
    - Sessioni qualificate via WhatsApp in attesa di colloquio (whatsapp_status = qualified)
    - Sessioni qualificate solo via WhatsApp - workflow terminato (whatsapp_status = qualified_whatsapp)
    """
    try:
        if db is None:
            return []
        
        # Filtra sessioni che hanno:
        # 1. Completato il colloquio (case_evaluation_report exists), OPPURE
        # 2. Stato WhatsApp "interrupted" (candidatura interrotta), OPPURE
        # 3. Stato WhatsApp "qualified" (pre-screening superato - flusso completo)
        # 4. Stato WhatsApp "qualified_whatsapp" (pre-screening superato - solo WhatsApp, workflow terminato)
        # 5. Risultato screening "qualified", "qualified_whatsapp" o "interrupted" (fallback per allineamento)
        query = {
            "$or": [
                {"stages.case_evaluation_report": {"$exists": True}},
                {"whatsapp_status": "interrupted"},
                {"whatsapp_status": "qualified"},
                {"whatsapp_status": "qualified_whatsapp"},
                {"whatsapp_screening_result": "interrupted"},
                {"whatsapp_screening_result": "qualified"},
                {"whatsapp_screening_result": "qualified_whatsapp"}
            ]
        }
        sessions = list(db[collection_name].find(query))
        
        results = []
        for s in sessions:
            pid = s.get("position_id")
            pname = None
            if pid:
                p = get_single_position_data_tenant(pid, collection_name.replace("_sessions", "_positions_data"))
                pname = (p or {}).get("position_name")
            
            stages = s.get("stages", {})
            download_info = stages.get("feedback_download", {})
            
            # Leggi downloaded_at, downloaded_by, downloaded_by_name dalla root o da feedback_download
            # Priorità: root (per token WhatsApp) > feedback_download (per feedback PDF)
            downloaded_at = s.get("downloaded_at") or download_info.get("downloaded_at")
            downloaded_by = s.get("downloaded_by") or download_info.get("downloaded_by")
            downloaded_by_name = s.get("downloaded_by_name") or download_info.get("downloaded_by_name")
            
            # 1. Partiamo dallo stato già salvato nel database
            # PRIORITÀ: stages.status ha la precedenza su root status (perché è più aggiornato)
            root_status = s.get("status")
            stages_status = stages.get("status")
            
            # Usa stages_status se presente, altrimenti root_status
            final_status = stages_status if stages_status else root_status
            
            # Debug: log per verificare lo status trovato
            print(f"[DEBUG STATUS] Sessione {s.get('_id')}: root_status='{root_status}', stages_status='{stages_status}', final_status='{final_status}'")
            
            if final_status and "batch" in final_status.lower():
                print(f"[DEBUG BATCH] Sessione {s.get('_id')} ha status batch: '{final_status}'")

            # Recupera stato WhatsApp e risultato screening
            whatsapp_status = s.get("whatsapp_status")
            whatsapp_screening_result = s.get("whatsapp_screening_result")
            interruption_reason = s.get("interruption_reason")
            
            # Allinea whatsapp_status con whatsapp_screening_result se necessario (fallback)
            if whatsapp_screening_result and not whatsapp_status:
                # Se c'è un risultato screening ma non lo status, allinea
                if whatsapp_screening_result in ["qualified", "interrupted", "disqualified"]:
                    whatsapp_status = whatsapp_screening_result
                    print(f"[DEBUG STATUS] Sessione {s.get('_id')}: Allineato whatsapp_status='{whatsapp_status}' da screening_result")
            
            # ============================================
            # LOGICA DI DETERMINAZIONE STATO - NUOVA NOMENCLATURA
            # ============================================
            # Ordine di priorità:
            # 1. FEEDBACK_DOWNLOADED - PDF scaricato
            # 2. FEEDBACK_READY - PDF generato ma non scaricato
            # 3. FEEDBACK_IN_PROGRESS - Generazione feedback in corso
            # 4. INTERVIEWED - Colloquio completato, feedback da generare
            # 5. INTERRUPTED - Candidatura interrotta
            # 6. QUALIFIED - Pre-screening OK, in attesa colloquio
            
            # PRIORITÀ 1: Feedback scaricato
            if downloaded_at and stages.get("feedback_pdf_path"):
                final_status = SESSION_STATUS["FEEDBACK_DOWNLOADED"]
                print(f"[DEBUG STATUS] Sessione {s.get('_id')}: PDF scaricato → feedback_downloaded")
            
            # PRIORITÀ 2: Feedback pronto (PDF esiste ma non scaricato)
            elif stages.get("feedback_pdf_path") and not downloaded_at:
                final_status = SESSION_STATUS["FEEDBACK_READY"]
                print(f"[DEBUG STATUS] Sessione {s.get('_id')}: PDF pronto → feedback_ready")
            
            # PRIORITÀ 3: Feedback in elaborazione (generazione avviata ma non completata)
            elif (stages.get("status") == SESSION_STATUS["FEEDBACK_IN_PROGRESS"] or 
                  stages.get("status") == SESSION_STATUS["FEEDBACK_GENERATION_IN_PROGRESS"] or
                  stages.get("status") == SESSION_STATUS["FEEDBACK_PENDING"] or
                  stages.get("status") == SESSION_STATUS["FEEDBACK_BATCH_PENDING"] or
                  (stages.get("status") and "elaborazione" in stages.get("status").lower()) or
                  (stages.get("status") and "batch" in stages.get("status").lower())):
                final_status = SESSION_STATUS["FEEDBACK_IN_PROGRESS"]
                print(f"[DEBUG STATUS] Sessione {s.get('_id')}: Generazione feedback in corso → feedback_in_progress")
            
            # PRIORITÀ 4: Colloquiato (colloquio completato, feedback da generare)
            elif stages.get("case_evaluation_report"):
                final_status = SESSION_STATUS["INTERVIEWED"]
                print(f"[DEBUG STATUS] Sessione {s.get('_id')}: Colloquio completato → interviewed")
            
            # PRIORITÀ 4: Interrotto (knockout fallito o ritiro)
            elif whatsapp_status == "interrupted" or whatsapp_screening_result == "interrupted":
                final_status = SESSION_STATUS["INTERRUPTED"]
                print(f"[DEBUG STATUS] Sessione {s.get('_id')}: WhatsApp interrupted → interrupted")
            
            # PRIORITÀ 5: Qualificato (pre-screening OK, in attesa colloquio)
            elif whatsapp_status in ["qualified", "qualified_whatsapp"] or whatsapp_screening_result in ["qualified", "qualified_whatsapp"]:
                final_status = SESSION_STATUS["QUALIFIED"]
                print(f"[DEBUG STATUS] Sessione {s.get('_id')}: Pre-screening OK → qualified")

            # Recupera interview_token dagli stages
            interview_token = stages.get("interview_token")
            
            results.append({
                "session_id": s.get("_id"),
                "candidate_name": s.get("candidate_name"),
                "candidate_email": s.get("candidate_email"), # Assicurati che il campo esista
                "position_id": pid,
                "position_name": pname,
                "status": final_status, # Usiamo lo stato finale che abbiamo determinato
                "interview_token": interview_token,
                "downloaded_at": downloaded_at,
                "downloaded_by": downloaded_by,
                "downloaded_by_name": downloaded_by_name,
                "whatsapp_status": s.get("whatsapp_status"),
                "interruption_reason": s.get("interruption_reason"),
            })
        
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []


def list_incomplete_sessions_tenant(collection_name: str) -> list:
    """List sessions that haven't completed the full interview (no skill summary) for Nuova Sessione dashboard.
    
    ESCLUDE:
    - Sessioni con whatsapp_status = "interrupted" (candidatura interrotta)
    - Sessioni con whatsapp_status = "qualified" (già in reportistica per colloquio)
    - Sessioni con whatsapp_status = "qualified_whatsapp" (workflow completato - solo pre-screening)
    - Sessioni completate (con skill_relevance)
    """
    try:
        if db is None:
            return []
        
        # Query MongoDB che ESCLUDE direttamente le sessioni qualificate/interrotte
        # e quelle completate (con skill_relevance)
        # Controlla sia whatsapp_status che whatsapp_screening_result per allineamento
        query = {
            "$and": [
                {
                    "$or": [
                        # Sessioni senza whatsapp_status (vecchie)
                        {"whatsapp_status": {"$exists": False}},
                        # Sessioni con status diverso da qualified/interrupted/qualified_whatsapp
                        {"whatsapp_status": {"$nin": ["interrupted", "qualified", "qualified_whatsapp"]}}
                    ]
                },
                {
                    "$or": [
                        # Sessioni senza whatsapp_screening_result (non ancora completato screening)
                        {"whatsapp_screening_result": {"$exists": False}},
                        # Sessioni con risultato diverso da qualified/interrupted/qualified_whatsapp
                        {"whatsapp_screening_result": {"$nin": ["interrupted", "qualified", "qualified_whatsapp"]}}
                    ]
                },
                {"stages.skill_relevance": {"$exists": False}}  # Escludi completate
            ]
        }
        
        sessions = list(db[collection_name].find(query))
        print(f"[DEBUG INCOMPLETE] Query MongoDB trovata {len(sessions)} sessioni (escluse qualified/interrupted)")
        
        results = []
        
        for s in sessions:
            # Doppio controllo per sicurezza (controlla entrambi i campi)
            whatsapp_status = s.get("whatsapp_status")
            whatsapp_screening_result = s.get("whatsapp_screening_result")
            session_id = s.get("_id")
            
            # Debug: log per verificare esclusione
            if whatsapp_status in ["interrupted", "qualified"] or whatsapp_screening_result in ["interrupted", "qualified"]:
                print(f"[DEBUG INCOMPLETE] ⚠️ Sessione {session_id} esclusa: whatsapp_status='{whatsapp_status}', screening_result='{whatsapp_screening_result}'")
                # Queste sessioni appaiono in Reportistica Candidati
                continue
            
            # Debug: log per sessioni incluse
            if whatsapp_status or whatsapp_screening_result:
                print(f"[DEBUG INCOMPLETE] Sessione {session_id} inclusa: whatsapp_status='{whatsapp_status}', screening_result='{whatsapp_screening_result}'")
            
            pid = s.get("position_id")
            pname = None
            if pid:
                p = get_single_position_data_tenant(pid, collection_name.replace("_sessions", "_positions_data"))
                pname = (p or {}).get("position_name")
            
            # Check if interview is NOT fully completed (no skill relevance)
            stages = s.get("stages", {})
            cv_status = stages.get("cv_analysis_status")
            conversation = stages.get("conversation")
            case_evaluation = stages.get("case_evaluation_report")
            skill_relevance = stages.get("skill_relevance")
            
            # Include sessions that haven't completed the full interview
            if not skill_relevance:  # No skill relevance means not fully completed
                # ============================================
                # LOGICA DI DETERMINAZIONE STATO - NUOVA NOMENCLATURA
                # Per sessioni incomplete (Nuova Sessione dashboard)
                # ============================================
                
                # Determina se è stato ingaggiato (WhatsApp inviato)
                is_engaged = whatsapp_status in ["sent", "active"] or s.get("whatsapp_first_message_sent")
                
                if cv_status == "Completed":
                    if is_engaged:
                        # WhatsApp inviato, conversazione in corso
                        status = SESSION_STATUS["ENGAGED"]  # "Ingaggiato"
                    else:
                        # CV analizzato, non ancora ingaggiato
                        status = SESSION_STATUS["CV_ANALYZED"]  # "CV analizzato"
                elif cv_status == "Failed":
                    status = "CV analysis failed"
                else:
                    # CV non ancora analizzato o in corso
                    status = SESSION_STATUS["CV_ANALYZED"]  # Default
                
                results.append({
                    "session_id": s.get("_id"),
                    "candidate_name": s.get("candidate_name"),
                    "candidate_email": s.get("candidate_email"),
                    "position_id": pid,
                    "position_name": pname,
                    "status": status,
                    "interview_token": stages.get("interview_token"),
                    "token_sent": s.get("token_sent", False),
                    "token_sent_by": s.get("token_sent_by"),
                    "token_sent_at": s.get("token_sent_at"),
                    "whatsapp_status": whatsapp_status,  # Includi per mostrare badge
                    "phone_number": s.get("phone_number"),
                })
        return results
    except Exception as e:
        print(f"Error listing incomplete sessions from tenant collection: {e}")
        return []


def get_dashboard_data_tenant(tenant_id: str, time_range: str = "30d", position_filter: str = None, workflow_filter: str = None) -> dict:
    """Get comprehensive dashboard data for HR analytics with real recruitment indicators
    
    Args:
        workflow_filter: "full" per iter completo, "whatsapp_only" per solo screening WhatsApp, None per tutti
    """
    if db is None:
        print(f"Database not available for tenant {tenant_id}")
        return {}
    
    try:
        from datetime import datetime, timedelta
        import math
        
        print(f"Getting dashboard data for tenant: {tenant_id}, time_range: {time_range}, position_filter: {position_filter}, workflow_filter: {workflow_filter}")
        
        # Calculate date range
        now = datetime.utcnow()
        if time_range == "7d":
            start_date = now - timedelta(days=7)
        elif time_range == "30d":
            start_date = now - timedelta(days=30)
        elif time_range == "90d":
            start_date = now - timedelta(days=90)
        elif time_range == "1y":
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)
        
        # Get tenant collections
        positions_collection = db[f"{tenant_id}_positions_data"]
        sessions_collection = db[f"{tenant_id}_sessions"]
        users_collection = db[f"{tenant_id}_users"]
        
        # Query base con filtro posizione e workflow
        query = {}
        if position_filter and position_filter != "all":
            query["position_id"] = position_filter
        
        # Filtra per workflow_type (recupera position_ids con il workflow specificato)
        if workflow_filter and workflow_filter in ["full", "whatsapp_only"]:
            # Trova tutte le posizioni con il workflow_type specificato
            workflow_positions = list(positions_collection.find(
                {"workflow_type": workflow_filter},
                {"_id": 1}
            ))
            workflow_position_ids = [p["_id"] for p in workflow_positions]
            
            if workflow_position_ids:
                if "position_id" in query:
                    # Se c'è già un filtro posizione, verifica che sia nel set
                    if query["position_id"] not in workflow_position_ids:
                        # Nessun match, ritorna dati vuoti
                        workflow_position_ids = []
                else:
                    query["position_id"] = {"$in": workflow_position_ids}
            else:
                # Nessuna posizione con questo workflow, forza query vuota
                query["position_id"] = {"$in": []}
        
        # 1. COLLOQUI COMPLETATI
        completed_interviews = sessions_collection.count_documents({
            **query,
            "stages.skill_relevance": {"$exists": True}
        })
        
        # 2. CANDIDATI IN ATTESA DI TOKEN
        waiting_token = sessions_collection.count_documents({
            **query,
            "stages.interview_token": {"$exists": True},
            "token_sent": False
        })
        
        # 3. COLLOQUIO IN CORSO
        in_progress = sessions_collection.count_documents({
            **query,
            "token_sent": True,
            "stages.skill_relevance": {"$exists": False}
        })
        
        # 4. DURATA MEDIA COLLOQUIO
        completed_sessions = list(sessions_collection.find({
            **query,
            "stages.skill_relevance": {"$exists": True},
            "interview_started_at": {"$exists": True}
        }))
        
        durations = []
        for session in completed_sessions:
            started_at = session.get("interview_started_at")
            if started_at:
                if isinstance(started_at, str):
                    started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                
                # Trova timestamp skill_relevance (ultimo aggiornamento)
                stages = session.get("stages", {})
                skill_relevance = stages.get("skill_relevance", {})
                if skill_relevance:
                    # Usa timestamp di creazione del documento come proxy per completamento
                    # In realtà dovremmo avere un campo "completed_at" specifico
                    duration_minutes = (now - started_at).total_seconds() / 60
                    durations.append(duration_minutes)
        
        avg_interview_duration = sum(durations) / len(durations) if durations else 0
        
        # 5. TEMPO DI PRESA IN CARICO
        takeover_times = []
        for session in completed_sessions:
            token_sent_at = session.get("token_sent_at")
            if token_sent_at:
                if isinstance(token_sent_at, str):
                    token_sent_at = datetime.fromisoformat(token_sent_at.replace('Z', '+00:00'))
                
                # Calcola differenza tra invio token e completamento
                # Per ora usiamo timestamp attuale come proxy per completamento
                takeover_hours = (now - token_sent_at).total_seconds() / 3600
                takeover_times.append(takeover_hours)
        
        avg_takeover_time = sum(takeover_times) / len(takeover_times) if takeover_times else 0
        
        # 6-7. TASSO RECUPERO E UNDERPERFORMING
        sessions_with_scores = list(sessions_collection.find({
            **query,
            "stages.skill_relevance": {"$exists": True}
        }))
        
        recovery_count = 0
        underperforming_count = 0
        total_evaluated = len(sessions_with_scores)
        
        all_interview_scores = []
        all_cv_scores = []
        
        for session in sessions_with_scores:
            scores = session.get("stages", {}).get("skill_relevance", {}).get("scores", [])
            if scores:
                avg_cv = sum(s.get("cv_relevance_score", 0) for s in scores) / len(scores)
                avg_interview = sum(s.get("interview_relevance_score", 0) for s in scores) / len(scores)
                diff = avg_interview - avg_cv
                
                all_interview_scores.append(avg_interview)
                all_cv_scores.append(avg_cv)
                
                if diff >= 0.5:
                    recovery_count += 1
                elif diff <= -0.5:
                    underperforming_count += 1
        
        recovery_rate = (recovery_count / total_evaluated * 100) if total_evaluated > 0 else 0
        underperforming_rate = (underperforming_count / total_evaluated * 100) if total_evaluated > 0 else 0
        
        # 8-10. SCORING MEDI
        avg_interview_score = sum(all_interview_scores) / len(all_interview_scores) if all_interview_scores else 0
        avg_cv_score = sum(all_cv_scores) / len(all_cv_scores) if all_cv_scores else 0
        avg_overall_score = (avg_interview_score + avg_cv_score) / 2 if (all_interview_scores and all_cv_scores) else 0
        
        # Lista posizioni per filtro dropdown
        positions_data = list(positions_collection.find({}))
        positions = [{"id": p.get("_id"), "name": p.get("position_name", "Unknown")} for p in positions_data]
        
        # ============ NUOVE METRICHE ============
        
        # FUNNEL DI CONVERSIONE - NUOVA NOMENCLATURA
        # Gli stati seguono il flusso: CV analizzato → Ingaggiato → Qualificato → Colloquiato → Feedback pronto → Feedback scaricato
        # Con "Interrotto" come uscita dal funnel
        
        # 1. CV ANALIZZATO: sessioni con CV processato ma WhatsApp non ancora inviato
        cv_analyzed = sessions_collection.count_documents({
            **query,
            "stages.cv_analysis_status": "Completed",
            "$or": [
                {"whatsapp_status": {"$exists": False}},
                {"whatsapp_status": "ready"}
            ]
        })
        
        # 2. INGAGGIATO: WhatsApp inviato, conversazione in corso
        engaged = sessions_collection.count_documents({
            **query,
            "whatsapp_status": {"$in": ["sent", "active"]}
        })
        
        # 3. INTERROTTO: candidatura interrotta (knockout o ritiro)
        interrupted = sessions_collection.count_documents({
            **query,
            "whatsapp_status": "interrupted"
        })
        
        # 4. QUALIFICATO: pre-screening WhatsApp completato positivamente
        qualified = sessions_collection.count_documents({
            **query,
            "$or": [
                {"whatsapp_status": "qualified"},
                {"whatsapp_status": "qualified_whatsapp"},
                {"whatsapp_screening_result": "qualified"}
            ]
        })
        
        # 5. COLLOQUIATO: colloquio AI completato (con evaluation report)
        interviewed = sessions_collection.count_documents({
            **query,
            "stages.case_evaluation_report": {"$exists": True}
        })
        
        # 6. FEEDBACK PRONTO: feedback PDF generato
        feedback_ready = sessions_collection.count_documents({
            **query,
            "feedback_ready": True,
            "$or": [
                {"feedback_downloaded": {"$exists": False}},
                {"feedback_downloaded": False}
            ]
        })
        
        # 7. FEEDBACK SCARICATO: feedback PDF scaricato dall'HR
        feedback_downloaded = sessions_collection.count_documents({
            **query,
            "feedback_downloaded": True
        })
        
        funnel = {
            "cv_analyzed": cv_analyzed,
            "engaged": engaged,
            "interrupted": interrupted,
            "qualified": qualified,
            "interviewed": interviewed,
            "feedback_ready": feedback_ready,
            "feedback_downloaded": feedback_downloaded,
            # Totali per compatibilità
            "total": sessions_collection.count_documents({**query}),
            "completed": completed_interviews
        }
        
        # WHATSAPP PRE-SCREENING STATS
        whatsapp_total_engaged = sessions_collection.count_documents({
            **query,
            "whatsapp_status": {"$exists": True, "$ne": "ready"}
        })
        
        whatsapp_qualified = sessions_collection.count_documents({
            **query,
            "$or": [
                {"whatsapp_status": "qualified"},
                {"whatsapp_status": "qualified_whatsapp"}
            ]
        })
        
        whatsapp_interrupted = sessions_collection.count_documents({
            **query,
            "whatsapp_status": "interrupted"
        })
        
        qualification_rate = (whatsapp_qualified / whatsapp_total_engaged * 100) if whatsapp_total_engaged > 0 else 0
        
        # Top motivi interruzione
        interruption_pipeline = [
            {"$match": {**query, "whatsapp_status": "interrupted", "interruption_reason": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$interruption_reason", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        interruption_reasons_raw = list(sessions_collection.aggregate(interruption_pipeline))
        interruption_reasons = [{"reason": r["_id"], "count": r["count"]} for r in interruption_reasons_raw]
        
        # In attesa di risposta: CV ingaggiati WhatsApp ma processo non concluso (non qualificati né interrotti)
        # Sessioni con whatsapp_status "sent" o "active" che non hanno ancora un risultato finale
        waiting_response = sessions_collection.count_documents({
            **query,
            "whatsapp_status": {"$in": ["sent", "active"]},
            "$or": [
                {"whatsapp_screening_result": {"$exists": False}},
                {"whatsapp_screening_result": {"$nin": ["qualified", "interrupted", "qualified_whatsapp"]}}
            ]
        })
        
        # Dettaglio interrotti: distinguere tra mancanza requisiti base e ritiro candidatura
        interrupted_sessions = list(sessions_collection.find({
            **query,
            "whatsapp_status": "interrupted"
        }, {
            "_id": 1,
            "interruption_reason": 1
        }))
        
        # Categorizza interrotti
        missing_requirements_count = 0
        withdrawal_count = 0
        withdrawal_reasons = {}
        
        for session in interrupted_sessions:
            reason = session.get("interruption_reason", "").lower() if session.get("interruption_reason") else ""
            
            # Se contiene parole chiave di knockout/requisiti, è mancanza requisiti base
            knockout_keywords = ["knockout", "requisito", "requirement", "mancanza", "manca", "non possiede", "non ha", "non soddisfa", "non rispetta"]
            withdrawal_keywords = ["ritiro", "withdrawal", "rinuncia", "non interessato", "non più interessato", "cambio idea", "cambiato idea"]
            
            is_knockout = any(keyword in reason for keyword in knockout_keywords)
            is_withdrawal = any(keyword in reason for keyword in withdrawal_keywords)
            
            if is_knockout or (not is_withdrawal and reason):
                # Se è chiaramente un knockout o non è chiaramente un ritiro, consideralo mancanza requisiti
                missing_requirements_count += 1
            elif is_withdrawal:
                withdrawal_count += 1
                # Raggruppa per motivazione
                reason_key = reason[:100] if reason else "Motivazione non specificata"
                withdrawal_reasons[reason_key] = withdrawal_reasons.get(reason_key, 0) + 1
            else:
                # Default: se non si capisce, consideralo mancanza requisiti
                missing_requirements_count += 1
        
        whatsapp_stats = {
            "total_engaged": whatsapp_total_engaged,
            "qualified": whatsapp_qualified,
            "interrupted": whatsapp_interrupted,
            "qualification_rate": round(qualification_rate, 1),
            "interruption_reasons": interruption_reasons,
            "waiting_response": waiting_response,
            "interrupted_details": {
                "missing_requirements": missing_requirements_count,
                "withdrawal": withdrawal_count,
                "withdrawal_reasons": [{"reason": k, "count": v} for k, v in withdrawal_reasons.items()]
            }
        }
        
        # PERFORMANCE PER POSIZIONE (top 5)
        position_pipeline = [
            {"$match": {**query}},
            {"$group": {
                "_id": "$position_id",
                "candidates": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$ifNull": ["$stages.skill_relevance", False]}, 1, 0]}},
                "qualified": {"$sum": {"$cond": [
                    {"$or": [
                        {"$eq": ["$whatsapp_status", "qualified"]},
                        {"$eq": ["$whatsapp_status", "qualified_whatsapp"]}
                    ]}, 1, 0
                ]}}
            }},
            {"$sort": {"candidates": -1}},
            {"$limit": 5}
        ]
        position_stats_raw = list(sessions_collection.aggregate(position_pipeline))
        
        # Arricchisci con nomi posizione e calcola score medio
        by_position = []
        for ps in position_stats_raw:
            pos_id = ps["_id"]
            pos_name = "Sconosciuta"
            
            # Trova nome posizione
            for p in positions_data:
                if p.get("_id") == pos_id:
                    pos_name = p.get("position_name", "Sconosciuta")
                    break
            
            # Calcola score medio per questa posizione
            pos_sessions = list(sessions_collection.find({
                "position_id": pos_id,
                "stages.skill_relevance": {"$exists": True}
            }))
            
            pos_scores = []
            for sess in pos_sessions:
                scores = sess.get("stages", {}).get("skill_relevance", {}).get("scores", [])
                if scores:
                    avg = sum(s.get("interview_relevance_score", 0) for s in scores) / len(scores)
                    pos_scores.append(avg)
            
            avg_score = sum(pos_scores) / len(pos_scores) if pos_scores else 0
            
            by_position.append({
                "position_id": pos_id,
                "position_name": pos_name,
                "candidates": ps["candidates"],
                "qualified": ps["qualified"],
                "completed": ps["completed"],
                "avg_score": round(avg_score, 2)
            })
        
        print(f"📊 Dashboard metrics: {completed_interviews} completed, {waiting_token} waiting, {in_progress} in progress")
        print(f"📈 Recovery: {recovery_count} ({recovery_rate:.1f}%), Underperforming: {underperforming_count} ({underperforming_rate:.1f}%)")
        print(f"📱 WhatsApp: {whatsapp_qualified} qualified, {whatsapp_interrupted} interrupted ({qualification_rate:.1f}% rate)")
        
        return {
            "metrics": {
                "completed_interviews": completed_interviews,
                "waiting_token": waiting_token,
                "in_progress": in_progress,
                "avg_interview_duration": round(avg_interview_duration, 1),
                "avg_takeover_time": round(avg_takeover_time, 1),
                "recovery_count": recovery_count,
                "recovery_rate": round(recovery_rate, 1),
                "underperforming_count": underperforming_count,
                "underperforming_rate": round(underperforming_rate, 1),
                "avg_interview_score": round(avg_interview_score, 2),
                "avg_cv_score": round(avg_cv_score, 2),
                "avg_overall_score": round(avg_overall_score, 2),
                "total_evaluated": total_evaluated
            },
            "funnel": funnel,
            "whatsapp": whatsapp_stats,
            "by_position": by_position,
            "positions": positions
        }
        
    except Exception as e:
        print(f"Error getting dashboard data for tenant {tenant_id}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "metrics": {
                "completed_interviews": 0,
                "waiting_token": 0,
                "in_progress": 0,
                "avg_interview_duration": 0,
                "avg_takeover_time": 0,
                "recovery_count": 0,
                "recovery_rate": 0,
                "underperforming_count": 0,
                "underperforming_rate": 0,
                "avg_interview_score": 0,
                "avg_cv_score": 0,
                "avg_overall_score": 0,
                "total_evaluated": 0
            },
            "funnel": {
                "cv_uploaded": 0,
                "prescreening_active": 0,
                "qualified": 0,
                "interview_started": 0,
                "completed": 0
            },
            "whatsapp": {
                "total_engaged": 0,
                "qualified": 0,
                "interrupted": 0,
                "qualification_rate": 0,
                "interruption_reasons": [],
                "waiting_response": 0,
                "interrupted_details": {
                    "missing_requirements": 0,
                    "withdrawal": 0,
                    "withdrawal_reasons": []
                }
            },
            "by_position": [],
            "positions": []
        }
