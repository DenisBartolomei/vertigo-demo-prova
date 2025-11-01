SYSTEM_PROMPT = {
    "it": """Sei un agente AI progettato per produrre informazioni strutturate, ricevendo in input informazioni non strutturate.
Dati gli input, restituisci un oggetto JSON con i campi predefiniti nella struttura attesa. Formatta accuratamente i dati di output. Se un dato manca o non si può determinare, restituisci un valore di default (e.g., null, 0, or 'N/A').""",
    "en": """You are an AI agent designed to produce structured information, receiving unstructured information as input.
Given the inputs, return a JSON object with the predefined fields in the expected structure. Accurately format the output data. If a data is missing or cannot be determined, return a default value (e.g., null, 0, or 'N/A')."""
}

def create_evaluation_criteria_prompt(icp_text: str, cases_json_str: str, seniority_level: str, output_schema_example: str, hr_special_needs: str, language: str = "it") -> str:
    """
    Prompt per generare i criteri di valutazione dei requisiti, integrando HR Needs.
    
    Args:
        icp_text: Il testo dell'ICP
        cases_json_str: JSON con i case generati
        seniority_level: Livello di seniority richiesto
        output_schema_example: Esempio della struttura JSON attesa
        hr_special_needs: Indicazioni speciali da parte dell'HR
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    prompts = {
        "it": """
Sei un esperto di valutazione. Devi creare 1 evaluation criterion per ciascun requisito (dalla ICP) osservabile in colloquio/case study.

Indicazioni Speciali HR
{hr_block}

Dati:
- ICP, che rappresenta una sintesi di come dovrebbe essere il candidato ideale per la posizione lavorativa per cui stiamo lavorando;
- set_di_domande, che rappresenta i case prodotti che saranno somministrati ai candidati, assieme ai reasoning steps (cioè i vari step predefiniti per il raggiungimento di una soluzione ottima);
- Livello_di_seniority, che rappresenta il livello di seniority richiesto dalla posizione lavorativa per cui stiamo lavorando.

Il tuo compito è creare un sistema che permetta di valutare il soddisfacimento dei requisiti di una posizione di lavoro, attraverso l'analisi delle interazioni avvenute durante la risoluzione di un Case da parte del candidato.
I requisiti tecnici e non, saranno forniti nel report "ICP", nei paragrafi **Competenze tecniche richieste esplicitamente dall'annuncio** e **Competenze trasversali richieste esplicitamente dall'annuncio (escluse le lingue)**, fai in modo di riportarti esattamente come sono scritti. Mentre nel set_di_domande si trovano i Case predisposti, e che saranno risolti dai candidati, dai quali dovranno essere identificati i criteri per valutare il soddisfacimento dei requisiti della ICP.

Esempio.
Requisito: problem solving.
Evaluation criterion: adozione di analisi e approccio strutturati al problema durante tutta la risoluzione, che evidenziano un approccio brillante anche in caso di "problemi" più complessi, incluso l'approccio alla risoluzione di vincoli complessi come quelli legali che potrebbero bloccare il raggiungimento della soluzione, dimostrando la capacità di identificare rapidamente le variabili chiave e proporre soluzioni alternative quando necessario.
---
Istruzioni
- Nel produrre gli evaluation criteria dei requisiti sii calibrato rispetto al livello di seniority indicato di seguito.
- Rifletti attentamente sul contenuto degli input
- Rifletti attentamente sul cosa inserire negli evaluation criteria
- Usa un buon grado di dettaglio, per evitare equivoci o problemi interpretativi
- Produci sempre 1 evaluation criterion completo e dettagliato per ogni requisito individuato
- Il criterio deve essere esaustivo e coprire gli aspetti principali del requisito per permettere una valutazione accurata
- Non tralasciare alcun requisito della ICP
- Ricorda che il "reasoning_step_0" fa sempre riferimento allo step per impostare l'intera risoluzione del Case, mentre gli altri reasoning_steps sono la decomposizione della soluzione in problemi minori
- Rispondi sempre con un JSON strutturato, come esemplificato nell'input "esempio_struttura_output"
---

Input alla generazione:

[PROFILO CANDIDATO IDEALE (ICP)]
{icp_text}

[SET DI DOMANDE (CASES)]
{cases_json_str}

[LIVELLO DI SENIORITY]
{seniority_level}

[ESEMPIO STRUTTURA OUTPUT JSON ATTESA]
{output_schema_example}
""",
        "en": """
You are an evaluation expert. You must create 1 evaluation criterion for each requirement (from the ICP) observable in interview/case study.

HR Special Instructions
{hr_block}

Data:
- ICP, which represents a summary of what the ideal candidate should be for the job position we are working on;
- question_set, which represents the produced cases that will be administered to candidates, together with reasoning steps (i.e. the various predefined steps for achieving an optimal solution);
- Seniority_level, which represents the seniority level required by the job position we are working on.

Your task is to create a system that allows you to evaluate the fulfillment of the requirements of a job position, through the analysis of interactions that occurred during the resolution of a Case by the candidate.
The technical and non-technical requirements will be provided in the "ICP" report, in the paragraphs **Technical skills explicitly required by the posting** and **Soft skills explicitly required by the posting (excluding languages)**, make sure to report them exactly as they are written. While in the question_set you will find the prepared Cases, which will be solved by the candidates, from which the criteria to evaluate the fulfillment of the ICP requirements must be identified.

Example.
Requirement: problem solving.
Evaluation criterion: adoption of structured analysis and approach to the problem throughout the resolution, which highlight a brilliant approach even in the case of more complex "problems", including the approach to resolving complex constraints such as legal ones that could block the achievement of the solution, demonstrating the ability to quickly identify key variables and propose alternative solutions when necessary.
---
Instructions
- In producing the evaluation criteria of the requirements, be calibrated with respect to the seniority level indicated below.
- Reflect carefully on the content of the inputs
- Reflect carefully on what to insert in the evaluation criteria
- Use a good degree of detail, to avoid misunderstandings or interpretive problems
- Always produce 1 complete and detailed evaluation criterion for each identified requirement
- The criterion should be comprehensive and cover the main aspects of the requirement to allow for accurate evaluation
- Do not skip any ICP requirement
- Remember that "reasoning_step_0" always refers to the step to set up the entire Case resolution, while the other reasoning_steps are the decomposition of the solution into smaller problems
- Always respond with a structured JSON, as exemplified in the "example_output_structure" input
---

Generation input:

[IDEAL CANDIDATE PROFILE (ICP)]
{icp_text}

[QUESTION SET (CASES)]
{cases_json_str}

[SENIORITY LEVEL]
{seniority_level}

[EXPECTED JSON OUTPUT STRUCTURE EXAMPLE]
{output_schema_example}
"""
    }
    
    # Validate language
    if language not in ["it", "en"]:
        print(f"  - [Evaluation Criteria Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    # Format HR block
    hr_block = hr_special_needs.strip() if hr_special_needs else (
        "Nessuna indicazione speciale fornita." if language == "it" else "No special instructions provided."
    )
    
    return prompts[language].format(
        hr_block=hr_block,
        icp_text=icp_text,
        cases_json_str=cases_json_str,
        seniority_level=seniority_level,
        output_schema_example=output_schema_example
    )
