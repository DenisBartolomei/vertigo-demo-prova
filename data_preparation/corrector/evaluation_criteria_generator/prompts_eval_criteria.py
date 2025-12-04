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

**⚠️ REGOLE CRITICHE PER LA SPECIFICITÀ DEI CRITERI ⚠️**

1. **ANALIZZA I REASONING STEPS E LE SKILLS_TO_TEST**:
   - Per ogni skill, analizza TUTTI i reasoning steps di TUTTI i case study forniti
   - Identifica in quali reasoning steps quella skill è presente nel campo `skills_to_test`
   - Leggi attentamente il `testing_method` associato a quella skill in ciascun reasoning step
   - Usa queste informazioni per creare un criterio SPECIFICO che rifletta come quella skill viene effettivamente testata nei case

2. **RIFERIMENTI AL CONTENUTO SPECIFICO DEL CASE**:
   - Il criterio DEVE fare riferimento a elementi concreti e specifici dei case study (es. "analisi dei requisiti di business", "progettazione di architetture cloud", "gestione di progetti Agile")
   - NON usare frasi generiche come "basandosi sulle evidenze emerse durante il colloquio" o "sui case study proposti"
   - Il criterio deve descrivere COSA specificamente il candidato deve dimostrare, basandoti sui reasoning steps e sul contenuto dei case

3. **CALIBRAZIONE SUL LIVELLO DI SENIORITY**:
   - Per Junior: focus su conoscenze base, capacità di apprendimento, approccio guidato
   - Per Mid-Level: competenze consolidate, autonomia operativa, capacità di problem-solving pratico
   - Per Senior: competenze avanzate, visione strategica, capacità di mentoring e leadership tecnica
   - Per Lead: visione architetturale, leadership strategica, capacità di definire standard e best practices

4. **STRUTTURA DEL CRITERIO**:
   - Inizia descrivendo COSA specificamente il candidato deve dimostrare (non "valutare la competenza")
   - Indica DOVE/DOVE questa skill viene testata (riferimenti ai reasoning steps specifici)
   - Specifica COME viene valutata (metodi di testing, aspetti chiave da osservare)
   - Includi indicatori concreti di successo per quel livello di seniority

**ESEMPI DI CRITERI SPECIFICI (CORRETTI)**:

Esempio 1 - Skill: "Problem Solving" (Mid-Level):
Il candidato deve dimostrare capacità di analisi strutturata dei problemi complessi, identificando variabili chiave e vincoli critici. Durante i reasoning steps che richiedono problem solving (es. analisi di processi aziendali, risoluzione di colli di bottiglia operativi), deve mostrare capacità di decomporre problemi in sottoproblemi gestibili, proporre soluzioni alternative valutando pro/contro, e anticipare potenziali rischi o impatti delle soluzioni proposte. Per il livello Mid-Level, si attende autonomia nell'identificare approcci risolutivi senza necessità di guida costante.

Esempio 2 - Skill: "Tecnologie Microsoft" (Senior):
Il candidato deve dimostrare padronanza avanzata delle tecnologie Microsoft (Azure, .NET, Power Platform) attraverso la capacità di progettare soluzioni architetturali complesse e guidare scelte tecnologiche strategiche. Nei reasoning steps che testano questa skill (es. progettazione di architetture cloud, integrazione di sistemi enterprise), deve mostrare comprensione profonda delle best practices Microsoft, capacità di valutare trade-off tra diverse tecnologie dello stack, e visione strategica sull'evoluzione delle piattaforme. Per il livello Senior, si attende capacità di mentoring tecnico e definizione di standard aziendali.

**ESEMPI DI CRITERI GENERICI (SBAGLIATI - DA EVITARE)**:

❌ SBAGLIATO: "Valutare la competenza del candidato in Problem Solving basandosi sulle evidenze emerse durante il colloquio e sui case study proposti."
❌ SBAGLIATO: "Il candidato deve dimostrare conoscenza di Tecnologie Microsoft durante la risoluzione dei case."
❌ SBAGLIATO: "Valutare la capacità del candidato di applicare le competenze richieste."

**PERCHÉ QUESTI SONO SBAGLIATI**:
- Non specificano COSA esattamente il candidato deve dimostrare
- Non fanno riferimento a elementi concreti dei case study
- Usano frasi generiche che non guidano la valutazione
- Non sono calibrati sul livello di seniority

