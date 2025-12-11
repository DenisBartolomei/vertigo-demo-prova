#!/usr/bin/env python3
"""
Script per aggiungere index MongoDB alle nuove collections del benchmark.
Eseguire questo script dopo il deploy per ottimizzare le query.

Usage: python scripts/add_benchmark_indexes.py
"""

import os
import sys
from dotenv import load_dotenv

# Aggiungi la root del progetto al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.data_manager import db
from recruitment_suite.config import settings

def add_benchmark_indexes():
    """Aggiunge index alle collections del benchmark per lookup veloce."""
    
    if db is None:
        print("ERRORE: Connessione a MongoDB non disponibile.")
        return False
    
    try:
        # Index per suite_offer_vectors
        collection_name = settings.MONGO_COLLECTION_OFFER_VECTORS
        collection = db[collection_name]
        
        # Rimuovi eventuali indici problematici (es. job_title_1 che causa duplicate key error)
        try:
            existing_indexes = collection.list_indexes()
            for idx in existing_indexes:
                idx_name = idx.get('name', '')
                if 'job_title' in idx_name.lower():
                    print(f"⚠ Rimozione indice problematico: {idx_name}")
                    collection.drop_index(idx_name)
        except Exception as e:
            print(f"⚠ Errore durante rimozione indici esistenti: {e}")
        
        # Index su _id (già presente di default, ma assicuriamoci)
        # Index su tenant_id per query multi-tenant
        collection.create_index("tenant_id")
        # Index su position_id per query
        collection.create_index("position_id")
        # Index compound su tenant_id + position_id per query veloci
        collection.create_index([("tenant_id", 1), ("position_id", 1)])
        # Index su created_at per query temporali
        collection.create_index("created_at")
        print(f"✓ Index creati per {collection_name}")
        
        # Index per suite_candidate_vectors
        collection_name = settings.MONGO_COLLECTION_CANDIDATE_VECTORS
        collection = db[collection_name]
        
        # Index su _id (già presente di default)
        # Index su text_hash per validazione rapida
        collection.create_index("text_hash")
        # Index su created_at per query temporali
        collection.create_index("created_at")
        print(f"✓ Index creati per {collection_name}")
        
        print("\n✓ Tutti gli index sono stati creati con successo!")
        return True
        
    except Exception as e:
        print(f"ERRORE durante la creazione degli index: {e}")
        return False

if __name__ == "__main__":
    load_dotenv()
    success = add_benchmark_indexes()
    sys.exit(0 if success else 1)

