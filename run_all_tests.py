#!/usr/bin/env python3
"""
Master Test Suite
Esegue tutti i test per verificare la configurazione Azure OpenAI
"""

import subprocess
import sys
import os
from pathlib import Path

def run_test(test_file, test_name):
    """Esegue un singolo test"""
    print(f"\n{'='*60}")
    print(f"🧪 ESEGUENDO: {test_name}")
    print(f"📁 File: {test_file}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([
            sys.executable, test_file
        ], capture_output=True, text=True, timeout=300)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout nel test {test_name}")
        return False
    except Exception as e:
        print(f"❌ Errore esecuzione test {test_name}: {e}")
        return False

def check_environment():
    """Verifica che l'ambiente sia configurato correttamente"""
    print("🔍 Verifica Ambiente...")
    
    # Verifica file di configurazione
    config_file = Path("env.azure.production")
    if not config_file.exists():
        print("❌ File env.azure.production non trovato")
        return False
    
    print("✅ File env.azure.production trovato")
    
    # Verifica dipendenze Python
    try:
        import openai
        print("✅ Package openai installato")
    except ImportError:
        print("❌ Package openai non installato")
        print("Installa con: pip install openai")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ Package python-dotenv installato")
    except ImportError:
        print("❌ Package python-dotenv non installato")
        print("Installa con: pip install python-dotenv")
        return False
    
    return True

def main():
    """Funzione principale"""
    print("🚀 MASTER TEST SUITE")
    print("Verifica completa configurazione Azure OpenAI")
    print("=" * 60)
    
    # Verifica ambiente
    if not check_environment():
        print("\n❌ Ambiente non configurato correttamente")
        return 1
    
    # Lista dei test da eseguire
    tests = [
        ("test_azure_openai.py", "Test Azure OpenAI Configuration"),
        ("test_llm_service.py", "Test LLM Service"),
        ("test_backend_endpoints.py", "Test Backend Endpoints"),
    ]
    
    results = []
    
    # Esegui tutti i test
    for test_file, test_name in tests:
        if Path(test_file).exists():
            success = run_test(test_file, test_name)
            results.append((test_name, success))
        else:
            print(f"❌ File test {test_file} non trovato")
            results.append((test_name, False))
    
    # Riepilogo finale
    print(f"\n{'='*60}")
    print("📊 RIEPILOGO FINALE")
    print(f"{'='*60}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nRisultato Complessivo: {passed}/{total} test superati")
    
    if passed == total:
        print("\n🎉 TUTTI I TEST SUPERATI!")
        print("✅ La configurazione Azure OpenAI è corretta")
        print("✅ Puoi procedere con il deploy in sicurezza")
        print("\n🚀 Prossimi passi:")
        print("1. Aggiorna le credenziali Azure nel file env.azure.production")
        print("2. Esegui il deploy con: bash deploy.sh")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test falliti")
        print("❌ Risolvi i problemi prima del deploy")
        print("\n🔧 Suggerimenti:")
        print("1. Verifica le credenziali Azure OpenAI")
        print("2. Assicurati che il deployment 'gpt-4.1' esista")
        print("3. Controlla la connessione internet")
        return 1

if __name__ == "__main__":
    exit(main())
