# GPU VM Auto-Management

## Panoramica

Il sistema implementa un meccanismo di **auto-start/stop** per la VM GPU per risparmiare costi. La VM viene:
- **Avviata automaticamente** quando il backend ha bisogno del GPU service
- **Spenta automaticamente** dopo 2 minuti di inattività

## Come Funziona

1. **Auto-Start**: Quando il backend chiama il GPU service per generare embeddings, il sistema:
   - Verifica se la VM è in esecuzione
   - Se spenta, la avvia automaticamente
   - Recupera l'IP della VM e aggiorna l'URL del GPU service
   - Procede con la richiesta

2. **Auto-Stop**: Un thread in background controlla periodicamente (ogni 10 secondi):
   - Se la VM è inattiva da più di 2 minuti (120 secondi)
   - Se sì, spegne automaticamente la VM per risparmiare costi

## Configurazione

### Variabili d'Ambiente

- `ENABLE_VM_AUTO_MANAGEMENT`: Abilita/disabilita l'auto-management (default: `true`)
- `VM_IDLE_TIMEOUT`: Timeout di inattività in secondi prima dello spegnimento (default: `120` = 2 minuti)
- `GCP_PROJECT_ID`: ID del progetto Google Cloud
- `GCP_ZONE`: Zona della VM (es: `europe-west8-a`)
- `GPU_VM_NAME`: Nome della VM (default: `vertigo-gpu-service`)

### Permessi Necessari

Il service account usato da Cloud Run deve avere il ruolo:
```
roles/compute.instanceAdmin.v1
```

Per aggiungere i permessi:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
    --role="roles/compute.instanceAdmin.v1"
```

## Costi

Con l'auto-management abilitato:
- La VM viene addebitata **solo quando è in esecuzione**
- Se la VM è spenta, paghi solo per lo storage del disco (circa $0.17/mese per 50GB)
- La VM si avvia in ~30-60 secondi quando necessaria
- Si spegne automaticamente dopo 2 minuti di inattività

**Risparmio stimato**: Se la VM è in uso solo 2 ore al giorno, risparmi circa **$0.50/giorno** rispetto a tenerla accesa H24.

## Disabilitare Auto-Management

Per disabilitare l'auto-management e tenere la VM sempre accesa:

```bash
export ENABLE_VM_AUTO_MANAGEMENT=false
```

Oppure nel `deploy.sh`:
```bash
ENABLE_VM_AUTO_MANAGEMENT="false"
```

## Troubleshooting

### La VM non si avvia automaticamente

1. Verifica i permessi del service account:
   ```bash
   gcloud projects get-iam-policy PROJECT_ID \
       --flatten="bindings[].members" \
       --filter="bindings.members:SERVICE_ACCOUNT_EMAIL"
   ```

2. Verifica i log del backend per errori di avvio VM

3. Verifica che `gcloud` sia disponibile nel container Cloud Run (dovrebbe essere già incluso)

### La VM non si spegne automaticamente

1. Verifica che `ENABLE_VM_AUTO_MANAGEMENT=true`
2. Verifica i log per errori nel thread auto-stop
3. Verifica manualmente lo stato della VM:
   ```bash
   gcloud compute instances describe vertigo-gpu-service --zone=europe-west8-a
   ```

### L'IP della VM cambia dopo l'avvio

L'IP esterno della VM può cambiare se la VM viene spenta e riavviata. Il sistema aggiorna automaticamente l'URL quando la VM viene avviata.

