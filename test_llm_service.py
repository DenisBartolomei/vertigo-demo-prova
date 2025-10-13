#!/usr/bin/env python3
"""
Test LLM Service
Verifica che il nostro servizio LLM funzioni correttamente con Azure OpenAI
"""

import os
import sys
import json
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv('env.azure.production')

# Aggiungi il path per importare i nostri moduli
sys.path.append('.')

try:
    from interviewer.llm_service import get_llm_response, get_structured_llm_response
except ImportError as e:
    print(f"❌ ERRORE: Impossibile importare llm_service: {e}")
    sys.exit(1)

def test_llm_service():
    """Test completo del nostro servizio LLM"""
    print("🧪 Test LLM Service...")
    print("=" * 50)
    
    try:
        # Test 1: Chiamata semplice
        print("\n🔄 Test 1: get_llm_response (chiamata semplice)...")
        response = get_llm_response(
            prompt="Dimmi solo 'LLM Service test completato con successo!'",
            model="gpt-4.1-2025-04-14",
            system_prompt="Sei un assistente utile e conciso. Rispondi sempre in italiano."
        )
        print(f"✅ Risposta ricevuta: {response}")
        
        # Verifica che non sia un messaggio di errore
        if "Errore:" in response or "Error:" in response:
            print(f"❌ Risposta contiene errore: {response}")
            return False
        
        # Test 2: Chiamata strutturata
        print("\n🔄 Test 2: get_structured_llm_response (chiamata strutturata)...")
        
        tool_schema = {
            "type": "object",
            "properties": {
                "test_status": {
                    "type": "string",
                    "description": "Status del test",
                    "enum": ["success", "error"]
                },
                "timestamp": {
                    "type": "string", 
                    "description": "Timestamp del test"
                },
                "model_used": {
                    "type": "string",
                    "description": "Modello utilizzato"
                }
            },
            "required": ["test_status", "timestamp", "model_used"]
        }
        
        structured_response = get_structured_llm_response(
            prompt="Restituisci un JSON con test_status: 'success', timestamp: '2025-01-01', model_used: 'gpt-4.1'",
            model="gpt-4.1-2025-04-14",
            system_prompt="Sei un assistente che restituisce sempre JSON strutturato valido.",
            tool_name="test_function",
            tool_schema=tool_schema,
            temperature=0.1,
            max_tokens=200
        )
        
        if structured_response:
            print(f"✅ Risposta strutturata ricevuta: {structured_response}")
            
            # Verifica che sia JSON valido
            try:
                parsed = json.loads(structured_response)
                print(f"✅ JSON valido: {parsed}")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON non valido: {e}")
                print(f"Contenuto: {structured_response}")
        else:
            print("❌ Nessuna risposta strutturata ricevuta")
            return False
        
        # Test 3: Modello leggero
        print("\n🔄 Test 3: Test modello leggero (gpt-4o-mini)...")
        light_response = get_llm_response(
            prompt="Rispondi con una sola parola: 'Eccellente'",
            model="gpt-4o-mini",
            system_prompt="Sei un assistente molto conciso.",
            max_tokens=10
        )
        print(f"✅ Risposta modello leggero: {light_response}")
        
        # Test 4: Test con parametri personalizzati
        print("\n🔄 Test 4: Test con parametri personalizzati...")
        custom_response = get_llm_response(
            prompt="Genera 3 aggettivi positivi per descrivere un sistema AI",
            model="gpt-4.1-2025-04-14",
            system_prompt="Sei un assistente creativo.",
            temperature=0.7,
            max_tokens=100
        )
        print(f"✅ Risposta personalizzata: {custom_response}")
        
        print("\n🎉 LLM Service test completato con successo!")
        print("✅ Il nostro servizio LLM funziona correttamente con Azure OpenAI")
        return True
        
    except Exception as e:
        print(f"\n❌ ERRORE durante il test LLM Service: {e}")
        print(f"Tipo errore: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

def test_model_mapping():
    """Test specifico per il mapping dei modelli"""
    print("\n🔄 Test 5: Verifica Model Mapping...")
    
    try:
        from interviewer.llm_service import MODEL_MAPPING
        
        print(f"✅ Model mapping configurato: {MODEL_MAPPING}")
        
        # Verifica che il mapping sia corretto
        expected_mapping = {
            "gpt-4.1-2025-04-14": "gpt-4.1",
            "gpt-4o-mini": "gpt-4.1"
        }
        
        if MODEL_MAPPING == expected_mapping:
            print("✅ Model mapping corretto")
            return True
        else:
            print(f"❌ Model mapping errato. Atteso: {expected_mapping}")
            return False
            
    except Exception as e:
        print(f"❌ Errore nel test model mapping: {e}")
        return False

def main():
    """Funzione principale"""
    print("🚀 LLM Service Test Suite")
    print("Verifica che il nostro servizio LLM funzioni con Azure OpenAI")
    print("=" * 50)
    
    # Test configurazione base
    if not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_API_KEY"):
        print("❌ ERRORE: Variabili d'ambiente Azure OpenAI non configurate")
        print("Verifica il file env.azure.production")
        return 1
    
    success_llm = test_llm_service()
    success_mapping = test_model_mapping()
    
    if success_llm and success_mapping:
        print("\n✅ TUTTI I TEST LLM SERVICE SUPERATI!")
        print("Il servizio è pronto per il deploy")
        return 0
    else:
        print("\n❌ TEST LLM SERVICE FALLITI!")
        print("Risolvi i problemi prima del deploy")
        return 1

if __name__ == "__main__":
    exit(main())
