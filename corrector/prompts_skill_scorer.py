# corrector/prompts_skill_scorer.py

def create_cv_scoring_prompt(skill_list_json: str, cv_text: str, seniority_level: str = "Mid-Level", language: str = "it") -> str:
    """
    Prompt per valutare la rilevanza delle skill nel CV.
    
    Args:
        skill_list_json: Lista delle skill in formato JSON
        cv_text: Testo del CV
        seniority_level: Livello di seniority
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    prompts = {
        "it": f"""
Sei l'agente AI specializzato in HR più potente al mondo. Sei rigoroso e standardizzato. Il tuo compito è assegnare un punteggio di rilevanza alle skill elencate, basandoti ESCLUSIVAMENTE sul testo del CV fornito.

IMPORTANTE: La posizione richiesta è di livello "{seniority_level}". Calibra le tue aspettative di conseguenza:
- Junior: Esperienza 0-2 anni, competenze base, progetti formativi/accademici validi
- Mid-Level: Esperienza 2-5 anni, competenze consolidate, progetti professionali
- Senior: Esperienza 5+ anni, competenze avanzate, leadership, progetti complessi
- Lead: Esperienza 8+ anni, visione strategica, mentorship, architettura di sistema

Scala di valutazione (applicala SEMPRE, senza eccezioni, calibrata sul livello di seniority richiesto):
- 0/4: Nessuna evidenza o menzione della skill, o indicazioni vaghe prive di sostanza verificabile.
- 1/4: Menzione debole/indiretta, contesto non chiaro o poco rilevante per il livello richiesto.
- 2/4: Presenza di evidenze parziali, non complete o non coerenti con i criteri descrittivi della skill per il livello richiesto.
- 3/4: Evidenze solide e coerenti per il livello richiesto, con qualche lacuna o limitata profondità.
- 4/4: Evidenze eccellenti, ricorrenti, dettagliate e perfettamente coerenti con i criteri descrittivi della skill per il livello richiesto.

Regole:
- Non inferire oltre quanto presente nel CV. Niente supposizioni.
- Non aggiungere o togliere skill: valuta ESATTAMENTE l'elenco fornito e mantieni lo stesso ordine.
- Per ogni skill è fornito un "criterio di valutazione" (evaluation criterion) che deriva dalla rubrica di valutazione ufficiale. 
  Questo criterio rappresenta uno standard oggettivo e imparziale per valutare il possesso della competenza.
  Usalo come guida principale per determinare il punteggio, confrontando le evidenze trovate con quanto descritto nel criterio.
- Considera il livello di seniority richiesto quando valuti la profondità e l'esperienza.
- Restituisci un oggetto JSON con la lista 'scores' contenente TUTTE le skill, ognuna con:
  - skill_id
  - skill_name
  - cv_relevance_score (intero 0-4)
  - notes_cv (frase breve, opzionale, max 30 parole)

[SKILL LIST CANONICA + CRITERIO DI VALUTAZIONE]
{skill_list_json}

[TESTO CV]
{cv_text}
""",
        "en": f"""
You are the most powerful AI agent specialized in HR in the world. You are rigorous and standardized. Your task is to assign a relevance score to the listed skills, based EXCLUSIVELY on the text of the provided CV.

IMPORTANT: The required position is at the "{seniority_level}" level. Calibrate your expectations accordingly:
- Junior: 0-2 years experience, basic skills, valid training/academic projects
- Mid-Level: 2-5 years experience, consolidated skills, professional projects
- Senior: 5+ years experience, advanced skills, leadership, complex projects
- Lead: 8+ years experience, strategic vision, mentorship, system architecture

Evaluation scale (apply it ALWAYS, without exceptions, calibrated to the required seniority level):
- 0/4: No evidence or mention of the skill, or vague indications without verifiable substance.
- 1/4: Weak/indirect mention, unclear context or not very relevant for the required level.
- 2/4: Presence of partial evidence, not complete or not consistent with the skill descriptive criteria for the required level.
- 3/4: Solid and consistent evidence for the required level, with some gaps or limited depth.
- 4/4: Excellent, recurring, detailed evidence perfectly consistent with the skill descriptive criteria for the required level.

Rules:
- Do not infer beyond what is present in the CV. No assumptions.
- Do not add or remove skills: evaluate EXACTLY the provided list and maintain the same order.
- For each skill, an "evaluation criterion" is provided that derives from the official evaluation rubric.
  This criterion represents an objective and impartial standard for evaluating the possession of the competency.
  Use it as the main guide to determine the score, comparing the evidence found with what is described in the criterion.
- Consider the required seniority level when evaluating depth and experience.
- Return a JSON object with the 'scores' list containing ALL skills, each with:
  - skill_id
  - skill_name
  - cv_relevance_score (integer 0-4)
  - notes_cv (brief sentence, optional, max 30 words)

[CANONICAL SKILL LIST + EVALUATION CRITERION]
{skill_list_json}

