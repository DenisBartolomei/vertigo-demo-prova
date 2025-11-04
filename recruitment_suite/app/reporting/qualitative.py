# File: app/reporting/qualitative.py
# Scopo: Generare un report di posizionamento qualitativo per un candidato, confrontandolo con i trend di mercato.

import json
from recruitment_suite.config import settings
from interviewer.llm_service import get_llm_response


def generate_qualitative_llm_report(candidate_json: dict, market_json: dict, job_offer_text: str) -> str:
    """
    Usa un LLM per generare un report qualitativo che confronta la carriera di un
    candidato con i trend di mercato, contestualizzandolo rispetto all'offerta di lavoro.
    """

    system_prompt = """
    Sei un partner strategico per l'acquisizione di talenti.
    Il tuo compito è analizzare in modo approfondito il percorso di carriera di un candidato, confrontarlo con i trend di mercato e valutarne l'adeguatezza per una specifica offerta di lavoro.
    L'obiettivo è fornire un'analisi chiara e actionable per aiutare il team di recruiting a prendere una decisione informata.
    """
    
    user_prompt_template = """
    **DATI A DISPOSIZIONE**

    1. **OFFERTA DI LAVORO TARGET:**
    ```
    {job_offer}
    ```

    2. **TREND DI MERCATO (Percorsi di Carriera Passati Aggregati per Durata in Mesi):**
    Questo JSON mostra le professioni più comuni nei percorsi di carriera di chi oggi ricopre la posizione target.
    ```json
    {market_data}
    ```

    3. **PERCORSO DI CARRIERA DEL CANDIDATO (Esperienze Passate):**
    Questo JSON elenca le esperienze passate del candidato, normalizzate con le mansioni ESCO.
    ```json
    {candidate_data}
    ```

    **ISTRUZIONI**
   - Basandoti ESCLUSIVAMENTE sui dati forniti, redigi un report di posizionamento dettagliato.
   - Struttura l'output rivolgendoti direttamente al candidato, quindi usa sempre la seconda persona singolare.
   - Ricordati che l'output sarà inviato ad un candidato da parte dell'azienda per cui lavori, quindi rivolgiti a nome dell'azienda usando sempre la prima persona plurale
   - Mantieni uno stile professionale ma realista e oggettivo. Non essere sempre accondiscendente.
   - Concentrati esclusivamente sull'ananlisi rispetto al trend di mercato, senza fornire consigli al candidato. 
    *FORMATO DELL'OUTPUT RICHIESTO**
    Usa esattamente questa struttura Markdown:

    ### Analisi dei Trend di Mercato
    Sintetizza in 2-3 frasi quali sono i percorsi di carriera più comuni o i ruoli propedeutici più importanti che emergono dai dati di mercato per arrivare a ricoprire il ruolo target.

    ### Valutazione del Candidato
    Valuta qualitativamente se il percorso del candidato è tradizionale (in linea con il mercato), atipico ma coerente, o con evidenti deviazioni.

    Mantieni un tono professionale, oggettivo e costruttivo. NON ripetere i dati grezzi dei JSON.
    """
    
    # Verifica che market_json e candidate_json siano dizionari validi
    if not isinstance(market_json, dict):
        print(f"⚠ ERRORE: market_json non è un dizionario, è {type(market_json)}")
        market_json = {}
    if not isinstance(candidate_json, dict):
        print(f"⚠ ERRORE: candidate_json non è un dizionario, è {type(candidate_json)}")
        candidate_json = {}
    
    # Serializza in JSON per il prompt
    try:
        market_data_str = json.dumps(market_json, indent=2, ensure_ascii=False) if market_json else "{}"
        candidate_data_str = json.dumps(candidate_json, indent=2, ensure_ascii=False) if candidate_json else "{}"
    except Exception as e:
        print(f"✗ ERRORE durante serializzazione JSON: {e}")
        market_data_str = "{}"
        candidate_data_str = "{}"
    
    user_prompt = user_prompt_template.format(
        job_offer=job_offer_text,
        market_data=market_data_str,
        candidate_data=candidate_data_str
    )

    return get_llm_response(
        prompt=user_prompt,
        model=settings.LLM_MODEL,
        system_prompt=system_prompt,
        temperature=0.4,
        max_tokens=1000
    )

