import json
import re
from typing import List
from pydantic import BaseModel, Field
from interviewer.llm_service import get_structured_llm_response
from . import prompts_final
from interviewer.llm_service import AZURE_DEPLOYMENT_NAME
from utils.json_toon_converter import convert_json_to_toon

def _normalize_skill_name(skill_name: str) -> str:
    """
    Normalizza il nome di una skill rimuovendo suffissi comuni come "(technical)" o "(soft)".
    
    Args:
        skill_name: Nome della skill da normalizzare
    
    Returns:
        Nome normalizzato (lowercase, senza spazi extra, senza suffissi tra parentesi)
    """
    if not skill_name:
        return ""
    
    # Rimuovi spazi extra e converti in lowercase
    normalized = skill_name.strip().lower()
    
    # Rimuovi pattern comuni come "(technical)", "(soft)", "(technical skill)", etc.
    # Pattern regex per rimuovere parentesi con contenuto
    normalized = re.sub(r'\s*\([^)]*\)\s*$', '', normalized)
    
    # Rimuovi spazi extra finali
    normalized = normalized.strip()
    
    return normalized

class SkillToTest(BaseModel):
    skill_name: str = Field(description="Il nome della skill o competenza da verificare (es. 'Problem Solving', 'Python').")
    testing_method: str = Field(description="Breve descrizione di come lo step può essere usato per valutare questa specifica skill.")

class ReasoningStep(BaseModel):
    id: int = Field(description="ID numerico progressivo dello step, partendo da 0.")
    title: str = Field(description="Titolo breve e descrittivo dello step di ragionamento.")
    description: str = Field(description="Descrizione dettagliata dello step o domanda da porre al candidato.")
    skills_to_test: List[SkillToTest] = Field(description="Una lista di 2-5 skill che possono essere verificate in questo step.", max_items=5)

class CaseStructure(BaseModel):
    question_id: str = Field(description="ID univoco per il caso, es. 'case-pm-01'.")
    question_title: str = Field(description="Titolo principale del caso di studio.")
    question_text: str = Field(description="Testo narrativo completo che introduce il problema e l'obiettivo del caso.")
    reasoning_steps: List[ReasoningStep] = Field(description="Lista di reasoning steps che decompongono la soluzione.")

class CaseCollection(BaseModel):
    cases: List[CaseStructure] = Field(description="Una lista contenente esattamente 5 casi di studio.")

FINAL_MODEL = AZURE_DEPLOYMENT_NAME