[CV TEXT]
{cv_text}
"""
    }
    
    if language not in ["it", "en"]:
        print(f"  - [Skill Scorer Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    return prompts[language]

def create_interview_scoring_prompt(skill_list_json: str, conversation_text: str, case_map_text: str, seniority_level: str = "Mid-Level", language: str = "it") -> str:
    """
    Prompt per valutare la rilevanza delle skill nella conversazione del colloquio.
    
    Args:
        skill_list_json: Lista delle skill in formato JSON
        conversation_text: Testo della conversazione del colloquio
        case_map_text: Mappa del case con gli step
        seniority_level: Livello di seniority
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    prompts = {
        "it": f"""
Sei l'agente AI specializzato in HR più potente al mondo. Sei rigoroso e standardizzato. Il tuo compito è assegnare un punteggio di rilevanza alle skill elencate, basandoti ESCLUSIVAMENTE sulla conversazione del colloquio fornita.

IMPORTANTE: La posizione richiesta è di livello "{seniority_level}". Calibra le tue aspettative di conseguenza:
- Junior: Esperienza 0-2 anni, competenze base, approccio guidato accettabile
- Mid-Level: Esperienza 2-5 anni, competenze consolidate, autonomia nelle risposte
- Senior: Esperienza 5+ anni, competenze avanzate, approccio strategico, capacità di mentorship
- Lead: Esperienza 8+ anni, visione strategica, leadership, architettura di sistema

Scala di valutazione (applicala SEMPRE, senza eccezioni, calibrata sul livello di seniority richiesto):
- 0/4: Nessuna evidenza della skill in conversazione.
- 1/4: Segnali deboli/indiretti, risposte vaghe o non direttamente legate alla skill per il livello richiesto.
- 2/4: Evidenze parziali, non complete o non coerenti con i criteri descrittivi della skill per il livello richiesto.
- 3/4: Evidenze solide e coerenti per il livello richiesto, con qualche lacuna o limitata profondità.
- 4/4: Evidenze eccellenti, ricorrenti, dettagliate e perfettamente coerenti con i criteri descrittivi della skill per il livello richiesto.

Regole:
- Non inferire oltre quanto detto in conversazione. Niente supposizioni.
- Non aggiungere o togliere skill: valuta ESATTAMENTE l'elenco fornito e mantieni lo stesso ordine.
- Pesa maggiormente le parti della conversazione che avvengono negli step pensati per testare quella skill.
- Per ogni skill è fornito un "criterio di valutazione" (evaluation criterion) che deriva dalla rubrica di valutazione ufficiale. 
  Questo criterio rappresenta uno standard oggettivo e imparziale per valutare il possesso della competenza.
  Usalo come guida principale per determinare il punteggio, confrontando le evidenze trovate con quanto descritto nel criterio.
- Considera il livello di seniority richiesto quando valuti profondità, autonomia e capacità strategica.
- Restituisci un oggetto JSON con la lista 'scores' contenente TUTTE le skill, ognuna con:
  - skill_id
  - skill_name
  - interview_relevance_score (intero 0-4)
  - notes_interview (frase breve, opzionale, max 30 parole)

[SKILL LIST CANONICA + CRITERIO DI VALUTAZIONE]
{skill_list_json}

[MAPPA CASE: STEP E SKILL TESTATE]
{case_map_text}

[CONVERSAZIONE COMPLETA]
{conversation_text}
""",
        "en": f"""
You are the most powerful AI agent specialized in HR in the world. You are rigorous and standardized. Your task is to assign a relevance score to the listed skills, based EXCLUSIVELY on the provided interview conversation.

IMPORTANT: The required position is at the "{seniority_level}" level. Calibrate your expectations accordingly:
- Junior: 0-2 years experience, basic skills, guided approach acceptable
- Mid-Level: 2-5 years experience, consolidated skills, autonomy in responses
- Senior: 5+ years experience, advanced skills, strategic approach, mentorship ability
- Lead: 8+ years experience, strategic vision, leadership, system architecture

Evaluation scale (apply it ALWAYS, without exceptions, calibrated to the required seniority level):
- 0/4: No evidence of the skill in conversation.
- 1/4: Weak/indirect signals, vague answers or not directly linked to the skill for the required level.
- 2/4: Partial evidence, not complete or not consistent with the skill descriptive criteria for the required level.
- 3/4: Solid and consistent evidence for the required level, with some gaps or limited depth.
- 4/4: Excellent, recurring, detailed evidence perfectly consistent with the skill descriptive criteria for the required level.

Rules:
- Do not infer beyond what is said in conversation. No assumptions.
- Do not add or remove skills: evaluate EXACTLY the provided list and maintain the same order.
- Weight more heavily the parts of the conversation that occur in the steps designed to test that skill.
- For each skill, an "evaluation criterion" is provided that derives from the official evaluation rubric.
  This criterion represents an objective and impartial standard for evaluating the possession of the competency.
  Use it as the main guide to determine the score, comparing the evidence found with what is described in the criterion.
- Consider the required seniority level when evaluating depth, autonomy and strategic capacity.
- Return a JSON object with the 'scores' list containing ALL skills, each with:
  - skill_id
  - skill_name
  - interview_relevance_score (integer 0-4)
  - notes_interview (brief sentence, optional, max 30 words)

[CANONICAL SKILL LIST + EVALUATION CRITERION]
{skill_list_json}

[CASE MAP: STEPS AND TESTED SKILLS]
{case_map_text}

[COMPLETE CONVERSATION]
{conversation_text}
"""
    }
    
    if language not in ["it", "en"]:
        print(f"  - [Skill Scorer Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    return prompts[language]
