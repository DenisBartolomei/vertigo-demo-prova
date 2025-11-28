import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from typing import Optional

# Carica le variabili dal file .env se presente (per lo sviluppo locale)
load_dotenv()

# Variabili Azure OpenAI
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-14")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Variabili Azure OpenAI per Classificazione (con fallback alle variabili standard)
AZURE_CLASSIFICATION_ENDPOINT = os.getenv("AZURE_OPENAI_CLASSIFICATION_ENDPOINT") or AZURE_ENDPOINT
AZURE_CLASSIFICATION_API_KEY = os.getenv("AZURE_OPENAI_CLASSIFICATION_API_KEY") or AZURE_API_KEY
AZURE_CLASSIFICATION_API_VERSION = os.getenv("AZURE_OPENAI_CLASSIFICATION_API_VERSION") or AZURE_API_VERSION
AZURE_CLASSIFICATION_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CLASSIFICATION_DEPLOYMENT_NAME", "gpt-4.1-mini")

# Inizializza il client Azure OpenAI solo se tutte le variabili sono state trovate
client = None
if not all([AZURE_ENDPOINT, AZURE_API_KEY, AZURE_DEPLOYMENT_NAME]):
    print("ERRORE CRITICO: Variabili Azure OpenAI mancanti.")
    print(f"   AZURE_OPENAI_ENDPOINT: {'OK' if AZURE_ENDPOINT else 'MISSING'}")
    print(f"   AZURE_OPENAI_API_KEY: {'OK' if AZURE_API_KEY else 'MISSING'}")
    print(f"   AZURE_OPENAI_DEPLOYMENT_NAME: {'OK' if AZURE_DEPLOYMENT_NAME else 'MISSING'}")
    print(f"   AZURE_OPENAI_API_VERSION: {AZURE_API_VERSION}")
else:
    client = AzureOpenAI(
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION,
        azure_endpoint=AZURE_ENDPOINT
    )

# Inizializza il client Azure OpenAI per Classificazione
classification_client = None
if all([AZURE_CLASSIFICATION_ENDPOINT, AZURE_CLASSIFICATION_API_KEY, AZURE_CLASSIFICATION_DEPLOYMENT_NAME]):
    classification_client = AzureOpenAI(
        api_key=AZURE_CLASSIFICATION_API_KEY,
        api_version=AZURE_CLASSIFICATION_API_VERSION,
        azure_endpoint=AZURE_CLASSIFICATION_ENDPOINT
    )
    print(f"✓ Client di classificazione inizializzato con deployment: {AZURE_CLASSIFICATION_DEPLOYMENT_NAME}")
else:
    print("⚠ ATTENZIONE: Client di classificazione non inizializzato (variabili mancanti)")

