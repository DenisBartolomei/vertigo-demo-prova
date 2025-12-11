# Nel file analyzer/run_analyzer.py (o dove si trova)
import json
import re  # Importiamo il modulo per le espressioni regolari

from interviewer.llm_service import get_llm_response, AZURE_DEPLOYMENT_NAME
from .prompts_analyzer import create_cv_analysis_prompt

ANALYZER_MODEL = AZURE_DEPLOYMENT_NAME 

def parse_mixed_llm_response(response_text: str) -> dict:
    """
    Parser robusto per estrarre il report testuale e la parte JSON da una stringa mista.
    Estrae: report_text, structured_experience, candidate_name
    """
    report_text = ""
    structured_experience = []
    candidate_name = None

    # Cerchiamo il blocco JSON. L'espressione regolare cerca una '{' che apre un JSON
    # e lo cattura fino alla sua corrispondente '}' di chiusura.
    # re.DOTALL fa sì che '.' includa anche i caratteri di nuova riga.
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(0)
        # Il report è tutto ciò che precede l'inizio del blocco JSON
        report_text = response_text[:json_match.start()].strip()
        
        try:
            # Proviamo a parsare il blocco JSON trovato
            parsed_json = json.loads(json_str)
            if isinstance(parsed_json, dict):
                # Estrai candidate_name se presente
                candidate_name = parsed_json.get("candidate_name")
                if candidate_name:
                    print(f"Parser: Nome candidato estratto: {candidate_name}")
                
                # Estrai experience se presente
                if "experience" in parsed_json:
                    structured_experience = parsed_json["experience"]
                    print("Parser: Blocco JSON estratto e parsato con successo.")
                else:
                    print("Parser: JSON trovato ma non contiene la chiave 'experience'.")
                    # Aggiungiamo il JSON "malformato" al report per non perdere l'informazione
                    report_text += f"\n\n--- BLOCCO JSON NON VALIDO RICEVUTO ---\n{json_str}"
            else:
                print("Parser: JSON trovato ma non è un dizionario.")
                report_text += f"\n\n--- BLOCCO JSON NON VALIDO RICEVUTO ---\n{json_str}"

        except json.JSONDecodeError:
            print("Parser: Trovato un blocco che sembra JSON, ma il parsing è fallito.")
            # Se il parsing fallisce, lo trattiamo come testo normale e lo aggiungiamo al report.
            report_text += f"\n\n--- BLOCCO JSON NON PARSABILE RICEVUTO ---\n{json_str}"
    else:
        # Se non troviamo nessun blocco JSON, l'intera risposta è considerata il report
        print("Parser: Nessun blocco JSON trovato nella risposta. Tratto tutto come report testuale.")
        report_text = response_text.strip()
        
    # Pulizia finale del report: se inizia con "REPORT.", lo rimuoviamo per coerenza
    if report_text.upper().startswith("REPORT."):
        report_text = report_text[len("REPORT."):].strip()

    return {
        "report_text": report_text,
        "structured_experience": structured_experience,
        "candidate_name": candidate_name
    }


def analyze_cv(cv_text: str, job_description_text: str, hr_special_needs: str = "", language: str = "it") -> dict:
    """
    Esegue l'analisi unificata del CV usando un singolo prompt che richiede un output misto.
    Utilizza un parser robusto per separare il report testuale dal JSON delle esperienze.
    
    Args:
        cv_text: Testo del CV
        job_description_text: Testo della job description
        hr_special_needs: Indicazioni speciali HR
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Dizionario con report_text e structured_experience
    """
    print("1. Creazione del prompt unificato...")
    # Qui usiamo la TUA nuova funzione create_cv_analysis_prompt con language
    analysis_prompt = create_cv_analysis_prompt(cv_text, job_description_text, hr_special_needs, language)
    
    print(f"2. Invio della richiesta al modello '{ANALYZER_MODEL}' per output misto...")
    
    # Un system prompt che incoraggia il formato corretto (bilingue)
    system_prompts = {
        "it": "Agisci come un recruiter AI. Il tuo compito è seguire SCRUPOLOSAMENTE le istruzioni e il formato di output richiesto nel prompt dell'utente, producendo prima il report testuale e poi il blocco JSON.",
        "en": "Act as an AI recruiter. Your task is to SCRUPULOUSLY follow the instructions and the output format required in the user prompt, producing first the textual report and then the JSON block."
    }
    analyzer_system_prompt = system_prompts.get(language, system_prompts["it"])

    # Aumentiamo i token per contenere sia il testo che il JSON
    raw_response = get_llm_response(
        prompt=analysis_prompt,
        model=ANALYZER_MODEL,
        system_prompt=analyzer_system_prompt,
        max_tokens=3500,
        temperature=0.2
    )
    
    if not raw_response:
        print("Errore: La chiamata all'LLM non ha restituito una risposta.")
        return {"report_text": "Errore durante l'analisi del CV.", "structured_experience": []}
    
    print("3. Risposta ricevuta dall'LLM. Avvio del parsing robusto...")
    
    # Usiamo la nostra nuova funzione di parsing per separare i dati
    parsed_data = parse_mixed_llm_response(raw_response)
    
    print("4. Parsing completato.")
    return parsed_data