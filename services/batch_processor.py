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
        """Controlla batch in progress e recupera risultati se completati"""
        try:
            # Trova batch in progress
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
            if not self.batch_service.batch_collection:
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
            if not self.batch_service.batch_collection:
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
