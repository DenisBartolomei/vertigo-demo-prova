# System prompt per definire il ruolo dell'LLM
SYSTEM_PROMPT = {
    "it": """Sei un agente AI esperto nell'interpretazione di documenti aziendali, con il fine di estrarre spunti per la generazione di use-case che siano affini alle attività aziendali.
Non lasci mai trasparire nel report finale dati sensibili.""",
    "en": """You are an AI agent expert in interpreting corporate documents, with the aim of extracting insights for generating use-cases that are aligned with business activities.
You never reveal sensitive data in the final report."""
}

def create_kb_synthesis_prompt(icp_text: str, kb_content: str, language: str = "it") -> str:
    """
    Assembla il prompt per sintetizzare la Knowledge Base in relazione all'ICP.
    
    Args:
        icp_text: Il testo dell'ICP
        kb_content: Contenuto della knowledge base
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    prompts = {
        "it": """
Data l'ICP riportata di seguito, estrai insight specifici ed effettivamente connessi alla ICP dalla seguente Knowledge Base collegata. Alcuni esempi di insight:
o	Sintesi delle modalità di applicazione delle responsabilità e delle skill riportate nel report ICP ai progetti e attività interni. Vogliamo prendere spunto da documenti reali per guidare la generazione di use-case, per la verifica di competenze, che siano affini al mondo dell'azienda.
o	Eventuali ulteriori insight concreti che ritieni utili.
Sintetizza i risultati rilevanti in un report autoconsistente che verrà usato da un esperto esaminatore per costruire le giuste domande.
---
**Istruzioni**:
o	Analizzare passo-passo la ICP riportata di seguito.
o	Pianifica un utilizzo consono della documentazione a disposizione.
o	Utilizza la documentazione per attingere a progetti svolti e documenti prodotti dal team di riferimento.
o	Non lasciar trapelare alcun tipo di dato reale e potenzialmente confidenziale dell'azienda.
o	Non usare emoji.
o	Usa la struttura di output riportata di seguito.
---

**Struttura dell'output**

Ragionamento
Utilizza questa sezione per pianificare la costruzione del report e approfondire passo per passo quanto richiesto nelle istruzioni

Knowledge Base Insight
In questa sezione è contenuto il report che, con brevi paragrafi, sintetizza i progetti e le attività estratte dalla documentazione, da cui prendere spunto e senza l'utilizzo di dati particolarmente sensibili.
Attenzione: Non produrre ulteriore testo oltre alle due parti sopra citate. Niente introduzioni o frasi conclusive ulteriori agli output richiesti
---
**DOCUMENTAZIONE (KNOWLEDGE BASE):**
{kb_content}

**PROFILO DEL CANDIDATO IDEALE (ICP):**
{icp_text}
""",
        "en": """
Given the ICP reported below, extract specific insights effectively connected to the ICP from the following linked Knowledge Base. Some examples of insights:
o	Summary of the methods of application of the responsibilities and skills reported in the ICP report to internal projects and activities. We want to draw inspiration from real documents to guide the generation of use-cases, for skills verification, that are aligned with the company's world.
o	Any additional concrete insights you consider useful.
Summarize the relevant results in a self-consistent report that will be used by an expert examiner to construct the right questions.
---
**Instructions**:
o	Analyze step-by-step the ICP reported below.
o	Plan an appropriate use of the available documentation.
o	Use the documentation to draw on projects carried out and documents produced by the reference team.
o	Do not reveal any type of real and potentially confidential company data.
o	Do not use emojis.
o	Use the output structure reported below.
---

**Output Structure**

Reasoning
Use this section to plan the construction of the report and deepen step by step what is required in the instructions

Knowledge Base Insight
This section contains the report that, with brief paragraphs, summarizes the projects and activities extracted from the vertical documentation, from which to take inspiration and without the use of particularly sensitive data.
Attention: Do not produce additional text beyond the two parts mentioned above. No introductions or additional conclusive sentences beyond the required outputs
---
**DOCUMENTATION (KNOWLEDGE BASE):**
{kb_content}

**IDEAL CANDIDATE PROFILE (ICP):**
{icp_text}
"""
    }
    
    # Validate language
    if language not in ["it", "en"]:
        print(f"  - [KB Summarizer Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    return prompts[language].format(kb_content=kb_content, icp_text=icp_text)