from interviewer.llm_service import get_llm_response_async

async def generate_qualitative_llm_report_async(candidate_json: dict, market_json: dict, job_offer_text: str) -> str:
    """
    Versione ASINCRONA: Usa un LLM per generare un report qualitativo che confronta 
    la carriera di un candidato con i trend di mercato.
    """

    system_prompt = """
    Sei un partner strategico per l'acquisizione di talenti.
    Il tuo compito è analizzare in modo approfondito il percorso di carriera di un candidato, confrontarlo con i trend di mercato e valutarne l'adeguatezza per una specifica offerta di lavoro.
    L'obiettivo è fornire un'analisi chiara e actionable per aiutare il team di recruiting a prendere una decisione informata.
    """
    
    user_prompt_template = """
    **DATI A DISPOSIZIONE**

    1. **OFFERTA DI LAVORO TARGET:**
    ```
    {job_offer}
    ```

    2. **TREND DI MERCATO (Percorsi di Carriera Passati Aggregati per Durata in Mesi):**
    Questo JSON mostra le professioni più comuni nei percorsi di carriera di chi oggi ricopre la posizione target.
    ```json
    {market_data}
    ```

    3. **PERCORSO DI CARRIERA DEL CANDIDATO (Esperienze Passate):**
    Questo JSON elenca le esperienze passate del candidato, normalizzate con le mansioni ESCO.
    ```json
    {candidate_data}
    ```

    **ISTRUZIONI**
   - Basandoti ESCLUSIVAMENTE sui dati forniti, redigi un report di posizionamento dettagliato.
   - Struttura l'output rivolgendoti direttamente al candidato, quindi usa sempre la seconda persona singolare.
   - Ricordati che l'output sarà inviato ad un candidato da parte dell'azienda per cui lavori, quindi rivolgiti a nome dell'azienda usando sempre la prima persona plurale
   - Mantieni uno stile professionale ma realista e oggettivo. Non essere sempre accondiscendente.
   - Concentrati esclusivamente sull'ananlisi rispetto al trend di mercato, senza fornire consigli al candidato. 
    *FORMATO DELL'OUTPUT RICHIESTO**
    Usa esattamente questa struttura Markdown:

    ### Analisi dei Trend di Mercato
    Sintetizza in 2-3 frasi quali sono i percorsi di carriera più comuni o i ruoli propedeutici più importanti che emergono dai dati di mercato per arrivare a ricoprire il ruolo target.

    ### Valutazione del Candidato
    Valuta qualitativamente se il percorso del candidato è tradizionale (in linea con il mercato), atipico ma coerente, o con evidenti deviazioni.

    Mantieni un tono professionale, oggettivo e costruttivo. NON ripetere i dati grezzi dei JSON.
    """
    
    # Verifica che market_json e candidate_json siano dizionari validi
    if not isinstance(market_json, dict):
        print(f"⚠ ERRORE (async): market_json non è un dizionario, è {type(market_json)}")
        market_json = {}
    if not isinstance(candidate_json, dict):
        print(f"⚠ ERRORE (async): candidate_json non è un dizionario, è {type(candidate_json)}")
        candidate_json = {}
    
    # Serializza in JSON per il prompt
    try:
        market_data_str = json.dumps(market_json, indent=2, ensure_ascii=False) if market_json else "{}"
        candidate_data_str = json.dumps(candidate_json, indent=2, ensure_ascii=False) if candidate_json else "{}"
    except Exception as e:
        print(f"✗ ERRORE durante serializzazione JSON (async): {e}")
        market_data_str = "{}"
        candidate_data_str = "{}"
    
    # La preparazione del prompt rimane identica, è un'operazione sincrona e veloce
    user_prompt = user_prompt_template.format(
        job_offer=job_offer_text,
        market_data=market_data_str,
        candidate_data=candidate_data_str
    )

    # <-- MODIFICA CHIAVE: Chiama la versione async con 'await' -->
    return await get_llm_response_async(
        prompt=user_prompt,
        model=settings.LLM_MODEL,
        system_prompt=system_prompt,
        temperature=0.4,
        max_tokens=1000
    )