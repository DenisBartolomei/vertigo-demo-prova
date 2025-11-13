# GPU Embedding Service

Microservizio dedicato per generare embeddings usando GPU, migliorando drasticamente le prestazioni del feedback report e del benchmark di mercato.

## Architettura

Il GPU service è un servizio FastAPI separato che gira su Compute Engine con GPU T4. Il backend Cloud Run chiama questo servizio via HTTP API per generare embeddings invece di usare CPU locale.

```
Cloud Run Backend → HTTP API → GPU Service (Compute Engine) → CUDA → Embedding Models
```

## Setup

### 1. Creare VM con GPU

```bash
chmod +x gpu_service/setup-gpu-vm.sh
./gpu_service/setup-gpu-vm.sh
```

Questo script:
- Crea una VM Compute Engine con GPU T4
- Configura firewall rules
- Installa driver NVIDIA automaticamente

### 2. Build e Deploy

```bash
# Build immagine Docker
gcloud builds submit --tag gcr.io/PROJECT_ID/vertigo-gpu-service:latest --config cloudbuild-gpu-service.yaml .

# Deploy su VM
chmod +x gpu_service/deploy-to-vm.sh
./gpu_service/deploy-to-vm.sh vertigo-gpu-service europe-west8-a
```

### 3. Configurare Backend

Aggiungi queste environment variables al backend Cloud Run:

```bash
GPU_SERVICE_URL=http://EXTERNAL_IP:8080
ENABLE_GPU_SERVICE=true
GPU_SERVICE_TIMEOUT=30
GPU_SERVICE_RETRY_ATTEMPTS=3
```

## Environment Variables

### GPU Service (VM)

- `GPU_SERVICE_HOST`: Host binding (default: `0.0.0.0`)
- `GPU_SERVICE_PORT`: Porta del servizio (default: `8080`)
- `GPU_SERVICE_DEFAULT_MODEL`: Modello di default (default: `all-MiniLM-L6-v2`)
- `GPU_SERVICE_MAX_BATCH_SIZE`: Max batch size (default: `32`)
- `GPU_SERVICE_LOG_LEVEL`: Log level (default: `INFO`)

### Backend (Cloud Run)

- `GPU_SERVICE_URL`: URL completo del GPU service (es: `http://10.0.0.5:8080`)
- `ENABLE_GPU_SERVICE`: Abilita/disabilita GPU service (default: `true`)
- `GPU_SERVICE_TIMEOUT`: Timeout richieste in secondi (default: `30`)
- `GPU_SERVICE_RETRY_ATTEMPTS`: Numero di retry (default: `3`)
- `GPU_SERVICE_RETRY_DELAY`: Delay tra retry in secondi (default: `1.0`)
- `GPU_EMBEDDING_CACHE_SIZE`: Dimensione cache locale embeddings (default: `1000`)

## API Endpoints

### `GET /health`

Health check del servizio.

**Response:**
```json
{
  "status": "healthy",
  "gpu_available": true,
  "models_loaded": ["all-MiniLM-L6-v2"],
  "gpu_memory": {
    "device_name": "Tesla T4",
    "memory_allocated_mb": 1024.5,
    "memory_total_mb": 16384.0
  }
}
```

### `POST /embed`

Genera embedding per un singolo testo.

**Request:**
```json
{
  "text": "Testo da convertire in embedding",
  "model_name": "all-MiniLM-L6-v2",
  "normalize": true
}
```

**Response:**
```json
{
  "embedding": [0.123, 0.456, ...],
  "model_name": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

### `POST /embed-batch`

Genera embeddings per un batch di testi.

**Request:**
```json
{
  "texts": ["Testo 1", "Testo 2", "Testo 3"],
  "model_name": "all-MiniLM-L6-v2",
  "normalize": true,
  "batch_size": 16
}
```

**Response:**
```json
{
  "embeddings": [[0.123, ...], [0.456, ...], [0.789, ...]],
  "model_name": "all-MiniLM-L6-v2",
  "dimension": 384,
  "count": 3
}
```

## Fallback CPU

Se il GPU service non è disponibile, il client library usa automaticamente CPU locale come fallback. Questo garantisce che l'applicazione continui a funzionare anche se la GPU non è disponibile.

## Modelli Supportati

- `all-MiniLM-L6-v2`: Modello leggero per RAG corsi (384 dimensioni)
- `paraphrase-multilingual-mpnet-base-v2`: Modello multilingue per benchmark (768 dimensioni)

## Costi Stimati

- **T4 Preemptible**: ~$0.11/ora = ~$80/mese (se usato 24/7)
- **T4 Standard**: ~$0.35/ora = ~$250/mese
- **Storage**: ~$10/mese
- **Network**: ~$5/mese
- **Totale (preemptible)**: ~$95-100/mese

## Performance

Con GPU T4, le operazioni di embedding sono **5-10x più veloci** rispetto a CPU:
- Embedding singolo: ~10ms (vs ~50ms CPU)
- Batch 16 embeddings: ~50ms (vs ~500ms CPU)

Questo riduce il tempo di generazione feedback report da **10 minuti a ~1-2 minuti**.

## Troubleshooting

### GPU non disponibile

Verifica che i driver NVIDIA siano installati:
```bash
gcloud compute ssh vertigo-gpu-service --zone=europe-west8-a
nvidia-smi
```

### Service non raggiungibile

Verifica firewall rules:
```bash
gcloud compute firewall-rules list | grep gpu-service
```

Verifica che il container sia running:
```bash
gcloud compute ssh vertigo-gpu-service --zone=europe-west8-a --command="docker ps"
```

### Logs

```bash
gcloud compute ssh vertigo-gpu-service --zone=europe-west8-a --command="docker logs vertigo-gpu-service"
```