def generate_final_cases(icp_text: str, guide_text: str, kb_summary: str, seniority_level: str, reasoning_steps: int, hr_special_needs: str = "", language: str = "it", canonical_skills: list = None) -> CaseCollection | None:
    """
    Genera una collezione di 5 casi di studio strutturati in formato JSON.
    Integra le Indicazioni HR nella generazione.
    reasoning_steps: Numero di reasoning steps richiesti dall'HR (il sistema aggiungerà automaticamente lo step 0)
    canonical_skills: Lista canonica delle skills (UNICA fonte di verità) - se None, non viene validata
    """
    # Calcola quante skill devono essere distribuite
    total_skills = len(canonical_skills) if canonical_skills else 0
    total_steps_per_case = reasoning_steps + 1  # +1 per step 0
    total_steps_all_cases = 5 * total_steps_per_case  # 5 case
    
    # Calcola skills per step (minimo per coprire tutto, massimo 5)
    if total_skills > 0 and total_steps_all_cases > 0:
        # Calcola il minimo necessario per coprire tutte le skill
        min_skills_per_step = max(2, (total_skills + total_steps_all_cases - 1) // total_steps_all_cases)  # Arrotondamento per eccesso
        min_skills_per_step = min(min_skills_per_step, 5)  # Max 5
        # Assicurati che con questo minimo si coprano tutte le skill
        if min_skills_per_step * total_steps_all_cases < total_skills:
            min_skills_per_step = min(5, min_skills_per_step + 1)
    else:
        min_skills_per_step = 2
    
    # Crea esempio con più skills (3) per mostrare la varietà e incoraggiare l'uso di più skill
    example_skills = [
        SkillToTest(skill_name="Esempio Skill 1", testing_method="Metodo di test per skill 1"),
        SkillToTest(skill_name="Esempio Skill 2", testing_method="Metodo di test per skill 2"),
        SkillToTest(skill_name="Esempio Skill 3", testing_method="Metodo di test per skill 3"),
    ]
    example_step = {
        "id": 0, 
        "title": "Titolo Esempio Step", 
        "description": "Descrizione Esempio Step",
        "skills_to_test": [skill.model_dump() for skill in example_skills]
    }
    example_case = {
        "question_id": "case-example-01", 
        "question_title": "Titolo Esempio Caso",
        "question_text": "Testo Esempio Caso", 
        "reasoning_steps": [example_step]
    }
    example_collection = {"cases": [example_case]}
    json_example_str = json.dumps(example_collection, indent=2)
    
    # Converti a TOON per il prompt
    try:
        example_toon_str = convert_json_to_toon(json_example_str)
    except Exception as e:
        print(f"⚠ ERRORE durante conversione TOON esempio: {e}, uso JSON originale")
        example_toon_str = json_example_str

    print("1. Creazione del prompt finale con esempio strutturato...")
    if total_skills > 0:
        print(f"   - Skill canoniche da distribuire: {total_skills}")
        print(f"   - Reasoning steps totali (5 case × {total_steps_per_case} step): {total_steps_all_cases}")
        print(f"   - Minimo skill per step consigliato: {min_skills_per_step}")
    
    final_prompt = prompts_final.create_final_case_prompt(
        icp_text, guide_text, kb_summary, seniority_level, example_toon_str, hr_special_needs, reasoning_steps, language, canonical_skills=canonical_skills, min_skills_per_step=min_skills_per_step, total_skills=total_skills
    )

    print(f"2. Invio della richiesta al modello '{FINAL_MODEL}' per la generazione strutturata...")

    tool_call_args = get_structured_llm_response(
        prompt=final_prompt,
        model=FINAL_MODEL,
        system_prompt=prompts_final.SYSTEM_PROMPT[language],
        tool_name="save_generated_cases",
        tool_schema=CaseCollection.model_json_schema(),
        max_tokens=8000,  # Aumentato per evitare troncamento del JSON (5 casi con reasoning steps possono essere molto lunghi)
        temperature=0.4
    )

    if not tool_call_args:
        print("Errore critico: la chiamata all'LLM per i casi non ha restituito dati.")
        return None

    try:
        print("3. Output strutturato ricevuto, ora lo valido...")
        print(f"  - Lunghezza risposta: {len(tool_call_args)} caratteri")
        
        # Prova a fare il parsing del JSON
        try:
            parsed_json = json.loads(tool_call_args)
        except json.JSONDecodeError as json_err:
            print(f"  ✗ Errore parsing JSON: {json_err}")
            print(f"  - Messaggio: {json_err.msg}")
            if hasattr(json_err, 'lineno') and json_err.lineno:
                print(f"  - Posizione errore: linea {json_err.lineno}, colonna {json_err.colno if hasattr(json_err, 'colno') else 'N/A'}")
            
            # Prova a estrarre un frammento del JSON intorno all'errore per debugging
            error_pos = getattr(json_err, 'pos', 0)
            start = max(0, error_pos - 200)
            end = min(len(tool_call_args), error_pos + 200)
            snippet = tool_call_args[start:end]
            print(f"  - Frammento JSON intorno all'errore (posizione {error_pos}):")
            print(f"    ...{snippet}...")
            
            # Prova a "riparare" il JSON se possibile (rimuove caratteri non validi comuni)
            print("  - Tentativo di riparazione automatica del JSON...")
            try:
                cleaned_json = tool_call_args
                
                # Rimuovi eventuali BOM o caratteri invisibili
                cleaned_json = cleaned_json.replace('\ufeff', '').replace('\u200b', '')
                
                # Rimuovi eventuali caratteri di controllo non validi (mantieni solo caratteri stampabili e whitespace)
                import string
                printable_chars = set(string.printable)
                cleaned_chars = []
                for char in cleaned_json:
                    if char in printable_chars or ord(char) > 127:  # Permetti anche caratteri Unicode
                        cleaned_chars.append(char)
                    else:
                        # Sostituisci caratteri di controllo con spazio
                        cleaned_chars.append(' ')
                cleaned_json = ''.join(cleaned_chars)
                
                # Prova a trovare l'ultima parentesi graffa chiusa valida se il JSON è troncato
                if cleaned_json.count('{') > cleaned_json.count('}'):
                    # JSON potrebbe essere troncato, prova ad aggiungere parentesi mancanti
                    missing_braces = cleaned_json.count('{') - cleaned_json.count('}')
                    # Trova l'ultima posizione valida prima dell'errore
                    last_valid_brace = cleaned_json.rfind('}', 0, error_pos)
                    if last_valid_brace > 0:
                        # Prova a prendere solo fino all'ultima parentesi valida e chiudere
                        cleaned_json = cleaned_json[:last_valid_brace+1]
                        for _ in range(missing_braces):
                            cleaned_json += '}'
                        print(f"  - Tentativo riparazione: aggiunte {missing_braces} parentesi graffe mancanti")
                
                # Prova a rimuovere eventuali virgolette non escape all'interno di stringhe
                # Questo è più complesso, ma possiamo provare a sostituire virgolette singole problematiche
                # Solo se sono chiaramente all'interno di una stringa JSON
                
                # Prova di nuovo il parsing
                parsed_json = json.loads(cleaned_json)
                print("  ✓ JSON riparato con successo")
            except Exception as repair_err:
                print(f"  ✗ Impossibile riparare il JSON: {repair_err}")
                print(f"  - Lunghezza totale risposta: {len(tool_call_args)} caratteri")
                print(f"  - Primi 500 caratteri: {tool_call_args[:500]}")
                print(f"  - Ultimi 500 caratteri: {tool_call_args[-500:]}")
                
                # Se l'errore è alla fine del JSON, potrebbe essere troncato
                if error_pos > len(tool_call_args) * 0.9:
                    print(f"  ⚠ ATTENZIONE: L'errore è vicino alla fine del JSON ({error_pos}/{len(tool_call_args)}).")
                    print(f"     Il JSON potrebbe essere stato troncato. Considera di aumentare max_tokens.")
                
                raise json_err  # Rilancia l'errore originale
        
        # Valida con Pydantic
        validated_data = CaseCollection.model_validate(parsed_json)
        
        # Valida che tutte le skills_to_test corrispondano alle canonical_skills
        if canonical_skills:
            print("4. Validazione coerenza skills con lista canonica...")
            # Crea mappe normalizzate per matching flessibile (ignora suffissi come "(technical)", "(soft)")
            canonical_skill_names_normalized = {_normalize_skill_name(skill['skill_name']): skill['skill_name'] for skill in canonical_skills}
            canonical_skill_map = {_normalize_skill_name(skill['skill_name']): skill['skill_name'] for skill in canonical_skills}
            
            invalid_skills = []
            corrected_count = 0
            
            for case in validated_data.cases:
                for step in case.reasoning_steps:
                    for skill_test in step.skills_to_test:
                        skill_name_normalized = _normalize_skill_name(skill_test.skill_name)
                        original_skill_name = skill_test.skill_name
                        
                        # Verifica se la skill corrisponde (usando normalizzazione)
                        if skill_name_normalized in canonical_skill_names_normalized:
                            # Match trovato! Normalizza il nome al canonical
                            canonical_name = canonical_skill_map[skill_name_normalized]
                            if original_skill_name != canonical_name:
                                skill_test.skill_name = canonical_name
                                corrected_count += 1
                                print(f"    ✓ Corretto nome skill: '{original_skill_name}' -> '{canonical_name}'")
                        else:
                            # Skill non trovata nemmeno con normalizzazione
                            invalid_skills.append({
                                'case': case.question_id,
                                'step': step.id,
                                'skill': original_skill_name
                            })
                            print(f"    ⚠ Skill non canonica trovata: '{original_skill_name}' in case {case.question_id}, step {step.id}")
            
            if invalid_skills:
                print(f"  ⚠ ATTENZIONE: Trovate {len(invalid_skills)} skill non canoniche nei reasoning steps.")
                print(f"     Queste skill non corrispondono alla lista canonica e potrebbero causare inconsistenze.")
            else:
                print(f"  ✓ Tutte le skills nei reasoning steps corrispondono alla lista canonica.")
            
            if corrected_count > 0:
                print(f"  ✓ Corrette {corrected_count} skill con matching case-insensitive.")
            
            # VALIDAZIONE CRITICA: Verifica che TUTTE le skill canoniche siano state incluse
            print("5. Validazione copertura completa delle skill canoniche...")
            skills_found = set()
            
            for case in validated_data.cases:
                for step in case.reasoning_steps:
                    for skill_test in step.skills_to_test:
                        skill_name_normalized = _normalize_skill_name(skill_test.skill_name)
                        if skill_name_normalized in canonical_skill_names_normalized:
                            skills_found.add(skill_name_normalized)
            
            missing_skills_normalized = set(canonical_skill_names_normalized.keys()) - skills_found
            if missing_skills_normalized:
                print(f"  ⚠ ERRORE CRITICO: {len(missing_skills_normalized)} skill canoniche NON sono state incluse in nessun reasoning step!")
                for missing_normalized in missing_skills_normalized:
                    # Trova il nome originale (case-sensitive) dalla mappa
                    original_name = canonical_skill_map.get(missing_normalized, missing_normalized)
                    print(f"     - {original_name}")
                print(f"  ⚠ ATTENZIONE: La generazione NON ha incluso tutte le skill richieste.")
                print(f"     Skill incluse: {len(skills_found)}/{len(canonical_skill_names_normalized)}")
                print(f"     Considera di rigenerare i case per includere tutte le skill canoniche.")
            else:
                print(f"  ✓ Validazione completata: TUTTE le {len(canonical_skill_names_normalized)} skill canoniche sono state incluse nei reasoning steps.")
                print(f"     Skill incluse: {len(skills_found)}/{len(canonical_skill_names_normalized)}")
        
        print("6. Dati validati con successo. Generazione completata.")
        return validated_data
        
    except json.JSONDecodeError as json_err:
        print(f"✗ Errore critico durante il parsing JSON dei casi: {json_err}")
        print(f"  - Tipo errore: JSONDecodeError")
        print(f"  - Messaggio: {json_err.msg}")
        if hasattr(json_err, 'pos'):
            print(f"  - Posizione: carattere {json_err.pos}")
        return None
    except Exception as e:
        print(f"✗ Errore critico durante la validazione dei casi: {e}")
        print(f"  - Tipo errore: {type(e).__name__}")
        import traceback
        print(f"  - Traceback: {traceback.format_exc()}")
        return None