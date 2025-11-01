SYSTEM_PROMPT = {
    "it": """Sei un Senior Talent Manager con un'eccezionale capacità di sintesi e giudizio. Il tuo compito è riconciliare due diverse valutazioni di un candidato - una basata sul suo curriculum e una basata sulla sua performance in un test pratico - per creare un profilo di valutazione finale, equilibrato e definitivo.""",
    "en": """You are a Senior Talent Manager with exceptional synthesis and judgment skills. Your task is to reconcile two different evaluations of a candidate - one based on their resume and one based on their performance in a practical test - to create a final, balanced and definitive evaluation profile."""
}

def create_consolidation_prompt(cv_analysis_report: str, case_evaluation_report: str, language: str = "it") -> str:
    """
    Assembla il prompt per consolidare i due report di valutazione.
    """
    prompts = {
        "it": f"""
**Obiettivo**
Analizza i due report di valutazione forniti di seguito. Il primo (`ANALISI CV`) è una valutazione basata sulle esperienze e competenze dichiarate nel curriculum del candidato. Il secondo (`VALUTAZIONE CASE STUDY`) è una valutazione della sua performance pratica durante un caso di studio simulato.

Il tuo compito è creare un unico **Report di Valutazione Consolidato**.

**Istruzioni per la Generazione:**

Integra il report dell'analisi CV con il report del colloquio per produrre un profilo sintetico del candidato. Struttura la risposta come segue:

1. Profilo generale: una frase riassuntiva che descrive il candidato
2. Punti di forza (motivazione, skill tecniche, soft skill)
3. Gap rilevanti (espliciti)
4. Coerenza tra CV e colloquio

Concludi con una "diagnosi finale" di 3 righe con tono costruttivo e realistico.

Attenzione: ricorda che il tuo obiettivo principale è la verifica delle skill, è quindi anche importante che vengano qua verificati allineamenti / disallineamenti fra analisi del CV e valutazione del case study. Per esempio, alcune skill che emergono nel CV potrebbero non essere state messe in pratica correttamente dal candidato nel Case, o viceversa.
---
**INPUTS**

[REPORT 1: ANALISI CV]
{cv_analysis_report}

---

[REPORT 2: VALUTAZIONE DEL CASE STUDY]
{case_evaluation_report}
""",
        "en": f"""
**Objective**
Analyze the two evaluation reports provided below. The first (`CV ANALYSIS`) is an evaluation based on the experiences and skills declared in the candidate's resume. The second (`CASE STUDY EVALUATION`) is an evaluation of their practical performance during a simulated case study.

Your task is to create a single **Consolidated Evaluation Report**.

**Generation Instructions:**

Integrate the CV analysis report with the interview report to produce a synthetic candidate profile. Structure the response as follows:

1. General profile: a summary sentence describing the candidate
2. Strengths (motivation, technical skills, soft skills)
3. Relevant gaps (explicit)
4. Consistency between CV and interview

Conclude with a "final diagnosis" of 3 lines with a constructive and realistic tone.

Attention: remember that your main objective is the verification of skills, so it is also important that alignments/misalignments between CV analysis and case study evaluation are verified here. For example, some skills that emerge in the CV might not have been correctly put into practice by the candidate in the Case, or vice versa.
---
**INPUTS**

[REPORT 1: CV ANALYSIS]
{cv_analysis_report}

---

[REPORT 2: CASE STUDY EVALUATION]
{case_evaluation_report}
"""
    }
    
    if language not in ["it", "en"]:
        print(f"  - [Consolidator Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    return prompts[language]
