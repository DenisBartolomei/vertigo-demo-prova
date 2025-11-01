def create_cv_analysis_prompt(cv_text: str, job_description_text: str, hr_special_needs: str, language: str = "it") -> str:
    """
    Assembla il prompt completo per l'analisi del CV, combinando istruzioni, 
    passi di ragionamento e i dati specifici del candidato e dell'annuncio.
    
    Args:
        cv_text: Il testo del CV del candidato
        job_description_text: Il testo della job description
        hr_special_needs: Indicazioni speciali da parte dell'HR
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    prompts = {
        "it": """
Istruzioni
•	Segui sempre il formato e i passi di ragionamento indicati.
•	Non fornire suggerimenti o raccomandazioni operative al candidato, devi solo eseguire una valutazione.
•	Integra eventuali "Indicazioni Speciali" date dall'HR, trattandole come priorità. Ad esempio, se il CV risulta allineato al 100% all'annuncio di lavoro, ma l'HR impone che qualsiasi CV senza laurea in ingegneria non è valido, allora tu devi considerare il CV come privo di valore. Mentre se invece l'input HR è solo una "preferenza" allora trattala come un qualsiasi altro requisito.
•	Scrivi nella stessa lingua dell'annuncio di lavoro (italiano o inglese).
•	Non confondere i requisiti con le attività / responsabilità attese per il ruolo.
•	Mantieni uno stile professionale ma leggibile rapidamente, senza abusare dei punti elenco (evita testi densi o prolissi).
•	Usa solo testo, niente emoji, immagini o icone.
•	Se una sezione è particolarmente povera di contenuti, segnalalo brevemente ma non inventare informazioni.
•	Sii critico, segnala sia punti di allineamento ma anche le carenze.
•	Se sono presenti requisiti chiari, non inventare o dedurre ulteriori informazioni.
•	Attenzione: distingui con cura ciò che si intende come "Requisito" richiesto dalla posizione e ciò che invece è un'attività o responsabilità tipica della posizione (queste sono inserite nella sezione 2.2. dell'output)

Formato dell'Output
Usa sempre il titolo REPORT.
Produci l'output nella lingua in cui è scritto l'annuncio di lavoro, ma mantieni i titolo sempre invariati (che ti sono forniti sia per la versione italiana, che inglese).

La sezione REPORT avrà la seguente struttura:

1. Analisi della struttura del CV / Resume structural analysis (Max 200 token)
Valuta:
    •	Ordine e chiarezza delle sezioni.
    •	Qualità visiva e leggibilità (ad esempio, CV più lunghi di una pagina sono difficili da leggere).
    •	Presenza di errori formali, grammaticali o incoerenze (non considerare mai le date nelle analisi).
    •	Bilanciamento dei contenuti (ad esempio, vogliamo evitare che siano usate eccessive parole per esprimere pochi concetti, magari poco rilevanti).
    •	Completezza delle sezioni, che dovrebbero essere almeno: (1) breve descrizione iniziale; (2) contatti personali; (3) esperienze lavorative; (4) formazione; (5) principali skill hard e soft.
    •	Eventuali punti critici segnalati nella sezione "indicazioni speciali" dall'HR. 
(Usa brevi paragrafi per migliorare la leggibilità.)

2. Analisi dei contenuti / Content analysis (Max 600 token)

2.1. Verifica dei requisiti / Requirements 
In questo paragrafo valuterai l'allineamento tra i requisiti richiesti dall'annuncio e quanto presente nel CV, seguendo la traccia di seguito:
    o	Requisiti tecnici richiesti - per ciascuna carenza individuata segnala anche lo stato in cui si trova il candidato in base a quanto scritto nel CV.
    o	Requisiti trasversali (soft skills rilevanti per il ruolo).
    o	Altri requisiti espliciti (es. titoli di studio, certificazioni, settori di provenienza, etc.).
    o	Tool e tecnologie specifiche richieste.
    o	Anni di esperienza richiesti.

2.2. Verifica della compatibilità con le responsabilità / Responsibility alignment (Max 300 token)
Valuta allineamenti e disallineamenti tra le attività e/o responsabilità scritte nell'annuncio di lavoro (solo se presenti) rispetto a quanto riportato nel CV, seguendo lo schema di seguito:
    o	Responsabilità principali e attività operative di pertinenza della posizione vs Responsabilità e attività presenti nel CV.
    o	Contesto organizzativo: affinità del team di appartenenza e ruolo del team in azienda con le attività, i ruoli e i team riportati nel CV (se desumibile).

3. Il tuo compito adesso è estrarre le esperienze lavorative dal testo fornito e restituirle in un formato JSON strutturato.
Segui queste regole in modo RIGOROSO:
    o  **FORMATO DATE**: Le date `start_date` e `end_date` DEVONO essere nel formato numerico **YYYY-MM-DD**.
        - Se il giorno non è specificato nel CV, usa sempre '01'.
        - Esempio: "Settembre 2022" deve diventare "2022-09-01". "Dal 2020" deve diventare "2020-01-01".
    o  **DATA FINE**: Se l'esperienza è ancora in corso (es. "Presente", "Oggi", "in corso"), il valore di `end_date` deve essere la stringa esatta "present".
    o  **CONTENUTO**: Estrai SOLO le esperienze lavorative. IGNORA completamente istruzione, certificazioni, volontariato, hobby e qualsiasi dato personale (nome, telefono, email, indirizzo).
    o  **OUTPUT**: Restituisci ESCLUSIVAMENTE l'oggetto JSON, senza alcun testo o spiegazione prima o dopo.

    Ecco la struttura JSON che DEVI seguire:
    {{
      "current_position": "Titolo della posizione lavorativa più recente",
      "experience": [
        {{
          "title": "Titolo della posizione",
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD o present",
          "description": "Descrizione sintetica delle responsabilità e dei risultati."
        }}
      ]
    }}
    ---
