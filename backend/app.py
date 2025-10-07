from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
import os
import uuid
import fitz  # PyMuPDF
from datetime import datetime

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
)
from services.auth_service import authenticate_hr, create_jwt, verify_jwt, get_or_create_tenant_for_email
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
    get_dashboard_data_tenant
)
from services.email_service import send_interview_link


def hr_auth(authorization: str | None = Header(default=None)):
    token_val = None
    if authorization and authorization.lower().startswith("bearer "):
        token_val = authorization.split(" ", 1)[1]
    if not token_val:
        raise HTTPException(status_code=401, detail="Missing token")
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


app = FastAPI(title="Vertigo AI Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure per environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        }
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
    
    ok = create_or_update_position_tenant(position_id, payload.model_dump(exclude={"position_id"}), collections["positions"])
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to upsert position")
    return {"ok": True, "position_id": position_id}


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
    ok = run_full_generation_pipeline(position_id, collections["positions"])
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


@app.put("/sessions/{session_id}/token-sent")
def mark_token_sent(session_id: str, auth_data=Depends(hr_auth)):
    """Mark that the interview token has been sent to the candidate"""
    collections = get_tenant_collections_from_auth(auth_data)
    try:
        collection = db[collections["sessions"]]
        result = collection.update_one(
            {"_id": session_id},
            {"$set": {"token_sent": True, "token_sent_by": auth_data.get("sub"), "token_sent_at": datetime.utcnow()}}
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
        
        if jd_text and cv_text_for_market:
            qualitative_text, chart_cat_b64, market_skills_list = run_market_benchmark_from_text(
                job_description_text=jd_text,
                cv_text=cv_text_for_market,
                offer_title=role_title
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

# Sessions (HR)
@app.post("/sessions")
async def create_session(position_id: str = Form(...), candidate_name: str = Form("Candidato"), cv_file: UploadFile = File(...), candidate_email: str = Form(None), frontend_base_url: str = Form("") , auth_data=Depends(hr_auth)):
    collections = get_tenant_collections_from_auth(auth_data)
    session_id = str(uuid.uuid4())
    created = create_new_session_tenant(session_id, position_id, candidate_name, collections["sessions"])
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
def generate_feedback(session_id: str, auth_data=Depends(hr_auth)):
    """Generate final feedback report for a completed session"""
    collections = get_tenant_collections_from_auth(auth_data)
    
    # Check if session exists and is completed
    session_data = get_session_data_tenant(session_id, collections["sessions"])
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    stages = session_data.get("stages", {})
    if not (stages.get("cv_analysis_report") and stages.get("case_evaluation_report") and stages.get("skill_relevance")):
        raise HTTPException(status_code=400, detail="Session not ready for feedback generation")
    
    # Check if feedback is already generated
    if stages.get("feedback_pdf_path"):
        return {"ok": True, "message": "Feedback already generated", "pdf_path": stages.get("feedback_pdf_path")}
    
    try:
        # Import and run tenant-aware feedback pipeline
        pdf_path = run_feedback_pipeline_tenant(session_id, collections["sessions"])
        
        if pdf_path:
            # Save the PDF path to the session
            save_stage_output_tenant(session_id, "feedback_pdf_path", pdf_path, collections["sessions"])
            return {"ok": True, "pdf_path": pdf_path}
        else:
            raise HTTPException(status_code=500, detail="Feedback generation failed")
    except Exception as e:
        print(f"Error generating feedback for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Feedback generation failed: {str(e)}")


@app.get("/sessions/{session_id}/feedback-pdf")
def download_feedback_pdf(session_id: str, auth_data=Depends(hr_auth)):
    """Download the feedback PDF for a completed session"""
    collections = get_tenant_collections_from_auth(auth_data)
    
    # Check if session exists
    session_data = get_session_data_tenant(session_id, collections["sessions"])
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    stages = session_data.get("stages", {})
    pdf_path = stages.get("feedback_pdf_path")
    
    if not pdf_path:
        raise HTTPException(status_code=404, detail="Feedback PDF not found")
    
    try:
        import os
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found on disk")
        
        with open(pdf_path, "rb") as pdf_file:
            pdf_content = pdf_file.read()
        
        # Track download information
        download_info = {
            "downloaded_at": datetime.utcnow().isoformat(),
            "downloaded_by": auth_data.get("sub"),  # User email
            "downloaded_by_name": auth_data.get("name", auth_data.get("sub", "Unknown"))
        }
        
        # Update session with download tracking
        save_stage_output_tenant(session_id, "feedback_download", download_info, collections["sessions"])
        
        candidate_name = session_data.get("candidate_name", "Candidate")
        position_id = session_data.get("position_id", "Position")
        filename = f"Report_Feedback_{candidate_name}_{position_id}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        print(f"Error downloading feedback PDF for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error downloading PDF: {str(e)}")


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
    """List incomplete sessions for Nuova Sessione dashboard"""
    collections = get_tenant_collections_from_auth(auth_data)
    results = list_incomplete_sessions_tenant(collections["sessions"])
    return {"items": results}


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
    auth_data=Depends(hr_auth)
):
    """Get comprehensive dashboard data for HR analytics"""
    tenant_id = auth_data.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Invalid tenant ID")
    
    # Validate time range
    valid_ranges = ["7d", "30d", "90d", "1y"]
    if timeRange not in valid_ranges:
        timeRange = "30d"
    
    dashboard_data = get_dashboard_data_tenant(tenant_id, timeRange)
    
    if not dashboard_data:
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")
    
    return dashboard_data


# Candidate interview (public via token)
@app.get("/interviews/{token}")
def resolve_interview(token: str):
    result = resolve_token_global(token)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    session_id, tenant_id = result
    
    collections = get_tenant_collections(tenant_id)
    sess = get_session_data_tenant(session_id, collections["sessions"]) or {}
    
    # Check if evaluation is completed (has skill_summary)
    stages = sess.get("stages", {})
    skill_summary = stages.get("skill_summary")
    if skill_summary:
        raise HTTPException(status_code=410, detail="Interview completed and evaluation finished. Access no longer available.")
    
    pos_id = sess.get("position_id")
    pos = get_single_position_data_tenant(pos_id, collections["positions"]) if pos_id else {}
    return {
        "session_id": session_id,
        "position_name": (pos or {}).get("position_name"),
        "case_id": (sess.get("stages", {}) or {}).get("case_id"),
    }


@app.post("/interviews/{token}/start")
def start_interview(token: str):
    result = resolve_token_global(token)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    session_id, tenant_id = result
    
    # Check if evaluation is completed
    collections = get_tenant_collections(tenant_id)
    sess = get_session_data_tenant(session_id, collections["sessions"]) or {}
    stages = sess.get("stages", {})
    skill_summary = stages.get("skill_summary")
    if skill_summary:
        raise HTTPException(status_code=410, detail="Interview completed and evaluation finished. Access no longer available.")
    
    message = start_interview_for_session(session_id, tenant_id)
    return {"message": message}


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
    skill_summary = stages.get("skill_summary")
    if skill_summary:
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
        # Generate unique event ID
        event_id = f"{session_id}_{int(datetime.utcnow().timestamp() * 1000)}"
        security_event["_id"] = event_id
        
        # Save security event to database
        if db is not None:
            security_events_collection = db[f"security_events_{tenant_id}"]
            security_events_collection.insert_one(security_event)
            print(f"🔒 Security event saved: {event_id}")
        
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
        
        event_type = event_data.get("type", "unknown")
        summary["events_by_type"][event_type] = summary["events_by_type"].get(event_type, 0) + 1
        
        # Save updated session to database
        if db is not None:
            sessions_collection = db[f"sessions_{tenant_id}"]
            sessions_collection.update_one(
                {"_id": session_id}, 
                {"$set": {"security_summary": summary}}, 
                upsert=False
            )
            print(f"📊 Security summary updated for session: {session_id}")
        
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
        
        # Get detailed security events from database
        security_events = []
        if db is not None:
            try:
                security_events_collection = db[f"security_events_{tenant_id}"]
                events_cursor = security_events_collection.find({"session_id": session_id})
                security_events = list(events_cursor)
                print(f"🔍 Found {len(security_events)} security events for session {session_id}")
            except Exception as e:
                print(f"Error retrieving security events: {e}")
        
        # Sort events by timestamp
        security_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Generate risk assessment
        cheating_score = security_summary.get("cheating_score", 0)
        if cheating_score >= 50:
            risk_level = "HIGH"
            risk_color = "#dc3545"
        elif cheating_score >= 20:
            risk_level = "MEDIUM"
            risk_color = "#ffc107"
        elif cheating_score >= 5:
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


def get_security_recommendation(cheating_score: int) -> str:
    """Generate security recommendation based on cheating score"""
    if cheating_score >= 50:
        return "HIGH RISK: Multiple serious violations detected. Consider disqualifying candidate or requiring additional verification."
    elif cheating_score >= 20:
        return "MEDIUM RISK: Several violations detected. Review interview carefully and consider follow-up questions."
    elif cheating_score >= 5:
        return "LOW RISK: Minor violations detected. Monitor during final evaluation."
    else:
        return "MINIMAL RISK: No significant violations detected. Candidate appears to have followed guidelines."


# Evaluation and feedback (HR)
@app.post("/sessions/{session_id}/evaluate")
def evaluate_session(session_id: str, _=Depends(hr_auth)):
    ok = execute_case_evaluation(session_id=session_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Evaluation failed")
    # Skill relevance
    _ = compute_and_save_skill_relevance(session_id=session_id)
    return {"ok": True}


@app.post("/sessions/{session_id}/feedback")
def generate_feedback(session_id: str, _=Depends(hr_auth)):
    pdf_path = run_feedback_pipeline(session_id=session_id)
    if not pdf_path:
        raise HTTPException(status_code=500, detail="Feedback generation failed")
    return {"pdf_path": pdf_path}


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
            "cv_0_4": _scale_to_0_4(s.get("cv_relevance_pct")),
            "interview_0_4": _scale_to_0_4(s.get("interview_relevance_pct")),
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


@app.get("/health")
def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)


