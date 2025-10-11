import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from typing import Optional

# Carica le variabili dal file .env se presente (per lo sviluppo locale)
load_dotenv()

# ✅ CONFIGURAZIONE AZURE OPENAI (Europa)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") 
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# ✅ MAPPING MODELLI AZURE
MODEL_MAPPING = {
    "gpt-4.1-2025-04-14": "gpt-4.1",           # Modello principale
    "gpt-4o-mini": "gpt-4.1-nano"              # Modello leggero
}

# ✅ Client Azure OpenAI con residenza dati Europa
client = None
if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
    print("❌ ERRORE CRITICO: Configurazione Azure OpenAI mancante per compliance GDPR.")
else:
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )
    print("✅ Client Azure OpenAI configurato per residenza dati Europa (GDPR compliant)")

def get_llm_response(prompt: str, model: str, system_prompt: str, **kwargs) -> str:
    """
    Invia un prompt per una risposta testuale semplice.
    ✅ Dati processati esclusivamente in Europa
    """
    if client is None:
        return "Errore: Il servizio LLM non è configurato per compliance GDPR."

    # ✅ Mapping automatico modello
    azure_model = MODEL_MAPPING.get(model, model)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = client.chat.completions.create(
            model=azure_model,  # ✅ Usa deployment Azure
            messages=messages,
            **kwargs 
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Errore nella chiamata Azure OpenAI: {e}")
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
    # ✅ Controlla se il client Azure è stato inizializzato correttamente
    if client is None:
        print("Errore: Il servizio LLM non è configurato per compliance GDPR.")
        return None

    # ✅ Mapping automatico modello
    azure_model = MODEL_MAPPING.get(model, model)

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
        "model": azure_model,  # ✅ Usa deployment Azure
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
        print(f"Errore nella chiamata Azure OpenAI strutturata: {e}")
        return None