# analyzer/final_generator/prompts_final.py

SYSTEM_PROMPT = {
    "it": """Sei un agente AI progettato per produrre informazioni strutturate, ricevendo in input informazioni non strutturate. Ti occuperai di creare dei case study per usare durante colloqui con candidati. Il tuo mantra che non devi mai scordare è che TUTTE LE SKILL RICHIESTE DEVONO ESSERE INCLUSE IN CIASCUNO DEI CASE PRODOTTI.
Dati gli input, restituisci un oggetto JSON con i campi predefiniti nella struttura attesa. Formatta accuratamente i dati di output. Se un dato manca o non si può determinare, restituisci un valore di default (e.g., null, 0, or 'N/A').""",
    "en": """You are an AI agent designed to produce structured information, receiving unstructured information as input. You will be tasked with creating case studies to use during interviews with candidates. Your mantra that you must never forget is that ALL THE SKILLS REQUIRED MUST BE INCLUDED IN EACH CASE STUDY PRODUCED.
Given the inputs, return a JSON object with the predefined fields in the expected structure. Accurately format the output data. If a data is missing or cannot be determined, return a default value (e.g., null, 0, or 'N/A')."""
}

def create_final_case_prompt(icp_text: str, guide_text: str, kb_summary: str, seniority_level: str, json_example_str: str, hr_special_needs: str, reasoning_steps: int, language: str = "it", canonical_skills: list = None, min_skills_per_step: int = 2, total_skills: int = 0) -> str:
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
        canonical_skills: Lista canonica delle skills (UNICA fonte di verità)
    
    Returns:
        Il prompt formattato nella lingua specificata
    """
    # Calcola il numero effettivo di steps da generare (reasoning_steps + 1 per lo step 0)
    total_steps = reasoning_steps + 1
    total_steps_per_case = total_steps
    total_steps_all_cases = 5 * total_steps_per_case
    
    # Prepara il blocco canonical_skills PRIMA di definire i prompts (per usarlo nelle f-string)
    canonical_skills_block = ""
    if canonical_skills:
        skills_list = [f"- {skill['skill_name']} ({skill['skill_type']})" for skill in canonical_skills]
        skills_text = "\n".join(skills_list)
        if language == "it":
            canonical_skills_block = f"""
[LISTA CANONICA DELLE SKILL (UNICA FONTE DI VERITÀ)]
Questa è la lista COMPLETA e DEFINITIVA di tutte le skill che devono essere testate nei case.
DEVI usare SOLO queste skill, con i nomi ESATTI come indicati di seguito. NON inventare, NON variare, NON dedurre skill aggiuntive.

{skills_text}

**REGOLA CRITICA**: Per il campo `skills_to_test` in ogni reasoning step, puoi usare SOLO le skill elencate sopra, con i nomi ESATTI. Se una skill non è in questa lista, NON puoi usarla.
"""
        else:
            canonical_skills_block = f"""
[CANONICAL SKILLS LIST (SINGLE SOURCE OF TRUTH)]
This is the COMPLETE and DEFINITIVE list of all skills that must be tested in the cases.
You MUST use ONLY these skills, with the EXACT names as indicated below. DO NOT invent, DO NOT vary, DO NOT deduce additional skills.

{skills_text}

**CRITICAL RULE**: For the `skills_to_test` field in each reasoning step, you can use ONLY the skills listed above, with the EXACT names. If a skill is not in this list, you CANNOT use it.
"""
    
    # Prepara blocco di distribuzione skill con calcoli espliciti
    if canonical_skills and total_skills > 0:
        distribution_block_it = f"""
**⚠️ CALCOLO DISTRIBUZIONE SKILL (OBBLIGATORIO) ⚠️**
Hai {total_skills} skill canoniche da distribuire tra 5 case, ciascuno con {total_steps_per_case} reasoning steps (totale: {total_steps_all_cases} reasoning steps).

Per garantire che TUTTE le {total_skills} skill siano incluse:
- Ogni reasoning step DEVE contenere ALMENO {min_skills_per_step} skill (preferibilmente 3-5)
- Distribuisci le skill in modo che NESSUNA skill canonica rimanga esclusa
- Puoi ripetere alcune skill in step diversi, ma DEVI includere TUTTE le skill almeno una volta
- Verifica matematica: con {min_skills_per_step} skill per step su {total_steps_all_cases} step, hai {min_skills_per_step * total_steps_all_cases} posizioni disponibili per distribuire le {total_skills} skill

**REGOLA FONDAMENTALE ASSOLUTA**: Al termine della generazione, OGNI skill della lista canonica DEVE apparire in almeno un reasoning step di almeno un case. Se anche solo UNA skill non è inclusa, la generazione è INCOMPLETA e INACCETTABILE.
"""
        distribution_block_en = f"""
**⚠️ SKILL DISTRIBUTION CALCULATION (MANDATORY) ⚠️**
You have {total_skills} canonical skills to distribute across 5 cases, each with {total_steps_per_case} reasoning steps (total: {total_steps_all_cases} reasoning steps).

To ensure ALL {total_skills} skills are included:
- Each reasoning step MUST contain AT LEAST {min_skills_per_step} skills (preferably 3-5)
- Distribute skills so that NO canonical skill remains excluded
- You can repeat some skills in different steps, but you MUST include ALL skills at least once
- Mathematical verification: with {min_skills_per_step} skills per step on {total_steps_all_cases} steps, you have {min_skills_per_step * total_steps_all_cases} positions available to distribute the {total_skills} skills

**ABSOLUTE FUNDAMENTAL RULE**: At the end of generation, EVERY skill in the canonical list MUST appear in at least one reasoning step of at least one case. If even ONE skill is not included, the generation is INCOMPLETE and UNACCEPTABLE.
"""
    else:
        distribution_block_it = ""
        distribution_block_en = ""
    
    prompts = {
        "it": f"""
**⚠️ REGOLA FONDAMENTALE ASSOLUTA ⚠️**
TUTTE LE {total_skills if total_skills > 0 else 'SKILL'} SKILL DELLA LISTA CANONICA DEVONO ESSERE INCLUSE IN ALMENO UN REASONING STEP DI ALMENO UN CASE. 
NON PUOI OMETTERE NESSUNA SKILL. SE UNA SKILL NON È INCLUSA, LA GENERAZIONE È FALLITA.

{distribution_block_it}

Produci 5 casi studio complessi e strutturati, e decomponi il raggiungimento della soluzione in {reasoning_steps} step consecutivi (reasoning steps, da 1 a {reasoning_steps}).
Integra le INDICAZIONI SPECIALI HR come vincoli o preferenze operative nella costruzione degli scenari e nella scelta delle skill da testare.

Indicazioni Speciali HR: usa questo interpretando le richieste in chiave di quanto richiesto nella ICP e guida alla generazione. Dagli buona importanza dal momento che sono le richieste particolari.
{{hr_block}}

**DISTRIBUZIONE SKILL OBBLIGATORIA**:
Per ciascun reasoning step, indica ALMENO {min_skills_per_step} skill (preferibilmente 3-5) da poter testare, estratte ESCLUSIVAMENTE dalla LISTA CANONICA DELLE SKILL fornita sopra.
IMPORTANTE: Devi distribuire le skill in modo che TUTTE le {total_skills if total_skills > 0 else 'skill canoniche'} skill della lista canonica compaiano in almeno un reasoning step di almeno un case.

