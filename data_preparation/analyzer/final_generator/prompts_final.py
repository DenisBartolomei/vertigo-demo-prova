# analyzer/final_generator/prompts_final.py

SYSTEM_PROMPT = {
    "it": """Sei un agente AI progettato per produrre informazioni strutturate, ricevendo in input informazioni non strutturate.
Dati gli input, restituisci un oggetto JSON con i campi predefiniti nella struttura attesa. Formatta accuratamente i dati di output. Se un dato manca o non si può determinare, restituisci un valore di default (e.g., null, 0, or 'N/A').""",
    "en": """You are an AI agent designed to produce structured information, receiving unstructured information as input.
Given the inputs, return a JSON object with the predefined fields in the expected structure. Accurately format the output data. If a data is missing or cannot be determined, return a default value (e.g., null, 0, or 'N/A')."""
}

def create_final_case_prompt(icp_text: str, guide_text: str, kb_summary: str, seniority_level: str, json_example_str: str, hr_special_needs: str, reasoning_steps: int, language: str = "it") -> str:
    """
    Assembla il prompt finale per la generazione dei case strutturati, integrando le Indicazioni HR.
    
    Args:
        icp_text: Il testo dell'ICP
        guide_text: Guida alla generazione dei case
        kb_summary: Sintesi della knowledge base
        seniority_level: Livello di seniority richiesto
        json_example_str: Esempio JSON della struttura attesa
        hr_special_needs: Indicazioni speciali da parte dell'HR
        reasoning_steps: Numero di reasoning steps richiesti dall'HR (il sistema aggiungerà automaticamente lo step 0)
        language: Lingua del prompt ("it" o "en")
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    # Calcola il numero effettivo di steps da generare (reasoning_steps + 1 per lo step 0)
    total_steps = reasoning_steps + 1
    
    prompts = {
        "it": f"""
Produci 5 casi studio complessi e strutturati, e decomponi il raggiungimento della soluzione in {reasoning_steps} step consecutivi (reasoning steps, da 1 a {reasoning_steps}).
Integra le INDICAZIONI SPECIALI HR come vincoli o preferenze operative nella costruzione degli scenari e nella scelta delle skill da testare.

Indicazioni Speciali HR: usa questo interpretando le richieste in chiave di quanto richiesto nella ICP e guida alla generazione. Dagli buona importanza dal momento che sono le richieste particolari.
{{hr_block}}

