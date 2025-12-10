# File: app/reporting/qualitative.py
# Scopo: Generare un report di posizionamento qualitativo per un candidato, confrontandolo con i trend di mercato.

import json
from recruitment_suite.config import settings
from interviewer.llm_service import get_llm_response
from recruitment_suite.app.core.llm_cache import get_prompt_hash, get_cached_llm_response, save_cached_llm_response
from utils.json_toon_converter import convert_json_to_toon


def generate_qualitative_llm_report(candidate_json: dict, market_json: dict, job_offer_text: str, language: str = "it") -> str:
    """
    Usa un LLM per generare un report qualitativo che confronta la carriera di un
    candidato con i trend di mercato, contestualizzandolo rispetto all'offerta di lavoro.
    
    Args:
        candidate_json: Dizionario con le esperienze del candidato
        market_json: Dizionario con i trend di mercato
        job_offer_text: Testo dell'offerta di lavoro
        language: Lingua del report ("it" o "en"), default "it"
    """
    
    # Normalizza la lingua
    if language not in ["it", "en"]:
        language = "it"
    
    # Prompt bilingue
    system_prompts = {
        "it": """
    Sei un partner strategico per l'acquisizione di talenti.
    Il tuo compito è analizzare in modo approfondito il percorso di carriera di un candidato, confrontarlo con i trend di mercato e valutarne l'adeguatezza per una specifica offerta di lavoro.
    L'obiettivo è fornire un'analisi chiara e actionable per aiutare il team di recruiting a prendere una decisione informata.
    """,
        "en": """
    You are a strategic partner for talent acquisition.
    Your task is to thoroughly analyze a candidate's career path, compare it with market trends, and evaluate their suitability for a specific job offer.
    The goal is to provide a clear and actionable analysis to help the recruiting team make an informed decision.
    """
    }
    
    user_prompt_templates = {
        "it": """
    **DATI A DISPOSIZIONE**

    1. **OFFERTA DI LAVORO TARGET:**
    ```
    {job_offer}
    ```

    2. **TREND DI MERCATO (Percorsi di Carriera Passati Aggregati per Durata in Mesi):**
    Nei dati strutturati di seguito sono mostrate le professioni più comuni nei percorsi di carriera di chi oggi ricopre la posizione target.
    ```
    {market_data}
    ```

    3. **PERCORSO DI CARRIERA DEL CANDIDATO (Esperienze Passate):**
    Nei dati strutturati di seguito sono elencate le esperienze passate del candidato, normalizzate con le mansioni ESCO.
    ```
    {candidate_data}
    ```

    **ISTRUZIONI**
   - Basandoti ESCLUSIVAMENTE sui dati forniti, redigi un report di posizionamento dettagliato.
   - Struttura l'output rivolgendoti direttamente al candidato, quindi usa sempre la seconda persona singolare.
   - Ricordati che l'output sarà inviato ad un candidato da parte dell'azienda per cui lavori, quindi rivolgiti a nome dell'azienda usando sempre la prima persona plurale
   - Mantieni uno stile professionale ma realista e oggettivo. Non essere sempre accondiscendente.
   - Concentrati esclusivamente sull'analisi rispetto al trend di mercato, senza fornire consigli al candidato. 
    **FORMATO DELL'OUTPUT RICHIESTO**
    Usa esattamente questa struttura Markdown:

    ### Analisi dei Trend di Mercato
    Sintetizza in 2-3 frasi quali sono i percorsi di carriera più comuni o i ruoli propedeutici più importanti che emergono dai dati di mercato per arrivare a ricoprire il ruolo target.

    ### Valutazione del Candidato
    Valuta qualitativamente se il percorso del candidato è tradizionale (in linea con il mercato), atipico ma coerente, o con evidenti deviazioni.

    Mantieni un tono professionale, oggettivo e costruttivo. NON ripetere i dati grezzi strutturati.
    """,
        "en": """
    **AVAILABLE DATA**

    1. **TARGET JOB OFFER:**
    ```
    {job_offer}
    ```

    2. **MARKET TRENDS (Past Career Paths Aggregated by Duration in Months):**
    In the structured data below are shown the most common professions in the career paths of those who currently hold the target position.
    ```
    {market_data}
    ```

    3. **CANDIDATE'S CAREER PATH (Past Experiences):**
    In the structured data below are listed the candidate's past experiences, normalized with ESCO occupations.
    ```
    {candidate_data}
    ```

    **INSTRUCTIONS**
   - Based EXCLUSIVELY on the provided data, write a detailed positioning report.
   - Structure the output addressing the candidate directly, so always use the second person singular.
   - Remember that the output will be sent to a candidate by the company you work for, so address them on behalf of the company using the first person plural
   - Maintain a professional but realistic and objective style. Don't always be accommodating.
   - Focus exclusively on the analysis relative to market trends, without providing advice to the candidate. 
    **REQUIRED OUTPUT FORMAT**
    Use exactly this Markdown structure:

    ### Market Trends Analysis
    Summarize in 2-3 sentences what are the most common career paths or the most important preparatory roles that emerge from market data to reach the target role.

    ### Candidate Evaluation
    Qualitatively assess whether the candidate's path is traditional (in line with the market), atypical but coherent, or with evident deviations.

    Maintain a professional, objective and constructive tone. DO NOT repeat the raw structured data.
    """
    }
    
    system_prompt = system_prompts.get(language, system_prompts["it"])
    user_prompt_template = user_prompt_templates.get(language, user_prompt_templates["it"])
    
    # Verifica che market_json e candidate_json siano dizionari validi
    if not isinstance(market_json, dict):
        print(f"⚠ ERRORE: market_json non è un dizionario, è {type(market_json)}")
        market_json = {}
    if not isinstance(candidate_json, dict):
        print(f"⚠ ERRORE: candidate_json non è un dizionario, è {type(candidate_json)}")
        candidate_json = {}
    
    # Converti a TOON per il prompt
    try:
        market_data_str = convert_json_to_toon(market_json) if market_json else "{}"
        candidate_data_str = convert_json_to_toon(candidate_json) if candidate_json else "{}"
    except Exception as e:
        print(f"✗ ERRORE durante conversione TOON: {e}")
        # Fallback a JSON
        market_data_str = json.dumps(market_json, indent=2, ensure_ascii=False) if market_json else "{}"
        candidate_data_str = json.dumps(candidate_json, indent=2, ensure_ascii=False) if candidate_json else "{}"
    
    user_prompt = user_prompt_template.format(
        job_offer=job_offer_text,
        market_data=market_data_str,
        candidate_data=candidate_data_str
    )

    # TASK 5: Caching LLM responses per Market Benchmark qualitativo
    prompt_hash = None
    try:
        prompt_hash = get_prompt_hash(user_prompt, system_prompt, temperature=0.4, max_tokens=1000)
        cached_response = get_cached_llm_response(prompt_hash)
        
        if cached_response:
            print(f"✓ [Market Benchmark Qualitativo] Cache HIT - riuso risposta cached")
            return cached_response
    except Exception as e:
        print(f"⚠ Errore caching Market Benchmark: {e}, continuo senza cache")
    
    response = get_llm_response(
        prompt=user_prompt,
        model=settings.LLM_MODEL,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=1000
    )
    
    # Salva in cache
    try:
        if response and not response.startswith("Errore") and prompt_hash:
            save_cached_llm_response(prompt_hash, response)
    except Exception as e:
        print(f"⚠ Errore salvataggio cache Market Benchmark: {e}")
    
    return response

from interviewer.llm_service import get_llm_response_async

async def generate_qualitative_llm_report_async(candidate_json: dict, market_json: dict, job_offer_text: str, language: str = "it") -> str:
    """
    Versione ASINCRONA: Usa un LLM per generare un report qualitativo che confronta 
    la carriera di un candidato con i trend di mercato.
    
    Args:
        candidate_json: Dizionario con le esperienze del candidato
        market_json: Dizionario con i trend di mercato
        job_offer_text: Testo dell'offerta di lavoro
        language: Lingua del report ("it" o "en"), default "it"
    """
    
    # Normalizza la lingua
    if language not in ["it", "en"]:
        language = "it"
    
    # Prompt bilingue (riutilizziamo le stesse definizioni della versione sync)
    system_prompts = {
        "it": """
    Sei un partner strategico per l'acquisizione di talenti.
    Il tuo compito è analizzare in modo approfondito il percorso di carriera di un candidato, confrontarlo con i trend di mercato e valutarne l'adeguatezza per una specifica offerta di lavoro.
    L'obiettivo è fornire un'analisi chiara e actionable per aiutare il team di recruiting a prendere una decisione informata.
    """,
        "en": """
    You are a strategic partner for talent acquisition.
    Your task is to thoroughly analyze a candidate's career path, compare it with market trends, and evaluate their suitability for a specific job offer.
    The goal is to provide a clear and actionable analysis to help the recruiting team make an informed decision.
    """
    }
    
    user_prompt_templates = {
        "it": """
    **DATI A DISPOSIZIONE**

    1. **OFFERTA DI LAVORO TARGET:**
    ```
    {job_offer}
    ```

    2. **TREND DI MERCATO (Percorsi di Carriera Passati Aggregati per Durata in Mesi):**
    Nei dati strutturati di seguito sono mostrate le professioni più comuni nei percorsi di carriera di chi oggi ricopre la posizione target.
    ```
    {market_data}
    ```

    3. **PERCORSO DI CARRIERA DEL CANDIDATO (Esperienze Passate):**
    Nei dati strutturati di seguito sono elencate le esperienze passate del candidato, normalizzate con le mansioni ESCO.
    ```
    {candidate_data}
    ```

    **ISTRUZIONI**
   - Basandoti ESCLUSIVAMENTE sui dati forniti, redigi un report di posizionamento dettagliato.
   - Struttura l'output rivolgendoti direttamente al candidato, quindi usa sempre la seconda persona singolare.
   - Ricordati che l'output sarà inviato ad un candidato da parte dell'azienda per cui lavori, quindi rivolgiti a nome dell'azienda usando sempre la prima persona plurale
   - Mantieni uno stile professionale ma realista e oggettivo. Non essere sempre accondiscendente.
   - Concentrati esclusivamente sull'analisi rispetto al trend di mercato, senza fornire consigli al candidato. 
    **FORMATO DELL'OUTPUT RICHIESTO**
    Usa esattamente questa struttura Markdown:

    ### Analisi dei Trend di Mercato
    Sintetizza in 2-3 frasi quali sono i percorsi di carriera più comuni o i ruoli propedeutici più importanti che emergono dai dati di mercato per arrivare a ricoprire il ruolo target.

    ### Valutazione del Candidato
    Valuta qualitativamente se il percorso del candidato è tradizionale (in linea con il mercato), atipico ma coerente, o con evidenti deviazioni.

    Mantieni un tono professionale, oggettivo e costruttivo. NON ripetere i dati grezzi strutturati.
    """,
        "en": """
    **AVAILABLE DATA**

    1. **TARGET JOB OFFER:**
    ```
    {job_offer}
    ```

    2. **MARKET TRENDS (Past Career Paths Aggregated by Duration in Months):**
    In the structured data below are shown the most common professions in the career paths of those who currently hold the target position.
    ```
    {market_data}
    ```

    3. **CANDIDATE'S CAREER PATH (Past Experiences):**
    In the structured data below are listed the candidate's past experiences, normalized with ESCO occupations.
    ```
    {candidate_data}
    ```

    **INSTRUCTIONS**
   - Based EXCLUSIVELY on the provided data, write a detailed positioning report.
   - Structure the output addressing the candidate directly, so always use the second person singular.
   - Remember that the output will be sent to a candidate by the company you work for, so address them on behalf of the company using the first person plural
   - Maintain a professional but realistic and objective style. Don't always be accommodating.
   - Focus exclusively on the analysis relative to market trends, without providing advice to the candidate. 
    **REQUIRED OUTPUT FORMAT**
    Use exactly this Markdown structure:

    ### Market Trends Analysis
    Summarize in 2-3 sentences what are the most common career paths or the most important preparatory roles that emerge from market data to reach the target role.

    ### Candidate Evaluation
    Qualitatively assess whether the candidate's path is traditional (in line with the market), atypical but coherent, or with evident deviations.

    Maintain a professional, objective and constructive tone. DO NOT repeat the raw structured data.
    """
    }
    
    system_prompt = system_prompts.get(language, system_prompts["it"])
    user_prompt_template = user_prompt_templates.get(language, user_prompt_templates["it"])
    
    # Verifica che market_json e candidate_json siano dizionari validi
    if not isinstance(market_json, dict):
        print(f"⚠ ERRORE (async): market_json non è un dizionario, è {type(market_json)}")
        market_json = {}
    if not isinstance(candidate_json, dict):
        print(f"⚠ ERRORE (async): candidate_json non è un dizionario, è {type(candidate_json)}")
        candidate_json = {}
    
    # Converti a TOON per il prompt
    try:
        market_data_str = convert_json_to_toon(market_json) if market_json else "{}"
        candidate_data_str = convert_json_to_toon(candidate_json) if candidate_json else "{}"
    except Exception as e:
        print(f"✗ ERRORE durante conversione TOON (async): {e}")
        # Fallback a JSON
        market_data_str = json.dumps(market_json, indent=2, ensure_ascii=False) if market_json else "{}"
        candidate_data_str = json.dumps(candidate_json, indent=2, ensure_ascii=False) if candidate_json else "{}"
    
    # La preparazione del prompt rimane identica, è un'operazione sincrona e veloce
    user_prompt = user_prompt_template.format(
        job_offer=job_offer_text,
        market_data=market_data_str,
        candidate_data=candidate_data_str
    )

    # TASK 5: Caching LLM responses per Market Benchmark qualitativo (async)
    prompt_hash = None
    try:
        prompt_hash = get_prompt_hash(user_prompt, system_prompt, temperature=0.4, max_tokens=1000)
        cached_response = get_cached_llm_response(prompt_hash)
        
        if cached_response:
            print(f"✓ [Market Benchmark Qualitativo (async)] Cache HIT - riuso risposta cached")
            return cached_response
    except Exception as e:
        print(f"⚠ Errore caching Market Benchmark (async): {e}, continuo senza cache")
    
    # <-- MODIFICA CHIAVE: Chiama la versione async con 'await' -->
    response = await get_llm_response_async(
        prompt=user_prompt,
        model=settings.LLM_MODEL,
        system_prompt=system_prompt,
        temperature=0.2,
        max_tokens=1000
    )
    
    # Salva in cache
    try:
        if response and not response.startswith("Errore") and prompt_hash:
            save_cached_llm_response(prompt_hash, response)
    except Exception as e:
        print(f"⚠ Errore salvataggio cache Market Benchmark (async): {e}")
    
    return response