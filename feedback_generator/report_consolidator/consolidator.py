from interviewer.llm_service import get_llm_response
from . import prompts_consolidator

CONSOLIDATOR_MODEL = "gpt-4.1-2025-04-14"

def create_consolidated_report(cv_analysis_report: str, case_evaluation_report: str, language: str = "it") -> str:
    """
    Usa un LLM per fondere il report di analisi del CV e quello del case study.
    
    Args:
        cv_analysis_report: Report di analisi del CV
        case_evaluation_report: Report di valutazione del case
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Report consolidato nella lingua specificata
    """
    print("1. Creazione del prompt per il consolidamento dei report...")
    prompt = prompts_consolidator.create_consolidation_prompt(
        cv_analysis_report, case_evaluation_report, language
    )
    
    print(f"2. Invio della richiesta al modello '{CONSOLIDATOR_MODEL}' per il consolidamento...")
    
    consolidated_report = get_llm_response(
        prompt=prompt,
        model=CONSOLIDATOR_MODEL,
        system_prompt=prompts_consolidator.SYSTEM_PROMPT[language],
        temperature=0.2,
        max_tokens=2000
    )
    
    if "Errore" in consolidated_report:
        print(f"Errore ricevuto dall'LLM: {consolidated_report}")
        return "" # Restituisce una stringa vuota in caso di errore

    print("3. Report consolidato generato con successo.")
    return consolidated_report

from interviewer.llm_service import get_llm_response_async

async def create_consolidated_report_async(cv_analysis_report: str, case_evaluation_report: str, language: str = "it") -> str:
    """Versione ASINCRONA: Usa un LLM per fondere i report."""
    print("1. Creazione del prompt per il consolidamento dei report...")
    prompt = prompts_consolidator.create_consolidation_prompt(cv_analysis_report, case_evaluation_report, language)
    
    print(f"2. Invio della richiesta al modello '{CONSOLIDATOR_MODEL}' per il consolidamento...")
    consolidated_report = await get_llm_response_async( # <-- MODIFICA: usa await
        prompt=prompt,
        model=CONSOLIDATOR_MODEL,
        system_prompt=prompts_consolidator.SYSTEM_PROMPT[language],
        temperature=0.2,
        max_tokens=2000
    )
    
    if "Errore" in consolidated_report:
        print(f"Errore ricevuto dall'LLM: {consolidated_report}")
        return ""

    print("3. Report consolidato generato con successo.")
    return consolidated_report