# corrector/skill_relevance_scorer.py

import json
import re
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from difflib import SequenceMatcher
from interviewer.llm_service import get_structured_llm_response
from services.data_manager import db, get_session_data, save_stage_output
from services.tenant_data_manager import get_session_data_tenant, save_stage_output_tenant
from services.tenant_service import get_tenant_collections
from .prompts_skill_scorer import create_cv_scoring_prompt, create_interview_scoring_prompt
from interviewer.llm_service import AZURE_DEPLOYMENT_NAME

SKILL_SCORER_MODEL = AZURE_DEPLOYMENT_NAME
SKILL_SCORING_TEMPERATURE = 0.0

# ----- Schemi Pydantic per le tool call -----

class CVSkillScore(BaseModel):
    skill_id: str
    skill_name: str
    cv_relevance_score: int = Field(ge=0, le=4)
    notes_cv: Optional[str] = None

class CVScoreCollection(BaseModel):
    scores: List[CVSkillScore]

class InterviewSkillScore(BaseModel):
    skill_id: str
    skill_name: str
    interview_relevance_score: int = Field(ge=0, le=4)
    notes_interview: Optional[str] = None

class InterviewScoreCollection(BaseModel):
    scores: List[InterviewSkillScore]

class SkillScore(BaseModel):
    skill_id: str
    skill_name: str
    cv_relevance_score: int = Field(ge=0, le=4)
    interview_relevance_score: int = Field(ge=0, le=4)
    notes_cv: Optional[str] = None
    notes_interview: Optional[str] = None

class SkillScoreCollection(BaseModel):
    position_id: str
    scores: List[SkillScore]


# ----- Utils -----

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s\-_/]", "", text)
    text = re.sub(r"[\s/_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")

def _normalize_skill_name(skill_name: str) -> str:
    """
    Normalizza il nome di una skill per il matching:
    - Rimuove spazi extra
    - Converte in lowercase
    - Rimuove punteggiatura comune
    - Standardizza caratteri speciali
    """
    if not skill_name:
        return ""
    
    # Normalizza spazi e converte in lowercase
    normalized = re.sub(r'\s+', ' ', skill_name.strip().lower())
    
    # Rimuove punteggiatura comune che può variare
    normalized = re.sub(r'[,;:\.]+', '', normalized)
    
    # Standardizza parentesi e caratteri speciali
    normalized = re.sub(r'[()\[\]{}]', '', normalized)
    
    return normalized.strip()

def _find_best_skill_match(skill_name: str, requirements: List[str], threshold: float = 0.9) -> Optional[str]:
    """
    Trova il miglior match per una skill tra i requirements usando similarity ratio.
    Restituisce il requirement che ha la similarity più alta >= threshold, o None se nessuno supera la soglia.
    """
    if not skill_name or not requirements:
        return None
    
    normalized_skill = _normalize_skill_name(skill_name)
    best_match = None
    best_ratio = 0.0
    
    for req in requirements:
        if not req:
            continue
            
        normalized_req = _normalize_skill_name(req)
        
        # Calcola similarity ratio
        ratio = SequenceMatcher(None, normalized_skill, normalized_req).ratio()
        
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = req
    
    return best_match

def _format_conversation(conversation_history: List[dict]) -> str:
    lines = []
    for m in conversation_history:
        role = "Candidato" if m.get("role") == "user" else "Intervistatore (Vertigo)"
        lines.append(f"[{role}]: {m.get('content','')}")
    return "\n\n".join(lines)

def _build_case_map_text(caso_svolto_data: dict) -> str:
    map_lines = ["[MAPPA DI VALUTAZIONE DEL CASO SVOLTO]"]
    for step in caso_svolto_data.get("reasoning_steps", []):
        skills = ", ".join([s.get("skill_name", "N/A") for s in step.get("skills_to_test", [])])
        map_lines.append(f"- Step {step.get('id','N/A')} ({step.get('title','N/A')}): Progettato per testare '{skills}'.")
    return "\n".join(map_lines)

