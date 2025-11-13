SYSTEM_PROMPT = {
    "it": """Sei un agente AI progettato per produrre informazioni strutturate, ricevendo in input informazioni non strutturate.
Dati gli input, restituisci un oggetto JSON con i campi predefiniti nella struttura attesa. Formatta accuratamente i dati di output. Se un dato manca o non si può determinare, restituisci un valore di default (e.g., null, 0, or 'N/A').""",
    "en": """You are an AI agent designed to produce structured information, receiving unstructured information as input.
Given the inputs, return a JSON object with the predefined fields in the expected structure. Accurately format the output data. If a data is missing or cannot be determined, return a default value (e.g., null, 0, or 'N/A')."""
}

def create_evaluation_criteria_prompt(icp_text: str, cases_json_str: str, seniority_level: str, output_schema_example: str, hr_special_needs: str, language: str = "it", canonical_skills: list = None) -> str:
    """
    Prompt per generare i criteri di valutazione dei requisiti, integrando HR Needs.
    
    Args:
        icp_text: Il testo dell'ICP
        cases_json_str: JSON con i case generati
        seniority_level: Livello di seniority richiesto
        output_schema_example: Esempio della struttura JSON attesa
        hr_special_needs: Indicazioni speciali da parte dell'HR
        language: Lingua del prompt ("it" o "en")
        canonical_skills: Lista canonica delle skills (UNICA fonte di verità) - se fornita, genera criteri SOLO per queste skills
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    # Prepara il blocco canonical_skills per il prompt
    canonical_skills_block = ""
    if canonical_skills:
        skills_list = [f"- {skill['skill_name']} ({skill['skill_type']})" for skill in canonical_skills]
        skills_text = "\n".join(skills_list)
        if language == "it":
            canonical_skills_block = f"""
[LISTA CANONICA DELLE SKILL (UNICA FONTE DI VERITÀ)]
Questa è la lista COMPLETA e DEFINITIVA di tutte le skill per cui DEVI creare un criterio di valutazione.
DEVI creare esattamente 1 evaluation criterion per OGNI skill in questa lista, usando i nomi ESATTI come indicati.

{skills_text}

**REGOLA CRITICA**: Crea criteri SOLO per le skill elencate sopra. NON inventare, NON aggiungere, NON dedurre skill aggiuntive. Se una skill non è in questa lista, NON creare un criterio per essa.

"""
        else:
            canonical_skills_block = f"""
[CANONICAL SKILLS LIST (SINGLE SOURCE OF TRUTH)]
This is the COMPLETE and DEFINITIVE list of all skills for which you MUST create an evaluation criterion.
You MUST create exactly 1 evaluation criterion for EACH skill in this list, using the EXACT names as indicated.

{skills_text}

**CRITICAL RULE**: Create criteria ONLY for the skills listed above. DO NOT invent, DO NOT add, DO NOT deduce additional skills. If a skill is not in this list, DO NOT create a criterion for it.

"""
    # Prepara le parti condizionali del testo PRIMA di definire i prompts
    if language == "it":
        extraction_instruction = "" if canonical_skills else "Estrai SOLO questi requisiti, riportandoli esattamente come sono scritti. "
        skip_instruction = "Non tralasciare alcuna skill dalla LISTA CANONICA DELLE SKILL fornita sopra" if canonical_skills else "Non tralasciare alcun REQUISITO della ICP"
    else:
        extraction_instruction = "" if canonical_skills else "Extract ONLY these requirements, reporting them exactly as they are written. "
        skip_instruction = "Do not skip any skill from the CANONICAL SKILLS LIST provided above" if canonical_skills else "Do not skip any ICP REQUIREMENT"
    
    prompts = {
        "it": """
Sei un esperto di valutazione. Devi creare 1 evaluation criterion per ciascun REQUISITO (skill) dalla ICP osservabile in colloquio/case study.

**ATTENZIONE CRITICA - COSA ESTRARRE**:
Devi estrarre SOLO i REQUISITI (skill/competenze), NON le attività.

**COSA SONO I REQUISITI (da estrarre)**:
- Competenze tecniche: "Python", "Salesforce", "Machine Learning", "Conoscenza di SQL"
- Competenze trasversali: "Problem Solving", "Teamwork", "Leadership", "Comunicazione"

**COSA NON SONO REQUISITI (NON estrarre)**:
- Attività operative: "Sviluppare applicazioni", "Gestire il CRM", "Redigere report"
- Responsabilità: "Sarai responsabile di...", "Ti occuperai di...", "Dovrai fare..."
- Descrizioni di lavoro: "Partecipare a riunioni", "Collaborare con il team"

**REGOLE FONDAMENTALI**:
1. Estrai SOLO dalle sezioni "Competenze tecniche richieste esplicitamente dall'annuncio" e "Competenze trasversali richieste esplicitamente dall'annuncio"
2. IGNORA COMPLETAMENTE la sezione "Responsabilità principali e attività operative attese" - NON estrarre nulla da lì
3. Se un elemento sembra descrivere COSA fare (attività) invece di COSA sapere (skill), SCARTALO
4. Se hai dubbi se qualcosa è un requisito o un'attività, chiediti: "Questo descrive una competenza che il candidato deve avere, o un compito che dovrà svolgere?" Se è un compito, NON estrarlo.

Indicazioni Speciali HR
{hr_block}

Dati:
- ICP, che rappresenta una sintesi di come dovrebbe essere il candidato ideale per la posizione lavorativa per cui stiamo lavorando;
- set_di_domande, che rappresenta i case prodotti che saranno somministrati ai candidati, assieme ai reasoning steps (cioè i vari step predefiniti per il raggiungimento di una soluzione ottima);
- Livello_di_seniority, che rappresenta il livello di seniority richiesto dalla posizione lavorativa per cui stiamo lavorando.

