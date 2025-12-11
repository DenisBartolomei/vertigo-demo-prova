# System prompt per definire il ruolo dell'LLM
SYSTEM_PROMPT = {
    "it": """Sei un Talent Acquisition Strategist specializzato nell'analisi avanzata delle Job Description e nella costruzione strutturata di profili candidati ideali. Segui una metodologia professionale a step logici. L'output deve essere completo, strutturato e adatto a essere elaborato da moduli downstream nella medesima lingua della job description.""",
    "en": """You are a Talent Acquisition Strategist specialized in advanced Job Description analysis and structured construction of ideal candidate profiles. Follow a professional step-by-step methodology. The output must be complete, structured, and suitable for processing by downstream modules in the same language as the job description."""
}

def create_icp_generation_prompt(job_description_text: str, hr_special_needs: str, language: str = "it") -> str:
    """
    Assembla il prompt completo per generare l'Ideal Candidate Profile (ICP)
    a partire dal testo di una Job Description, integrando Indicazioni Speciali HR.
    
    Args:
        job_description_text: Il testo della job description
        hr_special_needs: Indicazioni speciali da parte dell'HR
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    prompts = {
        "it": """
**Istruzioni Critiche - Distinzione Requisiti vs Attività**:

**COSA SONO I REQUISITI (SKILL)**:
I requisiti sono competenze, conoscenze o capacità che il candidato DEVE POSSEDERE per essere considerato per la posizione. Sono caratteristiche del candidato stesso, non attività che svolgerà o responsabilità che avrà.

Esempi di REQUISITI (vanno in "Competenze tecniche" o "Competenze trasversali"):
- "Conoscenza di Python" → REQUISITO TECNICO
- "Esperienza con Salesforce" → REQUISITO TECNICO  
- "Problem Solving" → REQUISITO TRASVERSALE
- "Capacità di lavorare in team" → REQUISITO TRASVERSALE
- "Conoscenza di metodologie Agile" → REQUISITO TECNICO

**COSA SONO LE ATTIVITÀ (NON REQUISITI)**:
Le attività sono compiti, responsabilità o azioni che il candidato DOVRÀ SVOLGERE una volta assunto. Descrivono il lavoro da fare, non le competenze richieste.

Esempi di ATTIVITÀ (vanno in "Responsabilità principali e attività operative attese"):
- "Sviluppare applicazioni web" → ATTIVITÀ (non un requisito)
- "Gestire il CRM aziendale" → ATTIVITÀ (non un requisito)
- "Collaborare con il team di sviluppo" → ATTIVITÀ (non un requisito)
- "Redigere report mensili" → ATTIVITÀ (non un requisito)
- "Partecipare a riunioni di progetto" → ATTIVITÀ (non un requisito)

**REGOLE FONDAMENTALI**:
1. Se l'annuncio dice "devi avere conoscenza di X" → REQUISITO
2. Se l'annuncio dice "ti occuperai di X" o "svolgerai X" → ATTIVITÀ
3. Se l'annuncio dice "sarai responsabile di X" → ATTIVITÀ
4. Se l'annuncio dice "candidato con esperienza in X" → REQUISITO
5. Se l'annuncio dice "dovrai fare X" → ATTIVITÀ

**Istruzioni Generali**:
o	Analizzare attentamente la Job Description riportata di seguito.
o	Identificare in modo razionale e aderente alla Job Description tutti gli elementi chiave richiesti, distinguendo accuratamente tra requisiti (skill) e attività.
o	Sii concreto e preciso. Estrai i requisiti esattamente come riportati nell'annuncio e non confonderli con le attività da svolgere.
o	Se presenti dei requisiti "nice to have" o "plus", inseriscili nelle categorie appropriate secondo la logica di appartenenza.
o	ATTENZIONE CRITICA: non confondere MAI i requisiti con le attività. Se una frase descrive COSA il candidato farà (attività), NON è un requisito. Se descrive COSA il candidato deve saper fare o conoscere (skill), È un requisito.
o	Non considerare MAI le lingue come skill, evitale e non inserirle mai nell'output finale.
o	Non considerare MAI lauree, diplomi, certificazioni e/o esperienze lavorative pregresse come skills. Evitale e non inserirle mai nell'output finale.
o	Non dedurre o inferire nulla, attieniti strettamente a quanto scritto nella Job Description.
o	Se alcune skill sono considerabili affini, aggregale in un'unica riga. Esempio: "Comunicazione" e "Relazionalità" possono essere aggregate in "Comunicazione e Relazionalità".

