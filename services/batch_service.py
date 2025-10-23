import os
import json
import tempfile
from typing import List, Dict, Optional
from datetime import datetime
from openai import AzureOpenAI
from services.data_manager import db
from services.email_parser import extract_email_from_text

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
            
            # Recupera JD dal tenant specifico
            if db is not None:
                positions_collection = db[f"{tenant_id}_positions_data"]
                position = positions_collection.find_one({"_id": position_id})
                jd_text = position.get("job_description", "") if position else ""
            else:
                jd_text = ""
            
            # Crea prompt usando la funzione esistente
            try:
                from analyzer.prompts_analyzer import create_cv_analysis_prompt
                prompt = create_cv_analysis_prompt(cv_text, jd_text, "")
            except ImportError:
                # Fallback prompt se import fallisce
                prompt = f"Analizza questo CV per la posizione:\n\nCV:\n{cv_text}\n\nJob Description:\n{jd_text}"
            
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
                            "content": "Agisci come un recruiter aziendale esperto. Il tuo compito è valutare un CV in modo critico rispetto a un annuncio di lavoro. L'obiettivo è produrre un report professionale, chiaro e leggibile velocemente, che evidenzi i punti di allineamento e le carenze del profilo."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.4
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
    
    def check_batch_status(self, batch_id: str) -> str:
        """Controlla lo status di un batch job"""
        if not batch_client:
            return "error"
            
        try:
            batch = batch_client.batches.retrieve(batch_id)
            
            # Aggiorna status nel DB
            if self.batch_collection is not None:
                update_data = {
                    "status": batch.status,
                    "updated_at": datetime.utcnow()
                }
                
                if batch.status == "completed":
                    update_data["completed_at"] = datetime.utcnow()
                elif batch.status == "failed":
                    update_data["failed_at"] = datetime.utcnow()
                
                if hasattr(batch, 'request_counts') and batch.request_counts:
                    update_data["request_counts"] = {
                        "total": batch.request_counts.total,
                        "completed": batch.request_counts.completed,
                        "failed": batch.request_counts.failed
                    }
                
                self.batch_collection.update_one(
                    {"_id": batch_id},
                    {"$set": update_data}
                )
            
            return batch.status
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
            
            if batch.status != "completed":
                print(f"[WARN] Batch non completato. Status: {batch.status}")
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
                    
                    # Salva in sessione (tenant-specific)
                    sessions_collection.update_one(
                        {"_id": session_id},
                        {"$set": {
                            "stages.cv_analysis_report": analysis_text,
                            "stages.cv_analysis_status": "Completed",
                            "stages.cv_analysis_completed_at": datetime.utcnow().isoformat()
                        }}
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
            print(f"ERR Errore recupero risultati batch {batch_id}: {e}")
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
