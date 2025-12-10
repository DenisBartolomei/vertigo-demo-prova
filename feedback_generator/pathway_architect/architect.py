import json
from typing import List
from pydantic import BaseModel, Field, AliasChoices
from datetime import datetime
from interviewer.llm_service import get_structured_llm_response
from . import prompts_pathway
import difflib
from services.data_manager import db
from utils.json_toon_converter import convert_json_to_toon

# --- 1. Definizione dello Schema Dati Pydantic per l'Output ---

class SuggestedCourse(BaseModel):
    course_name: str = Field(description="Il nome del corso selezionato.")
    justification: str = Field(description="Breve spiegazione del perché questo corso è utile per il candidato.")
    level: str = Field(description="Il livello di difficoltà del corso (es. Beginner, Intermediate).")
    duration_hours: int = Field(description="La durata stimata del corso in ore.")
    url: str = Field(description="L'URL per accedere al corso.")

class FinalReportContent(BaseModel):
    # CAMPI DEL PDF PRODOTTO
    candidate_name: str = Field(description="Nome e Cognome del candidato.")
    target_role: str = Field(description="Il ruolo per cui il candidato è stato valutato.")
    
    # Sintesi generale.
    profile_summary: str = Field(
        description="Profilo sintetico di 3-4 righe sul candidato (Talent Passport).",
        validation_alias=AliasChoices("profile_summary", "Profilo sintetico", "Profile summary")
    )
    
    # Contiene la sintesi specifica dell'analisi del CV.
    cv_analysis_outcome: str = Field(
        description="Paragrafo che riassume gli esiti (punti di forza e carenze) emersi dall'analisi del solo Curriculum Vitae.",
        validation_alias=AliasChoices("cv_analysis_outcome", "cv_analysis", "Analisi CV")
    )
    
    # Contiene la sintesi specifica della performance nel colloquio.
    interview_outcome: str = Field(
        description="Paragrafo che riassume gli esiti (punti di forza e carenze) emersi dalla performance del candidato durante il colloquio/caso di studio.",
        validation_alias=AliasChoices("interview_outcome", "interview_analysis", "Analisi colloquio")
    )
    
    # Placeholder per la futura analisi di mercato.
    market_benchmark: str = Field(
        description="Paragrafo per il benchmark di mercato.",
        validation_alias=AliasChoices("market_benchmark", "Benchmark di mercato", "marketBenchmark")
    )
    
    # Il percorso formativo rimane una parte cruciale.
    suggested_pathway: List[SuggestedCourse] = Field(
        description="Lista ordinata di corsi che costituiscono il percorso formativo suggerito.",
        validation_alias=AliasChoices("suggested_pathway", "Percorso formativo", "training_pathway")
    )

# --- 2. Logica di Generazione ---

ARCHITECT_MODEL = "gpt-4.1-2025-04-14"

# OTTIMIZZATO: Usa i due report separati invece del report consolidato per ridurre i token.
def create_final_feedback_content(
    cv_analysis_report: str,
    case_evaluation_report: str,
    enriched_gaps_json_str: str, 
    candidate_name: str, 
    target_role: str,
    language: str = "it"
) -> FinalReportContent | None:
    """
    Genera il contenuto testuale e strutturato per il report finale in PDF.
    OTTIMIZZATO: Usa i due report separati (CV e colloquio) invece del report consolidato.
    
    Args:
        cv_analysis_report: Report di analisi del CV
        case_evaluation_report: Report di valutazione del colloquio
        enriched_gaps_json_str: JSON con gap e corsi suggeriti
        candidate_name: Nome del candidato
        target_role: Ruolo target
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        FinalReportContent validato o None
    """
    print("1. Creazione del prompt per il report di feedback finale con report CV e colloquio separati...")
    
    # Converti a TOON per il prompt
    try:
        enriched_gaps_toon_str = convert_json_to_toon(enriched_gaps_json_str)
    except Exception as e:
        print(f"⚠ ERRORE durante conversione TOON enriched_gaps: {e}, uso JSON originale")
        enriched_gaps_toon_str = enriched_gaps_json_str
    
    # OTTIMIZZATO: Usa i due report separati invece del report consolidato
    prompt = prompts_pathway.create_final_report_prompt(
        cv_analysis_report,
        case_evaluation_report,
        enriched_gaps_toon_str, 
        candidate_name, 
        target_role,
        language
    )
    
    print(f"2. Invio della richiesta al modello '{ARCHITECT_MODEL}' per creare il percorso...")
    
    structured_response_str = get_structured_llm_response(
        prompt=prompt,
        model=ARCHITECT_MODEL,
        system_prompt=prompts_pathway.SYSTEM_PROMPT.get(language, prompts_pathway.SYSTEM_PROMPT["it"]),
        tool_name="save_final_feedback_report",
        tool_schema=FinalReportContent.model_json_schema()
    )

    if not structured_response_str:
        return None

    try:
        print("3. Output strutturato ricevuto, validazione in corso...")
        parsed_json = json.loads(structured_response_str)
        validated_data = FinalReportContent.model_validate(parsed_json)
        
        # 4. Match degli URL dei corsi con quelli del database
        if validated_data.suggested_pathway:
            print("4. [URL MATCH] Correzione URL dei corsi con match dal database...")
            validated_data.suggested_pathway = _match_course_urls_from_db(validated_data.suggested_pathway)
        
        print("5. Contenuto del report finale generato e validato.")
        return validated_data
    except Exception as e:
        print(f"Errore critico durante la validazione del report finale: {e}")
        return None
    
