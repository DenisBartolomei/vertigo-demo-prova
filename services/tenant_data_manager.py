"""
Tenant-aware data manager functions
"""
import os
from services.data_manager import db


def create_or_update_position_tenant(position_id: str, payload: dict, collection_name: str) -> bool:
    """Create or update position in tenant-specific collection"""
    if db is None:
        print("DB not available for create_or_update_position_tenant")
        return False
    try:
        collection = db[collection_name]
        payload = payload.copy()
        payload["_id"] = position_id
        collection.update_one({"_id": position_id}, {"$set": payload}, upsert=True)
        print(f"📄 Position upserted in tenant collection: {collection_name} with ID: {position_id}")
        return True
    except Exception as e:
        print(f"Error during position upsert {position_id}: {e}")
        return False


def create_new_session_tenant(session_id: str, position_id: str, candidate_name: str, collection_name: str, candidate_email: str = None) -> bool:
    """Create new session in tenant-specific collection"""
    if db is None:
        return False
    try:
        collection = db[collection_name]
        new_document = {
            "_id": session_id, 
            "position_id": position_id, 
            "candidate_name": candidate_name, 
            "candidate_email": candidate_email,
            "status": "initialized", 
            "stages": {}
        }
        collection.insert_one(new_document)
        print(f"📄 Session created in tenant collection: {collection_name} with ID: {session_id}")
        return True
    except Exception as e:
        print(f"Error during session creation {session_id}: {e}")
        return False


def save_stage_output_tenant(session_id: str, stage_name: str, data_content: dict | str, collection_name: str):
    """Save stage output in tenant-specific collection"""
    if db is None:
        return
    try:
        collection = db[collection_name]
        
        # Convert ObjectId objects to strings if present in data_content
        if isinstance(data_content, dict):
            data_content = _convert_objectids_to_strings(data_content)
        
        update_query = {"$set": {f"stages.{stage_name}": data_content}}
        collection.update_one({"_id": session_id}, update_query)
        print(f"💾 Stage '{stage_name}' data saved for session {session_id} in tenant collection: {collection_name}")
    except Exception as e:
        print(f"Error saving stage '{stage_name}': {e}")


def _convert_objectids_to_strings(obj):
    """Recursively convert ObjectId objects to strings in nested dictionaries and lists"""
    from bson import ObjectId
    
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: _convert_objectids_to_strings(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_objectids_to_strings(item) for item in obj]
    else:
        return obj


def get_session_data_tenant(session_id: str, collection_name: str) -> dict | None:
    """Get session data from tenant-specific collection"""
    if db is None:
        return None
    try:
        collection = db[collection_name]
        return collection.find_one({"_id": session_id})
    except Exception as e:
        print(f"Error retrieving session {session_id}: {e}")
        return None


def get_available_positions_tenant(collection_name: str):
    """Get available positions from tenant-specific collection"""
    if db is None:
        print("DB not available for get_available_positions_tenant")
        return []
    try:
        collection = db[collection_name]
        positions = list(collection.find({}, {"_id": 1, "position_name": 1}))
        return sorted(positions, key=lambda p: p['position_name'])
    except Exception as e:
        print(f"Error retrieving positions from tenant collection: {e}")
        return []


def get_single_position_data_tenant(position_id: str, collection_name: str):
    """Get single position data from tenant-specific collection"""
    if db is None:
        print(f"DB not available for get_single_position_data_tenant for ID: {position_id}")
        return None
    try:
        collection = db[collection_name]
        return collection.find_one({"_id": position_id})
    except Exception as e:
        print(f"Error retrieving position {position_id}: {e}")
        return None


