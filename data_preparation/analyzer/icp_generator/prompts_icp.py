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
**Istruzioni**:
o	Analizzare attentamente la Job Description riportata di seguito.
o	Identificare in modo razionale e aderente alla Job Description tutti gli elementi chiave richiesti, generalmente requisiti e responsabilità / attività.
o	Sii concreto e preciso. Estrai i requisiti esattamente come riportati nell'annuncio e non confonderli con le attività da svolgere.
o	Se presenti dei requisiti "nice to have" o "plus", inseriscili nelle categorie "Competenze tecniche richieste esplicitamente dall'annuncio" o "Competenze trasversali richieste esplicitamente dall'annuncio (escluse le lingue)", secondo la logica di appartenenza. Non è necessario classificarli in un gruppo a parte.
o	ATTENZIONE: non confondere i requisiti con le attività previste / attese per il ruolo. Troverai spesso negli annunci sezioni dove si spiega quali attività sono previste per la risorsa (alcuni esempi: cosa andrai a fare, attività, di cosa ti occuperai,...), queste devono andare in "Responsabilità principali e attività operative attese", non nei requisiti.
o	Non considerare MAI le lingue come skill, evitale e non inserirle mai nell'output finale.
o	Non considerare MAI lauree, diplomi, certificazioni e/o esperienze lavorative pregresse come skills. Evitale e non inserirle mai nell'output finale.
o	Non dedurre o inferire nulla, attieniti strettamente a quanto scritto nella Job Description.
**Indicazioni Speciali HR**: queste sono inserite direttamente dagli interessati all'assunzione, trattale con cura e integrale in modo naturale con il resto.
{hr_block}

**Struttura dell'output**
Ragionamento
In questa sezione potrai esplicitare il ragionamento passo per passo, analizzando con cura la Job Description, riflettendo sulle istruzioni, e pianificando correttamente la costruizione della sezione di seguito "Ideal Candidate Profile".
Ideal Candidate Profile
Sulla base dell'analisi sopra sintetizza il profilo ideale per questa posizione, specificando chiaramente:
o	Competenze tecniche richieste esplicitamente dall'annuncio
o	Competenze trasversali richieste esplicitamente dall'annuncio
o	Responsabilità principali e attività operative attese

---
**JOB DESCRIPTION DA ANALIZZARE:**
{job_description_text}
""",
        "en": """
**Instructions**:
o	Carefully analyze the Job Description provided below.
o	Identify all key elements required in a rational manner adherent to the Job Description, typically requirements and responsibilities/activities.
o	Be concrete and precise. Extract requirements exactly as stated in the posting and do not confuse them with activities to be performed.
o	If "nice to have" or "plus" requirements are present, include them in the categories "Technical skills explicitly required by the posting" or "Soft skills explicitly required by the posting (excluding languages)", according to their logical belonging. It is not necessary to classify them in a separate group.
o	ATTENTION: do not confuse requirements with expected activities/responsibilities for the role. You will often find sections in postings explaining what activities are expected for the resource (some examples: what you will do, activities, what you will be responsible for, ...), these should go in "Main responsibilities and expected operational activities", not in the requirements.
o	NEVER consider languages as skills, avoid them and never include them in the final output.
o	NEVER consider degrees, diplomas, certifications, and/or previous work experience as skills. Avoid them and never include them in the final output.
o	Do not deduce or infer anything, stick strictly to what is written in the Job Description.
**HR Special Instructions**: these are entered directly by those interested in hiring, treat them carefully and integrate them naturally with the rest.
{hr_block}

**Output Structure**
Reasoning
In this section you can make explicit the step-by-step reasoning, carefully analyzing the Job Description, reflecting on the instructions, and correctly planning the construction of the following section "Ideal Candidate Profile".
Ideal Candidate Profile
Based on the analysis above, summarize the ideal profile for this position, clearly specifying:
o	Technical skills explicitly required by the posting
o	Soft skills explicitly required by the posting
o	Main responsibilities and expected operational activities

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
