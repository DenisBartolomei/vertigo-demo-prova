# Tenant-aware CV analysis pipeline
from services.data_manager import db
from services.tenant_data_manager import get_session_data_tenant, save_stage_output_tenant, get_single_position_data_tenant
from .cv_analyzer import analyze_cv

def run_cv_analysis_pipeline_tenant(session_id: str, tenant_id: str) -> bool:
    """
    Esegue l'analisi del CV leggendo tutti i dati necessari (CV e JD) da MongoDB con tenant isolation.
    """
    print(f"--- [PIPELINE] Avvio Analisi CV per sessione: {session_id} (tenant: {tenant_id}) ---")
    
    # Get tenant collections
    from services.tenant_service import get_tenant_collections
    collections = get_tenant_collections(tenant_id)
    
    # 1. Recupera i dati della sessione da MongoDB
    session_data = get_session_data_tenant(session_id, collections["sessions"])
    if not session_data:
        print(f"  - ERRORE: Dati di sessione non trovati per {session_id}")
        return False
        
    stages = session_data.get("stages", {})
    cv_text = stages.get("uploaded_cv_text")
    position_id = session_data.get("position_id")
    
    if not cv_text or not position_id:
        print("  - ERRORE: CV o position_id mancanti nel documento di sessione DB.")
        return False
        
    # 2. Carica la Job Description da MongoDB (tenant-specific)
    print(f"  - Caricamento Job Description per '{position_id}' da MongoDB (tenant: {tenant_id})...")
    try:
        if db is None:
            raise ConnectionError("Connessione a MongoDB non disponibile.")

        position_document = get_single_position_data_tenant(position_id, collections["positions"])
        
        if not position_document or "job_description" not in position_document:
            print(f"  - ERRORE: Documento o campo 'job_description' non trovato per la posizione {position_id} nel DB.")
            return False
            
        jd_text = position_document["job_description"]

    except Exception as e:
        print(f"  - ERRORE durante il recupero della Job Description da MongoDB: {e}")
        return False

    # 3. Esegui l'analisi del CV
    analysis_report = analyze_cv(cv_text=cv_text, job_description_text=jd_text, hr_special_needs="")
    
    # 4. Salva il risultato nel documento di sessione (tenant-specific)
    if analysis_report and "Errore" not in analysis_report:
        save_stage_output_tenant(session_id, "cv_analysis_report", analysis_report, collections["sessions"])
        save_stage_output_tenant(session_id, "cv_analysis_status", "Completed", collections["sessions"])
        print(f"  - Analisi CV completata e salvata per la sessione {session_id}.")
        return True
    else:
        print(f"  - Analisi CV fallita durante la chiamata LLM.")
        save_stage_output_tenant(session_id, "cv_analysis_status", "Failed", collections["sessions"])
        return False



