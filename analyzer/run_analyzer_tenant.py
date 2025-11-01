# Tenant-aware CV analysis pipeline
from services.data_manager import db
from services.tenant_data_manager import get_session_data_tenant, save_stage_output_tenant, get_single_position_data_tenant
from .cv_analyzer import analyze_cv

def run_cv_analysis_pipeline_tenant(session_id: str, tenant_id: str) -> bool:
    """
    Esegue l'analisi unificata del CV e l'estrazione delle esperienze con tenant isolation.
    """
    print(f"--- [PIPELINE] Avvio Analisi CV Unificata per sessione: {session_id} (tenant: {tenant_id}) ---")
    
    from services.tenant_service import get_tenant_collections
    collections = get_tenant_collections(tenant_id)
    
    # 1. Recupera i dati della sessione
    session_data = get_session_data_tenant(session_id, collections["sessions"])
    if not session_data:
        print(f"  - ERRORE: Dati di sessione non trovati per {session_id}")
        return False
        
    stages = session_data.get("stages", {})
    cv_text = stages.get("uploaded_cv_text")
    position_id = session_data.get("position_id")
    
    if not cv_text or not position_id:
        print("  - ERRORE: CV o position_id mancanti nel documento di sessione.")
        return False
        
    # 2. Carica la Job Description (tenant-specific)
    print(f"  - Caricamento Job Description per '{position_id}'...")
    try:
        position_document = get_single_position_data_tenant(position_id, collections["positions"])
        
        if not position_document or "job_description" not in position_document:
            print(f"  - ERRORE: Documento o 'job_description' non trovata per la posizione {position_id}.")
            return False
            
        jd_text = position_document["job_description"]
        hr_needs = position_document.get("hr_special_needs", "")
        language = position_document.get("language", "it")  # Get language, default to Italian

    except Exception as e:
        print(f"  - ERRORE durante il recupero della Job Description: {e}")
        return False

    # 3. Esegui l'analisi unificata con lingua
    print(f"  - Esecuzione analisi CV in lingua: {language}")
    analysis_result = analyze_cv(cv_text=cv_text, job_description_text=jd_text, hr_special_needs=hr_needs, language=language)

    # 4. Estrai i dati dal dizionario
    report_text = analysis_result.get("report_text")
    structured_experience = analysis_result.get("structured_experience")
    
    # 5. Salva entrambi i risultati
    if report_text and "Errore" not in report_text:
        save_stage_output_tenant(session_id, "cv_analysis_report", report_text, collections["sessions"])
        save_stage_output_tenant(session_id, "parsed_experience", structured_experience, collections["sessions"])
        save_stage_output_tenant(session_id, "cv_analysis_status", "Completed", collections["sessions"])
        print(f"  - Analisi CV unificata completata e salvata per la sessione {session_id}.")
        return True
    else:
        print(f"  - Analisi CV unificata fallita.")
        save_stage_output_tenant(session_id, "cv_analysis_status", "Failed", collections["sessions"])
        if report_text:
            save_stage_output_tenant(session_id, "cv_analysis_report", report_text, collections["sessions"])
        return False



