# recruitment_suite/config/settings.py (VERSIONE FINALE)

import os
from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURAZIONE GENERALE ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# --- CONFIGURAZIONE MODELLI ---
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
LLM_MODEL = "gpt-4.1-2025-04-14"

# --- CONFIGURAZIONE WORKFLOW ---
AFFINITY_THRESHOLD = 0.6
BATCH_SIZE = 50
MIN_EXPERIENCE_MONTHS_NORM = 6
TOP_N_MATCHES_NORM = 3
ID_COLUMN = 'profile_id'
TARGET_JOB_TITLE = "ESG Consultant"

# ==============================================================================
# --- NOMI COLLEZIONI MONGODB (SOSTITUISCONO I VECCHI PERCORSI DEI FILE) ---
# ==============================================================================
MONGO_COLLECTION_BENCHMARK_CANDIDATES = "suite_benchmark_candidates"
MONGO_COLLECTION_OCCUPATIONS_RAW = "suite_occupations_unfiltered"
MONGO_COLLECTION_OCCUPATIONS_FILTERED = "suite_occupations_filtered"
MONGO_COLLECTION_ESCO_HIERARCHY = "suite_esco_hierarchy"
MONGO_COLLECTION_EMBEDDINGS = "suite_embeddings"
# ==============================================================================

# --- FILE DI INPUT DINAMICI (Questi rimangono percorsi locali) ---
OFFER_FILE = os.path.join(DATA_DIR, "input", "offer.txt")
CV_PDF_FILE = os.path.join(DATA_DIR, "cv_da_analizzare", "MatteoRosellini_CV.pdf")

# --- FILE DI OUTPUT (Questi rimangono percorsi locali) ---
OUTPUT_LLM_FILE = os.path.join(OUTPUT_DIR, "llm_analysis_results.json")
OUTPUT_JSON_FILE_NORM = os.path.join(OUTPUT_DIR, "risultato_normalizzazione_cv.json")

# --- PROMPTS E KEYWORDS (invariati) ---
NON_JOB_KEYWORDS_NORM = ['studente', 'studentessa', 'tirocinio', 'tirocinante', 'stage', 'stagista', 'formazione', 'workshop', 'tesi', 'laureando', 'corso', 'volontario', 'student', 'intern', 'internship', 'trainee', 'training', 'thesis', 'course', 'volunteer']
LLM_PROMPT_CV_EXTRACTION_NORM = """
Sei un assistente HR esperto nell'analisi di CV. Il tuo compito è estrarre le esperienze lavorative dal testo fornito e restituirle in un formato JSON strutturato.

Segui queste regole in modo RIGOROSO:
1.  **FORMATO DATE**: Le date `start_date` e `end_date` DEVONO essere nel formato numerico **YYYY-MM-DD**.
    - Se il giorno non è specificato nel CV, usa sempre '01'.
    - Esempio: "Settembre 2022" deve diventare "2022-09-01". "Dal 2020" deve diventare "2020-01-01".
2.  **DATA FINE**: Se l'esperienza è ancora in corso (es. "Presente", "Oggi", "in corso"), il valore di `end_date` deve essere la stringa esatta "present".
3.  **CONTENUTO**: Estrai SOLO le esperienze lavorative. IGNORA completamente istruzione, certificazioni, volontariato, hobby e qualsiasi dato personale (nome, telefono, email, indirizzo).
4.  **OUTPUT**: Restituisci ESCLUSIVAMENTE l'oggetto JSON, senza alcun testo o spiegazione prima o dopo.

Ecco la struttura JSON che DEVI seguire:
{
  "current_position": "Titolo della posizione lavorativa più recente",
  "experience": [
    {
      "title": "Titolo della posizione",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD o present",
      "description": "Descrizione sintetica delle responsabilità e dei risultati."
    }
  ]
}
""" #"Sei un assistente HR che analizza CV. Estrai le informazioni in formato JSON strutturato. IGNORA E OMETTI QUALSIASI DATO PERSONALE. Estrai SOLO le esperienze lavorative.\nRestituisci ESCLUSIVAMENTE un oggetto JSON:\n{\n  \"current_position\": \"Titolo della posizione lavorativa più recente\",\n  \"experience\": [\n    {\n      \"title\": \"Titolo\", \"start_date\": \"Mese Anno\", \"end_date\": \"Mese Anno o Presente\",\n      \"description\": \"Descrizione delle responsabilità.\"\n    }\n  ]\n}"
LLM_PROMPT_ENRICHMENT_IT_NORM = "Sei un esperto di semantica HR. Il tuo obiettivo è arricchire una descrizione di lavoro per il matching semantico con il database ESCO.\n\nINPUT:\nTitolo: {title}\nDescrizione: {description}\n\nISTRUZIONI:\nGenera un singolo paragrafo fluente IN ITALIANO (massimo 100 parole) che descriva il ruolo. Se il ruolo è ambiguo, restituisci: {{ \"enriched_text\": null }}\n\nRestituisci ESCLUSIVAMENTE un oggetto JSON con questa struttura:\n{{\n  \"enriched_text\": \"Testo arricchito in italiano...\"\n}}"