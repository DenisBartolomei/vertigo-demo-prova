# Script per aggiungere index MongoDB per la cache LLM
# Esegui: python scripts/add_llm_cache_indexes.py

from services.data_manager import db
from recruitment_suite.config import settings
from datetime import datetime

def add_llm_cache_indexes():
    """Aggiunge index per la cache LLM su MongoDB"""
    if db is None:
        print("ERRORE: Connessione MongoDB non disponibile")
        return
    
    collection_name = "suite_llm_cache"
    collection = db[collection_name]
    
    print(f"Creazione index per collection '{collection_name}'...")
    
    try:
        # Index su expires_at per pulizia automatica cache scaduta
        collection.create_index(
            [("expires_at", 1)],
            name="expires_at_index",
            background=True
        )
        print("✓ Index creato su 'expires_at' per pulizia cache scaduta")
        
        # Index su created_at per statistiche
        collection.create_index(
            [("created_at", 1)],
            name="created_at_index",
            background=True
        )
        print("✓ Index creato su 'created_at' per statistiche")
        
        print(f"\n✓ Tutti gli index per '{collection_name}' creati con successo!")
        
        # Mostra index esistenti
        existing_indexes = collection.list_indexes()
        print(f"\nIndex esistenti su '{collection_name}':")
        for idx in existing_indexes:
            print(f"  - {idx.get('name', 'N/A')}: {idx.get('key', {})}")
            
    except Exception as e:
        print(f"ERRORE durante la creazione degli index: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_llm_cache_indexes()