def list_sessions_tenant(collection_name: str):
    """List sessions from tenant-specific collection with status logic"""
    if db is None:
        return []
    try:
        collection = db[collection_name]
        sessions = list(collection.find({}, {
            "_id": 1, 
            "candidate_name": 1, 
            "position_id": 1,
            "stages.cv_analysis_status": 1,
            "stages.conversation": 1
        }))
        
        # Get position names
        positions_collection = db[collection_name.replace("_sessions", "_positions_data")]
        results = []
        for s in sessions:
            pid = s.get("position_id")
            pname = None
            if pid:
                p = positions_collection.find_one({"_id": pid}, {"position_name": 1})
                pname = (p or {}).get("position_name")
            
            # Determine status based on cv_analysis_status and conversation
            stages = s.get("stages", {})
            cv_status = stages.get("cv_analysis_status")
            conversation = stages.get("conversation")
            
            status = "initialized"
            if cv_status == "Completed":
                if conversation:
                    # Both present - interview completed, don't show in dashboard
                    continue
                else:
                    # CV done but no conversation - interview pending
                    status = "Colloquio da completare"
            elif cv_status == "Failed":
                status = "CV analysis failed"
            
                results.append({
                    "session_id": s.get("_id"),
                    "candidate_name": s.get("candidate_name"),
                    "position_id": pid,
                    "position_name": pname,
                    "status": status,
                    "interview_token": s.get("interview_token"),  # Include interview token
                })
        return results
    except Exception as e:
        print(f"Error listing sessions from tenant collection: {e}")
        return []


def list_completed_sessions_tenant(collection_name: str) -> list:
    """List only sessions that have completed the full interview (have skill summaries) for Reportistica Candidati"""
    try:
        if db is None:
            return []
        
        sessions = list(db[collection_name].find({}))
        results = []
        
        for s in sessions:
            pid = s.get("position_id")
            pname = None
            if pid:
                p = get_single_position_data_tenant(pid, collection_name.replace("_sessions", "_positions_data"))
                pname = (p or {}).get("position_name")
            
            # Check if interview is fully completed (has skill relevance)
            stages = s.get("stages", {})
            cv_status = stages.get("cv_analysis_status")
            conversation = stages.get("conversation")
            case_evaluation = stages.get("case_evaluation_report")
            skill_relevance = stages.get("skill_relevance")  # This indicates full completion
            feedback_pdf_path = stages.get("feedback_pdf_path")
            
            # Only include sessions that have completed the full interview
            if cv_status == "Completed" and conversation and case_evaluation and skill_relevance:
                # Determine status based on feedback generation
                if feedback_pdf_path:
                    status = "Feedback ready"
                else:
                    status = "Feedback pending"
                
                # Get download information
                download_info = stages.get("feedback_download", {})
                
                results.append({
                    "session_id": s.get("_id"),
                    "candidate_name": s.get("candidate_name"),
                    "candidate_email": s.get("candidate_email"),
                    "position_id": pid,
                    "position_name": pname,
                    "status": status,
                    "interview_token": stages.get("interview_token"),
                    "feedback_pdf_path": feedback_pdf_path,
                    "downloaded_at": download_info.get("downloaded_at"),
                    "downloaded_by": download_info.get("downloaded_by"),
                    "downloaded_by_name": download_info.get("downloaded_by_name"),
                })
        return results
    except Exception as e:
        print(f"Error listing completed sessions from tenant collection: {e}")
        return []


