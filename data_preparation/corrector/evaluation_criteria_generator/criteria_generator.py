import json
import re
from typing import List
from pydantic import BaseModel, Field
from interviewer.llm_service import get_structured_llm_response, AZURE_DEPLOYMENT_NAME
from . import prompts_eval_criteria

class EvaluationCriterion(BaseModel):
    evaluation_criteria_1: str = Field(description="Criterio di valutazione per il requisito.")

class RequirementEvaluation(BaseModel):
    requirement: str = Field(description="Il requisito specifico estratto dall'ICP (es. 'Problem Solving', 'Conoscenza di Salesforce').")
    criteria: EvaluationCriterion = Field(description="Il criterio di valutazione associato a questo requisito.")

class EvaluationCriteriaCollection(BaseModel):
    evaluation_schema: List[RequirementEvaluation] = Field(description="Una lista completa dei requisiti e dei loro criteri di valutazione.")

GENERATION_MODEL = AZURE_DEPLOYMENT_NAME

def _is_likely_activity(requirement: str, language: str = "it") -> bool:
    """
    Valida se un requirement sembra essere un'attività invece di una skill.
    Usa pattern matching basato su parole chiave comuni.
    
    Returns:
        True se sembra un'attività (da scartare), False se sembra una skill valida
    """
    if not requirement:
        return False
    
    req_lower = requirement.lower().strip()
    
    # Pattern che indicano attività (cosa fare) invece di skill (cosa sapere)
    activity_patterns_it = [
        r'\b(sviluppare|sviluppo|creare|creazione|costruire|costruzione)\b',
        r'\b(gestire|gestione|amministrare|amministrazione)\b',
        r'\b(redigere|redazione|scrivere|scrittura|preparare|preparazione)\b',
        r'\b(partecipare|partecipazione|collaborare|collaborazione)\b',
        r'\b(coordinare|coordinamento|organizzare|organizzazione)\b',
        r'\b(analizzare|analisi|revisionare|revisione)\b',
        r'\b(riunioni|meeting|incontri)\b',
        r'\b(report|reportistica|documentazione)\b',
        r'\b(sarai|dovrai|ti occuperai|svolgerai|farai)\b',
        r'\b(responsabile di|responsabilità|compiti|attività)\b',
        r'\b(manutenzione|supporto|assistenza)\b',
    ]
    
    activity_patterns_en = [
        r'\b(develop|development|create|creation|build|building)\b',
        r'\b(manage|management|administer|administration)\b',
        r'\b(draft|drafting|write|writing|prepare|preparation)\b',
        r'\b(participate|participation|collaborate|collaboration)\b',
        r'\b(coordinate|coordination|organize|organization)\b',
        r'\b(analyze|analysis|review|reviewing)\b',
        r'\b(meetings|meeting|meet)\b',
        r'\b(report|reporting|documentation)\b',
        r'\b(you will|will be|will do|will handle|will perform)\b',
        r'\b(responsible for|responsibility|tasks|activities)\b',
        r'\b(maintenance|support|assistance)\b',
    ]
    
    patterns = activity_patterns_it if language == "it" else activity_patterns_en
    
    # Controlla se il requirement contiene pattern di attività
    for pattern in patterns:
        if re.search(pattern, req_lower):
            return True
    
    # Controlli aggiuntivi: se inizia con verbo all'infinito o imperativo, probabilmente è un'attività
    # (es. "Sviluppare applicazioni" vs "Conoscenza di Python")
    infinitive_verbs_it = ['sviluppare', 'gestire', 'creare', 'redigere', 'partecipare', 'coordinare', 
                          'analizzare', 'revisionare', 'organizzare', 'amministrare']
    infinitive_verbs_en = ['develop', 'manage', 'create', 'draft', 'participate', 'coordinate',
                           'analyze', 'review', 'organize', 'administer']
    
    verbs = infinitive_verbs_it if language == "it" else infinitive_verbs_en
    first_word = req_lower.split()[0] if req_lower.split() else ""
    
    if first_word in verbs:
        return True
    
    return False

def _validate_and_filter_requirements(collection: EvaluationCriteriaCollection, language: str = "it") -> EvaluationCriteriaCollection:
    """
    Valida e filtra i requisiti per rimuovere attività erroneamente classificate come requisiti.
    
    Returns:
        EvaluationCriteriaCollection filtrato con solo requisiti validi
    """
    original_count = len(collection.evaluation_schema)
    filtered_schema = []
    filtered_out = []
    
    for req_eval in collection.evaluation_schema:
        requirement = req_eval.requirement.strip()
        
        if _is_likely_activity(requirement, language):
            filtered_out.append(requirement)
            print(f"  - [VALIDATION] Scartato come attività (non requisito): '{requirement}'")
        else:
            filtered_schema.append(req_eval)
    
    if filtered_out:
        print(f"  - [VALIDATION] Filtro completato: {original_count} requisiti originali, "
              f"{len(filtered_schema)} requisiti validi, {len(filtered_out)} attività rimosse")
    else:
        print(f"  - [VALIDATION] Tutti i {original_count} requisiti sono validi (nessuna attività trovata)")
    
    return EvaluationCriteriaCollection(evaluation_schema=filtered_schema)