def _extract_skills_from_case(caso_svolto_data: dict, position_data: dict) -> List[dict]:
    """
    Estrae le skill effettivamente testate nel caso selezionato dai reasoning steps.
    Ogni item contiene: skill_id, skill_name, criteria_texts (lista con 2 stringhe).
    Usa matching fuzzy per gestire piccole differenze nei nomi delle skill.
    """
    # Estrai tutte le skill uniche testate nel caso
    tested_skills = set()
    for step in caso_svolto_data.get("reasoning_steps", []):
        for skill_test in step.get("skills_to_test", []):
            skill_name = skill_test.get("skill_name", "").strip()
            if skill_name:
                tested_skills.add(skill_name)
    
    print(f"  - [SKILL EXTRACTOR] Trovate {len(tested_skills)} skill uniche nel caso:")
    for skill in tested_skills:
        print(f"    * {skill}")
    
    # Trova i criteri di valutazione per le skill testate
    eval_criteria = position_data.get("evaluation_criteria", {})
    schema = eval_criteria.get("evaluation_schema", [])
    
    # Estrai tutti i requirements disponibili per il matching
    available_requirements = [item.get("requirement", "").strip() for item in schema if item.get("requirement")]
    print(f"  - [SKILL EXTRACTOR] Trovati {len(available_requirements)} requirements nell'ICP")
    
    canonical = []
    matched_skills = set()
    unmatched_skills = []
    
    for skill_name in tested_skills:
        # Prima prova matching esatto
        exact_match = None
        for item in schema:
            req = item.get("requirement", "").strip()
            if req == skill_name:
                exact_match = item
                break
        
        if exact_match:
            # Match esatto trovato
            crit = exact_match.get("criteria", {})
            c1 = crit.get("evaluation_criteria_1") or ""
            c2 = crit.get("evaluation_criteria_2") or ""
            canonical.append({
                "skill_id": _slugify(skill_name),
                "skill_name": skill_name,
                "criteria_texts": [c1, c2]
            })
            matched_skills.add(skill_name)
            print(f"    ✓ Match esatto: '{skill_name}' -> '{exact_match.get('requirement')}'")
        else:
            # Prova matching fuzzy
            best_match_req = _find_best_skill_match(skill_name, available_requirements, threshold=0.9)
            if best_match_req:
                # Trova l'item corrispondente
                for item in schema:
                    if item.get("requirement", "").strip() == best_match_req:
                        crit = item.get("criteria", {})
                        c1 = crit.get("evaluation_criteria_1") or ""
                        c2 = crit.get("evaluation_criteria_2") or ""
                        canonical.append({
                            "skill_id": _slugify(skill_name),
                            "skill_name": skill_name,
                            "criteria_texts": [c1, c2]
                        })
                        matched_skills.add(skill_name)
                        print(f"    ✓ Match fuzzy: '{skill_name}' -> '{best_match_req}'")
                        break
            else:
                # Nessun match trovato - includi comunque con criteri vuoti
                canonical.append({
                    "skill_id": _slugify(skill_name),
                    "skill_name": skill_name,
                    "criteria_texts": ["", ""]
                })
                unmatched_skills.append(skill_name)
                print(f"    ⚠ Nessun match: '{skill_name}' (inclusa con criteri vuoti)")
    
    print(f"  - [SKILL EXTRACTOR] Risultato: {len(matched_skills)} skill matchate, {len(unmatched_skills)} senza match")
    if unmatched_skills:
        print(f"    Skill senza match: {unmatched_skills}")
    
    return canonical

def _extract_canonical_skills(position_data: dict) -> List[dict]:
    """
    Estrae la lista canonica delle skill dai criteri di valutazione finali (evaluation_criteria.evaluation_schema).
    Ogni item contiene: skill_id, skill_name, criteria_texts (lista con 2 stringhe).
    
    DEPRECATED: Usa _extract_skills_from_case per estrarre solo le skill testate nel caso.
    """
    eval_criteria = position_data.get("evaluation_criteria", {})
    schema = eval_criteria.get("evaluation_schema", [])
    canonical = []
    for item in schema:
        req = item.get("requirement") or ""
        crit = item.get("criteria", {})
        c1 = crit.get("evaluation_criteria_1") or ""
        c2 = crit.get("evaluation_criteria_2") or ""
        if not req:
            continue
        canonical.append({
            "skill_id": _slugify(req),
            "skill_name": req,
            "criteria_texts": [c1, c2]
        })
    return canonical

