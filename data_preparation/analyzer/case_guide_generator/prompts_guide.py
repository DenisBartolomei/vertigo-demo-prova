# System prompt per definire il ruolo dell'LLM
SYSTEM_PROMPT = {
    "it": """Sei un agente AI esperto nell'arricchimento contestuale.
Ricevi un report verboso che descrive i requisiti e le aspettative per una posizione lavorativa.  
Il tuo compito è creare un report che supporti la stesura di Case utilizzati per la verifica dei requisiti nei candidati. In particolare, questi Case saranno composti da un testo iniziale dove si descrive la situazione e si dà un macro-obiettivo, uniti a una serie di "reasoning steps" che sono semplicemente una decomposizione del processo per raggiungere la soluzione.
Per creare il report che guiderà la stesura dei Case ti è richiesto di:
o	Leggere attentamente il testo.
o	Identificare i requisiti da esplorare, dalle sezioni dell'input ICP "Competenze tecniche richieste esplicitamente dall'annuncio" e "Competenze trasversali richieste esplicitamente dall'annuncio (escluse le lingue)".
o	Attenzione: si intendono solo quei requisiti che sono verificabili attraverso attività di test, non si intendono requisiti quali lauree, titoli, possesso di certificazioni.
o	Per tutti i requisiti individuati, definire delle modalità tramite cui ritieni più opportuno eseguire la verifica all'interno dei Case.
o	Sintetizzare i risultati della ricerca in un report finale coerente, in linguaggio naturale, utile per costruire test tecnici e comportamentali sul ruolo.""",
    "en": """You are an AI agent expert in contextual enrichment.
You receive a verbose report describing the requirements and expectations for a job position.
Your task is to create a report that supports the drafting of Case Studies used to verify requirements in candidates. In particular, these Cases will be composed of an initial text describing the situation and giving a macro-objective, combined with a series of "reasoning steps" which are simply a decomposition of the process to reach the solution.
To create the report that will guide the drafting of Cases you are required to:
o	Carefully read the text.
o	Identify the requirements to explore, from the ICP input sections "Technical skills explicitly required by the posting" and "Soft skills explicitly required by the posting (excluding languages)".
o	Attention: only those requirements that are verifiable through testing activities are meant, not requirements such as degrees, titles, possession of certifications.
o	For all identified requirements, define the methods by which you consider most appropriate to perform verification within the Cases.
o	Summarize the research results in a coherent final report, in natural language, useful for building technical and behavioral tests on the role."""
}

def create_case_guide_prompt(icp_text: str, seniority_level: str, hr_special_needs: str, language: str = "it") -> str:
    """
    Prompt per generare la guida alla creazione dei case con integrazione di HR Needs.
    
    Args:
        icp_text: Il testo dell'ICP
        seniority_level: Livello di seniority richiesto
        hr_special_needs: Indicazioni speciali da parte dell'HR
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    prompts = {
        "it": """
**Istruzioni**:
o	Analizza passo-passo la ICP riportata di seguito.
o	Identifica con spirito critico, tutti gli elementi chiave da valutare nei test. Non dedurre o inventare nulla.
o	Tieni in considerazione sempre il livello di seniority riportato di seguito per calibrare le esigenze dei test.
o	Non usare ulteriore testo, oltre a quanto richiesto dall'output.
o	ATTENZIONE: la sezione della ICP "**Responsabilità principali e attività operative attese**" non rappresenta un requisito per cui sviluppare le modalità di test, bensì rappresenta le attività tramite cui costruire le modalità di test dei requisiti.
o	Per definire le modalità di verifica dei requisiti, basati (se presenti) sulle responsabilità / attività operative attese per la posizione.
o	Contieni l'output entro i 2000 token.

**Indicazioni Speciali HR**
{hr_block}
---
**Esempio di report**
Guida alla generazione ed esecuzione dei test.
o	*Gestione Progetti AI/Digital/OpEx*: Simulare la pianificazione e l'esecuzione di un progetto tecnologico, includendo la gestione delle risorse e la mitigazione dei rischi.
o	*Conoscenza Base di Architettura IT*: Testare la capacità di progettare soluzioni IT che integrino componenti AI, considerando aspetti come la sicurezza e la scalabilità.
o	*Problem solving*: Sfruttare situazioni ambigue, con problemi da risolvere e challenge logico.
---
**PROFILO DEL CANDIDATO IDEALE (ICP):**
{icp_text}

**LIVELLO DI SENIORITY RICHIESTO:**
{seniority_level}
""",
        "en": """
**Instructions**:
o	Analyze step-by-step the ICP reported below.
o	Identify with a critical spirit all key elements to be evaluated in the tests. Do not deduce or invent anything.
o	Always take into account the seniority level reported below to calibrate the test requirements.
o	Do not use additional text beyond what is required by the output.
o	ATTENTION: the ICP section "**Main responsibilities and expected operational activities**" does not represent a requirement for which to develop test methods, but rather represents the activities through which to build the test methods for the requirements.
o	To define the methods for verifying requirements, base them (if present) on the responsibilities/operational activities expected for the position.
o	Keep the output within 2000 tokens.

**HR Special Instructions**
{hr_block}
---
**Report Example**
Guide to test generation and execution.
o	*AI/Digital/OpEx Project Management*: Simulate the planning and execution of a technology project, including resource management and risk mitigation.
o	*Basic IT Architecture Knowledge*: Test the ability to design IT solutions that integrate AI components, considering aspects such as security and scalability.
o	*Problem solving*: Leverage ambiguous situations, with problems to solve and logical challenges.
---
**IDEAL CANDIDATE PROFILE (ICP):**
{icp_text}

**REQUIRED SENIORITY LEVEL:**
{seniority_level}
"""
    }
    
    # Validate language
    if language not in ["it", "en"]:
        print(f"  - [Case Guide Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    # Format HR block
    hr_block = hr_special_needs.strip() if hr_special_needs else (
        "Nessuna indicazione speciale fornita." if language == "it" else "No special instructions provided."
    )
    
    return prompts[language].format(hr_block=hr_block, icp_text=icp_text, seniority_level=seniority_level)
