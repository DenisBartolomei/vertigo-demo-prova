import schedule
import time
import threading
from datetime import datetime
from services.batch_service import BatchService

class BatchScheduler:
    """Scheduler per eseguire batch jobs automaticamente"""
    
    def __init__(self):
        self.batch_service = BatchService()
        self.running = False
        self.scheduler_thread = None
    
    def schedule_daily_cv_batch(self, hour: str = "15:30"):
        """Schedula batch CV ogni giorno alle 15:30"""
        schedule.every().day.at(hour).do(self._run_cv_batch)
        print(f"📅 Scheduler configurato: batch CV alle {hour}")
    
    def _run_cv_batch(self):
        """Esegue batch CV per tutti i tenant"""
        print(f"\n{'='*60}")
        print(f"🕐 {datetime.now()} - Avvio batch schedulato CV analysis")
        print(f"{'='*60}\n")
        
        try:
            # Crea batch globale (multi-tenant)
            batch_id = self.batch_service.create_cv_analysis_batch()
            
            if batch_id:
                print(f"✅ Batch schedulato creato: {batch_id}")
            else:
                print("ℹ️ Nessun CV da processare nel batch schedulato")
                
        except Exception as e:
            print(f"❌ Errore durante batch schedulato: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self):
        """Avvia lo scheduler in background"""
        if self.running:
            print("⚠️ Scheduler già in esecuzione")
            return
            
        self.running = True
        
        def run_scheduler():
            print("🚀 Scheduler avviato in background")
            while self.running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Check ogni minuto
                except Exception as e:
                    print(f"❌ Errore nel scheduler: {e}")
                    time.sleep(60)  # Continua anche in caso di errore
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        print("✅ Scheduler thread avviato")
    
    def stop(self):
        """Ferma lo scheduler"""
        if not self.running:
            print("⚠️ Scheduler non in esecuzione")
            return
            
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("🛑 Scheduler fermato")
    
    def get_next_run_time(self) -> str:
        """Ottieni il prossimo orario di esecuzione"""
        jobs = schedule.get_jobs()
        if jobs:
            next_run = jobs[0].next_run
            return next_run.strftime("%Y-%m-%d %H:%M:%S")
        return "Nessun job schedulato"
    
    def trigger_manual_batch(self) -> str:
        """Trigger manuale del batch (per testing)"""
        print("🔧 Trigger manuale batch...")
        try:
            batch_id = self.batch_service.create_cv_analysis_batch()
            if batch_id:
                return f"Batch creato: {batch_id}"
            else:
                return "Nessun CV da processare"
        except Exception as e:
            return f"Errore: {e}"

# Singleton globale
_scheduler = None

def get_scheduler() -> BatchScheduler:
    """Ottieni l'istanza singleton del scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BatchScheduler()
    return _scheduler