def _canonical_skilllist_as_json(canonical_skills: List[dict]) -> str:
    """
    Prepara un JSON compatto con campi necessari al prompt:
    - skill_id, skill_name, criteria_texts[2]
    """
    payload = {"skills": canonical_skills}
    return json.dumps(payload, ensure_ascii=False, indent=2)

# ----- Scoring -----

def _score_cv_relevance(cv_text: str, canonical_skills: List[dict]) -> Dict[str, dict]:
    if not cv_text or not canonical_skills:
        return {}
    skill_list_json = _canonical_skilllist_as_json(canonical_skills)
    prompt = create_cv_scoring_prompt(skill_list_json, cv_text)

    tool_args = get_structured_llm_response(
        prompt=prompt,
        model=SKILL_SCORER_MODEL,
        system_prompt=(
            "Sei un valutatore HR rigoroso. Applica sempre la stessa rubrica e restituisci un output JSON per TUTTE le skill, "
            "senza ometterne nessuna e mantenendo l'ordine. Vietato inventare evidenze. "
            "Usa i 'criteria_texts' come estratti dalla rubrica 'evaluation_criteria'; se mancanti per una skill, valuta comunque."
        ),
        tool_name="save_cv_skill_scores",
        tool_schema=CVScoreCollection.model_json_schema(),
        temperature=SKILL_SCORING_TEMPERATURE,
        max_tokens=1800
    )
    if not tool_args:
        print("  - [Skill Scorer] Nessuna risposta strutturata per CV.")
        return {}
    try:
        parsed = json.loads(tool_args)
        validated = CVScoreCollection.model_validate(parsed)
        out = {}
        for s in validated.scores:
            out[s.skill_id] = {"score": s.cv_relevance_score, "notes": s.notes_cv or ""}
        return out
    except Exception as e:
        print(f"  - [Skill Scorer] Errore validando CV score: {e}")
        return {}

def _score_interview_relevance(conversation_json: List[dict], canonical_skills: List[dict], case_map_text: str) -> Dict[str, dict]:
    if not conversation_json or not canonical_skills:
        return {}
    conversation_text = _format_conversation(conversation_json)
    skill_list_json = _canonical_skilllist_as_json(canonical_skills)
    prompt = create_interview_scoring_prompt(skill_list_json, conversation_text, case_map_text)

    tool_args = get_structured_llm_response(
        prompt=prompt,
        model=SKILL_SCORER_MODEL,
        system_prompt=(
            "Sei un valutatore HR rigoroso. Applica sempre la stessa rubrica e restituisci un output JSON per TUTTE le skill, "
            "senza ometterne nessuna e mantenendo l'ordine. Pesa gli step che testano esplicitamente la skill. Vietato inventare evidenze. "
            "Usa i 'criteria_texts' come estratti dalla rubrica 'evaluation_criteria'; se mancanti per una skill, valuta comunque."
        ),
        tool_name="save_interview_skill_scores",
        tool_schema=InterviewScoreCollection.model_json_schema(),
        temperature=SKILL_SCORING_TEMPERATURE,
        max_tokens=2200
    )
    if not tool_args:
        print("  - [Skill Scorer] Nessuna risposta strutturata per colloquio.")
        return {}
    try:
        parsed = json.loads(tool_args)
        validated = InterviewScoreCollection.model_validate(parsed)
        out = {}
        for s in validated.scores:
            out[s.skill_id] = {"score": s.interview_relevance_score, "notes": s.notes_interview or ""}
        return out
    except Exception as e:
        print(f"  - [Skill Scorer] Errore validando interview score: {e}")
        return {}

# ----- Orchestratore -----

