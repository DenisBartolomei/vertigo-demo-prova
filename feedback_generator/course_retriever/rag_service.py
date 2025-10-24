import faiss
import numpy as np
import streamlit as st 
from sentence_transformers import SentenceTransformer
# Importiamo l'oggetto 'db' dal nostro servizio dati centralizzato
from services.data_manager import db
import asyncio

# --- Configurazione ---
# Il modello di embedding rimane lo stesso, locale e performante
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
# Il nome della collection da cui leggere i corsi su MongoDB
COURSES_COLLECTION_NAME = "courses"

class RAGService:
    """
    Un servizio per la ricerca semantica (RAG) che carica i dati dei corsi da MongoDB,
    crea un indice vettoriale in memoria con FAISS e permette di cercare corsi simili.
    """
    # La logica interna della classe rimane la stessa, cambiamo solo da dove carica i dati.
    def __init__(self):
        print("Inizializzazione del RAG Service...")
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        # --- MODIFICA CHIAVE: Carichiamo i dati da MongoDB ---
        self.courses_data = self._load_courses_from_mongo()
        # Il resto del processo di indicizzazione rimane invariato
        self.index, self.course_map = self._build_index()
        print("RAG Service inizializzato con successo.")

    def _load_courses_from_mongo(self) -> list:
        """
        Carica i dati dei corsi dalla collection dedicata su MongoDB Atlas.
        """
        try:
            # Controlla se la connessione al DB è disponibile
            if db is None:
                raise ConnectionError("Connessione al database MongoDB non disponibile.")
            
            # Seleziona la collection
            collection = db[COURSES_COLLECTION_NAME]
            print(f"  - Recupero corsi dalla collection '{COURSES_COLLECTION_NAME}' su MongoDB...")
            
            # find({}) recupera tutti i documenti. list(...) li converte in una lista di dizionari Python.
            courses = list(collection.find({}))
            
            if not courses:
                print(f"  - ATTENZIONE: Nessun corso trovato nella collection '{COURSES_COLLECTION_NAME}'.")
            else:
                print(f"  - Recuperati {len(courses)} corsi dal database.")
            return courses
        except Exception as e:
            print(f"ERRORE CRITICO: Impossibile caricare il database dei corsi da MongoDB. {e}")
            return []

    def _build_index(self):
        """Costruisce l'indice FAISS in memoria. Questa funzione non cambia."""
        if not self.courses_data:
            return None, None
        descriptions = [f"{course.get('Course Name', '')}. {course.get('Description', '')}" for course in self.courses_data]
        print(f"  - Creazione embeddings per {len(descriptions)} corsi...")
        embeddings = self.model.encode(descriptions, convert_to_tensor=False)
        d = embeddings.shape[1]
        index = faiss.IndexFlatL2(d)
        index.add(np.array(embeddings, dtype=np.float32))
        course_map = {i: course for i, course in enumerate(self.courses_data)}
        print("  - Indice FAISS costruito in memoria.")
        return index, course_map

    def search(self, query: str, k: int = 8) -> list:
        """Esegue una ricerca di similarità sull'indice FAISS. Questa funzione non cambia."""
        if not self.index:
            print("Ricerca saltata: l'indice FAISS non è stato inizializzato.")
            return []
        query_embedding = self.model.encode([query])
        distances, indices = self.index.search(np.array(query_embedding, dtype=np.float32), k)
        results = [self.course_map[i] for i in indices[0]]
        return results

    async def search_async(self, query: str, k: int = 3) -> list:
            """
            Versione ASINCRONA della ricerca.
            Delega il lavoro pesante (sincrono) a un altro thread per non bloccare FastAPI.
            """
            print(f"Esecuzione di RAG search_async per la query: '{query[:30]}...'")
            # Questa riga esegue il tuo vecchio metodo `search` in modo sicuro,
            # senza bloccare il server.
            # È la soluzione più semplice e robusta se non hai un client DB async.
            try:
                loop = asyncio.get_running_loop()
                # Eseguiamo la funzione `self.search` (bloccante) in un thread separato
                results = await loop.run_in_executor(
                    None,      # Usa l'executor di default
                    self.search, # La funzione da eseguire
                    query,     # Il primo argomento di self.search
                    k          # Il secondo argomento di self.search
                )
                return results
            except Exception as e:
                print(f"Errore in RAG search_async: {e}")
                return []