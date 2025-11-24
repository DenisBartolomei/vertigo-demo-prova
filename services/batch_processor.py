import time
import threading
from datetime import datetime
from services.batch_service import BatchService

class BatchProcessor:
    """Worker che controlla batch in progress e recupera risultati automaticamente"""
    
    def __init__(self):
        self.batch_service = BatchService()
        self.running = False
        self.processor_thread = None
    
    def start_monitoring(self, check_interval_seconds: int = 300):
        """
        Monitora batch jobs ogni 5 minuti (default)
        
        Args:
            check_interval_seconds: Intervallo tra i controlli in secondi
        """
        if self.running:
            print("⚠️ Batch processor già in esecuzione")
            return
            
        self.running = True
        print(f"🔄 Batch processor avviato (controllo ogni {check_interval_seconds}s)")
        
        def monitor_loop():
            while self.running:
                try:
                    self._check_and_process_batches()
                except Exception as e:
                    print(f"❌ Errore nel batch processor: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Sleep con possibilità di interruzione
                for _ in range(check_interval_seconds):
                    if not self.running:
                        break
                    time.sleep(1)
        
        self.processor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.processor_thread.start()
        print("✅ Batch processor thread avviato")
    
    def stop_monitoring(self):
        """Ferma il monitoring"""
        if not self.running:
            print("⚠️ Batch processor non in esecuzione")
            return
            
        self.running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=10)
        print("🛑 Batch processor fermato")
    
    def _check_and_process_batches(self):
        """Controlla batch in progress e recupera risultati se completati, e crea nuovi batch se necessario"""
        try:
            # 1. Controlla se creare nuovi batch di feedback
            self._check_and_create_feedback_batch()
            
            # 2. Trova batch in progress
            in_progress_batches = self._get_in_progress_batches()
            
            if not in_progress_batches:
                return  # Nessun batch da controllare
            
            print(f"🔍 Controllo {len(in_progress_batches)} batch in progress...")
            
            for batch_info in in_progress_batches:
                batch_id = batch_info["_id"]
                print(f"   📋 Controllo batch {batch_id}...")
                
                # Controlla status
                status = self.batch_service.check_batch_status(batch_id)
                
                if status == "completed":
                    # Verifica che non sia già stato processato
                    if not batch_info.get("processed_at"):
                        print(f"   ✅ Batch {batch_id} completato! Recupero risultati...")
                        # Usa il metodo appropriato in base al tipo di batch
                        batch_type = batch_info.get("type", "cv_analysis")
                        if batch_type == "feedback":
                            success = self.batch_service.retrieve_feedback_batch_results(batch_id)
                        else:
                            success = self.batch_service.retrieve_batch_results(batch_id)
                        if success:
                            print(f"   ✅ Risultati batch {batch_id} salvati con successo")
                        else:
                            print(f"   ❌ Errore nel salvataggio risultati batch {batch_id}")
                    else:
                        print(f"   ℹ️ Batch {batch_id} già processato")
                        
                elif status == "failed":
                    print(f"   ❌ Batch {batch_id} fallito")
                    
                elif status in ["validating", "in_progress", "finalizing"]:
                    print(f"   ⏳ Batch {batch_id} ancora in corso (status: {status})")
                    
                else:
                    print(f"   ❓ Batch {batch_id} status sconosciuto: {status}")
                    
        except Exception as e:
            print(f"❌ Errore nel controllo batch: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_in_progress_batches(self) -> list:
        """Ottieni lista batch in progress dal database"""
        try:
            if self.batch_service.batch_collection is None:
                return []
            
            # Trova batch che non sono ancora stati processati
            in_progress = list(self.batch_service.batch_collection.find({
                "status": {"$in": ["validating", "in_progress", "finalizing", "completed"]},
                "processed_at": {"$exists": False}  # Non ancora processati
            }))
            
            return in_progress
            
        except Exception as e:
            print(f"❌ Errore nel recupero batch in progress: {e}")
            return []
    
    def _check_and_create_feedback_batch(self):
        """Controlla se ci sono abbastanza sessioni FEEDBACK_PENDING e crea un batch se necessario"""
        try:
            from services.data_manager import db
            if db is None:
                return
            
            # Conta sessioni FEEDBACK_PENDING con dati pronti
            collections = db.list_collection_names()
            session_collections = [c for c in collections if c.endswith("_sessions")]
            
            total_pending = 0
            for collection_name in session_collections:
                collection = db[collection_name]
                count = collection.count_documents({
                    "stages.status": "Feedback in coda batch (può richiedere fino a 24h)",
                    "stages.gap_analysis": {"$exists": True},
                    "stages.enriched_gaps": {"$exists": True},
                    "stages.cv_analysis_report": {"$exists": True},
                    "stages.case_evaluation_report": {"$exists": True}
                })
                total_pending += count
            
            if total_pending == 0:
                return  # Nessuna sessione pending
            
            # Controlla se esiste un batch feedback precedente
            last_feedback_batch = None
            if self.batch_service.batch_collection is not None:
                from datetime import timedelta
                # Cerca l'ultimo batch feedback (qualsiasi, non solo quelli recenti)
                last_feedback_batch = self.batch_service.batch_collection.find_one(
                    {"type": "feedback"},
                    sort=[("created_at", -1)]  # Ordina per data decrescente, prendi il più recente
                )
            
            # Logica di creazione batch:
            # 1. Se non ci sono batch precedenti → crea batch subito con almeno 1 sessione
            # 2. Se >= 10 sessioni → crea batch subito (indipendentemente dal tempo)
            # 3. Altrimenti, se è passato >= 60 minuti dall'ultimo batch → crea batch
            # 4. Altrimenti → aspetta
            
            if last_feedback_batch is None:
                # Primo batch: crea subito se ci sono sessioni pending
                print(f"📦 Creazione primo batch feedback per {total_pending} sessioni pending...")
                batch_id = self.batch_service.create_feedback_batch()
                if batch_id:
                    print(f"✅ Batch feedback creato: {batch_id}")
                else:
                    print(f"⚠️ Impossibile creare batch feedback")
            elif total_pending >= 10:
                # Abbastanza sessioni: crea batch subito (indipendentemente dal tempo)
                print(f"📦 Creazione batch feedback per {total_pending} sessioni pending...")
                batch_id = self.batch_service.create_feedback_batch()
                if batch_id:
                    print(f"✅ Batch feedback creato: {batch_id}")
                else:
                    print(f"⚠️ Impossibile creare batch feedback")
            else:
                # Controlla se sono passati >= 60 minuti dall'ultimo batch
                from datetime import timedelta
                last_batch_time = last_feedback_batch.get("created_at")
                if last_batch_time:
                    sixty_minutes_ago = datetime.utcnow() - timedelta(minutes=60)
                    if last_batch_time <= sixty_minutes_ago:
                        # Sono passati >= 60 minuti dall'ultimo batch → crea batch
                        print(f"📦 Creazione batch feedback per {total_pending} sessioni pending (sono passati >= 60 minuti dall'ultimo batch)...")
                        batch_id = self.batch_service.create_feedback_batch()
                        if batch_id:
                            print(f"✅ Batch feedback creato: {batch_id}")
                        else:
                            print(f"⚠️ Impossibile creare batch feedback")
                    else:
                        # Meno di 60 minuti dall'ultimo batch → aspetta
                        minutes_since_last = (datetime.utcnow() - last_batch_time).total_seconds() / 60
                        print(f"ℹ️ {total_pending} sessioni feedback pending (minimo 10 per creare batch, oppure aspetta 60 minuti dall'ultimo batch - ultimo batch {minutes_since_last:.1f} minuti fa)")
                else:
                    # Batch senza timestamp: crea comunque (caso edge)
                    print(f"📦 Creazione batch feedback per {total_pending} sessioni pending (ultimo batch senza timestamp)...")
                    batch_id = self.batch_service.create_feedback_batch()
                    if batch_id:
                        print(f"✅ Batch feedback creato: {batch_id}")
                    else:
                        print(f"⚠️ Impossibile creare batch feedback")
                
        except Exception as e:
            print(f"❌ Errore nel controllo batch feedback: {e}")
            import traceback
            traceback.print_exc()
    
    def force_check_batch(self, batch_id: str) -> str:
        """Forza controllo di un batch specifico (per testing)"""
        try:
            print(f"🔧 Controllo forzato batch {batch_id}...")
            
            status = self.batch_service.check_batch_status(batch_id)
            
            if status == "completed":
                success = self.batch_service.retrieve_batch_results(batch_id)
                if success:
                    return f"Batch {batch_id} completato e risultati salvati"
                else:
                    return f"Batch {batch_id} completato ma errore nel salvataggio"
            else:
                return f"Batch {batch_id} status: {status}"
                
        except Exception as e:
            return f"Errore controllo batch {batch_id}: {e}"
    
    def get_monitoring_stats(self) -> dict:
        """Ottieni statistiche del monitoring"""
        try:
            if self.batch_service.batch_collection is None:
                return {"error": "Database non disponibile"}
            
            # Conta batch per status
            stats = {
                "total_batches": self.batch_service.batch_collection.count_documents({}),
                "in_progress": self.batch_service.batch_collection.count_documents({
                    "status": {"$in": ["validating", "in_progress", "finalizing"]}
                }),
                "completed": self.batch_service.batch_collection.count_documents({
                    "status": "completed"
                }),
                "failed": self.batch_service.batch_collection.count_documents({
                    "status": "failed"
                }),
                "processed": self.batch_service.batch_collection.count_documents({
                    "processed_at": {"$exists": True}
                }),
                "monitoring_active": self.running
            }
            
            return stats
            
        except Exception as e:
            return {"error": f"Errore statistiche: {e}"}

# Singleton globale
_processor = None

def get_processor() -> BatchProcessor:
    """Ottieni l'istanza singleton del processor"""
    global _processor
    if _processor is None:
        _processor = BatchProcessor()
    return _processor