---
Istruzioni
- Nel produrre gli evaluation criteria dei requisiti sii calibrato rispetto al livello di seniority indicato di seguito.
- Estrai SOLO requisiti (skill), MAI attività
- Rifletti attentamente sul contenuto degli input per distinguere requisiti da attività
- **CRITICO**: Per ogni skill, analizza i reasoning steps dei case study per identificare come quella skill viene testata e crea un criterio SPECIFICO basato su questi elementi concreti
- **CRITICO**: Evita TASSATIVAMENTE frasi generiche come "basandosi sulle evidenze emerse" o "durante il colloquio". Usa invece riferimenti specifici ai reasoning steps e al contenuto dei case
- **CRITICO**: Il criterio deve descrivere COSA specificamente il candidato deve dimostrare, DOVE (in quali reasoning steps), e COME (metodi di testing), calibrato sul livello di seniority
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

**⚠️ CRITICAL RULES FOR CRITERIA SPECIFICITY ⚠️**

1. **ANALYZE REASONING STEPS AND SKILLS_TO_TEST**:
   - For each skill, analyze ALL reasoning steps of ALL case studies provided
   - Identify in which reasoning steps that skill is present in the `skills_to_test` field
   - Carefully read the `testing_method` associated with that skill in each reasoning step
   - Use this information to create a SPECIFIC criterion that reflects how that skill is actually tested in the cases

2. **REFERENCES TO SPECIFIC CASE CONTENT**:
   - The criterion MUST reference concrete and specific elements of the case studies (e.g., "business requirements analysis", "cloud architecture design", "Agile project management")
   - DO NOT use generic phrases like "based on evidence emerged during the interview" or "on the proposed case studies"
   - The criterion must describe WHAT specifically the candidate must demonstrate, based on the reasoning steps and case content

3. **CALIBRATION ON SENIORITY LEVEL**:
   - For Junior: focus on basic knowledge, learning ability, guided approach
   - For Mid-Level: consolidated skills, operational autonomy, practical problem-solving ability
   - For Senior: advanced skills, strategic vision, technical mentoring and leadership capability
   - For Lead: architectural vision, strategic leadership, ability to define standards and best practices

4. **CRITERION STRUCTURE**:
   - Start by describing WHAT specifically the candidate must demonstrate (not "evaluate the competence")
   - Indicate WHERE this skill is tested (references to specific reasoning steps)
   - Specify HOW it is evaluated (testing methods, key aspects to observe)
   - Include concrete success indicators for that seniority level

**EXAMPLES OF SPECIFIC CRITERIA (CORRECT)**:

Example 1 - Skill: "Problem Solving" (Mid-Level):
The candidate must demonstrate structured analysis capability of complex problems, identifying key variables and critical constraints. During reasoning steps that require problem solving (e.g., business process analysis, operational bottleneck resolution), they must show ability to decompose problems into manageable sub-problems, propose alternative solutions evaluating pros/cons, and anticipate potential risks or impacts of proposed solutions. For Mid-Level, autonomy in identifying resolution approaches without constant guidance is expected.

Example 2 - Skill: "Microsoft Technologies" (Senior):
The candidate must demonstrate advanced mastery of Microsoft technologies (Azure, .NET, Power Platform) through the ability to design complex architectural solutions and guide strategic technology choices. In reasoning steps that test this skill (e.g., cloud architecture design, enterprise system integration), they must show deep understanding of Microsoft best practices, ability to evaluate trade-offs between different technologies in the stack, and strategic vision on platform evolution. For Senior level, technical mentoring capability and definition of company standards is expected.

**EXAMPLES OF GENERIC CRITERIA (WRONG - TO AVOID)**:

❌ WRONG: "Evaluate the candidate's competence in Problem Solving based on evidence emerged during the interview and the proposed case studies."
❌ WRONG: "The candidate must demonstrate knowledge of Microsoft Technologies during case resolution."
❌ WRONG: "Evaluate the candidate's ability to apply the required competencies."

**WHY THESE ARE WRONG**:
- They don't specify WHAT exactly the candidate must demonstrate
- They don't reference concrete elements of the case studies
- They use generic phrases that don't guide evaluation
- They are not calibrated on seniority level

---
Instructions
- In producing the evaluation criteria of the requirements, be calibrated with respect to the seniority level indicated below.
- Extract ONLY requirements (skills), NEVER activities
- Reflect carefully on the content of the inputs to distinguish requirements from activities
- **CRITICAL**: For each skill, analyze the reasoning steps of the case studies to identify how that skill is tested and create a SPECIFIC criterion based on these concrete elements
- **CRITICAL**: ABSOLUTELY avoid generic phrases like "based on evidence emerged" or "during the interview". Instead use specific references to reasoning steps and case content
- **CRITICAL**: The criterion must describe WHAT specifically the candidate must demonstrate, WHERE (in which reasoning steps), and HOW (testing methods), calibrated on seniority level
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
