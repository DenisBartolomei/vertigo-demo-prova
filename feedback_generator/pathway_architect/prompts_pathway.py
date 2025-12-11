SYSTEM_PROMPT = {
    "it": """Sei un Career Coach AI e un formatore esperto. Il tuo obiettivo è analizzare una grande quantità di dati su un candidato e produrre un report di feedback finale che sia costruttivo, empatico e orientato all'azione. Devi trasformare un'analisi tecnica in un consiglio di carriera personalizzato e di valore.""",
    "en": """You are an AI Career Coach and expert trainer. Your goal is to analyze a large amount of data about a candidate and produce a final feedback report that is constructive, empathetic and action-oriented. You must transform a technical analysis into personalized and valuable career advice."""
}

# La funzione e il prompt sono stati riscritti per gestire i report separati e la nuova struttura di output.

def create_final_report_prompt(
    cv_analysis_report: str,
    case_evaluation_report: str,
    enriched_gaps_json_str: str,
    candidate_name: str,
    target_role: str,
    language: str = "it"
) -> str:
    """
    Assembla il prompt per generare il contenuto del report finale in PDF con la nuova struttura.
    """
    prompts = {
        "it": f"""
**Obiettivo**
Analizza i dati forniti per creare un report di feedback completo e personalizzato per un candidato. Il report deve essere strutturato in sezioni distinte come descritto di seguito. Trattandosi di un report che riceverà il candidato, usa un linguaggio professionale e utilizza la seconda persona singolare (tu).

**Dati a Disposizione:**
1.  **Report Analisi CV:** Una valutazione basata esclusivamente sulle esperienze e competenze dichiarate nel curriculum del candidato.
2.  **Report Valutazione Colloquio:** Una valutazione della performance pratica del candidato durante un caso di studio simulato.
3.  **Analisi dei Gap e Corsi Suggeriti:** Nei dati strutturati di seguito sono elencate le carenze complessive e una lista di corsi potenzialmente utili.
4.  **Dati Candidato:** Nome (`{candidate_name}`) e Ruolo Target (`{target_role}`).

**Struttura dell'output (deve essere un JSON con chiavi esattamente come elencate):**
- `candidate_name`: "{candidate_name}"
- `target_role`: "{target_role}"
- `profile_summary`: Profilo sintetico di 2-3 righe che fonde le impressioni da CV e colloquio.
- `cv_analysis_outcome`: Paragrafo che sintetizza l'esito dell'analisi del solo CV - 2-3 righe.
- `interview_outcome`: Paragrafo che sintetizza l'esito della performance nel solo colloquio, evidenziando cosa è stato confermato o smentito rispetto al CV - 2-3 righe.
- `market_benchmark`: Paragrafo che confronta il profilo del candidato con le tendenze di mercato disponibili. Se non hai dati, spiega l'assenza usando la lingua richiesta.
- `suggested_pathway`: Lista ordinata e logica di corsi selezionati. Se nessun corso risulta pertinente, la lista deve essere vuota.

**Istruzioni per la Generazione:**

0.  Usa sempre e solo le chiavi JSON indicate nella sezione "Struttura dell'output". Non tradurre o rinominare le chiavi.

1.  **Per la sezione "profile_summary":**
    *   Crea una sintesi generale ed equilibrata del candidato, tenendo conto di entrambe le fonti (CV e colloquio).
2.  **Per la sezione "cv_analysis_outcome":**
    *   Leggi il "Report Analisi CV" e sintetizza i suoi punti chiave in un paragrafo. Concentrati su ciò che il CV comunica in termini di potenziale, esperienza e competenze dichiarate.
3.  **Per la sezione "interview_outcome":**
    *   Leggi il "Report Valutazione Colloquio". Descrivi come ti sei comportato nella prova pratica. Metti in evidenza le competenze che hai dimostrato efficacemente e quelle dove sono emerse difficoltà. Fai un confronto costruttivo con quanto emergeva dal CV.
4.  **Per la sezione "suggested_pathway":**
    *   Analizza la lista di "corsi suggeriti" nei dati strutturati per ciascuna skill family.
    *   Seleziona fino a 2 corsi per famiglia di gap presenti nei dati strutturati ANALISI DEI GAP E CORSI SUGGERITI che creino il percorso più logico ed efficiente.
    *   Ordina i corsi in modo sequenziale (es. Beginner prima di Advanced).
    *   Per ogni corso, giustifica brevemente perché è stato scelto e a quale gap risponde.
    *   Metti nel report ALMENO 3 corsi

**Formato di Output**
Rispondi esclusivamente con un oggetto JSON che rispetti la struttura richiesta.

---
**INPUTS**

[REPORT 1: ANALISI CV]
{cv_analysis_report}

---

[REPORT 2: VALUTAZIONE COLLOQUIO]
{case_evaluation_report}

---

[ANALISI DEI GAP E CORSI SUGGERITI]
Nei dati strutturati di seguito sono contenuti i gap e i corsi suggeriti:
{enriched_gaps_json_str}
""",
        "en": f"""
**Objective**
Analyze the provided data to create a complete and personalized feedback report for a candidate. The report must be structured in distinct sections as described below. Since this is a report that the candidate will receive, use professional language and use the second person singular (you).

**Available Data:**
1.  **CV Analysis Report:** An evaluation based exclusively on the experiences and skills declared in the candidate's resume.
2.  **Interview Evaluation Report:** An evaluation of the candidate's practical performance during a simulated case study.
3.  **Gap Analysis and Suggested Courses:** In the structured data below are listed the overall gaps and a list of potentially useful courses.
4.  **Candidate Data:** Name (`{candidate_name}`) and Target Role (`{target_role}`).

**Output Structure (must be a JSON):**
- `candidate_name`: "{candidate_name}"
- `target_role`: "{target_role}"
- `profile_summary`: Synthetic profile of 2-3 lines that merges impressions from CV and interview.
- `cv_analysis_outcome`: Paragraph that summarizes the outcome of the CV analysis only - 2-3 lines.
- `interview_outcome`: Paragraph that summarizes the outcome of the performance in the interview only, highlighting what was confirmed or refuted compared to the CV - 2-3 lines.
- `market_benchmark`: Paragraph that compares the candidate profile with the available market trends. If you lack data, explain the absence using the requested language.
- `suggested_pathway`: Ordered and logical list of selected courses. If no course is relevant, the list must be empty.

**Generation Instructions:**

0.  Always and only use the JSON keys indicated in the "Output Structure" section. Do not translate or rename the keys.

1.  **For the "profile_summary" section:**
    *   Create a general and balanced synthesis of the candidate, taking into account both sources (CV and interview).
2.  **For the "cv_analysis_outcome" section:**
    *   Read the "CV Analysis Report" and summarize its key points in a paragraph. Focus on what the CV communicates in terms of potential, experience and declared skills.
3.  **For the "interview_outcome" section:**
    *   Read the "Interview Evaluation Report". Describe how you performed in the practical test. Highlight the skills you demonstrated effectively and those where difficulties emerged. Make a constructive comparison with what emerged from the CV.
4.  **For the "suggested_pathway" section:**
    *   Analyze the list of "suggested courses" in the structured data for each skill family.
    *   Select up to 2 courses per gap family present in the structured data GAP ANALYSIS AND SUGGESTED COURSES that create the most logical and efficient path.
    *   Sort courses sequentially (e.g. Beginner before Advanced).
    *   For each course, briefly justify why it was chosen and which gap it addresses.
    *   Put AT LEAST 3 courses in the report

**Output Format**
Reply exclusively with a JSON object that respects the required structure.

---
**INPUTS**

[REPORT 1: CV ANALYSIS]
{cv_analysis_report}

---

[REPORT 2: INTERVIEW EVALUATION]
{case_evaluation_report}

---

[GAP ANALYSIS AND SUGGESTED COURSES]
In the structured data below are contained the gaps and suggested courses:
{enriched_gaps_json_str}
"""
    }
    
    if language not in ["it", "en"]:
        print(f"  - [Pathway Architect Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    return prompts[language]
