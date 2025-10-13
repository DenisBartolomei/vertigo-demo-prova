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

# Inizializza il client Azure OpenAI solo se tutte le variabili sono state trovate
client = None
if not all([AZURE_ENDPOINT, AZURE_API_KEY, AZURE_DEPLOYMENT_NAME]):
    print("❌ ERRORE CRITICO: Variabili Azure OpenAI mancanti.")
    print(f"   AZURE_OPENAI_ENDPOINT: {'✅' if AZURE_ENDPOINT else '❌'}")
    print(f"   AZURE_OPENAI_API_KEY: {'✅' if AZURE_API_KEY else '❌'}")
    print(f"   AZURE_OPENAI_DEPLOYMENT_NAME: {'✅' if AZURE_DEPLOYMENT_NAME else '❌'}")
    print(f"   AZURE_OPENAI_API_VERSION: {AZURE_API_VERSION}")
else:
    client = AzureOpenAI(
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION,
        azure_endpoint=AZURE_ENDPOINT
    )

def get_llm_response(prompt: str, model: str, system_prompt: str, **kwargs) -> str:
    """
    Invia un prompt per una risposta testuale semplice.
    """
    # Controlla se il client è stato inizializzato correttamente
    if client is None:
        return "Errore: Il servizio LLM non è configurato a causa di una chiave API mancante."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,  # Usa il deployment name per Azure
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
    temperature: Optional[float] = None,  # <-- Parametro opzionale
    max_tokens: Optional[int] = None      # <-- Nuovo parametro opzionale
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
        print(f"Errore nella chiamata LLM strutturata: {e}")
        return None