from interviewer.llm_service import get_structured_llm_response_async

async def create_final_feedback_content_async(
    cv_analysis_report: str,
    case_evaluation_report: str,
    enriched_gaps_json_str: str, 
    candidate_name: str, 
    target_role: str,
    language: str = "it"
) -> FinalReportContent | None:
    """Versione ASINCRONA: Genera il contenuto testuale e strutturato per il report finale.
    OTTIMIZZATO: Usa i due report separati (CV e colloquio) invece del report consolidato."""
    print("1. [Report Finale] Creazione del prompt con report CV e colloquio separati...")
    
    # Converti a TOON per il prompt
    try:
        enriched_gaps_toon_str = convert_json_to_toon(enriched_gaps_json_str)
    except Exception as e:
        print(f"⚠ ERRORE durante conversione TOON enriched_gaps (async): {e}, uso JSON originale")
        enriched_gaps_toon_str = enriched_gaps_json_str
    
    prompt = prompts_pathway.create_final_report_prompt(
        cv_analysis_report,
        case_evaluation_report,
        enriched_gaps_toon_str, 
        candidate_name, 
        target_role,
        language
    )
    
    print(f"2. [Report Finale] Invio richiesta a '{ARCHITECT_MODEL}' per creare il percorso...")
    structured_response_str = await get_structured_llm_response_async( # <-- MODIFICA: usa await
        prompt=prompt,
        model=ARCHITECT_MODEL,
        system_prompt=prompts_pathway.SYSTEM_PROMPT.get(language, prompts_pathway.SYSTEM_PROMPT["it"]),
        tool_name="save_final_feedback_report",
        tool_schema=FinalReportContent.model_json_schema()
    )

    if not structured_response_str:
        print("❌ ERRORE: Nessuna risposta strutturata ricevuta dall'LLM")
        return None
    
    # FIX: Verifica se la risposta contiene un errore di rate limit
    if "Rate limit" in structured_response_str or "429" in structured_response_str or "Errore: Rate limit" in structured_response_str:
        print(f"❌ ERRORE: Rate limit rilevato nella risposta LLM: {structured_response_str}")
        return None

    parsed_json = None
    try:
        print("3. [Report Finale] Output strutturato ricevuto, validazione in corso...")
        parsed_json = json.loads(structured_response_str)
        
        # FALLBACK: Assicura che candidate_name e target_role siano sempre presenti
        # (anche se l'LLM non li include nel JSON)
        if "candidate_name" not in parsed_json or not parsed_json.get("candidate_name"):
            print(f"⚠ ATTENZIONE: candidate_name mancante nel JSON LLM, uso valore fornito: {candidate_name}")
            parsed_json["candidate_name"] = candidate_name
        
        if "target_role" not in parsed_json or not parsed_json.get("target_role"):
            print(f"⚠ ATTENZIONE: target_role mancante nel JSON LLM, uso valore fornito: {target_role}")
            parsed_json["target_role"] = target_role
        
        # Gestione alias: Pydantic può restituire errori se il JSON usa alias invece dei nomi dei campi
        # Convertiamo manualmente gli alias ai nomi dei campi prima della validazione
        if "Profilo sintetico" in parsed_json and "profile_summary" not in parsed_json:
            parsed_json["profile_summary"] = parsed_json.pop("Profilo sintetico")
            print("⚠ ATTENZIONE: Convertito alias 'Profilo sintetico' in 'profile_summary'")
        if "Analisi CV" in parsed_json and "cv_analysis_outcome" not in parsed_json:
            parsed_json["cv_analysis_outcome"] = parsed_json.pop("Analisi CV")
            print("⚠ ATTENZIONE: Convertito alias 'Analisi CV' in 'cv_analysis_outcome'")
        if "Analisi colloquio" in parsed_json and "interview_outcome" not in parsed_json:
            parsed_json["interview_outcome"] = parsed_json.pop("Analisi colloquio")
            print("⚠ ATTENZIONE: Convertito alias 'Analisi colloquio' in 'interview_outcome'")
        if "Benchmark di mercato" in parsed_json and "market_benchmark" not in parsed_json:
            parsed_json["market_benchmark"] = parsed_json.pop("Benchmark di mercato")
            print("⚠ ATTENZIONE: Convertito alias 'Benchmark di mercato' in 'market_benchmark'")
        if "Percorso formativo" in parsed_json and "suggested_pathway" not in parsed_json:
            parsed_json["suggested_pathway"] = parsed_json.pop("Percorso formativo")
            print("⚠ ATTENZIONE: Convertito alias 'Percorso formativo' in 'suggested_pathway'")
        
        validated_data = FinalReportContent.model_validate(parsed_json)
        
        # 4. Match degli URL dei corsi con quelli del database
        if validated_data.suggested_pathway:
            print("4. [Report Finale] [URL MATCH] Correzione URL dei corsi con match dal database...")
            validated_data.suggested_pathway = _match_course_urls_from_db(validated_data.suggested_pathway)
        
        print("5. [Report Finale] Contenuto generato e validato.")
        return validated_data
    except json.JSONDecodeError as e:
        print(f"✗ ERRORE: JSON non valido ricevuto dall'LLM: {e}")
        print(f"   Risposta ricevuta (primi 500 caratteri): {structured_response_str[:500]}")
        return None
    except Exception as validation_error:
        # Gestione specifica per errori di validazione Pydantic
        print(f"✗ ERRORE critico durante la validazione del report finale: {validation_error}")
        print(f"   JSON ricevuto (primi 500 caratteri): {structured_response_str[:500] if structured_response_str else 'Nessuna risposta'}")
        
        # Prova a fare un fallback più robusto: ricarica il JSON e gestisci gli errori campo per campo
        try:
            # Riprova a parsare il JSON se non era già stato parsato
            if parsed_json is None:
                parsed_json = json.loads(structured_response_str)
            
            # Se la validazione fallisce, prova a costruire manualmente i campi mancanti
            if "candidate_name" not in parsed_json or not parsed_json.get("candidate_name"):
                parsed_json["candidate_name"] = candidate_name
            if "target_role" not in parsed_json or not parsed_json.get("target_role"):
                parsed_json["target_role"] = target_role
            
            # Gestione alias anche nel fallback
            if "Profilo sintetico" in parsed_json and "profile_summary" not in parsed_json:
                parsed_json["profile_summary"] = parsed_json.pop("Profilo sintetico")
            if "Analisi CV" in parsed_json and "cv_analysis_outcome" not in parsed_json:
                parsed_json["cv_analysis_outcome"] = parsed_json.pop("Analisi CV")
            if "Analisi colloquio" in parsed_json and "interview_outcome" not in parsed_json:
                parsed_json["interview_outcome"] = parsed_json.pop("Analisi colloquio")
            if "Benchmark di mercato" in parsed_json and "market_benchmark" not in parsed_json:
                parsed_json["market_benchmark"] = parsed_json.pop("Benchmark di mercato")
            if "Percorso formativo" in parsed_json and "suggested_pathway" not in parsed_json:
                parsed_json["suggested_pathway"] = parsed_json.pop("Percorso formativo")

            # Riprova la validazione dopo il fallback
            validated_data = FinalReportContent.model_validate(parsed_json, strict=False)
            print("⚠ [FALLBACK] Validazione riuscita dopo correzione dei campi mancanti")
            
            # Match degli URL dei corsi anche nel fallback
            if validated_data.suggested_pathway:
                print("⚠ [FALLBACK] [URL MATCH] Correzione URL dei corsi con match dal database...")
                validated_data.suggested_pathway = _match_course_urls_from_db(validated_data.suggested_pathway)
            
            return validated_data
        except Exception as fallback_error:
            print(f"✗ ERRORE anche nel fallback: {fallback_error}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            return None


def _match_course_urls_from_db(suggested_courses: List[SuggestedCourse]) -> List[SuggestedCourse]:
    """
    Matcha gli URL dei corsi suggeriti con quelli nel database usando fuzzy matching sul nome.
    
    Per ogni corso generato dall'LLM, cerca il corso corrispondente nel database usando
    fuzzy matching sul nome del corso. Se trova un match con similarità >= 0.7,
    sostituisce l'URL generato con quello corretto dal database.
    
    Args:
        suggested_courses: Lista di corsi generati dall'LLM con URL potenzialmente errati
        
    Returns:
        Lista di corsi con URL corretti dal database
    """
    if not suggested_courses:
        return suggested_courses
    
    # 1. Carica tutti i corsi dal database con URL
    if db is None:
        print("⚠️ [URL MATCH] Database non disponibile, mantengo URL originali")
        return suggested_courses
    
    try:
        courses_collection = db["courses"]
        # Carica solo i campi necessari: Course Name e URL
        db_courses = list(courses_collection.find(
            {},
            {"Course Name": 1, "URL": 1, "_id": 0}
        ))
        
        if not db_courses:
            print("⚠️ [URL MATCH] Nessun corso trovato nel database, mantengo URL originali")
            return suggested_courses
        
        print(f"🔍 [URL MATCH] Caricati {len(db_courses)} corsi dal database per il match URL")
        
        # 2. Crea un dizionario per lookup veloce: nome_corso -> URL
        # Normalizza i nomi per il matching (lowercase, rimuovi spazi extra)
        db_courses_map = {}
        for course in db_courses:
            course_name = course.get("Course Name", "").strip()
            course_url = course.get("URL", "").strip()
            if course_name and course_url:
                # Normalizza il nome per il matching
                normalized_name = course_name.lower().strip()
                db_courses_map[normalized_name] = {
                    "original_name": course_name,
                    "url": course_url
                }
        
        # 3. Per ogni corso suggerito, trova il match migliore
        matched_courses = []
        matched_count = 0
        
        for suggested_course in suggested_courses:
            suggested_name = suggested_course.course_name.strip()
            normalized_suggested = suggested_name.lower().strip()
            
            # Prima prova match esatto (case-insensitive)
            best_match = None
            best_ratio = 0.0
            
            if normalized_suggested in db_courses_map:
                # Match esatto trovato
                best_match = db_courses_map[normalized_suggested]
                best_ratio = 1.0
            else:
                # Fuzzy matching: trova il corso con la similarità più alta
                for normalized_db_name, db_course_info in db_courses_map.items():
                    # Usa SequenceMatcher per calcolare la similarità
                    ratio = difflib.SequenceMatcher(None, normalized_suggested, normalized_db_name).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match = db_course_info
            
            # Soglia minima di similarità: 0.7 (70%)
            if best_match and best_ratio >= 0.7:
                # Crea una nuova istanza con l'URL corretto (Pydantic models possono essere immutabili)
                original_url = suggested_course.url
                corrected_course = SuggestedCourse(
                    course_name=suggested_course.course_name,
                    justification=suggested_course.justification,
                    level=suggested_course.level,
                    duration_hours=suggested_course.duration_hours,
                    url=best_match["url"]  # URL corretto dal database
                )
                matched_count += 1
                print(f"✅ [URL MATCH] Corso '{suggested_name}' -> URL corretto (similarità: {best_ratio:.2f})")
                if original_url != best_match["url"]:
                    print(f"   URL originale: {original_url[:50]}...")
                    print(f"   URL corretto: {best_match['url'][:50]}...")
                matched_courses.append(corrected_course)
            else:
                # Nessun match trovato o similarità troppo bassa
                print(f"⚠️ [URL MATCH] Nessun match per corso '{suggested_name}' (miglior ratio: {best_ratio:.2f}), mantengo URL originale")
                matched_courses.append(suggested_course)
        
        print(f"✅ [URL MATCH] Completato: {matched_count}/{len(suggested_courses)} corsi con URL corretti")
        return matched_courses
        
    except Exception as e:
        print(f"❌ [URL MATCH] Errore durante il match degli URL: {e}")
        import traceback
        traceback.print_exc()
        # In caso di errore, ritorna i corsi originali
        return suggested_courses