DATI DI INPUT DA ANALIZZARE:

[ANNUNCIO DI LAVORO]
{job_description_text}

[CV CANDIDATO]
{cv_text}

[INDICAZIONI SPECIALI HR]
{hr_guidance}
---
Inizia ora la tua analisi.
""",
        "en": """
Instructions
•	Always follow the format and reasoning steps indicated.
•	Do not provide operational suggestions or recommendations to the candidate, you must only perform an evaluation.
•	Integrate any "Special Instructions" given by HR, treating them as a priority. For example, if the CV is 100% aligned with the job posting, but HR requires that any CV without an engineering degree is not valid, then you must consider the CV as having no value. Whereas if the HR input is only a "preference" then treat it as any other requirement.
•	Write in the same language as the job posting (Italian or English).
•	Do not confuse requirements with expected activities/responsibilities for the role.
•	Maintain a professional but quickly readable style, without abusing bullet points (avoid dense or wordy texts).
•	Use only text, no emojis, images or icons.
•	If a section is particularly poor in content, briefly report it but do not invent information.
•	Be critical, point out both alignment points but also shortcomings.
•	If there are clear requirements, do not invent or deduce additional information.
•	Attention: carefully distinguish what is meant as a "Requirement" required by the position and what is instead an activity or typical responsibility of the position (these are inserted in section 2.2. of the output)

Output Format
Always use the title REPORT.
Produce the output in the language in which the job posting is written, but always keep the titles unchanged (which are provided to you for both the Italian and English version).

The REPORT section will have the following structure:

1. Analisi della struttura del CV / Resume structural analysis (Max 200 tokens)
Evaluate:
    •	Order and clarity of sections.
    •	Visual quality and readability (for example, CVs longer than one page are difficult to read).
    •	Presence of formal, grammatical errors or inconsistencies (never consider dates in the analyses).
    •	Balance of content (for example, we want to avoid using excessive words to express few concepts, perhaps not very relevant).
    •	Completeness of sections, which should be at least: (1) brief initial description; (2) personal contacts; (3) work experiences; (4) education; (5) main hard and soft skills.
    •	Any critical points reported in the "special instructions" section by HR.
(Use short paragraphs to improve readability.)

2. Analisi dei contenuti / Content analysis (Max 600 tokens)

2.1. Verifica dei requisiti / Requirements
In this paragraph you will evaluate the alignment between the requirements required by the posting and what is present in the CV, following the outline below:
    o	Required technical requirements - for each identified shortcoming, also report the state in which the candidate is based on what is written in the CV.
    o	Cross-cutting requirements (soft skills relevant to the role).
    o	Other explicit requirements (e.g. educational qualifications, certifications, sectors of origin, etc.).
    o	Specific tools and technologies required.
    o	Years of experience required.

2.2. Verifica della compatibilità con le responsabilità / Responsibility alignment (Max 300 tokens)
Evaluate alignments and misalignments between the activities and/or responsibilities written in the job posting (only if present) compared to what is reported in the CV, following the scheme below:
    o	Main responsibilities and operational activities pertaining to the position vs Responsibilities and activities present in the CV.
    o	Organizational context: affinity of the team membership and role of the team in the company with the activities, roles and teams reported in the CV (if inferable).

3. Your task now is to extract work experiences from the provided text and return them in a structured JSON format.
Follow these rules STRICTLY:
    o  **DATE FORMAT**: The dates `start_date` and `end_date` MUST be in the numeric format **YYYY-MM-DD**.
        - If the day is not specified in the CV, always use '01'.
        - Example: "September 2022" must become "2022-09-01". "From 2020" must become "2020-01-01".
    o  **END DATE**: If the experience is still ongoing (e.g. "Present", "Current", "ongoing"), the value of `end_date` must be the exact string "present".
    o  **CONTENT**: Extract ONLY work experiences. COMPLETELY IGNORE education, certifications, volunteering, hobbies and any personal data (name, phone, email, address).
    o  **OUTPUT**: Return EXCLUSIVELY the JSON object, without any text or explanation before or after.

    Here is the JSON structure you MUST follow:
    {{
      "current_position": "Title of the most recent work position",
      "experience": [
        {{
          "title": "Position title",
          "start_date": "YYYY-MM-DD",
          "end_date": "YYYY-MM-DD or present",
          "description": "Brief description of responsibilities and results."
        }}
      ]
    }}
    ---
INPUT DATA TO ANALYZE:

[JOB POSTING]
{job_description_text}

[CANDIDATE CV]
{cv_text}

[HR SPECIAL INSTRUCTIONS]
{hr_guidance}
---
Begin your analysis now.
"""
    }
    
    # Validate language
    if language not in ["it", "en"]:
        print(f"  - [Analyzer Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    # Gestisce il caso in cui non ci siano indicazioni speciali dall'HR
    hr_guidance = hr_special_needs if hr_special_needs else (
        "Nessuna indicazione speciale fornita." if language == "it" else "No special instructions provided."
    )
    
    return prompts[language].format(
        job_description_text=job_description_text,
        cv_text=cv_text,
        hr_guidance=hr_guidance
    )
