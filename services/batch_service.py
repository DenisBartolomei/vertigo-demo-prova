import os
import json
import tempfile
import sys
import io
from typing import List, Dict, Optional
from datetime import datetime
from openai import AzureOpenAI
from services.data_manager import db
from services.email_parser import extract_email_from_text

# Sopprimi errori tkinter da PyMuPDF durante upload batch
class TkinterErrorFilter:
    """Filtra errori tkinter non bloccanti da stderr"""
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
    
    def write(self, message):
        # Filtra errori tkinter comuni (non bloccanti)
        if any(keyword in message for keyword in [
            'RuntimeError: main thread is not in main loop',
            'Tcl_AsyncDelete',
            'Exception ignored in: <function Image.__del__',
            'Exception ignored in: <function Variable.__del__',
            'function Image.__del__',
            'function Variable.__del__'
        ]):
            # Ignora questi errori (sono non bloccanti e causati da PyMuPDF)
            return
        # Scrivi tutto il resto su stderr originale
        self.original_stderr.write(message)
    
    def flush(self):
        self.original_stderr.flush()
    
    def __enter__(self):
        sys.stderr = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr = self.original_stderr
        return False

# Configurazione credenziali batch con fallback
BATCH_ENDPOINT = os.getenv("AZURE_OPENAI_BATCH_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
BATCH_API_KEY = os.getenv("AZURE_OPENAI_BATCH_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
BATCH_DEPLOYMENT = os.getenv("AZURE_OPENAI_BATCH_DEPLOYMENT_NAME", "gpt-4.1-batch")
API_VERSION = "2024-10-21"  # Versione con batch support

# Client separato per batch
batch_client = None
if BATCH_ENDPOINT and BATCH_API_KEY:
    batch_client = AzureOpenAI(
        api_key=BATCH_API_KEY,
        api_version=API_VERSION,
        azure_endpoint=BATCH_ENDPOINT
    )
    print(f"Batch client inizializzato con deployment: {BATCH_DEPLOYMENT}")
else:
    print("Batch client non inizializzato: credenziali mancanti")

class BatchService:
    """Gestisce batch processing con Azure OpenAI"""
    
    def __init__(self):
        self.batch_collection = db["batch_jobs"] if db is not None else None
        # RIMOSSO: self.sessions_collection globale - usiamo collezioni tenant-specific
    
    def create_cv_analysis_batch(self) -> Optional[str]:
        """
        Crea un batch job per analizzare tutti i CV pending (multi-tenant).
        
        Returns:
            batch_id: ID del batch job creato o None se nessun CV da processare
        """
        if not batch_client:
            print("ERR Batch client non disponibile")
            return None
            
        print(f"[PROC] Creazione batch per CV analysis...")
        
        # 1. Trova tutte le sessioni con CV pending (tutti i tenant)
        pending_sessions = []
        
        # Cerca in tutte le collection di sessioni tenant
        if db is not None:
            collections = db.list_collection_names()
            session_collections = [c for c in collections if c.endswith("_sessions")]
            
            for collection_name in session_collections:
                collection = db[collection_name]
                tenant_sessions = list(collection.find({
                    "stages.cv_analysis_status": "pending"
                }))
                
                # Aggiungi tenant_id a ogni sessione
                tenant_id = collection_name.replace("_sessions", "")
                for session in tenant_sessions:
                    session["tenant_id"] = tenant_id
                    pending_sessions.append(session)
        
        if not pending_sessions:
            print("OK Nessun CV da processare")
            return None
        
        print(f"[INFO] Trovati {len(pending_sessions)} CV da analizzare")
        
        # 2. Crea file JSONL per batch API
        batch_requests = []
        for session in pending_sessions:
            session_id = session["_id"]
            tenant_id = session["tenant_id"]
            cv_text = session.get("stages", {}).get("uploaded_cv_text", "")
            position_id = session.get("position_id")
            
            # Recupera JD, hr_special_needs e language dal tenant specifico
            if db is not None:
                positions_collection = db[f"{tenant_id}_positions_data"]
                position = positions_collection.find_one({"_id": position_id})
                jd_text = position.get("job_description", "") if position else ""
                hr_special_needs = position.get("hr_special_needs", "") if position else ""
                language = position.get("language", "it") if position else "it"
            else:
                jd_text = ""
                hr_special_needs = ""
                language = "it"
            
            # Crea prompt usando la funzione esistente con hr_special_needs e language
            try:
                from analyzer.prompts_analyzer import create_cv_analysis_prompt
                prompt = create_cv_analysis_prompt(cv_text, jd_text, hr_special_needs, language)
            except ImportError:
                # Fallback prompt se import fallisce
                prompt = f"Analizza questo CV per la posizione:\n\nCV:\n{cv_text}\n\nJob Description:\n{jd_text}"
            
            # System prompt bilingue basato sulla lingua
            system_prompts = {
                "it": "Agisci come un recruiter AI. Il tuo compito è seguire SCRUPOLOSAMENTE le istruzioni e il formato di output richiesto nel prompt dell'utente, producendo prima il report testuale e poi il blocco JSON.",
                "en": "Act as an AI recruiter. Your task is to SCRUPULOUSLY follow the instructions and the output format required in the user prompt, producing first the textual report and then the JSON block."
            }
            analyzer_system_prompt = system_prompts.get(language, system_prompts["it"])
            
            # Formato batch API Azure OpenAI
            batch_requests.append({
                "custom_id": f"{tenant_id}:{session_id}",  # Per identificare tenant e sessione
                "method": "POST",
                "url": "/chat/completions",
                "body": {
                    "model": BATCH_DEPLOYMENT,
                    "messages": [
                        {
                            "role": "system", 
                            "content": analyzer_system_prompt
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2500,
                    "temperature": 0.2
                }
            })
        
        # 3. Salva JSONL in file temporaneo
        batch_filename = f"batch_cv_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        temp_file_path = os.path.join(tempfile.gettempdir(), batch_filename)
        
        # Validazione dimensione batch
        if len(batch_requests) > 1000:
            print(f"[WARN] Batch troppo grande ({len(batch_requests)} richieste), limitato a 1000")
            batch_requests = batch_requests[:1000]
        
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            for req in batch_requests:
                f.write(json.dumps(req) + '\n')
        
        # 4. Upload file ad Azure OpenAI
        print("[CLOUD] Upload batch file ad Azure...")
        try:
            # Sopprimi errori tkinter non bloccanti durante upload
            with TkinterErrorFilter(sys.stderr):
                with open(temp_file_path, 'rb') as f:
                    batch_input_file = batch_client.files.create(
                        file=f,
                        purpose="batch"
                    )
        except Exception as e:
            print(f"ERR Errore upload file: {e}")
            # Cleanup file temporaneo
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return None
        
        # 5. Crea batch job
        print("[LAUNCH] Creazione batch job...")
        try:
            batch_job = batch_client.batches.create(
                input_file_id=batch_input_file.id,
                endpoint="/chat/completions",
                completion_window="24h",
                metadata={
                    "description": "CV Analysis Batch",
                    "created_at": datetime.utcnow().isoformat(),
                    "total_requests": len(batch_requests)
                }
            )
        except Exception as e:
            print(f"ERR Errore creazione batch: {e}")
            # Cleanup file temporaneo
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return None
        
        # 6. Salva info batch nel DB
        if self.batch_collection is not None:
            batch_doc = {
                "_id": batch_job.id,
                "type": "cv_analysis",
                "status": batch_job.status,
                "created_at": datetime.utcnow(),
                "input_file_id": batch_input_file.id,
                "session_ids": [s["_id"] for s in pending_sessions],
                "tenant_ids": list(set([s["tenant_id"] for s in pending_sessions])),
                "total_requests": len(batch_requests)
            }
            self.batch_collection.insert_one(batch_doc)
        
        # 7. Cleanup file locale
        os.remove(temp_file_path)
        
        print(f"OK Batch creato: {batch_job.id}")
        print(f"   Status: {batch_job.status}")
        print(f"   Requests: {len(batch_requests)}")
        
        return batch_job.id
    
    def create_feedback_batch(self) -> Optional[str]:
        """
        Crea un batch job per generare i report finali di feedback per tutte le sessioni pending (multi-tenant).
        
        Returns:
            batch_id: ID del batch job creato o None se nessuna sessione da processare
        """
        if not batch_client:
            print("ERR Batch client non disponibile")
            return None
            
        print(f"[PROC] Creazione batch per Feedback generation...")
        
        # 1. Trova tutte le sessioni con status FEEDBACK_PENDING e dati pronti (tutti i tenant)
        pending_sessions = []
        
        # Cerca in tutte le collection di sessioni tenant
        if db is not None:
            collections = db.list_collection_names()
            session_collections = [c for c in collections if c.endswith("_sessions")]
            
            for collection_name in session_collections:
                collection = db[collection_name]
                tenant_id = collection_name.replace("_sessions", "")
                
                # Trova sessioni con status FEEDBACK_PENDING e dati necessari
                tenant_sessions = list(collection.find({
                    "stages.status": "Feedback in coda batch (può richiedere fino a 24h)",
                    "stages.gap_analysis": {"$exists": True},
                    "stages.enriched_gaps": {"$exists": True},
                    "stages.cv_analysis_report": {"$exists": True},
                    "stages.case_evaluation_report": {"$exists": True}
                }))
                
                # Aggiungi tenant_id a ogni sessione
                for session in tenant_sessions:
                    session["tenant_id"] = tenant_id
                    pending_sessions.append(session)
        
        if not pending_sessions:
            print("OK Nessuna sessione feedback da processare")
            return None
        
        print(f"[INFO] Trovate {len(pending_sessions)} sessioni per generazione feedback")
        
        # 2. Valida e filtra sessioni con dati validi
        valid_sessions = []
        invalid_count = 0
        
        for session in pending_sessions:
            session_id = session["_id"]
            tenant_id = session["tenant_id"]
            stages = session.get("stages", {})
            
            # Validazione rigorosa dei dati
            validation_errors = []
            
            # 1. Validazione cv_analysis_report
            cv_report = stages.get("cv_analysis_report")
            if not cv_report or not isinstance(cv_report, str) or cv_report.strip() == "":
                validation_errors.append("cv_analysis_report mancante o vuoto")
            
            # 2. Validazione case_evaluation_report
            case_report = stages.get("case_evaluation_report")
            if not case_report or not isinstance(case_report, str) or case_report.strip() == "":
                validation_errors.append("case_evaluation_report mancante o vuoto")
            
            # 3. Validazione enriched_gaps
            enriched_gaps_json = stages.get("enriched_gaps")
            if not enriched_gaps_json or not isinstance(enriched_gaps_json, str) or enriched_gaps_json.strip() == "":
                validation_errors.append("enriched_gaps mancante o vuoto")
            elif enriched_gaps_json.strip() == "[]":
                validation_errors.append("enriched_gaps è una lista vuota '[]'")
            else:
                # Verifica che sia JSON valido
                try:
                    import json
                    parsed = json.loads(enriched_gaps_json)
                    if not parsed or (isinstance(parsed, list) and len(parsed) == 0):
                        validation_errors.append("enriched_gaps è una lista vuota dopo parsing")
                except json.JSONDecodeError:
                    validation_errors.append("enriched_gaps non è un JSON valido")
            
            # 4. Validazione gap_analysis
            gap_analysis = stages.get("gap_analysis")
            if not gap_analysis:
                validation_errors.append("gap_analysis mancante")
            elif isinstance(gap_analysis, dict) and len(gap_analysis) == 0:
                validation_errors.append("gap_analysis è un dizionario vuoto")
            elif isinstance(gap_analysis, str) and gap_analysis.strip() == "":
                validation_errors.append("gap_analysis è una stringa vuota")
            
            # Se ci sono errori di validazione, escludi la sessione
            if validation_errors:
                invalid_count += 1
                print(f"⚠️ [VALIDATION] Sessione {session_id} (tenant: {tenant_id}) esclusa dal batch:")
                for error in validation_errors:
                    print(f"   - {error}")
                continue
            
            # Sessione valida, aggiungila alla lista
            valid_sessions.append(session)
        
        if invalid_count > 0:
            print(f"⚠️ [VALIDATION] {invalid_count} sessioni escluse dal batch per dati invalidi")
        
        if not valid_sessions:
            print("❌ [VALIDATION] Nessuna sessione valida da processare. Batch non creato.")
            return None
        
        print(f"✅ [VALIDATION] {len(valid_sessions)} sessioni valide su {len(pending_sessions)} totali")
        
        # 3. Crea file JSONL per batch API
        batch_requests = []
        for session in valid_sessions:
            session_id = session["_id"]
            tenant_id = session["tenant_id"]
            stages = session.get("stages", {})
            
            cv_report = stages.get("cv_analysis_report", "")
            case_report = stages.get("case_evaluation_report", "")
            enriched_gaps_json = stages.get("enriched_gaps", "[]")
            candidate_name = session.get("candidate_name", "Candidato")
            
            # Recupera target_role e language dalla posizione
            position_id = session.get("position_id")
            target_role = "Ruolo non specificato"
            language = "it"
            
            if db is not None and position_id:
                positions_collection = db[f"{tenant_id}_positions_data"]
                position = positions_collection.find_one({"_id": position_id})
                if position:
                    target_role = position.get("position_name", target_role)
                    language = position.get("language", "it")
            
            # Validazione finale prima di creare il prompt
            if not candidate_name or candidate_name.strip() == "":
                print(f"⚠️ [VALIDATION] Sessione {session_id}: candidate_name mancante, uso default")
                candidate_name = "Candidato"
            
            if not target_role or target_role.strip() == "":
                print(f"⚠️ [VALIDATION] Sessione {session_id}: target_role mancante, uso default")
                target_role = "Ruolo non specificato"
            
            # Verifica che i dati siano ancora validi (doppio controllo)
            if not cv_report or cv_report.strip() == "":
                print(f"⚠️ [VALIDATION] Sessione {session_id}: cv_report vuoto dopo validazione iniziale, esclusa")
                continue
            
            if not case_report or case_report.strip() == "":
                print(f"⚠️ [VALIDATION] Sessione {session_id}: case_report vuoto dopo validazione iniziale, esclusa")
                continue
            
            if not enriched_gaps_json or enriched_gaps_json.strip() == "" or enriched_gaps_json.strip() == "[]":
                print(f"⚠️ [VALIDATION] Sessione {session_id}: enriched_gaps vuoto dopo validazione iniziale, esclusa")
                continue
            
            # Crea prompt usando la funzione esistente
            try:
                from feedback_generator.pathway_architect.prompts_pathway import create_final_report_prompt
                prompt = create_final_report_prompt(
                    cv_analysis_report=cv_report,
                    case_evaluation_report=case_report,
                    enriched_gaps_json_str=enriched_gaps_json,
                    candidate_name=candidate_name,
                    target_role=target_role,
                    language=language
                )
                
                # Verifica che il prompt non sia vuoto
                if not prompt or prompt.strip() == "":
                    print(f"⚠️ [VALIDATION] Sessione {session_id}: prompt generato vuoto, esclusa")
                    continue
            except ImportError:
                print(f"[WARN] Errore import prompts_pathway per sessione {session_id}")
                continue
            except Exception as e:
                print(f"⚠️ [VALIDATION] Errore creazione prompt per sessione {session_id}: {e}")
                continue
            
            # System prompt
            system_prompts = {
                "it": "Sei un Career Coach AI e un formatore esperto. Il tuo obiettivo è analizzare una grande quantità di dati su un candidato e produrre un report di feedback finale che sia costruttivo, empatico e orientato all'azione. Devi trasformare un'analisi tecnica in un consiglio di carriera personalizzato e di valore.",
                "en": "You are an AI Career Coach and expert trainer. Your goal is to analyze a large amount of data about a candidate and produce a final feedback report that is constructive, empathetic and action-oriented. You must transform a technical analysis into personalized and valuable career advice."
            }
            system_prompt = system_prompts.get(language, system_prompts["it"])
            
            # Schema per tool calling (FinalReportContent)
            try:
                from feedback_generator.pathway_architect.architect import FinalReportContent
                tool_schema = FinalReportContent.model_json_schema()
            except ImportError:
                print(f"[WARN] Errore import FinalReportContent per sessione {session_id}")
                continue
            
            # Formato batch API Azure OpenAI con tool calling
            batch_requests.append({
                "custom_id": f"{tenant_id}:{session_id}",
                "method": "POST",
                "url": "/chat/completions",
                "body": {
                    "model": BATCH_DEPLOYMENT,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "save_final_feedback_report",
                                "description": "Salva i dati strutturati per il report finale di feedback",
                                "parameters": tool_schema
                            }
                        }
                    ],
                    "tool_choice": {"type": "function", "function": {"name": "save_final_feedback_report"}},
                    "temperature": 0.7,
                    "max_tokens": 3000
                }
            })
        
        if not batch_requests:
            print("OK Nessuna richiesta valida da processare")
            return None
        
        # 4. Salva JSONL in file temporaneo
        batch_filename = f"batch_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        temp_file_path = os.path.join(tempfile.gettempdir(), batch_filename)
        
        # Validazione dimensione batch
        if len(batch_requests) > 1000:
            print(f"[WARN] Batch troppo grande ({len(batch_requests)} richieste), limitato a 1000")
            batch_requests = batch_requests[:1000]
        
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            for req in batch_requests:
                f.write(json.dumps(req) + '\n')
        
        # 5. Upload file ad Azure OpenAI
        print("[CLOUD] Upload batch file ad Azure...")
        try:
            # Sopprimi errori tkinter non bloccanti durante upload
            with TkinterErrorFilter(sys.stderr):
                with open(temp_file_path, 'rb') as f:
                    batch_input_file = batch_client.files.create(
                        file=f,
                        purpose="batch"
                    )
        except Exception as e:
            print(f"ERR Errore upload file: {e}")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return None
        
        # 6. Crea batch job
        print("[LAUNCH] Creazione batch job...")
        try:
            batch_job = batch_client.batches.create(
                input_file_id=batch_input_file.id,
                endpoint="/chat/completions",
                completion_window="24h",
                metadata={
                    "description": "Feedback Report Generation Batch",
                    "created_at": datetime.utcnow().isoformat(),
                    "total_requests": len(batch_requests)
                }
            )
        except Exception as e:
            print(f"ERR Errore creazione batch: {e}")
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return None
        
        # 7. Salva info batch nel DB
        if self.batch_collection is not None:
            batch_doc = {
                "_id": batch_job.id,
                "type": "feedback",
                "status": batch_job.status,
                "created_at": datetime.utcnow(),
                "input_file_id": batch_input_file.id,
                "session_ids": [s["_id"] for s in pending_sessions],
                "tenant_ids": list(set([s["tenant_id"] for s in pending_sessions])),
                "total_requests": len(batch_requests)
            }
            self.batch_collection.insert_one(batch_doc)
        
        # 7. Cleanup file locale
        os.remove(temp_file_path)
        
        print(f"OK Batch creato: {batch_job.id}")
        print(f"   Status: {batch_job.status}")
        print(f"   Requests: {len(batch_requests)}")
        
        return batch_job.id
    
    def check_batch_status(self, batch_id: str) -> str:
        """Controlla lo status di un batch job su Azure e sincronizza il DB.
        
        Nota: l'Azure OpenAI Batch API usa lo stato `succeeded` quando il batch
        è completato con successo. Internamente lo normalizziamo a `completed`
        per coerenza con il resto del codice (batch processor, UI, ecc.).
        """
        if not batch_client:
            return "error"
            
        try:
            batch = batch_client.batches.retrieve(batch_id)
            
            # Normalizza lo stato Azure -> interno
            raw_status = getattr(batch, "status", None)
            normalized_status = "completed" if raw_status == "succeeded" else raw_status
            
            # Aggiorna status nel DB
            if self.batch_collection is not None and normalized_status is not None:
                update_data = {
                    "status": normalized_status,
                    "updated_at": datetime.utcnow()
                }
                
                if normalized_status == "completed":
                    update_data["completed_at"] = datetime.utcnow()
                elif normalized_status == "failed":
                    update_data["failed_at"] = datetime.utcnow()
                
                # request_counts è disponibile solo dopo la validazione
                if hasattr(batch, "request_counts") and batch.request_counts:
                    update_data["request_counts"] = {
                        "total": batch.request_counts.total,
                        "completed": batch.request_counts.completed,
                        "failed": batch.request_counts.failed
                    }
                
                self.batch_collection.update_one(
                    {"_id": batch_id},
                    {"$set": update_data}
                )
            
            return normalized_status or "error"
        except Exception as e:
            print(f"ERR Errore controllo status batch {batch_id}: {e}")
            return "error"
    
    def retrieve_batch_results(self, batch_id: str) -> bool:
        """Recupera e salva i risultati di un batch completato"""
        if not batch_client:
            print("ERR Batch client non disponibile")
            return False
            
        print(f"[DOWNLOAD] Recupero risultati batch {batch_id}...")
        
        try:
            # 1. Ottieni info batch
            batch = batch_client.batches.retrieve(batch_id)
            
            # Normalizza status Azure -> interno (succeeded -> completed)
            raw_status = getattr(batch, "status", None)
            normalized_status = "completed" if raw_status == "succeeded" else raw_status
            
            if normalized_status != "completed":
                print(f"[WARN] Batch non completato. Status Azure: {raw_status}, normalizzato: {normalized_status}")
                return False
            
            # 2. Download file risultati
            if not batch.output_file_id:
                print("ERR Nessun file output disponibile")
                return False
            
            print(f"[DOWNLOAD] File output ID: {batch.output_file_id}")
            result_file_content = batch_client.files.content(batch.output_file_id)
            print(f"[DOWNLOAD] File risultati scaricato ({len(result_file_content.text)} caratteri)")
            
            # 3. Parse risultati (JSONL)
            results = []
            lines = result_file_content.text.strip().split('\n')
            print(f"[PARSE] Parsing {len(lines)} righe JSONL...")
            for line_num, line in enumerate(lines, 1):
                if line.strip():
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"[WARN] Errore parsing riga {line_num}: {e}")
                        print(f"       Contenuto: {line[:100]}...")
            
            print(f"[PARSE] Parsati {len(results)} risultati validi")
            
            # 4. Salva risultati in MongoDB con tenant isolation
            success_count = 0
            for result in results:
                custom_id = result.get("custom_id", "")
                
                # Split tenant_id:session_id
                if ":" not in custom_id:
                    print(f"[WARN] Custom ID malformato: {custom_id}")
                    continue
                
                tenant_id, session_id = custom_id.split(":", 1)
                
                # Verifica che il tenant esista
                if db is None:
                    continue
                    
                sessions_collection = db[f"{tenant_id}_sessions"]
                session = sessions_collection.find_one({"_id": session_id})
                
                if not session:
                    print(f"[WARN] Sessione {session_id} non trovata per tenant {tenant_id}")
                    continue
                
                if result.get("response") and result["response"]["status_code"] == 200:
                    # Estrai la risposta
                    response_body = result["response"]["body"]
                    analysis_text = response_body["choices"][0]["message"]["content"]
                    
                    # Parsa la risposta per estrarre report_text, structured_experience e candidate_name
                    try:
                        from analyzer.cv_analyzer import parse_mixed_llm_response
                        parsed_data = parse_mixed_llm_response(analysis_text)
                        report_text = parsed_data.get("report_text", analysis_text)
                        structured_experience = parsed_data.get("structured_experience", [])
                        candidate_name = parsed_data.get("candidate_name")
                    except Exception as e:
                        print(f"[WARN] Errore durante il parsing della risposta per sessione {session_id}: {e}")
                        # Fallback: salva il testo grezzo
                        report_text = analysis_text
                        structured_experience = []
                        candidate_name = None
                    
                    # Prepara i campi da aggiornare
                    update_fields = {
                        "stages.cv_analysis_report": report_text,
                        "stages.parsed_experience": structured_experience,
                        "stages.cv_analysis_status": "Completed",
                        "stages.cv_analysis_completed_at": datetime.utcnow().isoformat()
                    }
                    
                    # Aggiungi candidate_name se estratto (salvato nel root del documento, non in stages)
                    if candidate_name:
                        update_fields["candidate_name"] = candidate_name
                        print(f"  - Nome candidato estratto per sessione {session_id}: {candidate_name}")
                    
                    # Salva in sessione (tenant-specific)
                    sessions_collection.update_one(
                        {"_id": session_id},
                        {"$set": update_fields}
                    )
                    success_count += 1
                else:
                    # Gestisci errore
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    sessions_collection.update_one(
                        {"_id": session_id},
                        {"$set": {
                            "stages.cv_analysis_status": "Failed",
                            "stages.cv_analysis_error": error_msg
                        }}
                    )
            
            print(f"OK Processati {success_count}/{len(results)} risultati")
            
            # 5. Genera token automaticamente per sessioni completate
            print(f"[TOKEN] Generazione automatica token per {success_count} sessioni...")
            for result in results:
                custom_id = result.get("custom_id", "")
                if ":" not in custom_id:
                    continue
                
                tenant_id, session_id = custom_id.split(":", 1)
                sessions_collection = db[f"{tenant_id}_sessions"]
                
                if result.get("response") and result["response"]["status_code"] == 200:
                    # Genera token se non esiste
                    from services.token_service import issue_interview_token
                    session = sessions_collection.find_one({"_id": session_id})
                    if session and not session.get("stages", {}).get("interview_token"):
                        token = issue_interview_token(session_id, f"{tenant_id}_interview_links")
                        sessions_collection.update_one(
                            {"_id": session_id},
                            {"$set": {"stages.interview_token": token}}
                        )
                        print(f"   🔑 Token generato automaticamente per sessione {session_id}")
            
            # 6. Marca batch come processato
            if self.batch_collection is not None:
                self.batch_collection.update_one(
                    {"_id": batch_id},
                    {"$set": {
                        "status": "processed",
                        "processed_at": datetime.utcnow(),
                        "results_saved": success_count
                    }}
                )
            
            return True
            
        except Exception as e:
            print(f"ERR Errore recupero risultati batch {batch_id}: {e}")
            return False
    
    def retrieve_feedback_batch_results(self, batch_id: str) -> bool:
        """Recupera e processa i risultati di un batch di feedback completato"""
        if not batch_client:
            print("ERR Batch client non disponibile")
            return False
            
        print(f"[DOWNLOAD] Recupero risultati feedback batch {batch_id}...")
        
        try:
            # 1. Ottieni info batch
            batch = batch_client.batches.retrieve(batch_id)
            
            # Normalizza status Azure -> interno (succeeded -> completed)
            raw_status = getattr(batch, "status", None)
            normalized_status = "completed" if raw_status == "succeeded" else raw_status
            
            if normalized_status != "completed":
                print(f"[WARN] Batch non completato. Status Azure: {raw_status}, normalizzato: {normalized_status}")
                return False
            
            # 2. Download file risultati
            if not batch.output_file_id:
                print("ERR Nessun file output disponibile")
                return False
            
            result_file_content = batch_client.files.content(batch.output_file_id)
            
            # 3. Parse risultati (JSONL)
            results = []
            for line in result_file_content.text.strip().split('\n'):
                if line.strip():
                    results.append(json.loads(line))
            
            # 4. Processa risultati e genera PDF per ogni sessione
            success_count = 0
            for result in results:
                custom_id = result.get("custom_id", "")
                
                # Split tenant_id:session_id
                if ":" not in custom_id:
                    print(f"[WARN] Custom ID malformato: {custom_id}")
                    continue
                
                tenant_id, session_id = custom_id.split(":", 1)
                
                # Verifica che il tenant esista
                if db is None:
                    continue
                    
                sessions_collection = db[f"{tenant_id}_sessions"]
                session = sessions_collection.find_one({"_id": session_id})
                
                if not session:
                    print(f"[WARN] Sessione {session_id} non trovata per tenant {tenant_id}")
                    continue
                
                if result.get("response") and result["response"]["status_code"] == 200:
                    # Estrai la risposta (tool call arguments)
                    response_body = result["response"]["body"]
                    tool_calls = response_body.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
                    
                    if not tool_calls:
                        print(f"[WARN] Nessun tool call nella risposta per sessione {session_id}")
                        continue
                    
                    # Estrai arguments dal tool call
                    arguments_str = tool_calls[0].get("function", {}).get("arguments", "{}")
                    
                    try:
                        # Valida e crea FinalReportContent
                        from feedback_generator.pathway_architect.architect import FinalReportContent, _match_course_urls_from_db
                        parsed_json = json.loads(arguments_str)
                        final_report_content = FinalReportContent.model_validate(parsed_json)
                        
                        # Match degli URL dei corsi con quelli del database
                        if final_report_content.suggested_pathway:
                            print(f"   🔍 [URL MATCH] Correzione URL dei corsi per sessione {session_id}...")
                            final_report_content.suggested_pathway = _match_course_urls_from_db(final_report_content.suggested_pathway)
                        
                        # Recupera dati aggiuntivi dalla sessione
                        stages = session.get("stages", {})
                        language = "it"
                        position_id = session.get("position_id")
                        
                        if db is not None and position_id:
                            positions_collection = db[f"{tenant_id}_positions_data"]
                            position = positions_collection.find_one({"_id": position_id})
                            if position:
                                language = position.get("language", "it")
                        
                        # Aggiungi market benchmark se disponibile
                        market_benchmark_text = stages.get("market_benchmark_text")
                        if market_benchmark_text:
                            final_report_content.market_benchmark = market_benchmark_text
                        
                        # Genera PDF
                        from feedback_generator.pathway_architect.pdf_service import create_feedback_pdf
                        import os
                        
                        temp_dir = "temp_pdf"
                        os.makedirs(temp_dir, exist_ok=True)
                        temp_pdf_path = os.path.join(temp_dir, f"{session_id}.pdf")
                        
                        create_feedback_pdf(
                            report_content=final_report_content,
                            output_path=temp_pdf_path,
                            language=language,
                            market_benchmark_text=market_benchmark_text,
                            market_chart_categories_base64=stages.get("market_chart_categories_base64"),
                            market_skills_list=stages.get("market_chart_skills_base64")
                        )
                        
                        # Salva PDF
                        if os.path.exists(temp_pdf_path):
                            with open(temp_pdf_path, "rb") as f:
                                pdf_bytes = f.read()
                            
                            from services.tenant_data_manager import save_pdf_report_tenant
                            pdf_path = save_pdf_report_tenant(pdf_bytes, session_id, f"{tenant_id}_sessions")
                            os.remove(temp_pdf_path)
                            
                            # Aggiorna sessione
                            from services.tenant_data_manager import SESSION_STATUS
                            sessions_collection.update_one(
                                {"_id": session_id},
                                {"$set": {
                                    "stages.feedback_pdf_path": pdf_path,
                                    "stages.status": SESSION_STATUS["FEEDBACK_READY"]
                                }}
                            )
                            success_count += 1
                            print(f"   ✅ PDF generato per sessione {session_id}")
                        else:
                            print(f"   ❌ PDF non generato per sessione {session_id}")
                            
                    except Exception as e:
                        print(f"[WARN] Errore durante il processing per sessione {session_id}: {e}")
                        import traceback
                        traceback.print_exc()
                        # Marca come fallito
                        from services.tenant_data_manager import SESSION_STATUS
                        sessions_collection.update_one(
                            {"_id": session_id},
                            {"$set": {
                                "stages.status": SESSION_STATUS["FEEDBACK_GENERATION_FAILED"],
                                "stages.feedback_error": str(e)
                            }}
                        )
                else:
                    # Gestisci errore
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    from services.tenant_data_manager import SESSION_STATUS
                    sessions_collection.update_one(
                        {"_id": session_id},
                        {"$set": {
                            "stages.status": SESSION_STATUS["FEEDBACK_GENERATION_FAILED"],
                            "stages.feedback_error": error_msg
                        }}
                    )
            
            print(f"OK Processati {success_count}/{len(results)} risultati feedback")
            
            # 5. Marca batch come processato
            if self.batch_collection is not None:
                self.batch_collection.update_one(
                    {"_id": batch_id},
                    {"$set": {
                        "status": "processed",
                        "processed_at": datetime.utcnow(),
                        "results_saved": success_count
                    }}
                )
            
            return True
            
        except Exception as e:
            print(f"ERR Errore recupero risultati feedback batch {batch_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_batch_info(self, batch_id: str) -> Optional[Dict]:
        """Ottieni informazioni dettagliate su un batch"""
        if self.batch_collection is None:
            return None
            
        return self.batch_collection.find_one({"_id": batch_id})
    
    def list_batches(self, limit: int = 20) -> List[Dict]:
        """Lista tutti i batch jobs"""
        try:
            if self.batch_collection is None:
                print("ERR Batch collection non disponibile")
                return []
                
            batches = list(self.batch_collection.find(
                {},
                sort=[("created_at", -1)],
                limit=limit
            ))
            
            # Converti ObjectId in string per JSON serialization
            for batch in batches:
                if '_id' in batch:
                    batch['_id'] = str(batch['_id'])
                    
            return batches
            
        except Exception as e:
            print(f"ERR Errore nel list_batches: {e}")
            return []
