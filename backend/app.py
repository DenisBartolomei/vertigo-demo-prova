from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List
import os
import uuid
import fitz  # PyMuPDF
from datetime import datetime
import asyncio
import json
import traceback
from bson import ObjectId

# SEMAFORO: Garantisce che solo 1 feedback venga generato alla volta (coda sequenziale)
FEEDBACK_GENERATION_LOCK = asyncio.Semaphore(1)

# Reuse existing services and pipelines
from services.data_manager import (
    create_or_update_position,
    get_available_positions_from_db,
    get_single_position_data_from_db,
    create_new_session,
    save_stage_output,
    get_session_data,
    save_pdf_report,
    db,
)
from data_preparation.analyzer.run_production_pipeline import run_full_generation_pipeline
from analyzer.run_analyzer import run_cv_analysis_pipeline
from analyzer.run_analyzer_tenant import run_cv_analysis_pipeline_tenant
from corrector.run_final_evaluation import execute_case_evaluation
from corrector.skill_relevance_scorer import compute_and_save_skill_relevance
from feedback_generator.run_feedback_generator import run_feedback_pipeline

from interviewer.chat_session_service import (
    initialize_chatbot_for_session,
    start_interview_for_session,
    send_message_for_session,
    get_interview_state,
)
from services.token_service import (
    issue_interview_token,
    resolve_token,
    resolve_token_global,
    mark_interview_started_global,
)
from services.auth_service import authenticate_hr, create_jwt, verify_jwt, get_or_create_tenant_for_email, refresh_jwt, is_token_expired
from services.user_service import (
    create_user, get_users_by_tenant, update_user_password, 
    deactivate_user, update_user_info, create_initial_admin_user
)
from services.tenant_service import get_tenant_collections, ensure_tenant_collections, get_tenant_by_id
from services.tenant_data_manager import (
    create_or_update_position_tenant,
    create_new_session_tenant,
    save_stage_output_tenant,
    get_session_data_tenant,
    get_available_positions_tenant,
    get_single_position_data_tenant,
    list_sessions_tenant,
    list_completed_sessions_tenant,
    list_incomplete_sessions_tenant,
    get_dashboard_data_tenant,
    SESSION_STATUS
)
from services.batch_service import BatchService
from services.email_parser import extract_email_from_text
from services.interview_config_service import (
    get_interview_config,
    save_interview_config,
    get_interview_config_or_default,
    InterviewConfig,
)
from services.email_service import send_interview_link

# Async imports for feedback generation
from feedback_generator.report_consolidator.consolidator import create_consolidated_report_async
from feedback_generator.gap_analyzer.gap_identifier import identify_skill_gaps_async
from feedback_generator.pathway_architect.architect import create_final_feedback_content_async
from feedback_generator.market_integration import run_market_benchmark_from_text_async
from feedback_generator.course_retriever.prompts_retriever import create_query_refinement_prompt
from feedback_generator.course_retriever.rag_service import RAGService
from recruitment_suite.app.core.pipeline import RecruitmentPipeline
from recruitment_suite.app.core.normalizer import CVNormalizer




def hr_auth(authorization: str | None = Header(default=None)):
    token_val = None
    if authorization and authorization.lower().startswith("bearer "):
        token_val = authorization.split(" ", 1)[1]
    if not token_val:
        raise HTTPException(status_code=401, detail="Missing token")
    
    # Check if token is expired
    if is_token_expired(token_val):
        raise HTTPException(status_code=401, detail="Token expired - please login again")
    
    data = verify_jwt(token_val)
    if not data or data.get("role") not in ["hr", "admin"]:
        raise HTTPException(status_code=401, detail="Invalid token")
    return data


def get_tenant_collections_from_auth(auth_data: dict):
    """Get tenant collections from auth data"""
    tenant_id = auth_data.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="No tenant ID in token")
    return get_tenant_collections(tenant_id)


class PositionPayload(BaseModel):
    position_id: str | None = None
    position_name: str
    job_description: str
    seniority_level: str | None = None
    hr_special_needs: str | None = None
    knowledge_base: list[dict] | None = None


class MessagePayload(BaseModel):
    text: str


class EvaluationCriterion(BaseModel):
    evaluation_criteria_1: str


class RequirementEvaluation(BaseModel):
    requirement: str
    criteria: EvaluationCriterion


class EvaluationCriteriaUpdate(BaseModel):
    evaluation_schema: list[RequirementEvaluation]


class StartInterviewPayload(BaseModel):
    name: str
    surname: str
    
    class Config:
        # Permetti campi extra per debugging
        extra = "allow"


app = FastAPI(title="Vertigo AI Backend", version="0.1.0")

# Global instances for heavy services (initialized once at startup)
rag_service_instance: RAGService | None = None
recruitment_pipeline_instance: RecruitmentPipeline | None = None
cv_normalizer_instance: CVNormalizer | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure per environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/sessions/{session_id}/generate-token")
def generate_token_for_session(session_id: str, auth_data=Depends(hr_auth)):
    """Generate interview token for a session that doesn't have one"""
    collections = get_tenant_collections_from_auth(auth_data)
    
    # Check if session exists and has completed CV analysis
    session_data = get_session_data_tenant(session_id, collections["sessions"])
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if CV analysis is completed
    stages = session_data.get("stages", {})
    cv_status = stages.get("cv_analysis_status")
    if cv_status != "Completed":
        raise HTTPException(status_code=400, detail="CV analysis not completed yet")
    
    # Check if token already exists
    if stages.get("interview_token"):
        raise HTTPException(status_code=400, detail="Token already exists for this session")
    
    # Generate new token
    token = issue_interview_token(session_id, collections["interview_links"])
    
    # Save token to session
    save_stage_output_tenant(session_id, "interview_token", token, collections["sessions"])
    
    return {"token": token, "message": "Token generated successfully"}


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug/db")
def debug_db():
    """Debug endpoint to check database connection"""
    import os
    from services.data_manager import db
    
    return {
        "mongodb_uri_set": bool(os.getenv("MONGODB_URI")),
        "mongodb_uri_length": len(os.getenv("MONGODB_URI", "")),
        "mongodb_uri_start": os.getenv("MONGODB_URI", "")[:20] + "..." if os.getenv("MONGODB_URI") else "None",
        "db_available": db is not None,
        "db_type": str(type(db)) if db else "None",
        "all_env_vars": {k: v for k, v in os.environ.items() if "MONGO" in k.upper()}
    }

# Auth (HR)
class LoginPayload(BaseModel):
    email: str
    password: str


class CreateUserPayload(BaseModel):
    email: str
    password: str
    name: str
    role: str = "hr"


class UpdateUserPayload(BaseModel):
    name: str = None
    role: str = None


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


class CreateTenantPayload(BaseModel):
    company_name: str
    admin_email: str
    admin_password: str
    admin_name: str


@app.post("/auth/login")
def login(payload: LoginPayload):
    user = authenticate_hr(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Get tenant_id from user data
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=500, detail="User has no associated tenant")
    
    ensure_tenant_collections(tenant_id)
    
    token = create_jwt(sub=payload.email, tenant_id=tenant_id, role=user.get("role", "hr"))
    return {
        "token": token, 
        "tenant_id": tenant_id,
        "user": {
            "id": user.get("_id"),
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role")
        },
        "expires_in": 3600  # 1 hour in seconds
    }


