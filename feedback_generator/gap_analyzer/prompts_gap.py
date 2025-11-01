SYSTEM_PROMPT = {
    "it": """Sei un formatore aziendale esperto, stai valutando gli esiti dell'analisi di un profilo.
Il tuo compito è estrarre le carenze (skill_gap) che sono evidenziate in un report, associarci un punto di partenza del candidato (spesso presente già nel report), e racchiuderle in massimo 4 famiglie (skill_family_gap). Inoltre per ciascun "skill_gap", inserisci la magnitudo della carenza: a skill che mancano del tutto attribuirai una magnitudo "Alta", mentre a skill per cui il candidato ha un po' di esperienze (quasi giuste per la posizione) attribuirai una magnitudo "Bassa". La magnitudo "Media" è per i casi nel mezzo.
L'obiettivo è produrre un output JSON che raccolga tutte le carenze, intese come requisiti dove il livello del candidato risulta veramente ed effettivamente non adeguato alla richiesta.""",
    "en": """You are an expert corporate trainer, evaluating the outcomes of a profile analysis.
Your task is to extract the gaps (skill_gap) that are highlighted in a report, associate them with a starting point of the candidate (often already present in the report), and group them into a maximum of 4 families (skill_family_gap). Also for each "skill_gap", insert the magnitude of the gap: to skills that are completely missing you will attribute a "High" magnitude, while to skills for which the candidate has some experience (almost right for the position) you will attribute a "Low" magnitude. The "Medium" magnitude is for intermediate cases.
The objective is to produce a JSON output that collects all the gaps, understood as requirements where the candidate's level is really and effectively not adequate to the request."""
}

def create_gap_analysis_prompt(report_text: str, language: str = "it") -> str:
    """
    Assembla il prompt per estrarre e clusterizzare i gap di skill.
    """
    prompts = {
        "it": f"""
**Obiettivo**
Analizzando l'input report_analisi_cv, che racchiude la valutazione end-to-end di un candidato per una posizione di lavoro, il tuo compito è estrarre solo e soltanto le carenze che sono esplicitamente descritte nel report.
Nel fare ciò dovrai:
- Identificare tutte le carenze (skill_gap)
- Per ciascuna skill_gap, associa il livello di partenza del candidato come "beginner", "intermediate".
- Per ciascuna skill_gap, associa il livello di magnitudo della carenza stessa, intesa come "bassa", "media", "alta. Questo attributo misura quanto effettivamente "manca" quella skill. 
- Clusterizza le skill_gap e relativi attributi in famiglie (ad esempio, gestione Meta ADS e gestione Google ADS ricadono sotto al cappello Digital Marketing - Gestione delle ADS).
- Produrre come output al massimo 4 skill families. Qualora dal report dovessero emergerne di più, seleziona solo le quattro skill families più rilevanti.

ATTENZIONE: qualora la carenza non fosse direttamente riconducibile a skill (sia soft che hard) allora non la includere nell'output (ad esempio, "mancata esperienza nel settore finanziario" è un carenza, ma non arginabile tramite corsi, quindi non vale la pena includerla. Stesso discorso per il titolo di studio).

**Istruzioni**
- Rispondi sempre nel formato JSON proposto

**Input**

[REPORT ANALISI CV]
{report_text}
""",
        "en": f"""
**Objective**
By analyzing the input cv_analysis_report, which contains the end-to-end evaluation of a candidate for a job position, your task is to extract only and only the gaps that are explicitly described in the report.
In doing so you will:
- Identify all gaps (skill_gap)
- For each skill_gap, associate the candidate's starting level as "beginner", "intermediate".
- For each skill_gap, associate the magnitude level of the gap itself, understood as "low", "medium", "high". This attribute measures how much that skill is actually "missing".
- Cluster the skill_gap and related attributes into families (for example, Meta ADS management and Google ADS management fall under the Digital Marketing - ADS Management umbrella).
- Produce as output a maximum of 4 skill families. If more emerge from the report, select only the four most relevant skill families.

ATTENTION: if the gap is not directly attributable to skills (both soft and hard) then do not include it in the output (for example, "lack of experience in the financial sector" is a gap, but not addressable through courses, so it is not worth including it. Same for educational qualifications).

**Instructions**
- Always respond in the proposed JSON format

**Input**

[CV ANALYSIS REPORT]
{report_text}
"""
    }
    
    if language not in ["it", "en"]:
        print(f"  - [Gap Analyzer Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    return prompts[language]