Perché i Case, e relativi reasoning steps siano perfetti:
o	**CRITICO**: Ciascun case study prodotto dovrà verificare TUTTE LE skill della LISTA CANONICA. Per fare ciò, distribuisci le skill tra i reasoning steps in modo intelligente, assicurandoti che ogni skill appaia almeno una volta in tutta la collezione di 5 case.
o	Per ciascun reasoning step, usa ALMENO {min_skills_per_step} skill (ideale: 3-5 skill) dalla lista canonica. NON limitarti a 1-2 skill per step.
o	Dovranno adattare la complessità e la profondità al livello di seniority richiesto (Evita domande da super-esperto se il ruolo è junior, e viceversa evita domande semplici per profili lead).
o	Dovranno prendere spunto dalla Knowledge Base (kb_insights) riportata di seguito (es. 'Descrivi come guideresti l'implementazione di [Tecnologia X] in un contesto simile a [Insight da Progetto Y da KB]'; Oppure ' Come utilizzeresti [Tecnologia / Metodologia X] in un contesto simile a [Insight da Progetto Z da KB]').
o	Dovrà esserci un reasoning step ulteriore, rispetto ai {reasoning_steps} creati per decomporre la soluzione. Il reasoning step in questione, chiamato sempre reasoning step 0, servirà a mettere in luce il ragionamento necessario per la risoluzione dei Case, lo costruirai dunque prendendo spunto dai {total_steps} reasoning step creati per decomporre la soluzione. Questo reasoning step servirà a un agente specializzato per capire come testare le capacità di impostare il ragionamento dei candidati.
o	Usa la sezione della ICP "Responsabilità principali e attività operative attese" solo ed esclusivamente per prendere spunto nella creazione dei casi. NON USARE MAI questa sezione per dedurre le skill_to_test
Dovranno essere risolvibili "su carta", cioè all'interno di una dinamica di test, senza poter effettivamente effettuare attività reali. La risoluzione sarà prettamente tramite PC, quindi non ci saranno interazioni con funzioni aziendali, clienti, colleghi. Puoi quindi simulare la casistica, ma non aspettarti che il candidato esegua attività effettivamente.
o	Il testo del Case dovrà essere articolato e non una domanda semplice e secca.
---
**Istruzioni**:
o	**VERIFICA FINALE OBBLIGATORIA**: Prima di completare, controlla mentalmente che OGNI skill della lista canonica appaia in almeno un reasoning step. Se manca anche solo una skill, la generazione è incompleta e DEVI rigenerare.
o	Non lasciar trapelare dati espliciti dalla Knowledge Base nel contenuto generato; puoi prendere spunto per la generazione, ma non copiare esattamente dati confidenziali e interni.
o	Non chiedere di esperienze personali. Puoi però chiedere come affronterebbero scenari concreti.
o	Dai a ciascun case un taglio narrativo, ad esempio: "Sei il responsabile del marketing digitale, del dipartimento sales & marketing. Ti si presenta la necessità di lanciare una nuova campagna in virtù della promozione di un nuovo prodotto. Considerate le condizioni X,Y, e i vincoli Z,K, il tuo compito è quello di mettere a terra una campagna digitale da zero, efficace per la promozione del prodotto"
o	Evita ambiguità ed eccessiva generalità.
o	Usa l'input "GUIDA ALLA GENERAZIONE" per comprendere come poter testare in modo efficace ciascuna requisito richiesto dall'annuncio, ricorda che ciascun case dovrà poter testare tutte le skill contenute nell'annuncio.
o	Non usare ulteriore testo oltre alla produzione di quanto richiesto sopra.
o   **IMPORTANTE**: Per il campo `skills_to_test`, assicurati di generare una lista di oggetti, dove ogni oggetto ha due chiavi: `skill_name` e `testing_method`. Non generare una semplice lista di stringhe. Le skills_to_test devono essere ESCLUSIVAMENTE dalla LISTA CANONICA DELLE SKILL fornita sopra, usando i nomi ESATTI senza variazioni, abbreviazioni o sinonimi. NON inventare, NON dedurre, NON variare i nomi delle skill.
o   **FORMATO JSON OBBLIGATORIO**: Il tuo output finale DEVE essere un oggetto JSON che rispetta esattamente la struttura, i nomi delle chiavi e i tipi di dati mostrati nell'esempio di seguito.

ESEMPIO DELLA STRUTTURA JSON ATTESA:
```json
{{json_example_str}}
---
INPUTS

{canonical_skills_block}

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
**⚠️ ABSOLUTE FUNDAMENTAL RULE ⚠️**
ALL {total_skills if total_skills > 0 else 'SKILLS'} SKILLS FROM THE CANONICAL LIST MUST BE INCLUDED IN AT LEAST ONE REASONING STEP OF AT LEAST ONE CASE.
YOU CANNOT OMIT ANY SKILL. IF A SKILL IS NOT INCLUDED, THE GENERATION HAS FAILED.

{distribution_block_en}

Produce 5 complex and structured case studies, and break down the achievement of the solution into {reasoning_steps} consecutive steps (reasoning steps, from 1 to {reasoning_steps}).
Integrate the HR SPECIAL INSTRUCTIONS as operational constraints or preferences in the construction of scenarios and in the choice of skills to test.

HR Special Instructions: use this by interpreting the requests in terms of what is required in the ICP and generation guide. Give it good importance since these are particular requests.
{{hr_block}}

**MANDATORY SKILL DISTRIBUTION**:
For each reasoning step, indicate AT LEAST {min_skills_per_step} skills (preferably 3-5) to test, extracted EXCLUSIVELY from the CANONICAL SKILLS LIST provided above.
IMPORTANT: You must distribute skills so that ALL {total_skills if total_skills > 0 else 'canonical'} skills from the canonical list appear in at least one reasoning step of at least one case.

For the Cases and related reasoning steps to be perfect:
o	**CRITICAL**: Each case study produced must verify ALL skills from the CANONICAL LIST. To do this, distribute skills among reasoning steps intelligently, ensuring that each skill appears at least once across the entire collection of 5 cases.
o	For each reasoning step, use AT LEAST {min_skills_per_step} skills (ideal: 3-5 skills) from the canonical list. DO NOT limit yourself to 1-2 skills per step.
o	They must adapt the complexity and depth to the required seniority level (Avoid super-expert questions if the role is junior, and vice versa avoid simple questions for lead profiles).
o	They must draw inspiration from the Knowledge Base (kb_insights) reported below (e.g. 'Describe how you would guide the implementation of [Technology X] in a context similar to [Insight from Project Y from KB]'; Or 'How would you use [Technology / Methodology X] in a context similar to [Insight from Project Z from KB]').
o	There must be an additional reasoning step, compared to the {reasoning_steps} created to break down the solution. The reasoning step in question, always called reasoning step 0, will serve to highlight the reasoning necessary for the resolution of the Cases, you will therefore build it by taking inspiration from the {total_steps} reasoning steps created to break down the solution. This reasoning step will serve a specialized agent to understand how to test the candidates' ability to set up reasoning.
o	Use the ICP section "Main responsibilities and expected operational activities" only and exclusively to take inspiration in creating cases. NEVER USE this section to deduce skills_to_test
They must be solvable "on paper", that is, within a test dynamic, without being able to actually perform real activities. The resolution will be purely through PC, so there will be no interactions with business functions, customers, colleagues. You can therefore simulate the case, but do not expect the candidate to actually perform activities.
o	The text of the Case must be articulated and not a simple and dry question.
---
**Instructions**:
o	**MANDATORY FINAL VERIFICATION**: Before completing, mentally check that EVERY skill from the canonical list appears in at least one reasoning step. If even one skill is missing, the generation is incomplete and you MUST regenerate.
o	Do not reveal explicit data from the Knowledge Base in the generated content; you can take inspiration for generation, but do not copy exactly confidential and internal data.
o	Do not ask for personal experiences. However, you can ask how they would approach concrete scenarios.
o	Give each case a narrative approach, for example: "You are the digital marketing manager, of the sales & marketing department. You are presented with the need to launch a new campaign for the promotion of a new product. Considering the conditions X,Y, and the constraints Z,K, your task is to implement a digital campaign from scratch, effective for the promotion of the product"
o	Avoid ambiguity and excessive generality.
o	Use the "GENERATION GUIDE" input to understand how to effectively test each requirement required by the posting, remember that each case must be able to test all the skills contained in the posting.
o	Do not use additional text beyond the production of what is required above.
o   **IMPORTANT**: For the `skills_to_test` field, make sure to generate a list of objects, where each object has two keys: `skill_name` and `testing_method`. Do not generate a simple list of strings. The skills_to_test must be EXCLUSIVELY from the CANONICAL SKILLS LIST provided above, using the EXACT names without variations, abbreviations or synonyms. DO NOT invent, DO NOT deduce, DO NOT vary the skill names.
o   **MANDATORY JSON FORMAT**: Your final output MUST be a JSON object that exactly respects the structure, key names and data types shown in the example below.

EXPECTED JSON STRUCTURE EXAMPLE:
```json
{{json_example_str}}
---
INPUTS

{canonical_skills_block}

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
        canonical_skills_block=canonical_skills_block,
        hr_block=hr_block,
        json_example_str=json_example_str,
        icp_text=icp_text,
        guide_text=guide_text,
        kb_summary=kb_summary,
        seniority_level=seniority_level
    )
