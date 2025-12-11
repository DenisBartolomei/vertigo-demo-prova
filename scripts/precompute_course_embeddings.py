"""
Script per pre-calcolare gli embeddings dei corsi e salvarli in MongoDB.
Esegui questo script UNA VOLTA dopo aver importato i corsi.

Usage:
    python scripts/precompute_course_embeddings.py
"""
import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentence_transformers import SentenceTransformer
from services.data_manager import db

EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
COURSES_COLLECTION_NAME = "courses"

def precompute_and_save_embeddings():
    """Calcola e salva gli embeddings per tutti i corsi."""
    print("=" * 70)
    print("🚀 INIZIO PRE-CALCOLO EMBEDDINGS CORSI")
    print("=" * 70)
    
    if db is None:
        print("❌ ERRORE: Connessione al database non disponibile.")
        print("   Verifica la variabile d'ambiente MONGO_CONNECTION_STRING")
        return False
    
    collection = db[COURSES_COLLECTION_NAME]
    
    # Recupera tutti i corsi
    print(f"\n📚 Recupero corsi dalla collection '{COURSES_COLLECTION_NAME}'...")
    courses = list(collection.find({}))
    
    if not courses:
        print("❌ ERRORE: Nessun corso trovato nel database.")
        print(f"   Assicurati di aver importato i corsi nella collection '{COURSES_COLLECTION_NAME}'")
        return False
    
    print(f"✓ Trovati {len(courses)} corsi nel database")
    
    # Carica il modello di embedding
    print(f"\n🤖 Caricamento modello di embedding '{EMBEDDING_MODEL_NAME}'...")
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("✓ Modello caricato con successo")
    except Exception as e:
        print(f"❌ ERRORE nel caricamento del modello: {e}")
        return False
    
    # Calcola embeddings per ogni corso
    print(f"\n⚙️  Calcolo embeddings per {len(courses)} corsi...")
    print("-" * 70)
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, course in enumerate(courses, 1):
        course_id = course.get('_id')
        course_name = course.get('Course Name', 'Unknown')
        
        # Check if embedding already exists
        if 'embedding' in course and course['embedding']:
            skipped_count += 1
            if i % 10 == 0 or i == len(courses):
                print(f"  [{i}/{len(courses)}] Saltato '{course_name}' (embedding già presente)")
            continue
        
        try:
            # Crea descrizione per l'embedding
            description = f"{course.get('Course Name', '')}. {course.get('Description', '')}"
            
            # Calcola embedding
            embedding = model.encode(description, convert_to_tensor=False)
            
            # Salva nel database (converti numpy array in lista)
            collection.update_one(
                {"_id": course_id},
                {"$set": {"embedding": embedding.tolist()}}
            )
            updated_count += 1
            
            # Progress indicator
            if i % 10 == 0 or i == len(courses):
                print(f"  [{i}/{len(courses)}] ✓ Processato '{course_name[:50]}...'")
        
        except Exception as e:
            error_count += 1
            print(f"  [{i}/{len(courses)}] ❌ ERRORE per '{course_name}': {e}")
    
    # Riepilogo finale
    print("-" * 70)
    print(f"\n📊 RIEPILOGO:")
    print(f"   • Corsi aggiornati: {updated_count}")
    print(f"   • Corsi saltati (già presenti): {skipped_count}")
    print(f"   • Errori: {error_count}")
    print(f"   • Totale: {len(courses)}")
    
    if updated_count > 0:
        print(f"\n✅ COMPLETATO! Embeddings salvati per {updated_count} corsi.")
        print("💡 Il backend ora caricherà gli embeddings pre-calcolati invece di ricalcolarli!")
        print("🚀 Startup time: da 4-5s a ~0.5s | Memory: da 2GB+ a ~500MB")
    elif skipped_count == len(courses):
        print("\n✓ Tutti i corsi hanno già embeddings pre-calcolati.")
    else:
        print("\n⚠️  Alcuni corsi non sono stati processati. Controlla gli errori sopra.")
    
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = precompute_and_save_embeddings()
    sys.exit(0 if success else 1)