def list_incomplete_sessions_tenant(collection_name: str) -> list:
    """List sessions that haven't completed the full interview (no skill summary) for Nuova Sessione dashboard"""
    try:
        if db is None:
            return []
        
        sessions = list(db[collection_name].find({}))
        results = []
        
        for s in sessions:
            pid = s.get("position_id")
            pname = None
            if pid:
                p = get_single_position_data_tenant(pid, collection_name.replace("_sessions", "_positions_data"))
                pname = (p or {}).get("position_name")
            
            # Check if interview is NOT fully completed (no skill relevance)
            stages = s.get("stages", {})
            cv_status = stages.get("cv_analysis_status")
            conversation = stages.get("conversation")
            case_evaluation = stages.get("case_evaluation_report")
            skill_relevance = stages.get("skill_relevance")
            
            # Include sessions that haven't completed the full interview
            if not skill_relevance:  # No skill relevance means not fully completed
                status = "initialized"
                if cv_status == "Completed":
                    if conversation:
                        if case_evaluation and skill_relevance:
                            # Everything completed - should not appear in incomplete list
                            continue
                        elif case_evaluation:
                            # Case evaluation done, skill scoring pending
                            status = "Skill scoring pending"
                        else:
                            # CV done, conversation done, but no evaluation - evaluation pending
                            status = "Evaluation pending"
                    else:
                        # CV done but no conversation - interview pending
                        status = "Colloquio da completare"
                elif cv_status == "Failed":
                    status = "CV analysis failed"
                
                results.append({
                    "session_id": s.get("_id"),
                    "candidate_name": s.get("candidate_name"),
                    "candidate_email": s.get("candidate_email"),
                    "position_id": pid,
                    "position_name": pname,
                    "status": status,
                    "interview_token": stages.get("interview_token"),
                    "token_sent": s.get("token_sent", False),
                    "token_sent_by": s.get("token_sent_by"),
                    "token_sent_at": s.get("token_sent_at"),
                })
        return results
    except Exception as e:
        print(f"Error listing incomplete sessions from tenant collection: {e}")
        return []