def compute_and_save_skill_relevance(session_id: str, tenant_id: str = None) -> bool:
    """
    Orchestrazione:
    - legge sessione e dati posizione
    - costruisce skill canoniche (stabili per posizione) dalla rubrica evaluation_criteria
    - calcola punteggi CV e colloquio
    - salva in stages.skill_relevance
    """
    print(f"--- [SKILL SCORER] Avvio calcolo rilevanza skill per sessione: {session_id} ---")
    if tenant_id:
        collections = get_tenant_collections(tenant_id)
        session = get_session_data_tenant(session_id, collections["sessions"])
    else:
        session = get_session_data(session_id)
    if not session:
        print("  - ERRORE: sessione non trovata.")
        return False

    position_id = session.get("position_id")
    stages = session.get("stages", {})
    cv_text = stages.get("uploaded_cv_text", "")
    conversation_json = stages.get("conversation", [])

    if db is None:
        print("  - ERRORE: DB non disponibile.")
        return False

    # Carica posizione completa
    if tenant_id and collections:
        positions_collection = db[collections["positions"]]
    else:
        positions_collection = db["positions_data"]
    position_data = positions_collection.find_one({"_id": position_id})
    if not position_data:
        print(f"  - ERRORE: posizione '{position_id}' non trovata.")
        return False

    # Mappa del caso selezionato (se disponibile)
    case_map_text = ""
    caso_svolto_data = None
    try:
        selected_case_id = stages.get("case_id")
        all_cases_data = position_data.get("all_cases", {})
        caso_svolto_data = next((case for case in all_cases_data.get("cases", []) if case.get("question_id") == selected_case_id), None)
        if caso_svolto_data:
            case_map_text = _build_case_map_text(caso_svolto_data)
    except Exception:
        case_map_text = ""

    # Skill canoniche: usa le skill effettivamente testate nel caso selezionato
    if caso_svolto_data:
        canonical_skills = _extract_skills_from_case(caso_svolto_data, position_data)
        print(f"  - [SKILL SCORER] Estratte {len(canonical_skills)} skill testate nel caso selezionato.")
        if not canonical_skills:
            print("  - WARNING: Nessuna skill testata trovata nel caso. Usando tutte le skill dell'ICP come fallback.")
            canonical_skills = _extract_canonical_skills(position_data)
    else:
        print("  - WARNING: Caso selezionato non trovato. Usando tutte le skill dell'ICP.")
        canonical_skills = _extract_canonical_skills(position_data)
    
    if not canonical_skills:
        print("  - ERRORE: 'evaluation_criteria.evaluation_schema' non trovato o vuoto. Impossibile stabilire le skill canoniche.")
        return False

    # Scoring CV
    cv_scores_map = _score_cv_relevance(cv_text, canonical_skills) if cv_text else {}
    # Scoring colloquio
    interview_scores_map = _score_interview_relevance(conversation_json, canonical_skills, case_map_text) if conversation_json else {}

    # Merge risultati in ordine canonico
    final_scores: List[SkillScore] = []
    for item in canonical_skills:
        sid = item["skill_id"]
        sname = item["skill_name"]
        cv_score = cv_scores_map.get(sid, {}).get("score", 0)
        cv_notes = cv_scores_map.get(sid, {}).get("notes", "")
        int_score = interview_scores_map.get(sid, {}).get("score", 0)
        int_notes = interview_scores_map.get(sid, {}).get("notes", "")
        final_scores.append(SkillScore(
            skill_id=sid,
            skill_name=sname,
            cv_relevance_score=int(cv_score),
            interview_relevance_score=int(int_score),
            notes_cv=cv_notes or None,
            notes_interview=int_notes or None
        ))

    collection_obj = SkillScoreCollection(position_id=position_id, scores=final_scores)
    if tenant_id and collections:
        save_stage_output_tenant(session_id, "skill_relevance", collection_obj.model_dump(), collections["sessions"])
    else:
        save_stage_output(session_id, "skill_relevance", collection_obj.model_dump())
    print(f"  - [SKILL SCORER] Completato e salvato per sessione {session_id}.")
    
    # GENERAZIONE FEEDBACK TEMPORANEAMENTE DISABILITATA PER TEST
    print(f"  - [SKILL SCORER] Pipeline di feedback DISABILITATA per test")
    
    return True