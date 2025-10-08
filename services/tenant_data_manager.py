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


def get_dashboard_data_tenant(tenant_id: str, time_range: str = "30d") -> dict:
    """Get comprehensive dashboard data for HR analytics"""
    if db is None:
        print(f"❌ Database not available for tenant {tenant_id}")
        return {}
    
    try:
        from datetime import datetime, timedelta
        import math
        
        print(f"📊 Getting dashboard data for tenant: {tenant_id}, time_range: {time_range}")
        
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
        
        # Overview metrics
        total_positions = positions_collection.count_documents({})
        total_sessions = sessions_collection.count_documents({})
        
        # Active sessions (incomplete)
        active_sessions = sessions_collection.count_documents({
            "status": {"$ne": "completed"}
        })
        
        # Completed sessions
        completed_sessions = sessions_collection.count_documents({
            "status": "completed"
        })
        
        # Total users
        total_users = users_collection.count_documents({
            "active": True
        })
        
        print(f"📈 Found: {total_positions} positions, {total_sessions} sessions, {completed_sessions} completed, {total_users} users")
        
        # Calculate average completion time
        completed_sessions_data = list(sessions_collection.find({
            "status": "completed",
            "created_at": {"$gte": start_date}
        }))
        
        avg_completion_time = 0
        if completed_sessions_data:
            total_time = 0
            for session in completed_sessions_data:
                created_at = session.get("created_at", now)
                completed_at = session.get("completed_at", now)
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                if isinstance(completed_at, str):
                    completed_at = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                duration = (completed_at - created_at).total_seconds() / 60  # minutes
                total_time += duration
            avg_completion_time = total_time / len(completed_sessions_data)
        
        # Position performance
        positions_data = list(positions_collection.find({}))
        position_performance = []
        
        for position in positions_data:
            position_id = position.get("_id")
            position_name = position.get("position_name", "Unknown")
            
            # Count sessions for this position
            position_sessions = list(sessions_collection.find({"position_id": position_id}))
            total_pos_sessions = len(position_sessions)
            completed_pos_sessions = len([s for s in position_sessions if s.get("status") == "completed"])
            
            # Calculate average score
            avg_score = 0
            if completed_pos_sessions > 0:
                total_score = 0
                score_count = 0
                for session in position_sessions:
                    if session.get("status") == "completed":
                        stages = session.get("stages", {})
                        skill_relevance = stages.get("skill_relevance", {})
                        if isinstance(skill_relevance, dict) and "overall_score" in skill_relevance:
                            total_score += skill_relevance["overall_score"]
                            score_count += 1
                if score_count > 0:
                    avg_score = total_score / score_count
            
            # Last activity
            last_activity = "N/A"
            if position_sessions:
                latest_session = max(position_sessions, key=lambda s: s.get("created_at", ""))
                if latest_session.get("created_at"):
                    try:
                        last_date = datetime.fromisoformat(latest_session["created_at"].replace('Z', '+00:00'))
                        last_activity = last_date.strftime("%d/%m")
                    except:
                        last_activity = "N/A"
            
            position_performance.append({
                "_id": position_id,
                "position_name": position_name,
                "totalSessions": total_pos_sessions,
                "completedSessions": completed_pos_sessions,
                "avgScore": avg_score,
                "lastActivity": last_activity
            })
        
        # Recent activity
        recent_sessions = list(sessions_collection.find({
            "created_at": {"$gte": start_date}
        }).sort("created_at", -1).limit(10))
        
        recent_activity = []
        for session in recent_sessions:
            position_id = session.get("position_id")
            position_name = "Unknown"
            if position_id:
                position_doc = positions_collection.find_one({"_id": position_id})
                if position_doc:
                    position_name = position_doc.get("position_name", "Unknown")
            
            # Determine activity type
            activity_type = "session_created"
            if session.get("status") == "completed":
                activity_type = "session_completed"
            elif session.get("stages", {}).get("feedback_pdf_path"):
                activity_type = "feedback_generated"
            elif session.get("token_sent"):
                activity_type = "token_sent"
            
            recent_activity.append({
                "type": activity_type,
                "session_id": session.get("_id"),
                "candidate_name": session.get("candidate_name", "Unknown"),
                "position_name": position_name,
                "timestamp": session.get("created_at", now.isoformat()),
                "user_name": session.get("token_sent_by")
            })
        
        # Performance metrics
        completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        # Calculate average interview duration (from conversation data)
        interview_durations = []
        for session in completed_sessions_data:
            stages = session.get("stages", {})
            conversation = stages.get("conversation", [])
            if conversation and len(conversation) > 1:
                # More accurate estimation based on conversation length and complexity
                message_count = len(conversation)
                # Estimate: 1-2 minutes per message exchange (question + answer)
                # More messages = more complex interview = longer duration
                if message_count <= 5:
                    duration = message_count * 1.5  # Short interviews
                elif message_count <= 10:
                    duration = message_count * 2.0  # Medium interviews
                else:
                    duration = message_count * 2.5  # Long interviews
                interview_durations.append(duration)
        
        avg_interview_duration = sum(interview_durations) / len(interview_durations) if interview_durations else 0
        
        # Calculate real feedback generation time
        feedback_times = []
        for session in completed_sessions_data:
            stages = session.get("stages", {})
            if stages.get("feedback_pdf_path"):
                # Estimate feedback generation time based on when feedback was generated
                # This is a rough estimate - in a real system you'd track actual timestamps
                feedback_times.append(3)  # Assume 3 minutes average
        
        feedback_generation_time = sum(feedback_times) / len(feedback_times) if feedback_times else 0
        
        # Calculate real token usage rate
        total_tokens_issued = sessions_collection.count_documents({})
        tokens_used = sessions_collection.count_documents({
            "token_sent": True
        })
        token_usage_rate = (tokens_used / total_tokens_issued * 100) if total_tokens_issued > 0 else 0
        
        # Skill analytics
        skill_analytics = []
        all_skills = {}
        
        for session in completed_sessions_data:
            stages = session.get("stages", {})
            skill_relevance = stages.get("skill_relevance", {})
            if isinstance(skill_relevance, dict) and "skill_scores" in skill_relevance:
                skill_scores = skill_relevance["skill_scores"]
                if isinstance(skill_scores, dict):
                    for skill, score in skill_scores.items():
                        if skill not in all_skills:
                            all_skills[skill] = {"scores": [], "count": 0}
                        all_skills[skill]["scores"].append(score)
                        all_skills[skill]["count"] += 1
        
        for skill, data in all_skills.items():
            if data["count"] > 0:
                avg_score = sum(data["scores"]) / len(data["scores"])
                skill_analytics.append({
                    "skill": skill,
                    "avgScore": avg_score,
                    "frequency": data["count"],
                    "trend": "stable"  # Could be enhanced with historical data
                })
        
        # Sort by frequency and take top 10
        skill_analytics.sort(key=lambda x: x["frequency"], reverse=True)
        skill_analytics = skill_analytics[:10]
        
        # Monthly trends - use real data from database
        monthly_trends = []
        months = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
        
        # Get sessions from the last 6 months
        for i in range(6):
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30*i)
            if i == 0:
                month_end = now
            else:
                month_end = month_start + timedelta(days=30)
            
            # Count sessions in this month
            month_sessions = list(sessions_collection.find({
                "created_at": {
                    "$gte": month_start.isoformat(),
                    "$lt": month_end.isoformat()
                }
            }))
            
            sessions_count = len(month_sessions)
            completions_count = len([s for s in month_sessions if s.get("status") == "completed"])
            
            # Calculate average score for this month
            avg_score = 0
            if completions_count > 0:
                total_score = 0
                score_count = 0
                for session in month_sessions:
                    if session.get("status") == "completed":
                        stages = session.get("stages", {})
                        skill_relevance = stages.get("skill_relevance", {})
                        if isinstance(skill_relevance, dict) and "overall_score" in skill_relevance:
                            total_score += skill_relevance["overall_score"]
                            score_count += 1
                if score_count > 0:
                    avg_score = total_score / score_count
            
            month_name = months[month_start.month - 1]
            
            monthly_trends.append({
                "month": month_name,
                "sessions": sessions_count,
                "completions": completions_count,
                "avgScore": avg_score
            })
        
        monthly_trends.reverse()  # Show oldest to newest
        
        return {
            "overview": {
                "totalPositions": total_positions,
                "totalSessions": total_sessions,
                "activeSessions": active_sessions,
                "completedSessions": completed_sessions,
                "totalUsers": total_users,
                "avgCompletionTime": avg_completion_time
            },
            "positions": position_performance,
            "recentActivity": recent_activity,
            "performanceMetrics": {
                "completionRate": completion_rate,
                "avgInterviewDuration": avg_interview_duration,
                "feedbackGenerationTime": feedback_generation_time,
                "tokenUsageRate": token_usage_rate
            },
            "skillAnalytics": skill_analytics,
            "monthlyTrends": monthly_trends
        }
        
    except Exception as e:
        print(f"Error getting dashboard data for tenant {tenant_id}: {e}")
        return {}