Il tuo compito è creare un sistema che permetta di valutare il soddisfacimento dei REQUISITI (skill) di una posizione di lavoro, attraverso l'analisi delle interazioni avvenute durante la risoluzione di un Case da parte del candidato.

{canonical_skills_block}

I requisiti tecnici e trasversali saranno forniti nel report "ICP", nei paragrafi **Competenze tecniche richieste esplicitamente dall'annuncio** e **Competenze trasversali richieste esplicitamente dall'annuncio (escluse le lingue)**. {extraction_instruction}IGNORA completamente la sezione delle attività.

Esempio di REQUISITO da estrarre:
Requisito: problem solving.
Evaluation criterion: adozione di analisi e approccio strutturati al problema durante tutta la risoluzione, che evidenziano un approccio brillante anche in caso di "problemi" più complessi, incluso l'approccio alla risoluzione di vincoli complessi come quelli legali che potrebbero bloccare il raggiungimento della soluzione, dimostrando la capacità di identificare rapidamente le variabili chiave e proporre soluzioni alternative quando necessario.

Esempio di COSA NON estrarre (è un'attività):
"Sviluppare applicazioni web" → NON è un requisito, è un'attività. NON estrarlo.
"Gestire il CRM aziendale" → NON è un requisito, è un'attività. NON estrarlo.

---
Istruzioni
- Nel produrre gli evaluation criteria dei requisiti sii calibrato rispetto al livello di seniority indicato di seguito.
- Estrai SOLO requisiti (skill), MAI attività
- Rifletti attentamente sul contenuto degli input per distinguere requisiti da attività
- Usa un buon grado di dettaglio, per evitare equivoci o problemi interpretativi
- Produci sempre 1 evaluation criterion completo e dettagliato per ogni REQUISITO individuato
- Il criterio deve essere esaustivo e coprire gli aspetti principali del requisito per permettere una valutazione accurata
- {skip_instruction} (ma ignora le attività)
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
You are an evaluation expert. You must create 1 evaluation criterion for each REQUIREMENT (skill) from the ICP observable in interview/case study.

**CRITICAL ATTENTION - WHAT TO EXTRACT**:
You must extract ONLY REQUIREMENTS (skills/competencies), NOT activities.

**WHAT ARE REQUIREMENTS (to extract)**:
- Technical skills: "Python", "Salesforce", "Machine Learning", "SQL knowledge"
- Soft skills: "Problem Solving", "Teamwork", "Leadership", "Communication"

**WHAT ARE NOT REQUIREMENTS (do NOT extract)**:
- Operational activities: "Develop applications", "Manage CRM", "Draft reports"
- Responsibilities: "You will be responsible for...", "You will handle...", "You will do..."
- Job descriptions: "Participate in meetings", "Collaborate with team"

**FUNDAMENTAL RULES**:
1. Extract ONLY from sections "Technical skills explicitly required by the posting" and "Soft skills explicitly required by the posting"
2. COMPLETELY IGNORE the section "Main responsibilities and expected operational activities" - extract NOTHING from there
3. If an element seems to describe WHAT to do (activity) instead of WHAT to know (skill), DISCARD it
4. If you have doubts whether something is a requirement or an activity, ask yourself: "Does this describe a competency the candidate must have, or a task they will perform?" If it's a task, do NOT extract it.

HR Special Instructions
{hr_block}

Data:
- ICP, which represents a summary of what the ideal candidate should be for the job position we are working on;
- question_set, which represents the produced cases that will be administered to candidates, together with reasoning steps (i.e. the various predefined steps for achieving an optimal solution);
- Seniority_level, which represents the seniority level required by the job position we are working on.

Your task is to create a system that allows you to evaluate the fulfillment of the REQUIREMENTS (skills) of a job position, through the analysis of interactions that occurred during the resolution of a Case by the candidate.

{canonical_skills_block}

The technical and soft skill requirements will be provided in the "ICP" report, in the paragraphs **Technical skills explicitly required by the posting** and **Soft skills explicitly required by the posting (excluding languages)**. {extraction_instruction}COMPLETELY IGNORE the activities section.

Example of REQUIREMENT to extract:
Requirement: problem solving.
Evaluation criterion: adoption of structured analysis and approach to the problem throughout the resolution, which highlight a brilliant approach even in the case of more complex "problems", including the approach to resolving complex constraints such as legal ones that could block the achievement of the solution, demonstrating the ability to quickly identify key variables and propose alternative solutions when necessary.

Example of WHAT NOT to extract (it's an activity):
"Develop web applications" → NOT a requirement, it's an activity. Do NOT extract it.
"Manage company CRM" → NOT a requirement, it's an activity. Do NOT extract it.

---
Instructions
- In producing the evaluation criteria of the requirements, be calibrated with respect to the seniority level indicated below.
- Extract ONLY requirements (skills), NEVER activities
- Reflect carefully on the content of the inputs to distinguish requirements from activities
- Use a good degree of detail, to avoid misunderstandings or interpretive problems
- Always produce 1 complete and detailed evaluation criterion for each REQUIREMENT identified
- The criterion should be comprehensive and cover the main aspects of the requirement to allow for accurate evaluation
- {skip_instruction} (but ignore activities)
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
        canonical_skills_block=canonical_skills_block,
        extraction_instruction=extraction_instruction,
        skip_instruction=skip_instruction,
        hr_block=hr_block,
        icp_text=icp_text,
        cases_json_str=cases_json_str,
        seniority_level=seniority_level,
        output_schema_example=output_schema_example
    )