Poiché per ciascun case dovranno essere verificate tutte le skill richieste dovrai, per ciascun reasoning step, indicare 3 skill da poter testare (estratte in modo accurato dalla ICP e basandoti sulle indicazioni della Guida alla generazione) all'interno del reasoning step stesso, esplictando brevemente in che modo (per questo lavoro aiutati con l'input GUIDA ALLA GENERAZIONE, che contiene tutti i requisiti da testare, e le modalità con cui è possibile farlo).
Perché i Case, e relativi reasoning steps siano perfetti:
o	Ciascun case dovrà essere in grado di verificare TUTTE LE skill riportate nei paragrafi della ICP intitolati: "Competenze tecniche richieste esplicitamente dall'annuncio", "Competenze trasversali richieste esplicitamente dall'annuncio (escluse le lingue)". Per fare ciò, dovrai quindi attribuire a ciascun reasoning step almeno 3 skill che secondo te sono ideali da verificare in quel contesto (secondo lo schema imposto).
o	Dovranno adattare la complessità e la profondità al livello di seniority richiesto (Evita domande da super-esperto se il ruolo è junior, e viceversa evita domande semplici per profili lead).
o	Dovranno prendere spunto dalla Knowledge Base (kb_insights) riportata di seguito (es. 'Descrivi come guideresti l'implementazione di [Tecnologia X] in un contesto simile a [Insight da Progetto Y da KB]'; Oppure ' Come utilizzeresti [Tecnologia / Metodologia X] in un contesto simile a [Insight da Progetto Z da KB]').
o	Dovrà esserci un reasoning step ulteriore, rispetto ai {reasoning_steps} creati per decomporre la soluzione. Il reasoning step in questione, chiamato sempre reasoning step 0, servirà a mettere in luce il ragionamento necessario per la risoluzione dei Case, lo costruirai dunque prendendo spunto dai {total_steps} reasoning step creati per decomporre la soluzione. Questo reasoning step servirà a un agente specializzato per capire come testare le capacità di impostare il ragionamento dei candidati.
o	Usa la sezione della ICP "Responsabilità principali e attività operative attese" solo ed esclusivamente per prendere spunto nella creazione dei casi. NON USARE MAI questa sezione per dedurre le skill_to_test
Dovranno essere risolvibili "su carta", cioè all'interno di una dinamica di test, senza poter effettivamente effettuare attività reali. La risoluzione sarà prettamente tramite PC, quindi non ci saranno interazioni con funzioni aziendali, clienti, colleghi. Puoi quindi simulare la casistica, ma non aspettarti che il candidato esegua attività effettivamente.
o	Il testo del Case dovrà essere articolato e non una domanda semplice e secca.
---
**Istruzioni**:
o	Non lasciar trapelare dati espliciti dalla Knowledge Base nel contenuto generato; puoi prendere spunto per la generazione, ma non copiare esattamente dati confidenziali e interni.
o	Non chiedere di esperienze personali. Puoi però chiedere come affronterebbero scenari concreti.
o	Dai a ciascun case un taglio narrativo, ad esempio: "Sei il responsabile del marketing digitale, del dipartimento sales & marketing. Ti si presenta la necessità di lanciare una nuova campagna in virtù della promozione di un nuovo prodotto. Considerate le condizioni X,Y, e i vincoli Z,K, il tuo compito è quello di mettere a terra una campagna digitale da zero, efficace per la promozione del prodotto"
o	Evita ambiguità ed eccessiva generalità.
o	Usa l'input "GUIDA ALLA GENERAZIONE" per comprendere come poter testare in modo efficace ciascuna requisito richiesto dall'annuncio, ricorda che ciascun case dovrà poter testare tutte le skill contenute nell'annuncio.
o	Non usare ulteriore testo oltre alla produzione di quanto richiesto sopra.
o   **IMPORTANTE**: Per il campo `skills_to_test`, assicurati di generare una lista di oggetti, dove ogni oggetto ha due chiavi: `skill_name` e `testing_method`. Non generare una semplice lista di stringhe. Le skills_to_test devono essere al 100% attinenti a quanto richiesto dalla ICP e dalle INDICAZIONI SPECIALI HR, inteso che devono essere scritte nello stesso identico modo, senza variazioni; non inventare o dedurre nulla di nuovo.
o   **FORMATO JSON OBBLIGATORIO**: Il tuo output finale DEVE essere un oggetto JSON che rispetta esattamente la struttura, i nomi delle chiavi e i tipi di dati mostrati nell'esempio di seguito.

ESEMPIO DELLA STRUTTURA JSON ATTESA:
```json
{{json_example_str}}
---
INPUTS

[PROFILO CANDIDATO IDEALE (ICP)]
{{icp_text}}

[GUIDA ALLA GENERAZIONE]
{{guide_text}}

[SINTESI KNOWLEDGE BASE]
{{kb_summary}}

[LIVELLO DI SENIORITY]
{{seniority_level}}
""",
        "en": f"""
Produce 5 complex and structured case studies, and break down the achievement of the solution into {reasoning_steps} consecutive steps (reasoning steps, from 1 to {reasoning_steps}).
Integrate the HR SPECIAL INSTRUCTIONS as operational constraints or preferences in the construction of scenarios and in the choice of skills to test.

HR Special Instructions: use this by interpreting the requests in terms of what is required in the ICP and generation guide. Give it good importance since these are particular requests.
{{hr_block}}

Since ALL THE HARD AND SOFT SKILLS from ICP must be verified for each case, you will need to indicate 3 or 4 skills to test for each reasoning step (accurately extracted from the ICP and based on the Generation Guide indications) within the reasoning step itself, briefly explaining how (for this work, help yourself with the GENERATION GUIDE input, which contains all the requirements to test, and the ways in which it is possible to do so).
For the Cases and related reasoning steps to be perfect:
o	Each case must be able to verify ALL the skills reported in the ICP paragraphs entitled: "Technical skills explicitly required by the posting", "Soft skills explicitly required by the posting (excluding languages)". To do this, you will therefore have to assign to each reasoning step at least 3 skills that you think are ideal to verify in that context (according to the imposed scheme).
o	They must adapt the complexity and depth to the required seniority level (Avoid super-expert questions if the role is junior, and vice versa avoid simple questions for lead profiles).
o	They must draw inspiration from the Knowledge Base (kb_insights) reported below (e.g. 'Describe how you would guide the implementation of [Technology X] in a context similar to [Insight from Project Y from KB]'; Or 'How would you use [Technology / Methodology X] in a context similar to [Insight from Project Z from KB]').
o	There must be an additional reasoning step, compared to the {reasoning_steps} created to break down the solution. The reasoning step in question, always called reasoning step 0, will serve to highlight the reasoning necessary for the resolution of the Cases, you will therefore build it by taking inspiration from the {total_steps} reasoning steps created to break down the solution. This reasoning step will serve a specialized agent to understand how to test the candidates' ability to set up reasoning.
o	Use the ICP section "Main responsibilities and expected operational activities" only and exclusively to take inspiration in creating cases. NEVER USE this section to deduce skills_to_test
They must be solvable "on paper", that is, within a test dynamic, without being able to actually perform real activities. The resolution will be purely through PC, so there will be no interactions with business functions, customers, colleagues. You can therefore simulate the case, but do not expect the candidate to actually perform activities.
o	The text of the Case must be articulated and not a simple and dry question.
---
**Instructions**:
o	Do not reveal explicit data from the Knowledge Base in the generated content; you can take inspiration for generation, but do not copy exactly confidential and internal data.
o	Do not ask for personal experiences. However, you can ask how they would approach concrete scenarios.
o	Give each case a narrative approach, for example: "You are the digital marketing manager, of the sales & marketing department. You are presented with the need to launch a new campaign for the promotion of a new product. Considering the conditions X,Y, and the constraints Z,K, your task is to implement a digital campaign from scratch, effective for the promotion of the product"
o	Avoid ambiguity and excessive generality.
o	Use the "GENERATION GUIDE" input to understand how to effectively test each requirement required by the posting, remember that each case must be able to test all the skills contained in the posting.
o	Do not use additional text beyond the production of what is required above.
o   **IMPORTANT**: For the `skills_to_test` field, make sure to generate a list of objects, where each object has two keys: `skill_name` and `testing_method`. Do not generate a simple list of strings. The skills_to_test must be 100% relevant to what is required by the ICP and the HR SPECIAL INSTRUCTIONS, meaning they must be written in the exact same way, without variations; do not invent or deduce anything new.
o   **MANDATORY JSON FORMAT**: Your final output MUST be a JSON object that exactly respects the structure, key names and data types shown in the example below.

EXPECTED JSON STRUCTURE EXAMPLE:
```json
{{json_example_str}}
---
INPUTS

[IDEAL CANDIDATE PROFILE (ICP)]
{{icp_text}}

[GENERATION GUIDE]
{{guide_text}}

[KNOWLEDGE BASE SUMMARY]
{{kb_summary}}

[SENIORITY LEVEL]
{{seniority_level}}
"""
    }
    
    # Validate language
    if language not in ["it", "en"]:
        print(f"  - [Final Case Prompts] Invalid language '{language}', defaulting to Italian")
        language = "it"
    
    # Format HR block
    hr_block = hr_special_needs.strip() if hr_special_needs else (
        "Nessuna indicazione speciale fornita." if language == "it" else "No special instructions provided."
    )
    
    return prompts[language].format(
        hr_block=hr_block,
        json_example_str=json_example_str,
        icp_text=icp_text,
        guide_text=guide_text,
        kb_summary=kb_summary,
        seniority_level=seniority_level
    )
