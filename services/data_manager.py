import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Carica le variabili dal file .env se presente (per lo sviluppo locale)
load_dotenv()

MONGO_URI = None
# --- LOGICA A CASCATA ROBUSTA ---
# Prova con le variabili d'ambiente
MONGO_URI = os.getenv("MONGO_CONNECTION_STRING") or os.getenv("MONGODB_URI")
# --- FINE LOGICA ROBUSTA ---


DB_NAME = "vertigo_ai_db"
SESSIONS_COLLECTION_NAME = "user_sessions"

# Gestione della connessione al database
db = None
sessions_collection = None

if not MONGO_URI:
    print("ERRORE CRITICO: MONGODB_URI non trovata. Controlla le variabili d'ambiente.")
else:
    try:
        print(f"Tentativo di connessione a MongoDB Atlas...")
        print(f"URI: {MONGO_URI[:50]}...")
        client = MongoClient(MONGO_URI, server_api=ServerApi('1'), serverSelectionTimeoutMS=10000)
        db = client[DB_NAME]
        sessions_collection = db[SESSIONS_COLLECTION_NAME]
        print(f"Test ping al database...")
        client.admin.command('ping')
        print("Connessione a MongoDB Atlas stabilita con successo!")
    except Exception as e:
        print(f"ERRORE CRITICO: Impossibile connettersi a MongoDB Atlas.")
        print(f"Tipo errore: {type(e).__name__}")
        print(f"Dettagli: {str(e)}")
        print(f"URI usata: {MONGO_URI[:50]}...")

# --- Funzioni di Gestione Dati ---

def create_or_update_position(position_id: str, payload: dict, collection_name: str = "positions_data") -> bool:
    """
    Crea o aggiorna una posizione nella collection specificata.
    Usa upsert=True per inserire se non esiste ancora.
    """
    if db is None:
        print("DB non disponibile per create_or_update_position")
        return False
    try:
        collection = db[collection_name]
        payload = payload.copy()
        payload["_id"] = position_id
        collection.update_one({"_id": position_id}, {"$set": payload}, upsert=True)
        print(f"📄 Posizione upserted su MongoDB con ID: {position_id} in collection: {collection_name}")
        return True
    except Exception as e:
        print(f"Errore durante l'upsert della posizione {position_id}: {e}")
        return False

def create_new_session(session_id: str, position_id: str, candidate_name: str = "Candidato Anonimo") -> bool:
    if sessions_collection is None: return False
    try:
        new_document = {"_id": session_id, "position_id": position_id, "candidate_name": candidate_name, "status": "initialized", "stages": {}}
        sessions_collection.insert_one(new_document)
        print(f"📄 Sessione creata su MongoDB con ID: {session_id}")
        return True
    except Exception as e:
        print(f"Errore durante la creazione della sessione {session_id} su MongoDB: {e}")
        return False

def save_stage_output(session_id: str, stage_name: str, data_content: dict | str):
    if sessions_collection is None: return
    try:
        update_query = {"$set": {f"stages.{stage_name}": data_content}}
        sessions_collection.update_one({"_id": session_id}, update_query)
        print(f"💾 Dati per lo stage '{stage_name}' salvati per la sessione {session_id}.")
    except Exception as e:
        print(f"Errore durante il salvataggio dello stage '{stage_name}': {e}")

def get_session_data(session_id: str) -> dict | None:
    if sessions_collection is None: return None
    try:
        return sessions_collection.find_one({"_id": session_id})
    except Exception as e:
        print(f"Errore nel recupero della sessione {session_id}: {e}")
        return None

def save_pdf_report(pdf_bytes: bytes, session_id: str) -> str:
    output_dir = os.path.join("data", "sessions", session_id)
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, "Report_Feedback_Candidato.pdf")
    try:
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"📄 PDF salvato localmente in: {file_path}")
        return file_path
    except Exception as e:
        print(f"Errore nel salvataggio del PDF: {e}")
        return ""

def get_available_positions_from_db():
    if db is None: 
        print("DB non disponibile per get_available_positions_from_db")
        return []
    try:
        collection = db["positions_data"]
        positions = list(collection.find({}, {"_id": 1, "position_name": 1}))
        return sorted(positions, key=lambda p: p['position_name'])
    except Exception as e:
        print(f"Errore nel recupero delle posizioni dal DB: {e}")
        return []

def get_single_position_data_from_db(_position_id: str):
    if db is None: 
        print(f"DB non disponibile per get_single_position_data_from_db per ID: {_position_id}")
        return None
    try:
        collection = db["positions_data"]
        return collection.find_one({"_id": _position_id})
    except Exception as e:
        print(f"Errore nel recupero dei dati per la posizione {_position_id}: {e}")
        return None