@app.post("/auth/refresh")
def refresh_token(request: Request, auth_data: dict = Depends(hr_auth)):
    """Refresh JWT token if it's close to expiration"""
    # Get the current token from the request
    authorization = request.headers.get("authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    current_token = authorization.split(" ", 1)[1]
    new_token = refresh_jwt(current_token)
    
    if new_token:
        return {
            "token": new_token,
            "expires_in": 3600,
            "refreshed": True
        }
    else:
        return {
            "token": current_token,
            "expires_in": 3600,
            "refreshed": False,
            "message": "Token doesn't need refresh yet"
        }


# Tenant Setup
@app.post("/auth/setup-tenant")
def setup_tenant(payload: CreateTenantPayload):
    """Create a new tenant with initial admin user"""
    from services.tenant_service import create_tenant
    
    try:
        # Create tenant (will return existing tenant_id if already exists)
        tenant_id = create_tenant(payload.admin_email, payload.company_name)
        ensure_tenant_collections(tenant_id)
        
        # Create initial admin user (will update existing user if already exists)
        user_id = create_user(
            email=payload.admin_email,
            password=payload.admin_password,
            tenant_id=tenant_id,
            role="admin",
            name=payload.admin_name
        )
        
        if not user_id:
            raise HTTPException(status_code=500, detail="Failed to create admin user")
        
        # Generate JWT token for immediate login
        token = create_jwt(sub=payload.admin_email, tenant_id=tenant_id, role="admin")
        
        return {
            "ok": True,
            "tenant_id": tenant_id,
            "token": token,
            "user": {
                "id": user_id,
                "email": payload.admin_email,
                "name": payload.admin_name,
                "role": "admin"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to setup tenant: {str(e)}")


# User Management
@app.get("/users")
def list_users(auth_data=Depends(hr_auth)):
    """List all users for the current tenant"""
    tenant_id = auth_data.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant information available")
    
    users = get_users_by_tenant(tenant_id)
    return {"users": users}


@app.post("/users")
def create_new_user(payload: CreateUserPayload, auth_data=Depends(hr_auth)):
    """Create a new user for the current tenant"""
    tenant_id = auth_data.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant information available")
    
    # Check if current user has admin role
    current_user_role = auth_data.get("role", "hr")
    if current_user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create users")
    
    user_id = create_user(
        email=payload.email,
        password=payload.password,
        tenant_id=tenant_id,
        role=payload.role,
        name=payload.name
    )
    
    if not user_id:
        raise HTTPException(status_code=400, detail="User already exists or creation failed")
    
    return {"ok": True, "user_id": user_id}


@app.put("/users/{user_id}")
def update_user(user_id: str, payload: UpdateUserPayload, auth_data=Depends(hr_auth)):
    """Update user information"""
    tenant_id = auth_data.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant information available")
    
    # Check if current user has admin role or is updating themselves
    current_user_email = auth_data.get("sub")
    current_user_role = auth_data.get("role", "hr")
    
    # Users can update their own info, admins can update anyone
    if current_user_role != "admin" and current_user_email != user_id:
        raise HTTPException(status_code=403, detail="You can only update your own information")
    
    success = update_user_info(user_id, payload.name, payload.role)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or update failed")
    
    return {"ok": True}


@app.post("/users/{user_id}/change-password")
def change_user_password(user_id: str, payload: ChangePasswordPayload, auth_data=Depends(hr_auth)):
    """Change user password"""
    tenant_id = auth_data.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant information available")
    
    # Check if current user has admin role or is changing their own password
    current_user_email = auth_data.get("sub")
    current_user_role = auth_data.get("role", "hr")
    
    if current_user_role != "admin" and current_user_email != user_id:
        raise HTTPException(status_code=403, detail="You can only change your own password")
    
    # For non-admin users, verify current password
    if current_user_role != "admin":
        from services.user_service import authenticate_user
        user = authenticate_user(current_user_email, payload.current_password)
        if not user:
            raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    success = update_user_password(user_id, payload.new_password)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or password update failed")
    
    return {"ok": True}


@app.delete("/users/{user_id}")
def deactivate_user_endpoint(user_id: str, auth_data=Depends(hr_auth)):
    """Deactivate a user (soft delete)"""
    tenant_id = auth_data.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant information available")
    
    # Only admins can deactivate users
    current_user_role = auth_data.get("role", "hr")
    if current_user_role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can deactivate users")
    
    # Prevent deactivating yourself
    current_user_email = auth_data.get("sub")
    if current_user_email == user_id:
        raise HTTPException(status_code=400, detail="You cannot deactivate yourself")
    
    success = deactivate_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or deactivation failed")
    
    return {"ok": True}


# Positions
@app.post("/positions")
def upsert_position(payload: PositionPayload, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    
    # Generate position_id if not provided
    position_id = payload.position_id
    if not position_id or position_id.strip() == "":
        # Generate a position_id from position_name
        import re
        position_id = re.sub(r'[^a-zA-Z0-9\-_]', '-', payload.position_name.lower())
        position_id = re.sub(r'-+', '-', position_id).strip('-')
        if not position_id:
            position_id = f"position-{uuid.uuid4().hex[:8]}"
    
    # Detect language from job description
    from services.language_detector import detect_language
    detected_language = detect_language(payload.job_description)
    
    # Add language to payload
    position_data = payload.model_dump(exclude={"position_id"})
    position_data["language"] = detected_language
    
    ok = create_or_update_position_tenant(position_id, position_data, collections["positions"])
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to upsert position")
    return {"ok": True, "position_id": position_id, "language": detected_language}


@app.get("/positions")
def list_positions(auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    return {"positions": get_available_positions_tenant(collections["positions"])}


@app.get("/positions/{position_id}")
def get_position(position_id: str, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    doc = get_single_position_data_tenant(position_id, collections["positions"])
    if not doc:
        raise HTTPException(status_code=404, detail="Position not found")
    return doc


@app.post("/positions/{position_id}/data-prep")
def run_data_prep(position_id: str, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    
    # Recupera configurazione intervista per il tenant
    tenant_id = auth_data.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="No tenant ID in token")
    
    config = get_interview_config_or_default(tenant_id)
    
    # Passa esplicitamente tenant_id invece di estrarre dalla collection
    ok = run_full_generation_pipeline(position_id, config.reasoning_steps, collections["positions"], tenant_id=tenant_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Data preparation failed")
    return {"ok": True}


@app.delete("/positions/{position_id}")
def delete_position(position_id: str, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    try:
        collection = db[collections["positions"]]
        result = collection.delete_one({"_id": position_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Position not found")
        return {"ok": True, "message": "Position deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete position: {str(e)}")


@app.put("/positions/{position_id}/evaluation-criteria")
def update_evaluation_criteria(position_id: str, payload: EvaluationCriteriaUpdate, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    
    try:
        collection = db[collections["positions"]]
        
        # Verifica che la posizione esista
        position = collection.find_one({"_id": position_id})
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Converti il payload in un dizionario per MongoDB
        evaluation_criteria = {
            "evaluation_schema": [
                {
                    "requirement": req.requirement,
                    "criteria": {
                        "evaluation_criteria_1": req.criteria.evaluation_criteria_1
                    }
                }
                for req in payload.evaluation_schema
            ]
        }
        
        # Aggiorna il documento
        result = collection.update_one(
            {"_id": position_id},
            {"$set": {"evaluation_criteria": evaluation_criteria}}
        )
        
        if result.modified_count == 0 and result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Position not found")
        
        return {"ok": True, "message": "Evaluation criteria updated successfully", "evaluation_criteria": evaluation_criteria}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update evaluation criteria: {str(e)}")


@app.put("/sessions/{session_id}/token-sent")
def mark_token_sent(session_id: str, auth_data=Depends(hr_auth)):
    """Mark that the interview token has been sent to the candidate"""
    collections = get_tenant_collections_from_auth(auth_data)
    try:
        collection = db[collections["sessions"]]
        result = collection.update_one(
            {"_id": session_id},
            {"$set": {
                "token_sent": True, 
                "token_sent_by": auth_data.get("sub"), 
                "token_sent_at": datetime.utcnow(),
                "is_new_batch": False  # Rimuove badge NEW quando token inviato
            }}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"ok": True, "message": "Token sent status updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update token sent status: {str(e)}")


# Tenant-aware feedback pipeline function
def run_feedback_pipeline_tenant(session_id: str, collection_name: str) -> str | None:
    """Tenant-aware version of the feedback generation pipeline"""
    import os
    import json
    from bson import ObjectId
    
    class ObjectIdEncoder(json.JSONEncoder):
        """Custom JSON encoder to handle ObjectId serialization"""
        def default(self, obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            return super().default(obj)
    
    print(f"--- [PIPELINE] Avvio Generazione Feedback per sessione: {session_id} (tenant-aware) ---")
    
    # Get session data using tenant-aware function
    session_data = get_session_data_tenant(session_id, collection_name)
    if not session_data:
        print(f"Errore: Dati di sessione non trovati per l'ID: {session_id}")
        return None
    
    candidate_name = session_data.get("candidate_name", "Candidato")
    target_role = session_data.get("position_id", "Ruolo non specificato")
    stages_data = session_data.get("stages", {})
    
    # Import feedback generator modules
    from feedback_generator.report_consolidator.consolidator import create_consolidated_report
    from feedback_generator.gap_analyzer.gap_identifier import identify_skill_gaps
    from feedback_generator.course_retriever.prompts_retriever import create_query_refinement_prompt
    from feedback_generator.pathway_architect.architect import create_final_feedback_content
    from feedback_generator.pathway_architect.pdf_service import create_feedback_pdf
    from feedback_generator.market_integration import run_market_benchmark_from_text
    from interviewer.llm_service import get_llm_response
    
    # STEP 1: Consolidamento
    consolidated_report = stages_data.get("consolidated_report")
    original_cv_report = stages_data.get("cv_analysis_report")
    case_eval_report = stages_data.get("case_evaluation_report")
    
    if not consolidated_report:
        print("\n[STEP 1/5] Generazione report consolidato...")
        if not original_cv_report or not case_eval_report:
            print("Errore: Report di analisi CV o valutazione del caso mancanti.")
            return None
        consolidated_report = create_consolidated_report(original_cv_report, case_eval_report)
        if not consolidated_report: 
            return None
        save_stage_output_tenant(session_id, "consolidated_report", consolidated_report, collection_name)
    else:
        print("\n[STEP 1/5] Report consolidato già presente.")

    # STEP 2: Identificazione Gap
    print("\n[STEP 2/5] Identificazione gap...")
    gap_analysis = identify_skill_gaps(consolidated_report)
    if not gap_analysis: 
        return None
    save_stage_output_tenant(session_id, "gap_analysis", gap_analysis.model_dump(), collection_name)

    # STEP 3: Recupero Corsi
    print("\n[STEP 3/5] Recupero corsi...")
    from feedback_generator.course_retriever.rag_service import get_rag_service
    rag_service = get_rag_service()
    
    enriched_skill_families = []
    for family in gap_analysis.skill_families:
        # Extract skill gaps as list of strings
        skill_gaps = [gap.skill_gap for gap in family.skill_gaps]
        refined_query = create_query_refinement_prompt(family.skill_family_gap, skill_gaps)
        courses = rag_service.search(refined_query, k=3)
        
        enriched_family = {
            "skill_family_gap": family.skill_family_gap,
            "skill_gaps": [gap.model_dump() for gap in family.skill_gaps],
            "suggested_courses": courses
        }
        enriched_skill_families.append(enriched_family)
    
    enriched_gaps_content_str = json.dumps(enriched_skill_families, ensure_ascii=False, indent=2, cls=ObjectIdEncoder)
    save_stage_output_tenant(session_id, "enriched_gaps", enriched_gaps_content_str, collection_name)

    # STEP 4: Market Benchmark (optional)
    print("\n[STEP 4/5] Benchmark di mercato...")
    qualitative_text = None
    chart_cat_b64 = None
    market_skills_list = None
    
    try:
        # Get position data for market benchmark
        position_data = get_single_position_data_tenant(target_role, collection_name.replace("_sessions", "_positions_data"))
        jd_text = position_data.get("job_description", "") if position_data else ""
        
        # Get CV text from session data
        cv_text_for_market = original_cv_report or ""
        role_title = position_data.get("position_name", target_role) if position_data else target_role
        language = (position_data or {}).get("language", "it")
        if language not in ("it", "en"):
            language = "it"
        
        if jd_text and cv_text_for_market:
            # Estrai tenant_id dal nome della collection (formato: {tenant_id}_sessions)
            tenant_id = None
            if collection_name.endswith("_sessions"):
                tenant_id = collection_name.replace("_sessions", "")
            
            qualitative_text, chart_cat_b64, market_skills_list = run_market_benchmark_from_text(
                job_description_text=jd_text,
                parsed_experiences=cv_text_for_market,  # Passa come parsed_experiences
                offer_title=role_title,
                position_id=target_role,  # Passa position_id per usare cache pre-calcolata
                tenant_id=tenant_id,  # Passa tenant_id per multi-tenant
                job_language=language
            )
            if qualitative_text:
                save_stage_output_tenant(session_id, "market_benchmark_text", qualitative_text, collection_name)
            if chart_cat_b64:
                save_stage_output_tenant(session_id, "market_chart_categories_base64", chart_cat_b64, collection_name)
            if market_skills_list:
                save_stage_output_tenant(session_id, "market_chart_skills_base64", market_skills_list, collection_name)
        else:
            print("Avviso: JD o testo CV non disponibili; benchmark di mercato saltato.")
    except Exception as e:
        print(f"Avviso: impossibile recuperare la JD o il titolo dal DB per il benchmark: {e}")

    # STEP 5: Creazione Contenuto Report
    print("\n[STEP 5/5] Creazione contenuto report PDF...")
    final_report_content = create_final_feedback_content(
        cv_analysis_report=original_cv_report,
        case_evaluation_report=case_eval_report,
        enriched_gaps_json_str=enriched_gaps_content_str,
        candidate_name=candidate_name,
        target_role=target_role
    )
    if not final_report_content: 
        return None

    # Override market benchmark if we have real text
    if qualitative_text:
        try:
            final_report_content.market_benchmark = qualitative_text
        except Exception:
            pass
    
    # STEP 6: Generazione PDF
    print("\n[STEP 6/6] Generazione del file PDF...")
    temp_dir = "temp_pdf"
    os.makedirs(temp_dir, exist_ok=True)
    temp_pdf_path = os.path.join(temp_dir, f"{session_id}.pdf")
    
    create_feedback_pdf(
        report_content=final_report_content,
        output_path=temp_pdf_path,
        language=language,
        market_benchmark_text=qualitative_text,
        market_chart_categories_base64=chart_cat_b64,
        market_skills_list=market_skills_list 
    )
    
    pdf_path = ""
    if os.path.exists(temp_pdf_path):
        with open(temp_pdf_path, "rb") as f:
            pdf_bytes = f.read()
        # Save PDF using tenant-aware function
        pdf_path = save_pdf_report_tenant(pdf_bytes, session_id, collection_name)
        os.remove(temp_pdf_path)
        
    print("--- [PIPELINE] Generazione Feedback completata (tenant-aware). ---")
    return pdf_path

def save_pdf_report_tenant(pdf_bytes: bytes, session_id: str, collection_name: str) -> str:
    """Tenant-aware version of save_pdf_report"""
    import os
    from services.data_manager import db
    
    if db is None:
        return ""
    
    try:
        output_dir = os.path.join("data", "sessions", session_id)
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, "feedback_report.pdf")
        
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"💾 PDF salvato in: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"Errore durante il salvataggio del PDF: {e}")
        return ""


# Async Optimized Feedback Pipeline
class ObjectIdEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle ObjectId serialization"""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)


async def run_feedback_pipeline_tenant_async(session_id: str, collection_name: str) -> str | None:
    """
    Versione ASINCRONA e OTTIMIZZATA del pipeline di feedback.
    Esegue in parallelo l'analisi dei gap e il benchmark di mercato.
    """
    #from feedback_generator.report_consolidator.consolidator import create_consolidated_report
    #from feedback_generator.gap_analyzer.gap_identifier import identify_skill_gaps
    from feedback_generator.course_retriever.prompts_retriever import create_query_refinement_prompt
    #from feedback_generator.pathway_architect.architect import create_final_feedback_content
    from feedback_generator.pathway_architect.pdf_service import create_feedback_pdf
    #from feedback_generator.market_integration import run_market_benchmark_from_text
    #from interviewer.llm_service import get_llm_response
    print(f"--- [PIPELINE ASYNC] Avvio Generazione Feedback per sessione: {session_id} ---")
    
    try:
        session_data = get_session_data_tenant(session_id, collection_name)
        if not session_data:
            print(f"Errore: Dati di sessione non trovati per l'ID: {session_id}")
            raise ValueError("Session data not found")
        
        candidate_name = session_data.get("candidate_name", "Candidato")
        target_role_id = session_data.get("position_id", "Ruolo non specificato")
        stages_data = session_data.get("stages", {})
        original_cv_report = stages_data.get("cv_analysis_report")
        case_eval_report = stages_data.get("case_evaluation_report")

        positions_collection_name = collection_name.replace("_sessions", "_positions_data")
        position_data = get_single_position_data_tenant(target_role_id, positions_collection_name) if target_role_id else None
        language = (position_data or {}).get("language", "it")
        if language not in ("it", "en"):
            print(f"ATTENZIONE: Lingua posizione non supportata '{language}', defaulto a 'it'")
            language = "it"

        role_title = (position_data or {}).get("position_name", target_role_id)
        jd_text = (position_data or {}).get("job_description", "")

        # STEP 1: Consolidamento (rimane sequenziale)
        consolidated_report = stages_data.get("consolidated_report")
        if not consolidated_report:
            print("\n[STEP 1/6] Generazione report consolidato...")
            if not original_cv_report or not case_eval_report:
                raise ValueError("Report di analisi CV o valutazione del caso mancanti.")
            consolidated_report = await create_consolidated_report_async(
                original_cv_report,
                case_eval_report,
                language=language
            )
            if not consolidated_report: 
                raise ValueError("Fallimento nella generazione del report consolidato.")
            save_stage_output_tenant(session_id, "consolidated_report", consolidated_report, collection_name)
        else:
            print("\n[STEP 1/6] Report consolidato già presente.")
    
        # --- INIZIO PARALLELIZZAZIONE PESANTE ---
        print("\n[STEP 2 & 4] Avvio in parallelo di Gap Analysis e Market Benchmark...")
        gap_task = asyncio.create_task(
            identify_skill_gaps_async(consolidated_report, language=language)
        )
        parsed_experiences = stages_data.get("parsed_experience", [])
        if not parsed_experiences:
            print("ATTENZIONE: Esperienze parsate non trovate. Il benchmark di mercato potrebbe essere incompleto.")
            # Continuiamo comunque, ma il report qualitativo non avrà i dati del candidato
        
        # Estrai tenant_id dal nome della collection (formato: {tenant_id}_sessions)
        tenant_id = None
        if collection_name.endswith("_sessions"):
            tenant_id = collection_name.replace("_sessions", "")
        
        market_task = asyncio.create_task(
            run_market_benchmark_from_text_async(
                job_description_text=jd_text,
                parsed_experiences=parsed_experiences,
                offer_title=role_title,
                db=db,
                position_id=target_role_id,  # Passa position_id per usare cache pre-calcolata
                tenant_id=tenant_id,  # Passa tenant_id per multi-tenant
                job_language=language
            )
        )

        results = await asyncio.gather(gap_task, market_task, return_exceptions=True)
        
        gap_analysis = results[0]
        if isinstance(gap_analysis, Exception) or not gap_analysis:
            raise ValueError(f"Errore critico durante l'analisi dei gap: {gap_analysis}")
        save_stage_output_tenant(session_id, "gap_analysis", gap_analysis.model_dump(), collection_name)
        print("[STEP 2/6] Analisi gap completata.")

        market_results = results[1]
        qualitative_text, chart_cat_b64, market_skills_list = None, None, None
        if isinstance(market_results, Exception):
            print(f"Avviso: Benchmark di mercato fallito: {market_results}")
        elif market_results:
            qualitative_text, chart_cat_b64, market_skills_list = market_results
            if qualitative_text: save_stage_output_tenant(session_id, "market_benchmark_text", qualitative_text, collection_name)
            if chart_cat_b64: save_stage_output_tenant(session_id, "market_chart_categories_base64", chart_cat_b64, collection_name)
            if market_skills_list: save_stage_output_tenant(session_id, "market_chart_skills_base64", market_skills_list, collection_name)
        print("[STEP 4/6] Benchmark di mercato completato.")

        # STEP 3: Recupero Corsi (parallelizzato al suo interno)
        print("\n[STEP 3/6] Recupero corsi in parallelo...")
        rag_service = rag_service_instance 

        if not rag_service:
            raise RuntimeError("Errore Critico: RAG Service non è stato inizializzato.")

        async def get_courses_for_family(family):
            skill_gaps = [gap.skill_gap for gap in family.skill_gaps]
            refined_query = create_query_refinement_prompt(
                family.skill_family_gap,
                skill_gaps,
                language=language
            )
            courses = await rag_service.search_async(refined_query, k=3) 
            return {
                "skill_family_gap": family.skill_family_gap,
                "skill_gaps": [gap.model_dump() for gap in family.skill_gaps],
                "suggested_courses": courses
            }
        
        course_tasks = [get_courses_for_family(family) for family in gap_analysis.skill_families]
        enriched_skill_families = await asyncio.gather(*course_tasks)

        enriched_gaps_content_str = json.dumps(enriched_skill_families, ensure_ascii=False, indent=2, cls=ObjectIdEncoder)
        save_stage_output_tenant(session_id, "enriched_gaps", enriched_gaps_content_str, collection_name)
        print("[STEP 3/6] Recupero corsi completato.")

        # STEP 5: Creazione Contenuto Report
        print("\n[STEP 5/6] Creazione contenuto report PDF...")
        final_report_content = await create_final_feedback_content_async(
            cv_analysis_report=original_cv_report,
            case_evaluation_report=case_eval_report,
            enriched_gaps_json_str=enriched_gaps_content_str,
            candidate_name=candidate_name,
            target_role=role_title,
            language=language
        )
        if not final_report_content: 
            raise ValueError("Fallimento nella creazione del contenuto del report finale.")
        if qualitative_text:
            final_report_content.market_benchmark = qualitative_text

        # STEP 6: Generazione PDF
        print("\n[STEP 6/6] Generazione del file PDF...")
        temp_dir = "temp_pdf"
        os.makedirs(temp_dir, exist_ok=True)
        temp_pdf_path = os.path.join(temp_dir, f"{session_id}.pdf")
        
        create_feedback_pdf(
            report_content=final_report_content,
            output_path=temp_pdf_path,
            language=language,
            market_benchmark_text=qualitative_text,
            market_chart_categories_base64=chart_cat_b64,
            market_skills_list=market_skills_list 
        )
        
        pdf_path = ""
        if os.path.exists(temp_pdf_path):
            with open(temp_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            pdf_path = save_pdf_report_tenant(pdf_bytes, session_id, collection_name)
            os.remove(temp_pdf_path)
            
        print(f"--- [PIPELINE ASYNC] Generazione Feedback completata per {session_id}. PDF Path: {pdf_path} ---")
        return pdf_path

    except Exception as e:
        print(f"🔥🔥🔥 ERRORE NEL PIPELINE ASINCRONO per sessione {session_id}: {e}")
        traceback.print_exc()
        raise


async def run_and_update_feedback_status(session_id: str, collection_name: str):
    """
    Funzione wrapper per eseguire il pipeline in background e aggiornare lo stato 
    della sessione in modo sicuro (successo o fallimento).
    
    Utilizza un semaforo per garantire che solo un feedback venga generato alla volta,
    creando una coda sequenziale automatica per tutte le richieste.
    """
    # Acquisisce il lock: se occupato, aspetta che il feedback precedente finisca
    async with FEEDBACK_GENERATION_LOCK:
        print(f"🔒 [LOCK ACQUIRED] Inizio generazione feedback per sessione {session_id}")
        
        try:
            pdf_path = await run_feedback_pipeline_tenant_async(session_id, collection_name)
                
            if pdf_path:
                save_stage_output_tenant(session_id, "feedback_pdf_path", pdf_path, collection_name)
                save_stage_output_tenant(session_id, "status", SESSION_STATUS["FEEDBACK_READY"], collection_name)
                print(f"✅ Feedback PDF generato con successo per sessione {session_id}")
            else:
                raise ValueError("Il pipeline non ha prodotto un percorso PDF valido.")
        except Exception as e:
            print(f"❌ [ERRORE] Generazione feedback fallita per sessione {session_id}: {e}")
            traceback.print_exc()
            save_stage_output_tenant(session_id, "status", SESSION_STATUS["FEEDBACK_GENERATION_FAILED"], collection_name)
            save_stage_output_tenant(session_id, "feedback_error", str(e), collection_name)
        finally:
            print(f"🔓 [LOCK RELEASED] Fine generazione feedback per sessione {session_id}")

# Sessions (HR)
@app.post("/sessions")
async def create_session(position_id: str = Form(...), cv_file: UploadFile = File(...), candidate_email: str = Form(None), frontend_base_url: str = Form("") , auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    session_id = str(uuid.uuid4())
    created = create_new_session_tenant(session_id, position_id, None, collections["sessions"], candidate_email)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create session")

    # Extract CV text
    content = await cv_file.read()
    cv_text = ""
    if cv_file.content_type == "application/pdf" or cv_file.filename.endswith(".pdf"):
        try:
            with fitz.open(stream=content, filetype="pdf") as doc:
                cv_text = "".join(page.get_text() for page in doc)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid PDF: {e}")
    else:
        try:
            cv_text = content.decode("utf-8")
        except Exception:
            raise HTTPException(status_code=400, detail="Unsupported CV format; provide PDF or UTF-8 text")

    save_stage_output_tenant(session_id, "uploaded_cv_text", cv_text, collections["sessions"])

    # Issue interview token/link (not yet initialized chatbot)
    token = issue_interview_token(session_id, collections["interview_links"])
    
    # Save the interview token to the session document for easy access
    save_stage_output_tenant(session_id, "interview_token", token, collections["sessions"])
    
    # Optionally send invite email
    if candidate_email and frontend_base_url:
        send_interview_link(candidate_email, token, frontend_base_url)
    return {"session_id": session_id, "interview_token": token}


@app.post("/sessions/{session_id}/prepare")
def prepare_session(session_id: str, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    tenant_id = auth_data.get("tenant_id")
    
    # CV analysis (tenant-aware)
    ok = run_cv_analysis_pipeline_tenant(session_id, tenant_id)
    if not ok:
        raise HTTPException(status_code=500, detail="CV analysis failed")

    # Initialize chatbot with random case and persist chatbot state
    meta = initialize_chatbot_for_session(session_id, tenant_id)
    if not meta:
        raise HTTPException(status_code=500, detail="Chatbot initialization failed")
    return meta


@app.get("/sessions/completed")
def list_completed_sessions(auth_data=Depends(hr_auth)):
    """List completed sessions for Reportistica Candidati page"""
    collections = get_tenant_collections_from_auth(auth_data)
    results = list_completed_sessions_tenant(collections["sessions"])
    return {"items": results}


@app.post("/sessions/{session_id}/generate-feedback")
async def generate_feedback(session_id: str, background_tasks: BackgroundTasks, auth_data=Depends(hr_auth)):
    """
    Avvia la generazione del feedback report in background e restituisce una risposta immediata.
    """
    collections = get_tenant_collections_from_auth(auth_data)
    collection_name = collections["sessions"]
    
    # 1. Verifica che la sessione esista e non sia già in elaborazione
    session_data = get_session_data_tenant(session_id, collection_name)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    stages = session_data.get("stages", {})
    
    # Check if session is ready for feedback generation
    if not (stages.get("cv_analysis_report") and stages.get("case_evaluation_report") and stages.get("skill_relevance")):
        raise HTTPException(status_code=400, detail="Session not ready for feedback generation")
    
    # Check if feedback is already generated
    if stages.get("feedback_pdf_path"):
        return {"ok": True, "message": "Feedback already generated", "pdf_path": stages.get("feedback_pdf_path")}
    
    # Check if already in progress (previene duplicati per la stessa sessione)
    current_status = stages.get("status")
    if current_status == SESSION_STATUS["FEEDBACK_GENERATION_IN_PROGRESS"]:
        raise HTTPException(
            status_code=409, 
            detail="Feedback generation is already in progress for this session. Please wait for it to complete."
        )

    # 2. Imposta lo stato su "in corso" per dare un feedback immediato all'UI
    save_stage_output_tenant(session_id, "status", SESSION_STATUS["FEEDBACK_GENERATION_IN_PROGRESS"], collection_name)
    
    # 3. Aggiungi il compito pesante al background
    background_tasks.add_task(run_and_update_feedback_status, session_id, collection_name)
    
    # 4. Restituisci una risposta immediata
    return {
        "ok": True, 
        "message": "Feedback generation started. The process will run in the background.",
        "status": SESSION_STATUS["FEEDBACK_GENERATION_IN_PROGRESS"]
    }


@app.get("/sessions/{session_id}/feedback-pdf")
def download_feedback_pdf(session_id: str, auth_data=Depends(hr_auth)):
    """Download the feedback PDF for a completed session"""
    collections = get_tenant_collections_from_auth(auth_data)
    
    session_data = get_session_data_tenant(session_id, collections["sessions"])
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    stages = session_data.get("stages", {})
    pdf_path = stages.get("feedback_pdf_path")
    
    if not pdf_path:
        raise HTTPException(status_code=404, detail="Feedback PDF not found for this session")
        
    normalized_path = pdf_path.replace("\\", "/")
    
    try:
        import os
        if not os.path.exists(normalized_path):
            print(f"🔥🔥🔥 PDF NOT FOUND AT PATH: {normalized_path}. Current working directory: {os.getcwd()}")
            raise HTTPException(status_code=404, detail=f"PDF file not found on disk.")
        
        with open(normalized_path, "rb") as pdf_file:
            pdf_content = pdf_file.read()
        
        download_info = {
            "downloaded_at": datetime.utcnow().isoformat(),
            "downloaded_by": auth_data.get("sub"),
            "downloaded_by_name": auth_data.get("name", auth_data.get("sub", "Unknown"))
        }
        
        save_stage_output_tenant(session_id, "feedback_download", download_info, collections["sessions"])
        
        candidate_name = session_data.get("candidate_name", "Candidate")
        position_id = session_data.get("position_id", "Position")
        filename = f"Report_Feedback_{candidate_name}_{position_id}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
    except Exception as e:
        print(f"Error downloading feedback PDF for session {session_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error while reading the PDF file.")


@app.get("/sessions/{session_id}")
def session_status(session_id: str, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    data = get_session_data_tenant(session_id, collections["sessions"])
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@app.get("/sessions/{session_id}/conversation")
def get_session_conversation(session_id: str, auth_data=Depends(hr_auth)):
    """Get the full conversation for a session"""
    collections = get_tenant_collections_from_auth(auth_data)
    
    # Check if session exists
    session_data = get_session_data_tenant(session_id, collections["sessions"])
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    stages = session_data.get("stages", {})
    conversation = stages.get("conversation", [])
    
    return {
        "session_id": session_id,
        "candidate_name": session_data.get("candidate_name"),
        "conversation": conversation
    }


@app.get("/sessions")
def list_sessions(auth_data=Depends(hr_auth)):
    """List incomplete sessions for Nuova Sessione dashboard with batch grouping"""
    collections = get_tenant_collections_from_auth(auth_data)
    results = list_incomplete_sessions_tenant(collections["sessions"])
    
    # Raggruppa sessioni per batch_date
    batch_groups = {}
    ungrouped_sessions = []
    
    for session in results:
        batch_date = session.get("batch_date")
        if batch_date:
            if batch_date not in batch_groups:
                batch_groups[batch_date] = {
                    "batch_date": batch_date,
                    "batch_id": session.get("batch_id", ""),
                    "sessions": [],
                    "total_count": 0,
                    "new_count": 0
                }
            
            batch_groups[batch_date]["sessions"].append(session)
            batch_groups[batch_date]["total_count"] += 1
            
            if session.get("is_new_batch", False):
                batch_groups[batch_date]["new_count"] += 1
        else:
            # Sessioni non batch (upload singolo)
            ungrouped_sessions.append(session)
    
    # Converti in lista ordinata per data (più recente prima)
    batch_groups_list = []
    for batch_date in sorted(batch_groups.keys(), reverse=True):
        batch_groups_list.append(batch_groups[batch_date])
    
    return {
        "items": results,  # Mantieni compatibilità con frontend esistente
        "batch_groups": batch_groups_list,
        "ungrouped_sessions": ungrouped_sessions,
        "total_batches": len(batch_groups_list)
    }


@app.get("/user/info")
def get_user_info(auth_data=Depends(hr_auth)):
    """Get current user information"""
    tenant_id = auth_data.get("tenant_id")
    email = auth_data.get("sub")
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant information available")
    
    tenant_info = get_tenant_by_id(tenant_id)
    if not tenant_info:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Get user information from user service
    from services.user_service import get_user_by_email
    user_info = get_user_by_email(email)
    
    return {
        "email": email,
        "company": tenant_info.get("company_name", "Unknown Company"),
        "tenant_id": tenant_id,
        "role": user_info.get("role", "hr") if user_info else "hr",
        "name": user_info.get("name", email.split('@')[0]) if user_info else email.split('@')[0],
        "id": user_info.get("_id") if user_info else None
    }


@app.get("/dashboard/data")
def get_dashboard_data(
    timeRange: str = "30d",
    positionFilter: str = "all",
    auth_data=Depends(hr_auth)
):
    """Get comprehensive dashboard data for HR analytics with real recruitment indicators"""
    tenant_id = auth_data.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    
    # Validate time range
    valid_ranges = ["7d", "30d", "90d", "1y"]
    if timeRange not in valid_ranges:
        timeRange = "30d"
    
    # Validate position filter
    if positionFilter not in ["all"] and not positionFilter:
        positionFilter = "all"
    
    dashboard_data = get_dashboard_data_tenant(tenant_id, timeRange, positionFilter)
    
    if not dashboard_data:
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")
    
    return dashboard_data


# Interview Configuration APIs
@app.get("/interview-config")
def get_interview_configuration(auth_data=Depends(hr_auth)):
    """Get interview configuration for the authenticated tenant"""
    tenant_id = auth_data["tenant_id"]
    config = get_interview_config_or_default(tenant_id)
    return {
        "reasoning_steps": config.reasoning_steps,
        "max_attempts": config.max_attempts,
        "estimated_duration_minutes": config.estimated_duration_minutes,
        "max_questions": config.max_questions
    }

@app.put("/interview-config")
def update_interview_configuration(
    config_data: dict,
    auth_data=Depends(hr_auth)
):
    """Update interview configuration for the authenticated tenant"""
    tenant_id = auth_data["tenant_id"]
    
    # Validate input
    reasoning_steps = config_data.get("reasoning_steps")
    max_attempts = config_data.get("max_attempts")
    
    if reasoning_steps is None or max_attempts is None:
        raise HTTPException(status_code=400, detail="reasoning_steps and max_attempts are required")
    
    if not isinstance(reasoning_steps, int) or not isinstance(max_attempts, int):
        raise HTTPException(status_code=400, detail="reasoning_steps and max_attempts must be integers")
    
    if reasoning_steps < 2 or reasoning_steps > 6:
        raise HTTPException(status_code=400, detail="reasoning_steps must be between 2 and 6")
    
    if max_attempts < 2 or max_attempts > 5:
        raise HTTPException(status_code=400, detail="max_attempts must be between 2 and 5")
    
    # Create new config
    config = InterviewConfig(
        tenant_id=tenant_id,
        reasoning_steps=reasoning_steps,
        max_attempts=max_attempts
    )
    
    # Save config
    success = save_interview_config(config)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save configuration")
    
    return {
        "reasoning_steps": config.reasoning_steps,
        "max_attempts": config.max_attempts,
        "estimated_duration_minutes": config.estimated_duration_minutes,
        "max_questions": config.max_questions,
        "message": "Configuration updated successfully"
    }


# Candidate interview (public via token)
@app.get("/interviews/{token}")
def resolve_interview(token: str):
    result = resolve_token_global(token)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    session_id, tenant_id = result
    
    collections = get_tenant_collections(tenant_id)
    sess = get_session_data_tenant(session_id, collections["sessions"]) or {}
    
    # Check if evaluation is completed (has skill_relevance)
    stages = sess.get("stages", {})
    skill_relevance = stages.get("skill_relevance")
    if skill_relevance:
        raise HTTPException(status_code=410, detail="Interview completed and evaluation finished. Access no longer available.")
    
    pos_id = sess.get("position_id")
    pos = get_single_position_data_tenant(pos_id, collections["positions"]) if pos_id else {}
    return {
        "session_id": session_id,
        "position_name": (pos or {}).get("position_name"),
        "case_id": (sess.get("stages", {}) or {}).get("case_id"),
    }


@app.post("/interviews/{token}/save-name")
def save_candidate_name(token: str, payload: StartInterviewPayload):
    """Salva solo nome e cognome del candidato, NON avvia l'intervista"""
    try:
        print(f"Salvataggio nome candidato con token: {token}")
        print(f"Payload ricevuto: name='{payload.name}', surname='{payload.surname}'")
    
        # Validate required fields
        if not payload.name or not payload.name.strip():
            raise HTTPException(status_code=422, detail="Name is required and cannot be empty")
        if not payload.surname or not payload.surname.strip():
            raise HTTPException(status_code=422, detail="Surname is required and cannot be empty")
        
        result = resolve_token_global(token)
        if not result:
            raise HTTPException(status_code=404, detail="Invalid or expired link")
        
        session_id, tenant_id = result
        print(f"✅ Token risolto: session_id={session_id}, tenant_id={tenant_id}")
        
        # Check if evaluation is completed
        collections = get_tenant_collections(tenant_id)
        sess = get_session_data_tenant(session_id, collections["sessions"]) or {}
        stages = sess.get("stages", {})
        skill_relevance = stages.get("skill_relevance")
        if skill_relevance:
            raise HTTPException(status_code=410, detail="Interview completed and evaluation finished. Access no longer available.")
        
        # Salva solo nome e cognome - NON avvia intervista
        full_name = f"{payload.name} {payload.surname}".strip()
        
        if db is not None:
            sessions_collection = db[f"{tenant_id}_sessions"]
            sessions_collection.update_one(
                {"_id": session_id},
                {"$set": {
                    "candidate_name": full_name  # Campo root
                },
                "$unset": {
                    "candidate_surname": "",  # Rimuovi campo duplicato
                    "stages.candidate_surname": ""
                }}
            )
        
        print(f"✅ Nome candidato salvato: {full_name}")
        return {"message": "Candidate name saved successfully", "candidate_name": full_name}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Errore salvataggio nome: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/interviews/{token}/start")
def start_interview(token: str):
    """Avvia l'intervista - NON salva nome (deve essere già salvato)"""
    try:
        print(f"Tentativo di avvio colloquio con token: {token}")
        
        result = resolve_token_global(token)
        if not result:
            print(f"Token non valido o scaduto: {token}")
            raise HTTPException(status_code=404, detail="Invalid or expired link")
        
        session_id, tenant_id = result
        print(f"✅ Token risolto: session_id={session_id}, tenant_id={tenant_id}")
        
        # Check if evaluation is completed
        collections = get_tenant_collections(tenant_id)
        sess = get_session_data_tenant(session_id, collections["sessions"]) or {}
        stages = sess.get("stages", {})
        skill_relevance = stages.get("skill_relevance")
        if skill_relevance:
            print(f"❌ Colloquio già completato per session_id={session_id}")
            raise HTTPException(status_code=410, detail="Interview completed and evaluation finished. Access no longer available.")
        
        # Check if interview has already been started (single-use token)
        if sess.get("interview_started"):
            print(f"❌ Colloquio già avviato per session_id={session_id}")
            raise HTTPException(status_code=409, detail="Interview has already been started. Token can only be used once.")
        
        # Check if candidate name is saved
        candidate_name = sess.get("candidate_name")
        if not candidate_name:
            print(f"❌ Nome candidato non salvato per session_id={session_id}")
            raise HTTPException(status_code=400, detail="Candidate name must be saved before starting interview")
        
        print(f"✅ Controlli superati, procedo con l'avvio del colloquio per {candidate_name}")
        
        # Marca intervista come avviata PRIMA di start_interview_for_session per single-use
        if db is not None:
            sessions_collection = db[f"{tenant_id}_sessions"]
            sessions_collection.update_one(
                {"_id": session_id},
                {"$set": {
                    "interview_started": True,
                    "interview_started_at": datetime.utcnow().isoformat()
                }}
            )
        
        message = start_interview_for_session(session_id, tenant_id)
        
        print(f"Interview started for session {session_id} - token marked as used")
        
        return {"message": message}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Errore inaspettato in start_interview: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/interviews/{token}/message")
def send_message(token: str, payload: MessagePayload):
    result = resolve_token_global(token)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    session_id, tenant_id = result
    
    # Check if evaluation is completed
    collections = get_tenant_collections(tenant_id)
    sess = get_session_data_tenant(session_id, collections["sessions"]) or {}
    stages = sess.get("stages", {})
    skill_relevance = stages.get("skill_relevance")
    if skill_relevance:
        raise HTTPException(status_code=410, detail="Interview completed and evaluation finished. Access no longer available.")
    
    reply = send_message_for_session(session_id, payload.text, tenant_id)
    
    # Try to get interview state, but if chatbot is not initialized, initialize it first
    try:
        state = get_interview_state(session_id, tenant_id)
    except ValueError as e:
        if "Chatbot not initialized" in str(e):
            # Initialize the chatbot if it's not initialized yet
            meta = initialize_chatbot_for_session(session_id, tenant_id)
            if not meta:
                raise HTTPException(status_code=500, detail="Failed to initialize interview chatbot")
            
            # Now try to get the state again
            state = get_interview_state(session_id, tenant_id)
        else:
            raise HTTPException(status_code=500, detail=f"Interview state error: {str(e)}")
    
    return {"reply": reply, "state": state}


@app.get("/interviews/{token}/state")
def interview_state(token: str):
    result = resolve_token_global(token)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    session_id, tenant_id = result
    
    # Try to get interview state, but if chatbot is not initialized, initialize it first
    try:
        state = get_interview_state(session_id, tenant_id)
        return state
    except ValueError as e:
        if "Chatbot not initialized" in str(e):
            # Initialize the chatbot if it's not initialized yet
            meta = initialize_chatbot_for_session(session_id, tenant_id)
            if not meta:
                raise HTTPException(status_code=500, detail="Failed to initialize interview chatbot")
            
            # Now try to get the state again
            state = get_interview_state(session_id, tenant_id)
            return state
        else:
            raise HTTPException(status_code=500, detail=f"Interview state error: {str(e)}")


# Security event reporting endpoint
@app.post("/interviews/{token}/security-event")
def report_security_event(token: str, event_data: dict):
    result = resolve_token_global(token)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    session_id, tenant_id = result
    
    # Validate event data
    required_fields = ['type', 'timestamp', 'severity']
    for field in required_fields:
        if field not in event_data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Store security event
    try:
        # Create security event record
        security_event = {
            "session_id": session_id,
            "tenant_id": tenant_id,
            "event_type": event_data.get("type"),
            "timestamp": event_data.get("timestamp"),
            "severity": event_data.get("severity"),
            "details": event_data.get("details", ""),
            "created_at": datetime.utcnow().isoformat()
        }       
        # Generate unique event ID with random component to avoid duplicates
        import uuid
        timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        random_suffix = str(uuid.uuid4())[:8]
        event_id = f"{session_id}_{timestamp_ms}_{random_suffix}"
        security_event["_id"] = event_id
        
        # Save security event to database with duplicate handling
        if db is not None:
            security_events_collection = db[f"security_events_{tenant_id}"]
            try:
                security_events_collection.insert_one(security_event)
                print(f"Security event saved: {event_id}")
            except Exception as duplicate_error:
                if "duplicate key" in str(duplicate_error).lower():
                    # Generate new ID and retry once
                    new_random_suffix = str(uuid.uuid4())[:8]
                    new_event_id = f"{session_id}_{timestamp_ms}_{new_random_suffix}"
                    security_event["_id"] = new_event_id
                    security_events_collection.insert_one(security_event)
                    print(f"Security event saved with new ID: {new_event_id}")
                else:
                    raise duplicate_error
        
        # Update session with security summary
        collections = get_tenant_collections(tenant_id)
        sess = get_session_data_tenant(session_id, collections["sessions"]) or {}
        
        if "security_summary" not in sess:
            sess["security_summary"] = {
                "total_events": 0,
                "high_severity_events": 0,
                "medium_severity_events": 0,
                "low_severity_events": 0,
                "cheating_score": 0,
                "events_by_type": {},
                "last_updated": datetime.utcnow().isoformat()
            }
        
        # Update security summary
        summary = sess["security_summary"]
        summary["total_events"] += 1
        summary["last_updated"] = datetime.utcnow().isoformat()
        
        severity = event_data.get("severity", "low")
        if severity == "high":
            summary["high_severity_events"] += 1
            summary["cheating_score"] += 10
        elif severity == "medium":
            summary["medium_severity_events"] += 1
            summary["cheating_score"] += 5
        else:
            summary["low_severity_events"] += 1
            summary["cheating_score"] += 1
        
        # Normalize cheating score to 0-100 range
        summary["cheating_score"] = normalize_cheating_score(summary["cheating_score"])
        
        event_type = event_data.get("type", "unknown")
        summary["events_by_type"][event_type] = summary["events_by_type"].get(event_type, 0) + 1
        
        # Save updated session to database
        if db is not None:
            try:
                sessions_collection = db[f"sessions_{tenant_id}"]
                sessions_collection.update_one(
                    {"_id": session_id}, 
                    {"$set": {"security_summary": summary}}, 
                    upsert=False
                )
                print(f"Security summary updated for session: {session_id}")
            except Exception as update_error:
                print(f"Warning: Failed to update security summary: {update_error}")
                # Continue - the event was still recorded
        
        return {"status": "success", "event_id": event_id}
        
    except Exception as e:
        print(f"Error storing security event: {e}")
        raise HTTPException(status_code=500, detail="Failed to store security event")


# Get security report for a session (HR only)
@app.get("/sessions/{session_id}/security-report")
def get_security_report(session_id: str, auth_data=Depends(hr_auth)):
    tenant_id = auth_data.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    
    try:
        collections = get_tenant_collections(tenant_id)
        
        # Get session data
        sess = get_session_data_tenant(session_id, collections["sessions"]) or {}
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get detailed security events from database first
        security_events = []
        if db is not None:
            try:
                security_events_collection = db[f"security_events_{tenant_id}"]
                events_cursor = security_events_collection.find({"session_id": session_id})
                security_events = list(events_cursor)
                print(f"🔍 Found {len(security_events)} security events for session {session_id}")
            except Exception as e:
                print(f"Error retrieving security events: {e}")
        
        # Get security summary from session
        security_summary = sess.get("security_summary", {
            "total_events": 0,
            "high_severity_events": 0,
            "medium_severity_events": 0,
            "low_severity_events": 0,
            "cheating_score": 0,
            "events_by_type": {},
            "last_updated": None
        })
        
        # If we have events but no summary, calculate it from events
        if security_events and security_summary.get("total_events", 0) == 0:
            print(f"🔧 Recalculating security summary from {len(security_events)} events")
            security_summary = {
                "total_events": len(security_events),
                "high_severity_events": sum(1 for e in security_events if e.get("severity") == "high"),
                "medium_severity_events": sum(1 for e in security_events if e.get("severity") == "medium"),
                "low_severity_events": sum(1 for e in security_events if e.get("severity") == "low"),
                "cheating_score": 0,
                "events_by_type": {},
                "last_updated": None
            }
            
            # Calculate cheating score
            raw_score = 0
            for event in security_events:
                severity = event.get("severity", "low")
                if severity == "high":
                    raw_score += 10
                elif severity == "medium":
                    raw_score += 5
                else:
                    raw_score += 1
                
                # Count by type
                event_type = event.get("event_type", "unknown")
                security_summary["events_by_type"][event_type] = security_summary["events_by_type"].get(event_type, 0) + 1
            
            # Normalize the score to 0-100 range
            security_summary["cheating_score"] = normalize_cheating_score(raw_score)
        
        # Sort events by timestamp
        security_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Generate risk assessment (using 0-100 scale)
        cheating_score = security_summary.get("cheating_score", 0)
        if cheating_score >= 80:
            risk_level = "HIGH"
            risk_color = "#dc3545"
        elif cheating_score >= 50:
            risk_level = "MEDIUM"
            risk_color = "#ffc107"
        elif cheating_score >= 20:
            risk_level = "LOW"
            risk_color = "#28a745"
        else:
            risk_level = "MINIMAL"
            risk_color = "#6c757d"
        
        return {
            "session_id": session_id,
            "security_summary": security_summary,
            "security_events": security_events[:50],  # Limit to last 50 events
            "risk_assessment": {
                "level": risk_level,
                "color": risk_color,
                "cheating_score": cheating_score,
                "recommendation": get_security_recommendation(cheating_score)
            }
        }
        
    except Exception as e:
        print(f"Error retrieving security report: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security report")


def normalize_cheating_score(raw_score: int) -> int:
    """
    Normalize cheating score to 0-100 range using logarithmic scaling.
    This prevents scores from exceeding 100 while maintaining relative differences.
    """
    if raw_score <= 0:
        return 0
    
    # Use logarithmic scaling to compress high scores
    # Formula: 100 * (1 - e^(-raw_score/50))
    # This ensures scores approach 100 asymptotically but never exceed it
    import math
    normalized = 100 * (1 - math.exp(-raw_score / 50))
    return min(100, int(round(normalized)))

def fix_existing_cheating_scores():
    """
    Fix existing cheating scores that exceed 100 by normalizing them.
    This should be run once to fix historical data.
    """
    if db is None:
        print("Database not available for score normalization")
        return False
    
    try:
        # Find all collections with sessions
        collections = db.list_collection_names()
        session_collections = [c for c in collections if c.endswith("_sessions")]
        
        fixed_count = 0
        for coll_name in session_collections:
            collection = db[coll_name]
            
            # Find sessions with cheating_score > 100
            sessions_to_fix = list(collection.find({
                "security_summary.cheating_score": {"$gt": 100}
            }))
            
            for session in sessions_to_fix:
                old_score = session["security_summary"]["cheating_score"]
                new_score = normalize_cheating_score(old_score)
                
                collection.update_one(
                    {"_id": session["_id"]},
                    {"$set": {"security_summary.cheating_score": new_score}}
                )
                
                print(f"Fixed session {session['_id']}: {old_score} -> {new_score}")
                fixed_count += 1
        
        print(f"Fixed {fixed_count} sessions with scores > 100")
        return True
        
    except Exception as e:
        print(f"Error fixing cheating scores: {e}")
        return False

def get_security_recommendation(cheating_score: int) -> str:
    """Generate security recommendation based on cheating score (0-100 scale)"""
    if cheating_score >= 80:
        return "RISCHIO ALTO: Rilevate multiple violazioni gravi. Considerare la squalifica del candidato o richiedere verifiche aggiuntive."
    elif cheating_score >= 50:
        return "RISCHIO MEDIO: Rilevate diverse violazioni. Rivedere attentamente il colloquio e considerare domande di follow-up."
    elif cheating_score >= 20:
        return "RISCHIO BASSO: Rilevate violazioni minori. Monitorare durante la valutazione finale."
    else:
        return "RISCHIO MINIMO: Nessuna violazione significativa rilevata. Il candidato sembra aver seguito le linee guida."


# Admin endpoint to fix existing cheating scores
@app.post("/admin/fix-cheating-scores", dependencies=[Depends(hr_auth)])
def fix_cheating_scores_admin(auth_data=Depends(hr_auth)):
    """Fix existing cheating scores that exceed 100 (admin only)"""
    # Check if user is admin
    if auth_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        success = fix_existing_cheating_scores()
        if success:
            return {"message": "Cheating scores normalized successfully", "status": "success"}
        else:
            return {"message": "Failed to normalize cheating scores", "status": "error"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fixing scores: {str(e)}")


@app.post("/admin/recompute-course-embeddings", dependencies=[Depends(hr_auth)])
def recompute_course_embeddings_admin(auth_data=Depends(hr_auth)):
    """
    Ricalcola gli embeddings per tutti i corsi e reinizializza il RAG Service.
    Da utilizzare quando si aggiungono o modificano corsi.
    (Admin only)
    """
    # Check if user is admin
    if auth_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Import necessary modules
        from sentence_transformers import SentenceTransformer
        from services.data_manager import db
        
        EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
        COURSES_COLLECTION_NAME = "courses"
        
        if db is None:
            raise HTTPException(status_code=500, detail="Database connection not available")
        
        collection = db[COURSES_COLLECTION_NAME]
        courses = list(collection.find({}))
        
        if not courses:
            raise HTTPException(status_code=404, detail="No courses found in database")
        
        # Load model and compute embeddings
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        
        updated_count = 0
        for course in courses:
            course_id = course.get('_id')
            description = f"{course.get('Course Name', '')}. {course.get('Description', '')}"
            
            # Calculate embedding
            embedding = model.encode(description, convert_to_tensor=False)
            
            # Save to database
            collection.update_one(
                {"_id": course_id},
                {"$set": {"embedding": embedding.tolist()}}
            )
            updated_count += 1
        
        # Reinitialize RAG service with new embeddings
        global rag_service_instance
        print("🔄 Reinizializzazione RAG Service con nuovi embeddings...")
        rag_service_instance = RAGService()
        print("✅ RAG Service reinizializzato con successo")
        
        return {
            "message": f"Embeddings recomputed successfully for {updated_count} courses",
            "status": "success",
            "courses_updated": updated_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recomputing embeddings: {str(e)}")


# Evaluation and feedback (HR)
@app.post("/sessions/{session_id}/evaluate")
def evaluate_session(session_id: str, _=Depends(hr_auth)):
    ok = execute_case_evaluation(session_id=session_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Evaluation failed")
    # Skill relevance
    _ = compute_and_save_skill_relevance(session_id=session_id)
    return {"ok": True}

@app.get("/sessions/{session_id}/feedback")
def download_feedback(session_id: str, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    sess = get_session_data_tenant(session_id, collections["sessions"])
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    # The pipeline stores the path; fetch persisted file
    base_dir = os.path.join("data", "sessions", session_id)
    file_path = os.path.join(base_dir, "Report_Feedback_Candidato.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    def iterfile():
        with open(file_path, "rb") as f:
            yield from f
    return StreamingResponse(iterfile(), media_type="application/pdf")


def _scale_to_0_4(pct_val):
    try:
        v = int(round((float(pct_val or 0) / 25.0)))
        return max(0, min(4, v))
    except Exception:
        return 0


@app.get("/sessions/{session_id}/skills_scaled")
def get_skills_scaled(session_id: str, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    data = get_session_data_tenant(session_id, collections["sessions"])
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    scores = (((data.get("stages") or {}).get("skill_relevance") or {}).get("scores") or [])
    items = []
    for s in scores:
        items.append({
            "skill_name": s.get("skill_name"),
            "cv_0_4": s.get("cv_relevance_score", 0),
            "interview_0_4": s.get("interview_relevance_score", 0),
            "notes_cv": s.get("notes_cv"),
            "notes_interview": s.get("notes_interview"),
        })
    return {"items": items}


@app.get("/sessions/{session_id}/report/{kind}")
def get_report(session_id: str, kind: str, auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    data = get_session_data_tenant(session_id, collections["sessions"])
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    stages = data.get("stages") or {}
    if kind == "cv":
        rep = stages.get("cv_analysis_report")
    elif kind == "case":
        rep = stages.get("case_evaluation_report")
    else:
        raise HTTPException(status_code=400, detail="Invalid kind; use 'cv' or 'case'")
    if rep is None:
        raise HTTPException(status_code=404, detail="Report not available")
    return {"report": rep}


# Interview Configuration Management
@app.get("/interview-config")
def get_interview_config_endpoint(auth_data=Depends(hr_auth)):
    """Get interview configuration for the current tenant"""
    tenant_id = auth_data.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    
    config = get_interview_config_or_default(tenant_id)
    return {
        "reasoning_steps": config.reasoning_steps,
        "max_attempts": config.max_attempts,
        "estimated_duration_minutes": config.estimated_duration_minutes,
        "max_questions": config.max_questions,
        "created_at": config.created_at,
        "updated_at": config.updated_at
    }

@app.put("/interview-config")
async def update_interview_config_endpoint(
    request: Request,
    auth_data=Depends(hr_auth)
):
    """Update interview configuration for the current tenant"""
    tenant_id = auth_data.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    
    # Extract parameters from request body
    body = await request.json()
    reasoning_steps = body.get("reasoning_steps")
    max_attempts = body.get("max_attempts")
    
    if reasoning_steps is None or max_attempts is None:
        raise HTTPException(status_code=400, detail="reasoning_steps and max_attempts are required")
    
    # Validate parameters
    if not (2 <= reasoning_steps <= 6):
        raise HTTPException(status_code=400, detail="reasoning_steps must be between 2 and 6")
    
    if not (2 <= max_attempts <= 5):
        raise HTTPException(status_code=400, detail="max_attempts must be between 2 and 5")
    
    # Create or update configuration
    config = InterviewConfig(
        tenant_id=tenant_id,
        reasoning_steps=reasoning_steps,
        max_attempts=max_attempts
    )
    
    success = save_interview_config(config)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save configuration")
    
    return {
        "ok": True,
        "message": "Configuration updated successfully",
        "config": {
            "reasoning_steps": config.reasoning_steps,
            "max_attempts": config.max_attempts,
            "estimated_duration_minutes": config.estimated_duration_minutes,
            "max_questions": config.max_questions,
            "updated_at": config.updated_at
        }
    }

# Batch Processing imports moved to top level

@app.post("/api/batch/upload-cvs", dependencies=[Depends(hr_auth)])
async def bulk_upload_cvs(
    position_id: str = Form(...),
    files: List[UploadFile] = File(...),
    auth_data: dict = Depends(hr_auth)
):
    """Upload massivo di CV per batch processing"""
    tenant_id = auth_data.get("tenant_id")
    collections = get_tenant_collections(tenant_id)
    
    if not files:
        raise HTTPException(status_code=400, detail="Nessun file fornito")
    
    # Validazione numero file
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Massimo 100 file per batch")
    
    # Validazione file PDF
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} non è un PDF")
    
    uploaded_sessions = []
    batch_date = datetime.now().strftime("%Y-%m-%d")
    batch_id = f"batch_{batch_date.replace('-', '')}_{datetime.now().strftime('%H%M%S')}"
    
    for file in files:
        try:
            # 1. Leggi CV
            cv_bytes = await file.read()
            cv_text = ""
            try:
                with fitz.open(stream=cv_bytes, filetype="pdf") as doc:
                    cv_text = "".join(page.get_text() for page in doc)
            except Exception as e:
                print(f"⚠️ Errore lettura PDF {file.filename}: {e}")
                continue
            
            # Validazione dimensione file
            if len(cv_bytes) > 10 * 1024 * 1024:  # 10MB limit
                print(f"⚠️ File {file.filename} troppo grande (>10MB), saltato")
                continue
            
            # 2. Estrai email con regex
            candidate_email = extract_email_from_text(cv_text)
            
            # 3. Crea sessione
            session_id = str(uuid.uuid4())
            candidate_name = file.filename.replace(".pdf", "").replace("_", " ")
            
            create_new_session_tenant(
                session_id,  # positional
                position_id,  # positional  
                "",  # candidate_name - positional
                collections["sessions"],  # collection_name - positional
                candidate_email  # candidate_email - positional
            )
            
            # 4. Salva CV e metadata batch
            save_stage_output_tenant(
                session_id=session_id,
                stage_name="uploaded_cv_text",
                data_content=cv_text,
                collection_name=collections["sessions"]
            )
            
            save_stage_output_tenant(
                session_id=session_id,
                stage_name="cv_analysis_status",
                data_content="pending",
                collection_name=collections["sessions"]
            )
            
            # 5. Aggiungi metadata batch
            if db is not None:
                sessions_collection = db[collections["sessions"]]
                sessions_collection.update_one(
                    {"_id": session_id},
                    {"$set": {
                        "tenant_id": tenant_id,  # CRITICO: Aggiungi tenant_id
                        "batch_id": batch_id,
                        "batch_date": batch_date,
                        "is_new_batch": True,
                        "candidate_surname": ""  # Nuovo campo
                    }}
                )
            
            uploaded_sessions.append({
                "session_id": session_id,
                "filename": file.filename,
                "candidate_email": candidate_email
            })
            
        except Exception as e:
            print(f"❌ Errore processing file {file.filename}: {e}")
            continue
    
    # Crea automaticamente un batch job per i CV caricati
    print(f"[BATCH] Creazione batch job per {len(uploaded_sessions)} CV...")
    batch_service = BatchService()
    batch_job_id = batch_service.create_cv_analysis_batch()
    
    if batch_job_id:
        print(f"[OK] Batch job creato: {batch_job_id}")
        return {
            "message": f"{len(uploaded_sessions)} CV caricati e batch job creato con successo",
            "sessions": uploaded_sessions,
            "batch_id": batch_id,
            "batch_date": batch_date,
            "batch_job_id": batch_job_id,
            "note": "I CV verranno processati tramite Azure OpenAI Batch API"
        }
    else:
        print(f"[WARN] Nessun batch job creato - nessun CV da processare")
        return {
            "message": f"{len(uploaded_sessions)} CV caricati con successo",
            "sessions": uploaded_sessions,
            "batch_id": batch_id,
            "batch_date": batch_date,
            "note": "Nessun batch job creato - nessun CV da processare"
        }

@app.post("/api/batch/trigger-manual", dependencies=[Depends(hr_auth)])
async def trigger_manual_batch(auth_data: dict = Depends(hr_auth)):
    """Trigger manuale del batch (per testing o urgenze)"""
    batch_service = BatchService()
    batch_id = batch_service.create_cv_analysis_batch()
    
    if not batch_id:
        return {"message": "Nessun CV da processare"}
    
    return {
        "message": "Batch creato con successo",
        "batch_id": batch_id,
        "status": "validating"
    }

@app.get("/api/batch/status/{batch_id}", dependencies=[Depends(hr_auth)])
async def get_batch_status(batch_id: str):
    """Controlla status di un batch"""
    batch_service = BatchService()
    status = batch_service.check_batch_status(batch_id)
    
    # Info dal DB
    batch_info = batch_service.get_batch_info(batch_id)
    
    return {
        "batch_id": batch_id,
        "status": status,
        "created_at": batch_info.get("created_at") if batch_info else None,
        "total_requests": batch_info.get("total_requests") if batch_info else 0,
        "request_counts": batch_info.get("request_counts", {}) if batch_info else {}
    }

@app.post("/api/batch/retrieve/{batch_id}", dependencies=[Depends(hr_auth)])
async def retrieve_batch_results(batch_id: str):
    """Recupera risultati di un batch completato"""
    batch_service = BatchService()
    success = batch_service.retrieve_batch_results(batch_id)
    
    if success:
        return {"message": "Risultati recuperati e salvati con successo"}
    else:
        raise HTTPException(status_code=400, detail="Batch non completato o errore")

@app.get("/api/batch/list", dependencies=[Depends(hr_auth)])
async def list_batches(auth_data: dict = Depends(hr_auth)):
    """Lista tutti i batch jobs"""
    try:
        print(f"Tentativo di listare batch jobs per tenant: {auth_data.get('tenant_id')}")
        
        batch_service = BatchService()
        print(f"BatchService inizializzato")
        
        batches = batch_service.list_batches(limit=20)
        print(f"Batch jobs recuperati: {len(batches)} items")
        
        return {"batches": batches}
    except Exception as e:
        import traceback
        print(f"❌ Errore in list_batches endpoint: {e}")
        print(f"❌ Traceback completo: {traceback.format_exc()}")
        return {"batches": [], "error": str(e)}

# Startup events per batch processor
@app.on_event("startup")
async def startup_event():
    """Inizializzazione app con batch processor e servizi pesanti"""
    global rag_service_instance, recruitment_pipeline_instance, cv_normalizer_instance
    
    try:
        # Initialize heavy services once at startup
        print("[STARTUP] Inizializzazione RAGService...")
        rag_service_instance = RAGService()
        print("[STARTUP] RAGService pronto.")
        
        print("[STARTUP] Inizializzazione RecruitmentPipeline...")
        recruitment_pipeline_instance = RecruitmentPipeline() 
        print("[STARTUP] RecruitmentPipeline pronto.")
        
        print("[STARTUP] Inizializzazione CVNormalizer (potrebbe essere lento)...")
        cv_normalizer_instance = CVNormalizer()
        print("[STARTUP] CVNormalizer pronto.")
        
        # Avvia batch processor per monitoring automatico
        from services.batch_processor import get_processor
        processor = get_processor()
        processor.start_monitoring(check_interval_seconds=300)  # 5 minuti
        print("Batch processor avviato (controllo ogni 5 minuti)")
        
    except Exception as e:
        print(f"Errore inizializzazione servizi: {e}")
        import traceback
        traceback.print_exc()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup al shutdown"""
    try:
        from services.batch_processor import get_processor
        
        processor = get_processor()
        processor.stop_monitoring()
        
        print("✅ Batch processor fermato")
    except Exception as e:
        print(f"⚠️ Errore durante shutdown: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=False)


