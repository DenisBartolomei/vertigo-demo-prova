# corrector/prompts_skill_scorer.py

def create_cv_scoring_prompt(skill_list_json: str, cv_text: str, seniority_level: str = "Mid-Level") -> str:
    """
    Prompt per valutare la rilevanza delle skill nel CV.
    """
    return f"""
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
- Per ogni skill, considera anche i "criteri descrittivi" (due frasi guida) come definizione/ancoraggio del requisito.
- Considera il livello di seniority richiesto quando valuti la profondità e l'esperienza.
- Restituisci un oggetto JSON con la lista 'scores' contenente TUTTE le skill, ognuna con:
  - skill_id
  - skill_name
  - cv_relevance_score (intero 0-4)
  - notes_cv (frase breve, opzionale, max 30 parole)

[SKILL LIST CANONICA + CRITERI DESCRITTIVI]
{skill_list_json}

[TESTO CV]
{cv_text}
"""

def create_interview_scoring_prompt(skill_list_json: str, conversation_text: str, case_map_text: str, seniority_level: str = "Mid-Level") -> str:
    """
    Prompt per valutare la rilevanza delle skill nella conversazione del colloquio.
    """
    return f"""
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
- Considera i "criteri descrittivi" come definizione/ancoraggio del requisito.
- Considera il livello di seniority richiesto quando valuti profondità, autonomia e capacità strategica.
- Restituisci un oggetto JSON con la lista 'scores' contenente TUTTE le skill, ognuna con:
  - skill_id
  - skill_name
  - interview_relevance_score (intero 0-4)
  - notes_interview (frase breve, opzionale, max 30 parole)

[SKILL LIST CANONICA + CRITERI DESCRITTIVI]
{skill_list_json}

[MAPPA CASE: STEP E SKILL TESTATE]
{case_map_text}

[CONVERSAZIONE COMPLETA]
{conversation_text}
"""