**Indicazioni Speciali HR**: queste sono inserite direttamente dagli interessati all'assunzione, trattale con cura e integrale in modo naturale con il resto.
{hr_block}

**Struttura dell'output JSON**:
Devi restituire un oggetto JSON strutturato con le seguenti sezioni:
- technical_skills: lista di skill tecniche (ogni skill ha "name" e opzionalmente "description")
- soft_skills: lista di skill trasversali (ogni skill ha "name" e opzionalmente "description")
- activities: lista di attività/responsabilità (ogni attività ha "description")

IMPORTANTE: Assicurati che ogni elemento sia nella categoria corretta. Le attività NON devono mai finire nelle liste delle skill.

---
**JOB DESCRIPTION DA ANALIZZARE:**
{job_description_text}
""",
        "en": """
**Critical Instructions - Distinguishing Requirements vs Activities**:

**WHAT ARE REQUIREMENTS (SKILLS)**:
Requirements are competencies, knowledge, or abilities that the candidate MUST POSSESS to be considered for the position. They are characteristics of the candidate themselves, not activities that they will perform or responsibilities that they will have.

Examples of REQUIREMENTS (go in "Technical skills" or "Soft skills"):
- "Knowledge of Python" → TECHNICAL REQUIREMENT
- "Experience with Salesforce" → TECHNICAL REQUIREMENT
- "Problem Solving" → SOFT SKILL REQUIREMENT
- "Ability to work in a team" → SOFT SKILL REQUIREMENT
- "Knowledge of Agile methodologies" → TECHNICAL REQUIREMENT

**WHAT ARE ACTIVITIES (NOT REQUIREMENTS)**:
Activities are tasks, responsibilities, or actions that the candidate WILL PERFORM once hired. They describe the work to be done, not the required competencies.

Examples of ACTIVITIES (go in "Main responsibilities and expected operational activities"):
- "Develop web applications" → ACTIVITY (not a requirement)
- "Manage company CRM" → ACTIVITY (not a requirement)
- "Collaborate with development team" → ACTIVITY (not a requirement)
- "Draft monthly reports" → ACTIVITY (not a requirement)
- "Participate in project meetings" → ACTIVITY (not a requirement)

**FUNDAMENTAL RULES**:
1. If the posting says "you must have knowledge of X" → REQUIREMENT
2. If the posting says "you will be responsible for X" or "you will perform X" → ACTIVITY
3. If the posting says "you will handle X" → ACTIVITY
4. If the posting says "candidate with experience in X" → REQUIREMENT
5. If the posting says "you will do X" → ACTIVITY

**General Instructions**:
o	Carefully analyze the Job Description provided below.
o	Identify all key elements required in a rational manner adherent to the Job Description, accurately distinguishing between requirements (skills) and activities.
o	Be concrete and precise. Extract requirements exactly as stated in the posting and do not confuse them with activities to be performed.
o	If "nice to have" or "plus" requirements are present, include them in the appropriate categories according to their logical belonging.
o	CRITICAL ATTENTION: NEVER confuse requirements with activities. If a phrase describes WHAT the candidate will do (activity), it is NOT a requirement. If it describes WHAT the candidate must know or be able to do (skill), it IS a requirement.
o	NEVER consider languages as skills, avoid them and never include them in the final output.
o	NEVER consider degrees, diplomas, certifications, and/or previous work experience as skills. Avoid them and never include them in the final output.
o	Do not deduce or infer anything, stick strictly to what is written in the Job Description.
o	If some skills are considered similar, aggregate them into a single line. Example: "Communication" and "Relationship Building" can be aggregated into "Communication and Relationship Building".

**HR Special Instructions**: these are entered directly by those interested in hiring, treat them carefully and integrate them naturally with the rest.
{hr_block}

**JSON Output Structure**:
You must return a structured JSON object with the following sections:
- technical_skills: list of technical skills (each skill has "name" and optionally "description")
- soft_skills: list of soft skills (each skill has "name" and optionally "description")
- activities: list of activities/responsibilities (each activity has "description")

IMPORTANT: Ensure that each element is in the correct category. Activities must NEVER end up in the skill lists.

---
**JOB DESCRIPTION TO ANALYZE:**
{job_description_text}
"""
    }
    
    # Validate language
    if language not in ["it", "en"]:
        print(f"  - [ICP Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    # Format HR block
    hr_block = hr_special_needs.strip() if hr_special_needs else (
        "Nessuna indicazione speciale fornita." if language == "it" else "No special instructions provided."
    )
    
    return prompts[language].format(hr_block=hr_block, job_description_text=job_description_text)
