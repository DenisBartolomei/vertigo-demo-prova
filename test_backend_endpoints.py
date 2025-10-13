#!/usr/bin/env python3
"""
Test Backend Endpoints
Verifica che gli endpoint del backend funzionino correttamente
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv('env.azure.production')

# Configurazione
BACKEND_URL = "http://localhost:8080"
API_BASE = BACKEND_URL

def test_backend_health():
    """Test che il backend sia raggiungibile"""
    print("🧪 Test Backend Health...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Backend raggiungibile")
            return True
        else:
            print(f"⚠️ Backend risponde con status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend non raggiungibile: {e}")
        print("💡 Assicurati che il backend sia in esecuzione su http://localhost:8080")
        return False

def test_interview_parameters_endpoint():
    """Test endpoint parametri colloquio"""
    print("\n🔄 Test Endpoint Interview Parameters...")
    
    # Simula un JWT token (per test)
    test_token = "test_jwt_token"
    
    try:
        response = requests.get(
            f"{API_BASE}/interview-parameters",
            headers={"Authorization": f"Bearer {test_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Endpoint interview-parameters funziona: {data}")
            return True
        elif response.status_code == 401:
            print("⚠️ Endpoint richiede autenticazione (normale)")
            return True
        else:
            print(f"⚠️ Status inaspettato: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Errore chiamata endpoint: {e}")
        return False

def test_llm_service_in_backend():
    """Test che il servizio LLM funzioni nel contesto backend"""
    print("\n🔄 Test LLM Service nel Backend...")
    
    # Test diretto del servizio LLM importato dal backend
    try:
        sys.path.append('.')
        from interviewer.llm_service import get_llm_response
        
        response = get_llm_response(
            prompt="Test backend integration",
            model="gpt-4.1-2025-04-14",
            system_prompt="Sei un assistente di test."
        )
        
        if response and "Errore:" not in response:
            print("✅ LLM Service funziona nel contesto backend")
            return True
        else:
            print(f"❌ LLM Service non funziona: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Errore test LLM backend: {e}")
        return False

def test_azure_config_in_backend():
    """Test che la configurazione Azure sia corretta nel backend"""
    print("\n🔄 Test Configurazione Azure nel Backend...")
    
    try:
        # Verifica variabili d'ambiente
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        
        print(f"Endpoint: {endpoint or '❌ MANCANTE'}")
        print(f"API Key: {'✅ Presente' if api_key else '❌ MANCANTE'}")
        print(f"API Version: {api_version or '❌ MANCANTE'}")
        
        if not endpoint or not api_key:
            print("❌ Configurazione Azure incompleta")
            return False
        
        if "your-resource" in endpoint or "your_azure_api_key" in api_key:
            print("⚠️ Credenziali sembrano essere placeholder")
            return False
        
        print("✅ Configurazione Azure corretta")
        return True
        
    except Exception as e:
        print(f"❌ Errore verifica configurazione: {e}")
        return False

def main():
    """Funzione principale"""
    print("🚀 Backend Endpoints Test Suite")
    print("Verifica che il backend funzioni correttamente")
    print("=" * 50)
    
    tests = [
        ("Configurazione Azure", test_azure_config_in_backend),
        ("Backend Health", test_backend_health),
        ("LLM Service Backend", test_llm_service_in_backend),
        ("Interview Parameters", test_interview_parameters_endpoint),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Errore nel test {test_name}: {e}")
            results.append((test_name, False))
    
    # Riepilogo risultati
    print(f"\n{'='*50}")
    print("📊 RIEPILOGO RISULTATI:")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nRisultato: {passed}/{total} test superati")
    
    if passed == total:
        print("\n🎉 TUTTI I TEST BACKEND SUPERATI!")
        print("Il backend è pronto per il deploy")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test falliti")
        print("Risolvi i problemi prima del deploy")
        return 1

if __name__ == "__main__":
    exit(main())