def get_dashboard_data_tenant(tenant_id: str, time_range: str = "30d", position_filter: str = None) -> dict:
    """Get comprehensive dashboard data for HR analytics with real recruitment indicators"""
    if db is None:
        print(f"Database not available for tenant {tenant_id}")
        return {}
    
    try:
        from datetime import datetime, timedelta
        import math
        
        print(f"Getting dashboard data for tenant: {tenant_id}, time_range: {time_range}, position_filter: {position_filter}")
        
        # Calculate date range
        now = datetime.utcnow()
        if time_range == "7d":
            start_date = now - timedelta(days=7)
        elif time_range == "30d":
            start_date = now - timedelta(days=30)
        elif time_range == "90d":
            start_date = now - timedelta(days=90)
        elif time_range == "1y":
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)
        
        # Get tenant collections
        positions_collection = db[f"{tenant_id}_positions_data"]
        sessions_collection = db[f"{tenant_id}_sessions"]
        users_collection = db[f"{tenant_id}_users"]
        
        # Query base con filtro posizione
        query = {}
        if position_filter and position_filter != "all":
            query["position_id"] = position_filter
        
        # 1. COLLOQUI COMPLETATI
        completed_interviews = sessions_collection.count_documents({
            **query,
            "stages.skill_relevance": {"$exists": True}
        })
        
        # 2. CANDIDATI IN ATTESA DI TOKEN
        waiting_token = sessions_collection.count_documents({
            **query,
            "stages.interview_token": {"$exists": True},
            "token_sent": False
        })
        
        # 3. COLLOQUIO IN CORSO
        in_progress = sessions_collection.count_documents({
            **query,
            "token_sent": True,
            "stages.skill_relevance": {"$exists": False}
        })
        
        # 4. DURATA MEDIA COLLOQUIO
        completed_sessions = list(sessions_collection.find({
            **query,
            "stages.skill_relevance": {"$exists": True},
            "interview_started_at": {"$exists": True}
        }))
        
        durations = []
        for session in completed_sessions:
            started_at = session.get("interview_started_at")
            if started_at:
                if isinstance(started_at, str):
                    started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                
                # Trova timestamp skill_relevance (ultimo aggiornamento)
                stages = session.get("stages", {})
                skill_relevance = stages.get("skill_relevance", {})
                if skill_relevance:
                    # Usa timestamp di creazione del documento come proxy per completamento
                    # In realtà dovremmo avere un campo "completed_at" specifico
                    duration_minutes = (now - started_at).total_seconds() / 60
                    durations.append(duration_minutes)
        
        avg_interview_duration = sum(durations) / len(durations) if durations else 0
        
        # 5. TEMPO DI PRESA IN CARICO
        takeover_times = []
        for session in completed_sessions:
            token_sent_at = session.get("token_sent_at")
            if token_sent_at:
                if isinstance(token_sent_at, str):
                    token_sent_at = datetime.fromisoformat(token_sent_at.replace('Z', '+00:00'))
                
                # Calcola differenza tra invio token e completamento
                # Per ora usiamo timestamp attuale come proxy per completamento
                takeover_hours = (now - token_sent_at).total_seconds() / 3600
                takeover_times.append(takeover_hours)
        
        avg_takeover_time = sum(takeover_times) / len(takeover_times) if takeover_times else 0
        
        # 6-7. TASSO RECUPERO E UNDERPERFORMING
        sessions_with_scores = list(sessions_collection.find({
            **query,
            "stages.skill_relevance": {"$exists": True}
        }))
        
        recovery_count = 0
        underperforming_count = 0
        total_evaluated = len(sessions_with_scores)
        
        all_interview_scores = []
        all_cv_scores = []
        
        for session in sessions_with_scores:
            scores = session.get("stages", {}).get("skill_relevance", {}).get("scores", [])
            if scores:
                avg_cv = sum(s.get("cv_relevance_score", 0) for s in scores) / len(scores)
                avg_interview = sum(s.get("interview_relevance_score", 0) for s in scores) / len(scores)
                diff = avg_interview - avg_cv
                
                all_interview_scores.append(avg_interview)
                all_cv_scores.append(avg_cv)
                
                if diff >= 0.5:
                    recovery_count += 1
                elif diff <= -0.5:
                    underperforming_count += 1
        
        recovery_rate = (recovery_count / total_evaluated * 100) if total_evaluated > 0 else 0
        underperforming_rate = (underperforming_count / total_evaluated * 100) if total_evaluated > 0 else 0
        
        # 8-10. SCORING MEDI
        avg_interview_score = sum(all_interview_scores) / len(all_interview_scores) if all_interview_scores else 0
        avg_cv_score = sum(all_cv_scores) / len(all_cv_scores) if all_cv_scores else 0
        avg_overall_score = (avg_interview_score + avg_cv_score) / 2 if (all_interview_scores and all_cv_scores) else 0
        
        # Lista posizioni per filtro dropdown
        positions_data = list(positions_collection.find({}))
        positions = [{"id": p.get("_id"), "name": p.get("position_name", "Unknown")} for p in positions_data]
        
        print(f"📊 Dashboard metrics: {completed_interviews} completed, {waiting_token} waiting, {in_progress} in progress")
        print(f"📈 Recovery: {recovery_count} ({recovery_rate:.1f}%), Underperforming: {underperforming_count} ({underperforming_rate:.1f}%)")
        
        return {
            "metrics": {
                "completed_interviews": completed_interviews,
                "waiting_token": waiting_token,
                "in_progress": in_progress,
                "avg_interview_duration": round(avg_interview_duration, 1),
                "avg_takeover_time": round(avg_takeover_time, 1),
                "recovery_count": recovery_count,
                "recovery_rate": round(recovery_rate, 1),
                "underperforming_count": underperforming_count,
                "underperforming_rate": round(underperforming_rate, 1),
                "avg_interview_score": round(avg_interview_score, 2),
                "avg_cv_score": round(avg_cv_score, 2),
                "avg_overall_score": round(avg_overall_score, 2),
                "total_evaluated": total_evaluated
            },
            "positions": positions
        }
        
    except Exception as e:
        print(f"Error getting dashboard data for tenant {tenant_id}: {e}")
        return {
            "metrics": {
                "completed_interviews": 0,
                "waiting_token": 0,
                "in_progress": 0,
                "avg_interview_duration": 0,
                "avg_takeover_time": 0,
                "recovery_count": 0,
                "recovery_rate": 0,
                "underperforming_count": 0,
                "underperforming_rate": 0,
                "avg_interview_score": 0,
                "avg_cv_score": 0,
                "avg_overall_score": 0,
                "total_evaluated": 0
            },
            "positions": []
        }
