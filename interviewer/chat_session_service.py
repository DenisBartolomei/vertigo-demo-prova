import random
from typing import Optional, Dict, Any

from services.data_manager import (
    get_single_position_data_from_db,
    save_stage_output,
    get_session_data,
)
from services.tenant_data_manager import (
    get_single_position_data_tenant,
    save_stage_output_tenant,
    get_session_data_tenant,
)
from services.tenant_service import get_tenant_collections
from .chatbot import SmartCaseStudyChatbot


_SESSION_CHATBOTS: dict[str, SmartCaseStudyChatbot] = {}


def initialize_chatbot_for_session(session_id: str, tenant_id: str = None) -> Optional[Dict[str, Any]]:
    if tenant_id:
        collections = get_tenant_collections(tenant_id)
        sess = get_session_data_tenant(session_id, collections["sessions"])
        position_id = sess.get("position_id") if sess else None
        if not position_id:
            return None
        position_data = get_single_position_data_tenant(position_id, collections["positions"])
    else:
        # Fallback to global collections for backward compatibility
        sess = get_session_data(session_id)
        if not sess:
            return None
        position_id = sess.get("position_id")
        if not position_id:
            return None
        position_data = get_single_position_data_from_db(position_id)
    
    if not position_data:
        return None

    all_cases = (position_data or {}).get("all_cases", {}).get("cases", [])
    all_criteria = (position_data or {}).get("all_criteria", {}).get("criteria_sets", [])
    if not all_cases:
        return None

    selected_case = random.choice(all_cases)
    selected_case_id = selected_case.get("question_id")
    if not selected_case_id:
        return None

    selected_criteria_set = next((c for c in all_criteria if c.get("question_id") == selected_case_id), None)
    steps_dict = {step["id"]: step for step in selected_case.get("reasoning_steps", [])}
    for criterion in (selected_criteria_set or {}).get("accomplishment_criteria", []):
        sid = criterion.get("step_id")
        if sid in steps_dict:
            steps_dict[sid]["criteria"] = criterion.get("criteria")

    chatbot = SmartCaseStudyChatbot(
        steps=steps_dict,
        case_title=selected_case.get("question_title", ""),
        case_text=selected_case.get("question_text", ""),
        case_id=selected_case_id,
    )
    _SESSION_CHATBOTS[session_id] = chatbot

    seniority = position_data.get("seniority_level", "Mid-Level")
    if tenant_id:
        collections = get_tenant_collections(tenant_id)
        save_stage_output_tenant(session_id, "case_id", selected_case_id, collections["sessions"])
        save_stage_output_tenant(session_id, "seniority_level", seniority, collections["sessions"])
    else:
        save_stage_output(session_id, "case_id", selected_case_id)
        save_stage_output(session_id, "seniority_level", seniority)
    return {"case_id": selected_case_id, "seniority_level": seniority}


def _get_chatbot(session_id: str) -> SmartCaseStudyChatbot | None:
    return _SESSION_CHATBOTS.get(session_id)


def start_interview_for_session(session_id: str, tenant_id: str = None) -> str:
    bot = _get_chatbot(session_id)
    if not bot:
        meta = initialize_chatbot_for_session(session_id, tenant_id)
        if not meta:
            raise ValueError("Chatbot not initialized")
        bot = _get_chatbot(session_id)
    message = bot.start_interview()
    return message


def send_message_for_session(session_id: str, text: str, tenant_id: str = None) -> str:
    bot = _get_chatbot(session_id)
    if not bot:
        raise ValueError("Chatbot not initialized")
    
    # Check if interview was finished before processing this message
    was_finished = bot.is_finished
    
    reply = bot.process_user_response(text)
    
    # Persist rolling conversation
    if tenant_id:
        collections = get_tenant_collections(tenant_id)
        save_stage_output_tenant(session_id, "conversation", bot.conversation_history, collections["sessions"])
    else:
        save_stage_output(session_id, "conversation", bot.conversation_history)
    
    # If interview just finished, trigger automatic evaluation in background
    if not was_finished and bot.is_finished:
        print(f"Interview completed for session {session_id}, starting automatic evaluation in background...")
        
        # Run evaluation in background thread to avoid blocking the response
        import threading
        def run_evaluation_background():
            try:
                # Import here to avoid circular imports
                from corrector.run_final_evaluation import execute_case_evaluation
                from corrector.skill_relevance_scorer import compute_and_save_skill_relevance
                
                # Add a small delay to ensure database consistency
                import time
                time.sleep(2)  # Wait 2 seconds for database to be consistent
                
                # Run evaluation with tenant_id if available
                if tenant_id:
                    eval_success = execute_case_evaluation(session_id=session_id, tenant_id=tenant_id)
                else:
                    eval_success = execute_case_evaluation(session_id=session_id)
                    
                if eval_success:
                    print(f"Case evaluation completed for session {session_id}")
                    # Run skill relevance scoring with tenant_id if available
                    if tenant_id:
                        compute_and_save_skill_relevance(session_id=session_id, tenant_id=tenant_id)
                    else:
                        compute_and_save_skill_relevance(session_id=session_id)
                    print(f"Skill relevance scoring completed for session {session_id}")
                else:
                    print(f"Case evaluation failed for session {session_id}")
            except Exception as e:
                print(f"Error during automatic evaluation for session {session_id}: {e}")
        
        # Start evaluation in background thread
        evaluation_thread = threading.Thread(target=run_evaluation_background)
        evaluation_thread.daemon = True
        evaluation_thread.start()
    
    return reply


def get_interview_state(session_id: str, tenant_id: str = None) -> Dict[str, Any]:
    bot = _get_chatbot(session_id)
    if not bot:
        raise ValueError("Chatbot not initialized")
    remaining = bot.MAX_QUESTIONS - bot.questions_asked_count
    return {
        "finished": bot.is_finished,
        "remaining_questions": remaining,
        "history_len": len(bot.conversation_history),
        "conversation": bot.conversation_history,  # Include full conversation for frontend
    }