def get_llm_response(prompt: str, model: str, system_prompt: str, use_classification_client: bool = False, **kwargs) -> str:
    """
    Invia un prompt per una risposta testuale semplice.
    
    Args:
        prompt: Il prompt da inviare
        model: Il nome del modello (usato per compatibilità, ma il deployment name viene scelto automaticamente)
        system_prompt: Il prompt di sistema
        use_classification_client: Se True, usa il client di classificazione invece del client principale
        **kwargs: Parametri aggiuntivi da passare all'API
    """
    # Scegli il client e il deployment name in base al parametro
    if use_classification_client:
        if classification_client is None:
            return "Errore: Il servizio LLM di classificazione non è configurato a causa di una chiave API mancante."
        selected_client = classification_client
        selected_deployment = AZURE_CLASSIFICATION_DEPLOYMENT_NAME
    else:
        if client is None:
            return "Errore: Il servizio LLM non è configurato a causa di una chiave API mancante."
        selected_client = client
        selected_deployment = AZURE_DEPLOYMENT_NAME

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    try:
        response = selected_client.chat.completions.create(
            model=selected_deployment,  # Usa il deployment name appropriato
            messages=messages,
            **kwargs 
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Errore nella chiamata LLM testuale: {e}")
        return f"Errore: {e}"

def get_structured_llm_response(
    prompt: str, 
    model: str, 
    system_prompt: str, 
    tool_name: str, 
    tool_schema: dict,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    use_classification_client: bool = False     
) -> Optional[str]:
    """
    Invia un prompt forzando un output strutturato tramite la definizione di un tool.

    Accetta parametri opzionali come 'temperature' e 'max_tokens'. Se non vengono
    forniti, non vengono inviati all'API, che utilizzerà i propri valori di default.

    Restituisce gli argomenti della funzione chiamata come stringa JSON.
    """
    # Controlla se il client è stato inizializzato correttamente
    if client is None:
        print("Errore: Il servizio LLM non è configurato a causa di una chiave API mancante.")
        return None

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": f"Salva i dati strutturati per {tool_name}",
                "parameters": tool_schema
            }
        }
    ]
    
    # Prepariamo gli argomenti per la chiamata API
    # Iniziamo con quelli obbligatori
    api_kwargs = {
        "model": AZURE_DEPLOYMENT_NAME,  # Usa il deployment name per Azure
        "messages": messages,
        "tools": tools,
        "tool_choice": {"type": "function", "function": {"name": tool_name}}
    }
    
    # Aggiungiamo i parametri opzionali SOLO se sono stati forniti
    if temperature is not None:
        api_kwargs['temperature'] = temperature
    if max_tokens is not None:
        api_kwargs['max_tokens'] = max_tokens
        
    # Retry logic per rate limits (429)
    import time
    max_retries = 3
    base_delay = 2  # secondi
    
    for attempt in range(max_retries):
        try:
            # Usiamo l'unpacking del dizionario (**) per passare tutti gli argomenti
            response = client.chat.completions.create(**api_kwargs)
            
            if response.choices and response.choices[0].message.tool_calls:
                arguments = response.choices[0].message.tool_calls[0].function.arguments
                return arguments
            else:
                print("Errore: La risposta dell'LLM non ha chiamato la funzione richiesta o è vuota.")
                return None
        except Exception as e:
            error_str = str(e)
            # Controlla se è un rate limit error (429)
            if "429" in error_str or "RateLimit" in error_str or "rate limit" in error_str.lower():
                if attempt < max_retries - 1:
                    # Estrai il tempo di attesa dal messaggio di errore se presente
                    wait_time = base_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                    if "retry after" in error_str.lower():
                        # Prova a estrarre il numero di secondi dal messaggio
                        import re
                        match = re.search(r'retry after (\d+)', error_str.lower())
                        if match:
                            wait_time = int(match.group(1)) + 5  # Aggiungi 5 secondi di buffer
                    
                    print(f"⚠ Rate limit raggiunto (tentativo {attempt + 1}/{max_retries}). Attendo {wait_time}s prima di riprovare...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ ERRORE CRITICO: Rate limit raggiunto dopo {max_retries} tentativi. Abbandono.")
                    return None
            else:
                # Altri errori: non retry, ritorna None
                print(f"Errore nella chiamata LLM strutturata: {e}")
                return None
    
    return None
    
from openai import AsyncAzureOpenAI

# Inizializza il client async solo se tutte le variabili sono state trovate
client_async = None
if all([AZURE_ENDPOINT, AZURE_API_KEY, AZURE_DEPLOYMENT_NAME]):
    client_async = AsyncAzureOpenAI(
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION,
        azure_endpoint=AZURE_ENDPOINT
    )
    print(f"✓ Client AsyncAzureOpenAI inizializzato:")
    print(f"   Endpoint: {AZURE_ENDPOINT}")
    print(f"   Deployment: {AZURE_DEPLOYMENT_NAME}")
    print(f"   API Version: {AZURE_API_VERSION}")
else:
    print("⚠ ATTENZIONE: Client AsyncAzureOpenAI non inizializzato (variabili mancanti)")
    print(f"   AZURE_OPENAI_ENDPOINT: {'OK' if AZURE_ENDPOINT else 'MISSING'}")
    print(f"   AZURE_OPENAI_API_KEY: {'OK' if AZURE_API_KEY else 'MISSING'}")
    print(f"   AZURE_OPENAI_DEPLOYMENT_NAME: {'OK' if AZURE_DEPLOYMENT_NAME else 'MISSING'}")

# <-- MODIFICA: Tutta la funzione è ora 'async def' e usa 'await' -->
async def get_llm_response_async(prompt: str, model: str, system_prompt: str, **kwargs) -> str:
    """
    Versione ASINCRONA: Invia un prompt per una risposta testuale semplice.
    """
    if client_async is None:
        return "Errore: Il servizio LLM non è configurato a causa di una chiave API mancante."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    # Retry logic per rate limits (429)
    import asyncio
    max_retries = 3
    base_delay = 2  # secondi
    
    for attempt in range(max_retries):
        try:
            # La chiamata al client ora è asincrona
            response = await client_async.chat.completions.create(
                model=AZURE_DEPLOYMENT_NAME,  # Usa il deployment name per Azure
                messages=messages,
                **kwargs 
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_str = str(e)
            # Controlla se è un rate limit error (429)
            if "429" in error_str or "RateLimit" in error_str or "rate limit" in error_str.lower():
                if attempt < max_retries - 1:
                    # Estrai il tempo di attesa dal messaggio di errore se presente
                    wait_time = base_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                    if "retry after" in error_str.lower():
                        # Prova a estrarre il numero di secondi dal messaggio
                        import re
                        match = re.search(r'retry after (\d+)', error_str.lower())
                        if match:
                            wait_time = int(match.group(1)) + 5  # Aggiungi 5 secondi di buffer
                    
                    print(f"⚠ Rate limit raggiunto (tentativo {attempt + 1}/{max_retries}). Attendo {wait_time}s prima di riprovare...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"❌ ERRORE CRITICO: Rate limit raggiunto dopo {max_retries} tentativi. Abbandono.")
                    return f"Errore: Rate limit raggiunto dopo {max_retries} tentativi"
            else:
                # Altri errori: non retry, ritorna errore
                print(f"Errore nella chiamata LLM testuale asincrona: {e}")
                return f"Errore: {e}"
    
    return f"Errore: Rate limit raggiunto dopo {max_retries} tentativi"

# <-- MODIFICA: Tutta la funzione è ora 'async def' e usa 'await' -->
async def get_structured_llm_response_async(
    prompt: str, 
    model: str, 
    system_prompt: str, 
    tool_name: str, 
    tool_schema: dict,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Optional[str]:
    """
    Versione ASINCRONA: Invia un prompt forzando un output strutturato.
    """
    if client_async is None:
        print("Errore: Il servizio LLM non è configurato a causa di una chiave API mancante.")
        return None

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": f"Salva i dati strutturati per {tool_name}",
                "parameters": tool_schema
            }
        }
    ]
    
    api_kwargs = {
        "model": AZURE_DEPLOYMENT_NAME,  # Usa il deployment name per Azure
        "messages": messages,
        "tools": tools,
        "tool_choice": {"type": "function", "function": {"name": tool_name}}
    }
    
    if temperature is not None:
        api_kwargs['temperature'] = temperature
    if max_tokens is not None:
        api_kwargs['max_tokens'] = max_tokens
        
    # Retry logic per rate limits (429)
    import asyncio
    max_retries = 3
    base_delay = 2  # secondi
    
    for attempt in range(max_retries):
        try:
            # La chiamata al client ora è asincrona
            response = await client_async.chat.completions.create(**api_kwargs)
            
            if response.choices and response.choices[0].message.tool_calls:
                arguments = response.choices[0].message.tool_calls[0].function.arguments
                return arguments
            else:
                print("Errore: La risposta dell'LLM non ha chiamato la funzione richiesta o è vuota.")
                return None
        except Exception as e:
            error_str = str(e)
            # Controlla se è un rate limit error (429)
            if "429" in error_str or "RateLimit" in error_str or "rate limit" in error_str.lower():
                if attempt < max_retries - 1:
                    # Estrai il tempo di attesa dal messaggio di errore se presente
                    wait_time = base_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                    if "retry after" in error_str.lower():
                        # Prova a estrarre il numero di secondi dal messaggio
                        import re
                        match = re.search(r'retry after (\d+)', error_str.lower())
                        if match:
                            wait_time = int(match.group(1)) + 5  # Aggiungi 5 secondi di buffer
                    
                    print(f"⚠ Rate limit raggiunto (tentativo {attempt + 1}/{max_retries}). Attendo {wait_time}s prima di riprovare...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"❌ ERRORE CRITICO: Rate limit raggiunto dopo {max_retries} tentativi. Abbandono.")
                    return None
            else:
                # Altri errori: non retry, ritorna None
                error_str = str(e)
                if "404" in error_str or "Resource not found" in error_str:
                    print(f"❌ ERRORE 404: Deployment '{AZURE_DEPLOYMENT_NAME}' non trovato.")
                    print(f"   Verifica che:")
                    print(f"   1. Il deployment name '{AZURE_DEPLOYMENT_NAME}' esista in Azure OpenAI")
                    print(f"   2. L'endpoint '{AZURE_ENDPOINT}' sia corretto (solo il dominio base, es: https://vertigo-realtime-gpt41.openai.azure.com)")
                    print(f"   3. La versione API '{AZURE_API_VERSION}' supporti tool calling")
                    print(f"   4. Le credenziali API siano corrette e abbiano i permessi necessari")
                    # Prova a suggerire una versione API alternativa se quella attuale non funziona
                    if "2025-04-14" in AZURE_API_VERSION:
                        print(f"   💡 Suggerimento: Prova a usare '2024-10-21' o '2024-08-01-preview' come AZURE_OPENAI_API_VERSION")
                else:
                    print(f"Errore nella chiamata LLM strutturata asincrona: {e}")
                return None
    
    return None