def generate_evaluation_criteria(icp_text: str, cases_json_str: str, seniority_level: str, hr_special_needs: str = "", language: str = "it", canonical_skills: list = None) -> EvaluationCriteriaCollection | None:
    """
    Genera i criteri di valutazione strutturati per i requisiti dell'ICP, integrando gli HR needs.
    
    Args:
        icp_text: Testo dell'ICP (per retrocompatibilità)
        cases_json_str: JSON dei case generati
        seniority_level: Livello di seniority
        hr_special_needs: Indicazioni speciali HR
        language: Lingua del prompt
        canonical_skills: Lista canonica delle skills (UNICA fonte di verità) - se fornita, genera criteri SOLO per queste skills
    """
    output_schema_example = EvaluationCriteriaCollection.model_json_schema()

    print("1. Creazione del prompt per la generazione dei criteri di valutazione...")
    prompt = prompts_eval_criteria.create_evaluation_criteria_prompt(
        icp_text, cases_json_str, seniority_level, json.dumps(output_schema_example, indent=2), hr_special_needs, language, canonical_skills=canonical_skills
    )

    print(f"2. Invio della richiesta al modello '{GENERATION_MODEL}'...")

    structured_response_str = get_structured_llm_response(
        prompt=prompt,
        model=GENERATION_MODEL,
        system_prompt=prompts_eval_criteria.SYSTEM_PROMPT[language],
        tool_name="save_evaluation_criteria",
        tool_schema=output_schema_example
    )

    if not structured_response_str:
        print("Errore critico: la chiamata all'LLM per i criteri di valutazione non ha restituito dati.")
        return None

    try:
        print("3. Output strutturato ricevuto, ora lo valido...")
        parsed_json = json.loads(structured_response_str)
        validated_data = EvaluationCriteriaCollection.model_validate(parsed_json)
        
        print("4. Validazione Pydantic completata. Applicazione filtro attività...")
        # Applica validazione post-estrazione per filtrare attività erroneamente classificate come requisiti
        filtered_data = _validate_and_filter_requirements(validated_data, language)
        
        # Se canonical_skills è fornita, valida che tutti i criteri corrispondano alle canonical skills
        if canonical_skills:
            print("5. Validazione coerenza con lista canonica skills...")
            canonical_skill_names = {skill['skill_name'].strip().lower() for skill in canonical_skills}
            canonical_skill_map = {skill['skill_name'].strip().lower(): skill['skill_name'] for skill in canonical_skills}
            
            validated_schema = []
            missing_skills = []
            invalid_skills = []
            created_default_criteria = []
            
            # Verifica che ogni canonical skill abbia un criterio corrispondente
            for canonical_skill in canonical_skills:
                skill_name_lower = canonical_skill['skill_name'].strip().lower()
                found = False
                for req_eval in filtered_data.evaluation_schema:
                    req_name_lower = req_eval.requirement.strip().lower()
                    if req_name_lower == skill_name_lower:
                        # Match esatto, normalizza il nome al canonical
                        req_eval.requirement = canonical_skill['skill_name']
                        validated_schema.append(req_eval)
                        found = True
                        break
                
                if not found:
                    # CREA automaticamente un criterio di default per questa skill canonica
                    missing_skills.append(canonical_skill['skill_name'])
                    print(f"    ⚠ Criterio mancante per skill canonica: '{canonical_skill['skill_name']}' - creazione criterio di default...")
                    
                    # Crea criterio di default nella stessa lingua del prompt
                    if language == "it":
                        default_criterion_text = f"Valutare la competenza del candidato in {canonical_skill['skill_name']} basandosi sulle evidenze emerse durante il colloquio e sui case study proposti."
                    else:
                        default_criterion_text = f"Evaluate the candidate's competence in {canonical_skill['skill_name']} based on evidence emerged during the interview and the proposed case studies."
                    
                    # Crea il criterio di default
                    default_criterion = EvaluationCriterion(evaluation_criteria_1=default_criterion_text)
                    default_req_eval = RequirementEvaluation(
                        requirement=canonical_skill['skill_name'],
                        criteria=default_criterion
                    )
                    validated_schema.append(default_req_eval)
                    created_default_criteria.append(canonical_skill['skill_name'])
                    print(f"    ✓ Criterio di default creato per: '{canonical_skill['skill_name']}'")
            
            # Verifica che non ci siano criteri per skill non canoniche
            for req_eval in filtered_data.evaluation_schema:
                req_name_lower = req_eval.requirement.strip().lower()
                if req_name_lower not in canonical_skill_names:
                    invalid_skills.append(req_eval.requirement)
                    print(f"    ⚠ Criterio per skill non canonica: '{req_eval.requirement}'")
                elif req_name_lower not in [r.requirement.strip().lower() for r in validated_schema]:
                    # Aggiungi solo se non è già stato aggiunto
                    req_eval.requirement = canonical_skill_map.get(req_name_lower, req_eval.requirement)
                    validated_schema.append(req_eval)
            
            if created_default_criteria:
                print(f"  ✓ Creati {len(created_default_criteria)} criteri di default per skill canoniche mancanti.")
            
            if invalid_skills:
                print(f"  ⚠ ATTENZIONE: {len(invalid_skills)} criteri per skill non canoniche (saranno scartati).")
            
            # Crea nuovo EvaluationCriteriaCollection con solo i criteri validati
            filtered_data.evaluation_schema = validated_schema
            print(f"  ✓ Validazione completata: {len(validated_schema)} criteri validi su {len(canonical_skills)} skill canoniche (garantita corrispondenza 1:1).")
        else:
            print("5. Criteri di valutazione validati e filtrati con successo (validazione canonical_skills saltata).")
        
        return filtered_data
    except Exception as e:
        print(f"Errore critico durante la validazione dei criteri di valutazione: {e}")
        return None