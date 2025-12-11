# Azure OpenAI Batch Processing Setup

## Overview

Il sistema di batch processing è stato implementato per processare centinaia di CV automaticamente, utilizzando l'Azure OpenAI Batch API per ridurre i costi e migliorare l'efficienza. I batch vengono creati e inviati immediatamente quando l'HR carica i CV, e un sistema di monitoraggio controlla ogni 5 minuti se OpenAI ha completato l'elaborazione.

## Configurazione Variabili d'Ambiente

### Variabili Richieste per Batch Processing

Aggiungi queste variabili al tuo file `.env` o alle variabili d'ambiente del deployment:

```bash
# Batch Azure OpenAI Configuration
AZURE_OPENAI_BATCH_DEPLOYMENT_NAME="gpt-4.1-batch"
AZURE_OPENAI_BATCH_ENDPOINT="https://your-batch-resource.openai.azure.com/"
AZURE_OPENAI_BATCH_API_KEY="your-batch-api-key"

# Real-time Azure OpenAI Configuration (esistenti)
AZURE_OPENAI_ENDPOINT="https://your-realtime-resource.openai.azure.com/"
AZURE_OPENAI_API_KEY="your-realtime-api-key"
AZURE_OPENAI_API_VERSION="2024-10-21"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4-1-2025-04-14"
```

### Fallback Configuration

Se le variabili batch non sono configurate, il sistema userà automaticamente le variabili real-time come fallback:

```python
BATCH_ENDPOINT = os.getenv("AZURE_OPENAI_BATCH_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
BATCH_API_KEY = os.getenv("AZURE_OPENAI_BATCH_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
```

## Deployment su GCP Cloud Run

### Aggiorna cloud-run-backend.yaml

```yaml
env:
  - name: AZURE_OPENAI_BATCH_DEPLOYMENT_NAME
    value: "gpt-4.1-batch"
  - name: AZURE_OPENAI_BATCH_ENDPOINT
    value: "https://your-batch-resource.openai.azure.com/"
  - name: AZURE_OPENAI_BATCH_API_KEY
    value: "your-batch-api-key"
```

### Aggiorna deploy.sh

```bash
#!/bin/bash

# ... existing code ...

gcloud run deploy vertigo-ai-backend \
  --source . \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars="AZURE_OPENAI_BATCH_DEPLOYMENT_NAME=gpt-4.1-batch" \
  --set-env-vars="AZURE_OPENAI_BATCH_ENDPOINT=https://your-batch-resource.openai.azure.com/" \
  --set-env-vars="AZURE_OPENAI_BATCH_API_KEY=your-batch-api-key"
```

## Funzionalità Implementate

### 1. Upload Massivo CV
- **Endpoint**: `POST /api/batch/upload-cvs`
- **Funzionalità**: Carica centinaia di PDF CV simultaneamente
- **Parsing**: Estrazione automatica email via regex
- **Storage**: Sessioni create con `cv_analysis_status: "pending"`

### 2. Batch Processing Automatico
- **Creazione Batch**: Esecuzione immediata all'upload dei CV tramite `BatchService`
- **Service**: `BatchService` per gestione Azure OpenAI Batch API
- **Monitoring**: `BatchProcessor` controlla ogni 5 minuti se OpenAI ha completato l'elaborazione e recupera i risultati automaticamente

### 3. Frontend HR Aggiornato
- **Upload Massivo**: Priorità principale con drag & drop
- **Upload Singolo**: Opzione emergenza collassabile
- **Batch Grouping**: Raggruppamento sessioni per data batch
- **NEW Badges**: Indicatori per candidati non ancora processati

### 4. Frontend Candidato Aggiornato
- **2-Step Form**: Token → Nome/Cognome
- **Validazione**: Verifica token prima di richiedere dati personali
- **Storage**: Salvataggio nome/cognome in sessione

## Database Schema Updates

### Sessions Collection
```javascript
{
  "batch_id": "batch_20251022_190000",
  "batch_date": "2025-10-22", 
  "is_new_batch": true,
  "candidate_name": "",
  "candidate_surname": "",
  "candidate_email": "estratta@dal.cv"
}
```

### Batch Jobs Collection
```javascript
{
  "_id": "batch_xxx",
  "tenant_ids": ["tenant1", "tenant2"],
  "type": "cv_analysis",
  "status": "completed",
  "created_at": ISODate,
  "session_ids": ["sess1", "sess2"],
  "total_requests": 50,
  "request_counts": {"completed": 48, "failed": 2}
}
```

## API Endpoints

### Batch Management
- `POST /api/batch/upload-cvs` - Upload massivo CV
- `POST /api/batch/trigger-manual` - Trigger manuale batch
- `GET /api/batch/status/{batch_id}` - Status batch
- `POST /api/batch/retrieve/{batch_id}` - Recupera risultati
- `GET /api/batch/list` - Lista batch jobs

### Session Updates
- `GET /sessions` - Ora include batch grouping
- `PUT /sessions/{id}/token-sent` - Rimuove badge NEW
- `POST /interviews/{token}/start` - Accetta nome/cognome

## Multi-Tenant Safety

Il sistema batch è **globale** ma mantiene l'isolamento tenant:

1. **Custom ID**: `{tenant_id}:{session_id}` per identificazione
2. **Data Retrieval**: Recupero JD da collezioni tenant-specifiche
3. **Result Storage**: Salvataggio in collezioni tenant corrette
4. **Validation**: Verifica tenant_id prima di ogni operazione

## Monitoring e Debugging

### Logs Importanti
```bash
# Startup
✅ Batch processor avviato (controllo ogni 5 minuti)

# Batch Creation
🔄 Creazione batch per CV analysis...
📋 Trovati 25 CV da analizzare
☁️ Upload batch file ad Azure...
🚀 Creazione batch job...
✅ Batch creato: batch_xxx

# Processing
🔍 Controllo batch batch_xxx...
✅ Batch batch_xxx completato! Recupero risultati...
✅ Processati 23/25 risultati
```

### Health Check
```bash
curl https://your-backend.com/health
```

## Testing

### Test Upload Massivo
1. Vai su `/nuova-sessione` (HR frontend)
2. Seleziona posizione
3. Carica 5-10 PDF CV
4. Verifica creazione sessioni con `cv_analysis_status: "pending"`

### Test Batch Manuale
```bash
curl -X POST https://your-backend.com/api/batch/trigger-manual \
  -H "Authorization: Bearer YOUR_JWT"
```

### Test Frontend Candidato
1. Vai su `/` (candidate frontend)
2. Inserisci token valido
3. Verifica step 2 con nome/cognome
4. Controlla salvataggio in database

## Troubleshooting

### Batch Non Si Avvia
- Verifica variabili d'ambiente batch
- Controlla logs startup per errori batch processor
- Verifica connessione Azure OpenAI

### CV Non Processati
- Controlla `cv_analysis_status: "pending"` in database
- Verifica batch job status via API
- Controlla logs batch processor

### Frontend Issues
- Verifica import CSS in `NuovaSessione.tsx`
- Controlla console browser per errori
- Verifica endpoint API responses

## Performance

- **Batch Size**: Fino a 100 CV per batch
- **Processing Time**: 24h window Azure OpenAI
- **Monitoring**: Controllo ogni 5 minuti
- **Storage**: MongoDB con indici su `batch_date`, `cv_analysis_status`

## Sicurezza

- **Tenant Isolation**: Verificata a ogni step
- **Token Validation**: JWT per tutti endpoint batch
- **File Validation**: Solo PDF accettati
- **Rate Limiting**: Gestito da Azure OpenAI Batch API

