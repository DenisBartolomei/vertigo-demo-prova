import faiss
import numpy as np
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
        # Usa SentenceTransformer locale (CPU) - più veloce per poche query singole
        self.model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        # --- MODIFICA CHIAVE: Carichiamo i dati da MongoDB ---
        self.courses_data = self._load_courses_from_mongo()
        # Il resto del processo di indicizzazione rimane invariato
        self.index, self.course_map = self._build_index()
        print("RAG Service inizializzato con successo.")

    def _load_courses_from_mongo(self) -> list:
        """
        Carica i dati dei corsi dalla collection dedicata su MongoDB Atlas.
        Ottimizzato: carica solo i campi necessari.
        """
        try:
            # Controlla se la connessione al DB è disponibile
            if db is None:
                raise ConnectionError("Connessione al database MongoDB non disponibile.")
            
            # Seleziona la collection
            collection = db[COURSES_COLLECTION_NAME]
            print(f"  - Recupero corsi dalla collection '{COURSES_COLLECTION_NAME}' su MongoDB...")
            
            # Ottimizzazione: carica solo i campi necessari (meno dati = più veloce)
            # IMPORTANTE: Include "URL" per il match post-generazione degli URL
            courses = list(collection.find(
                {},
                {"Course Name": 1, "Description": 1, "embedding": 1, "_id": 1, "URL": 1}
            ))
            
            if not courses:
                print(f"  - ATTENZIONE: Nessun corso trovato nella collection '{COURSES_COLLECTION_NAME}'.")
            else:
                print(f"  - Recuperati {len(courses)} corsi dal database.")
            return courses
        except Exception as e:
            print(f"ERRORE CRITICO: Impossibile caricare il database dei corsi da MongoDB. {e}")
            return []

    def _build_index(self):
        """
        Costruisce l'indice FAISS con InnerProduct (più veloce per cosine similarity).
        Ottimizzato: batch encoding e normalizzazione per InnerProduct.
        """
        if not self.courses_data:
            return None, None
        
        # Verifica se gli embeddings sono già stati pre-calcolati
        embeddings_list = []
        courses_with_embeddings = []
        
        for course in self.courses_data:
            if 'embedding' in course and course['embedding']:
                embeddings_list.append(course['embedding'])
                courses_with_embeddings.append(course)
        
        if embeddings_list:
            # ✅ CASO OTTIMIZZATO: Carica embeddings pre-calcolati
            print(f"  ✅ Caricamento {len(embeddings_list)} embeddings pre-calcolati da MongoDB...")
            embeddings = np.array(embeddings_list, dtype=np.float32)
        else:
            # ⚠️ FALLBACK: Calcola embeddings al volo (primo avvio)
            print(f"  ⚠️  Embeddings non trovati. Calcolo al volo...")
            print(f"  💡 TIP: Esegui 'python scripts/precompute_course_embeddings.py' per ottimizzare!")
            descriptions = [f"{course.get('Course Name', '')}. {course.get('Description', '')}" 
                           for course in self.courses_data]
            print(f"  - Creazione embeddings per {len(descriptions)} corsi (batch encoding)...")
            # Batch encoding per velocità
            embeddings = self.model.encode(
                descriptions, 
                convert_to_tensor=False,
                batch_size=32,  # Processa 32 corsi alla volta
                show_progress_bar=False
            )
            courses_with_embeddings = self.courses_data
        
        # Normalizza embeddings per usare InnerProduct (più veloce di L2 per cosine similarity)
        faiss.normalize_L2(embeddings)
        
        # Usa IndexFlatIP invece di IndexFlatL2 (più veloce per cosine similarity)
        d = embeddings.shape[1]
        index = faiss.IndexFlatIP(d)  # Inner Product = cosine similarity con embeddings normalizzati
        index.add(embeddings)
        course_map = {i: course for i, course in enumerate(courses_with_embeddings)}
        
        print(f"  - Indice FAISS (InnerProduct) costruito con {len(courses_with_embeddings)} corsi.")
        return index, course_map

    def search(self, query: str, k: int = 5) -> list:
        """
        Ricerca ottimizzata con InnerProduct (cosine similarity).
        k ridotto a 5 per default (era 8).
        """
        if not self.index:
            print("Ricerca saltata: l'indice FAISS non è stato inizializzato.")
            return []
        
        # Encoding singola query
        query_embedding = self.model.encode([query], convert_to_tensor=False)
        # Normalizza per InnerProduct
        faiss.normalize_L2(query_embedding)
        
        # Ricerca FAISS (velocissima con InnerProduct)
        distances, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        # Filtra risultati con similarity > 0.3 (soglia minima cosine similarity)
        # FIX: Tronca descrizioni a 150 caratteri per ridurre token nel prompt finale
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and distances[0][i] > 0.3:  # Soglia cosine similarity
                course = self.course_map[idx].copy()  # Copia per non modificare l'originale
                # Tronca Description a 150 caratteri se presente
                if 'Description' in course and course['Description']:
                    desc = str(course['Description'])
                    if len(desc) > 150:
                        course['Description'] = desc[:147] + "..."
                results.append(course)
        
        return results

    def search_batch(self, queries: list[str], k: int = 5) -> list[list]:
        """
        NUOVO: Batch search per multiple query in una volta.
        Molto più veloce di chiamare search() multiple volte.
        """
        if not self.index:
            return [[] for _ in queries]
        
        if not queries:
            return []
        
        # Batch encoding (molto più veloce di encoding singole)
        query_embeddings = self.model.encode(
            queries, 
            convert_to_tensor=False,
            batch_size=len(queries),
            show_progress_bar=False
        )
        
        # Normalizza per InnerProduct
        faiss.normalize_L2(query_embeddings)
        
        # Batch search FAISS
        distances, indices = self.index.search(query_embeddings.astype(np.float32), k)
        
        # Processa risultati
        # FIX: Tronca descrizioni a 150 caratteri per ridurre token nel prompt finale
        all_results = []
        for query_idx in range(len(queries)):
            results = []
            for i, idx in enumerate(indices[query_idx]):
                if idx >= 0 and distances[query_idx][i] > 0.3:  # Soglia cosine similarity
                    course = self.course_map[idx].copy()  # Copia per non modificare l'originale
                    # Tronca Description a 150 caratteri se presente
                    if 'Description' in course and course['Description']:
                        desc = str(course['Description'])
                        if len(desc) > 150:
                            course['Description'] = desc[:147] + "..."
                    results.append(course)
            all_results.append(results)
        
        return all_results

    async def search_async(self, query: str, k: int = 5) -> list:
        """
        Versione ASINCRONA della ricerca ottimizzata.
        Delega il lavoro pesante (sincrono) a un altro thread per non bloccare FastAPI.
        """
        try:
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(None, self.search, query, k)
            return results
        except Exception as e:
            print(f"Errore in RAG search_async: {e}")
            return []

    async def search_batch_async(self, queries: list[str], k: int = 5) -> list[list]:
        """
        NUOVO: Batch search async per multiple query.
        Molto più veloce di chiamare search_async() multiple volte.
        """
        try:
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(None, self.search_batch, queries, k)
            return results
        except Exception as e:
            print(f"Errore in RAG search_batch_async: {e}")
            return [[] for _ in queries]


# --- Singleton Pattern ---
# Mantiene una singola istanza di RAGService per tutta l'applicazione
# per evitare di ricaricare i dati e ricostruire l'indice FAISS più volte

_rag_service_instance: RAGService | None = None

def get_rag_service() -> RAGService:
    """
    Restituisce l'istanza singleton di RAGService.
    Se non esiste ancora, la crea. Altrimenti restituisce quella esistente.
    
    Returns:
        RAGService: L'istanza singleton del servizio RAG
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance