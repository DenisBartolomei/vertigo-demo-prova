#!/usr/bin/env python3
"""
Test Azure OpenAI Configuration
Verifica che la configurazione Azure OpenAI funzioni correttamente
"""

import os
import sys
from dotenv import load_dotenv

# Carica variabili d'ambiente dal file env.azure.production
load_dotenv('env.azure.production')

try:
    from openai import AzureOpenAI
except ImportError:
    print("❌ ERRORE: openai package non installato")
    print("Installa con: pip install openai")
    sys.exit(1)

# Configurazione Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") 
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-06-01")

# Mapping modelli (come nel nostro codice)
MODEL_MAPPING = {
    "gpt-4.1-2025-04-14": "gpt-4.1",
    "gpt-4o-mini": "gpt-4.1"
}

def test_azure_openai():
    """Test completo della configurazione Azure OpenAI"""
    print("🧪 Test Azure OpenAI Configuration...")
    print("=" * 50)
    
    # Verifica configurazione
    print("\n📋 Verifica Configurazione:")
    print(f"Endpoint: {AZURE_OPENAI_ENDPOINT or '❌ MANCANTE'}")
    print(f"API Key: {'✅ Presente' if AZURE_OPENAI_API_KEY else '❌ MANCANTE'}")
    print(f"API Version: {AZURE_OPENAI_API_VERSION}")
    
    if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
        print("\n❌ ERRORE: Configurazione Azure OpenAI mancante!")
        print("Aggiorna il file env.azure.production con le tue credenziali Azure")
        return False
    
    # Verifica che non siano placeholder
    if "your-resource" in AZURE_OPENAI_ENDPOINT or "your_azure_api_key" in AZURE_OPENAI_API_KEY:
        print("\n⚠️ ATTENZIONE: Le credenziali sembrano essere placeholder!")
        print("Aggiorna il file env.azure.production con le credenziali reali")
        return False
    
    try:
        # Inizializza client
        print("\n🔧 Inizializzazione Client...")
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION
        )
        print("✅ Client Azure OpenAI inizializzato correttamente")
        
        # Test chiamata semplice
        print("\n🔄 Test 1: Chiamata Semplice...")
        azure_model = MODEL_MAPPING["gpt-4.1-2025-04-14"]
        print(f"Deployment utilizzato: {azure_model}")
        
        response = client.chat.completions.create(
            model=azure_model,
            messages=[
                {"role": "system", "content": "Sei un assistente utile e conciso. Rispondi sempre in italiano."},
                {"role": "user", "content": "Dimmi solo 'Test Azure OpenAI completato con successo!'"}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ Risposta ricevuta: {result}")
        
        # Test chiamata strutturata (come nel nostro sistema)
        print("\n🔄 Test 2: Chiamata Strutturata...")
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "Funzione di test per verificare le chiamate strutturate",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "test_result": {
                                "type": "string",
                                "description": "Risultato del test"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["success", "error"],
                                "description": "Status del test"
                            }
                        },
                        "required": ["test_result", "status"]
                    }
                }
            }
        ]
        
        response = client.chat.completions.create(
            model=azure_model,
            messages=[
                {"role": "system", "content": "Sei un assistente che restituisce sempre JSON strutturato."},
                {"role": "user", "content": "Restituisci un JSON con test_result: 'Chiamata strutturata funzionante' e status: 'success'"}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "test_function"}},
            max_tokens=100,
            temperature=0.1
        )
        
        if response.choices and response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            print(f"✅ Chiamata strutturata ricevuta: {tool_call.function.arguments}")
        else:
            print("⚠️ Nessuna function call ricevuta")
        
        # Test con modello leggero (stesso deployment)
        print("\n🔄 Test 3: Modello Leggero (gpt-4o-mini -> gpt-4.1)...")
        light_model = MODEL_MAPPING["gpt-4o-mini"]
        print(f"Deployment utilizzato: {light_model}")
        
        response = client.chat.completions.create(
            model=light_model,
            messages=[
                {"role": "system", "content": "Sei un assistente conciso."},
                {"role": "user", "content": "Rispondi con una sola parola: 'Perfetto'"}
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ Risposta modello leggero: {result}")
        
        print("\n🎉 Tutti i test completati con successo!")
        print("✅ Azure OpenAI è configurato correttamente")
        return True
        
    except Exception as e:
        print(f"\n❌ ERRORE durante il test: {e}")
        print(f"Tipo errore: {type(e).__name__}")
        
        # Suggerimenti per errori comuni
        if "404" in str(e):
            print("\n💡 SUGGERIMENTO: Errore 404 - Verifica che il deployment 'gpt-4.1' esista nel tuo Azure OpenAI resource")
        elif "401" in str(e):
            print("\n💡 SUGGERIMENTO: Errore 401 - Verifica la tua API key")
        elif "endpoint" in str(e).lower():
            print("\n💡 SUGGERIMENTO: Verifica l'endpoint Azure OpenAI")
        
        return False

def main():
    """Funzione principale"""
    print("🚀 Azure OpenAI Test Suite")
    print("Verifica configurazione prima del deploy")
    print("=" * 50)
    
    success = test_azure_openai()
    
    if success:
        print("\n✅ TUTTI I TEST SUPERATI!")
        print("Puoi procedere con il deploy in sicurezza")
        return 0
    else:
        print("\n❌ TEST FALLITI!")
        print("Risolvi i problemi prima del deploy")
        return 1

if __name__ == "__main__":
    exit(main())
