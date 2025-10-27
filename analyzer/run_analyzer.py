# Importiamo 'db' per interrogare la collection delle posizioni
from services.data_manager import db, get_session_data, save_stage_output
from .cv_analyzer import analyze_cv

def run_cv_analysis_pipeline(session_id: str) -> bool:
    """
    Esegue l'analisi unificata del CV e l'estrazione delle esperienze.
    """
    print(f"--- [PIPELINE] Avvio Analisi CV Unificata per sessione: {session_id} ---")
    
    # 1. Recupera i dati della sessione
    session_data = get_session_data(session_id)
    if not session_data:
        print(f"  - ERRORE: Dati di sessione non trovati per {session_id}")
        return False
        
    stages = session_data.get("stages", {})
    cv_text = stages.get("uploaded_cv_text")
    position_id = session_data.get("position_id")
    
    if not cv_text or not position_id:
        print("  - ERRORE: CV o position_id mancanti nel documento di sessione.")
        return False
        
    # 2. Carica la Job Description da MongoDB
    print(f"  - Caricamento Job Description per '{position_id}'...")
    try:
        if db is None:
            raise ConnectionError("Connessione a MongoDB non disponibile.")

        positions_collection = db["positions_data"]
        # Recuperiamo anche hr_special_needs se esiste
        position_document = positions_collection.find_one(
            {"_id": position_id},
            {"job_description": 1, "hr_special_needs": 1}
        )
        
        if not position_document or "job_description" not in position_document:
            print(f"  - ERRORE: Documento o 'job_description' non trovata per la posizione {position_id}.")
            return False
            
        jd_text = position_document["job_description"]
        hr_needs = position_document.get("hr_special_needs", "")

    except Exception as e:
        print(f"  - ERRORE durante il recupero della Job Description: {e}")
        return False

    # 3. Esegui l'analisi unificata (ora `analyze_cv` restituisce un dizionario)
    analysis_result = analyze_cv(cv_text=cv_text, job_description_text=jd_text, hr_special_needs=hr_needs)
    
    # 4. Estrai i dati dal dizionario
    report_text = analysis_result.get("report_text")
    structured_experience = analysis_result.get("structured_experience")

    # 5. Salva entrambi i risultati
    if report_text and "Errore" not in report_text:
        save_stage_output(session_id, "cv_analysis_report", report_text)
        save_stage_output(session_id, "parsed_experience", structured_experience)
        save_stage_output(session_id, "cv_analysis_status", "Completed")
        print(f"  - Analisi CV unificata completata e salvata per la sessione {session_id}.")
        return True
    else:
        print(f"  - Analisi CV unificata fallita.")
        save_stage_output(session_id, "cv_analysis_status", "Failed")
        if report_text:
            save_stage_output(session_id, "cv_analysis_report", report_text)
        return False

# La parte __main__ può rimanere per il testing
if __name__ == "__main__":
    print("Questo script è progettato per essere importato e chiamato con un session_id.")