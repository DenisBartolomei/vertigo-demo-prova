SYSTEM_PROMPT = {
    "it": """Sei un agente AI progettato per produrre informazioni strutturate, ricevendo in input informazioni non strutturate. Il tuo specifico compito è costruire rubriche di valutazione estremamente personalizzate sui casi studio da valutare e sugli input ricevuti.
Dati gli input, restituisci un oggetto JSON con i campi predefiniti nella struttura attesa. Formatta accuratamente i dati di output. Se un dato manca o non si può determinare, restituisci un valore di default (e.g., null, 0, or 'N/A').""",
    "en": """You are an AI agent designed to produce structured information, receiving unstructured information as input. Your specific task is to build extremely personalized rubrics for evaluating case studies and the inputs received.
Given the inputs, return a JSON object with the predefined fields in the expected structure. Accurately format the output data. If a data is missing or cannot be determined, return a default value (e.g., null, 0, or 'N/A')."""
}

def create_criteria_generation_prompt(icp_text: str, cases_json_str: str, seniority_level: str, hr_special_needs: str, language: str = "it") -> str:
    """
    Assembla il prompt per la generazione degli accomplishment criteria, integrando gli HR needs.
    
    Args:
        icp_text: Il testo dell'ICP
        cases_json_str: Dati strutturati con i case generati
        seniority_level: Livello di seniority richiesto
        hr_special_needs: Indicazioni speciali da parte dell'HR
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    prompts = {
        "it": """
Sei un esperto di valutazione di test. Devi creare accomplishment criteria univoci per ciascun reasoning step di ciascun case.

Indicazioni Speciali HR
{hr_block}

Fai parte di una commissione che deve decidere lo schema per interpretare le risposte dei candidati a un test in modo univoco e standard. L'obiettivo è sempre quello di creare un sistema di valutazione oggettivo, e che permetta ai futuri scrutinatori di valutare in modo univoco e senza dubbi il modo in cui i candidati sono giunti o meno a una soluzione dei case proposto.

Produci 1 accomplishment criteria per ciascun reasoning step, di ciascun case presente nell'input. L'obiettivo è creare un sistema di valutazione univoco e personalizzato per ciascun reasoning step dei Case proposti nell'input "set_di_domande". Gli accomplishment criteria prodotti dovranno supportare i futuri valutatori offrendo una traccia inequivocabile e oggettiva per capire se un reasoning step si possa ritenere soddisfatto o meno.
Dati:
- ICP, che rappresenta una sintesi di come dovrebbe essere il candidato ideale per la posizione lavorativa per cui stiamo lavorando;
- set_di_domande, che rappresenta i case prodotti che saranno somministrati ai candidati, assieme ai reasoning steps (cioè i vari step predefiniti per il raggiungimento di una soluzione ottima);
- Livello_di_seniority, che rappresenta il livello di seniority richiesto dalla posizione lavorativa per cui stiamo lavorando.

Esempio.
Reasoning step 1: Analisi dell'attuale processo di onboarding e identificazione dei colli di bottiglia
Accomplishment criteria 1: Il candidato deve identificare la necessità di un analisi as-is del processo, dimostrandosi in grado di individuare i punti critici, distinguere tra problemi tecnici e organizzativi, e proporre metriche per la misurazione dell'efficienza.
---
**Istruzioni**
- Nel produrre gli schemi di valutazione dei requisiti sii calibrato rispetto al livello di seniority indicato di seguito.
- Rifletti attentamente sul contenuto degli input
- Rifletti attentamente sul cosa inserire negli accomplishment criteria
- Ripeti la struttura di output per tutti i Case nell'input "set_di_domande" e, per ciascun Case, considera tutti i reasoning_steps
- Usa un buon grado di dettaglio, per evitare equivoci o problemi interpretativi
- Usa la ICP per guidarti correttamente nella produzione dei criteri, in modo che siano allineati con le esigenze della posizione lavorativa

---
INPUTS

[PROFILO CANDIDATO IDEALE (ICP)]
{icp_text}

[SET DI DOMANDE (CASES)]
Nei dati strutturati di seguito sono contenuti i case generati:
{cases_json_str}

[LIVELLO DI SENIORITY]
{seniority_level}
""",
        "en": """
You are a test evaluation expert. You must create unique accomplishment criteria for each reasoning step of each case.

HR Special Instructions
{hr_block}

You are part of a committee that must decide the schema to interpret candidates' responses to a test in a unique and standard way. The objective is always to create an objective evaluation system that allows future examiners to evaluate in a unique way and without doubts the way in which candidates have reached or not reached a solution to the proposed case.

Produce 1 accomplishment criteria for each reasoning step, of each case present in the input. The objective is to create a unique and personalized evaluation system for each reasoning step of the Cases proposed in the "question_set" input. The produced accomplishment criteria must support future evaluators by offering an unequivocal and objective track to understand whether a reasoning step can be considered satisfied or not.
Data:
- ICP, which represents a summary of what the ideal candidate should be for the job position we are working on;
- question_set, which represents the produced cases that will be administered to candidates, together with reasoning steps (i.e. the various predefined steps for achieving an optimal solution);
- Seniority_level, which represents the seniority level required by the job position we are working on.

Example.
Reasoning step 1: Analysis of the current onboarding process and identification of bottlenecks
Accomplishment criteria 1: The candidate must identify the need for an as-is analysis of the process, demonstrating the ability to identify critical points, distinguish between technical and organizational problems, and propose metrics for measuring efficiency.
---
**Instructions**
- In producing the requirements evaluation schemas, be calibrated with respect to the seniority level indicated below.
- Reflect carefully on the content of the inputs
- Reflect carefully on what to insert in the accomplishment criteria
- Repeat the output structure for all Cases in the "question_set" input and, for each Case, consider all reasoning_steps
- Use a good degree of detail, to avoid misunderstandings or interpretive problems
- Use the ICP to guide you correctly in producing the criteria, so that they are aligned with the needs of the job position

---
INPUTS

[IDEAL CANDIDATE PROFILE (ICP)]
{icp_text}

[QUESTION SET (CASES)]
In the structured data below are contained the generated cases:
{cases_json_str}

[SENIORITY LEVEL]
{seniority_level}
"""
    }
    
    # Validate language
    if language not in ["it", "en"]:
        print(f"  - [Criteria Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    # Format HR block
    hr_block = hr_special_needs.strip() if hr_special_needs else (
        "Nessuna indicazione speciale fornita." if language == "it" else "No special instructions provided."
    )
    
    return prompts[language].format(
        hr_block=hr_block,
        icp_text=icp_text,
        cases_json_str=cases_json_str,
        seniority_level=seniority_level
    )
