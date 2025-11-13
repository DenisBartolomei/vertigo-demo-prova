#!/bin/bash

set -e

# Configuration
PROJECT_ID="poetic-orb-474016-q7"
REGION="europe-west8"  # Milan, Italy (per Cloud Run)
GPU_ZONE="europe-west1-b"  # Zone per GPU VM (Belgium - supporta N1+T4)
SERVICE_ACCOUNT="vertigo-ai-deploy@${PROJECT_ID}.iam.gserviceaccount.com"
GPU_VM_NAME="vertigo-gpu-service"

echo "🚀 Deploying Vertigo AI to Google Cloud Platform"
echo "📍 Region: ${REGION} (Milan, Italy)"
echo "🏗️  Project: ${PROJECT_ID}"

# Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable compute.googleapis.com

# 0. Setup GPU Service (se necessario)
echo "🖥️  Verifica e setup GPU Service..."
export GCP_PROJECT_ID="${PROJECT_ID}"
export GCP_REGION="${REGION}"
export GCP_ZONE="${GPU_ZONE}"

# Verifica se la VM GPU esiste già
if ! gcloud compute instances describe ${GPU_VM_NAME} --zone=${GPU_ZONE} --project=${PROJECT_ID} &>/dev/null; then
    echo "   GPU VM non trovata, creazione in corso..."
    if [ -f "./gpu_service/setup-gpu-vm.sh" ]; then
        chmod +x ./gpu_service/setup-gpu-vm.sh
        ./gpu_service/setup-gpu-vm.sh
    else
        echo "   ⚠️  Script setup-gpu-vm.sh non trovato, creazione VM manuale..."
        gcloud compute instances create ${GPU_VM_NAME} \
            --zone=${GPU_ZONE} \
            --machine-type=n1-standard-2 \
            --accelerator=type=nvidia-tesla-t4,count=1 \
            --maintenance-policy=TERMINATE \
            --image-family=ubuntu-2204-lts \
            --image-project=ubuntu-os-cloud \
            --boot-disk-size=50GB \
            --boot-disk-type=pd-standard \
            --metadata=install-nvidia-driver=True \
            --scopes=https://www.googleapis.com/auth/cloud-platform \
            --tags=gpu-service,http-server \
            --project=${PROJECT_ID}
        
        echo "   ⏳ Attesa che la VM sia pronta (60 secondi)..."
        sleep 60
        
        # Crea firewall rule
        gcloud compute firewall-rules create allow-gpu-service \
            --allow tcp:8080 \
            --source-ranges 0.0.0.0/0 \
            --target-tags gpu-service \
            --description "Allow traffic to GPU service" \
            --project=${PROJECT_ID} 2>/dev/null || echo "   Firewall rule già esistente"
    fi
else
    echo "   ✓ GPU VM già esistente"
fi

# Build e Deploy GPU Service sulla VM
echo "🚀 Building and Deploying GPU Service sulla VM..."
if [ -f "./gpu_service/deploy-to-vm.sh" ]; then
    chmod +x ./gpu_service/deploy-to-vm.sh
    # deploy-to-vm.sh fa già il build e il deploy
    ./gpu_service/deploy-to-vm.sh ${GPU_VM_NAME} ${GPU_ZONE}
else
    echo "   ⚠️  Script deploy-to-vm.sh non trovato, build e deploy manuale..."
    # Build immagine
    if [ -f "./cloudbuild-gpu-service.yaml" ]; then
        gcloud builds submit --config cloudbuild-gpu-service.yaml --project=${PROJECT_ID} .
    else
        gcloud builds submit --tag gcr.io/${PROJECT_ID}/vertigo-gpu-service:latest --project=${PROJECT_ID} ./gpu_service
    fi
    # Deploy sulla VM
    IMAGE_NAME="gcr.io/${PROJECT_ID}/vertigo-gpu-service:latest"
    gcloud compute ssh ${GPU_VM_NAME} --zone=${GPU_ZONE} --project=${PROJECT_ID} --command="
        docker pull ${IMAGE_NAME} || true
        docker stop vertigo-gpu-service || true
        docker rm vertigo-gpu-service || true
        docker run -d \
            --name vertigo-gpu-service \
            --restart=always \
            --gpus all \
            -p 8080:8080 \
            -e GPU_SERVICE_HOST=0.0.0.0 \
            -e GPU_SERVICE_PORT=8080 \
            ${IMAGE_NAME}
    "
fi

# Recupera IP della VM e imposta GPU_SERVICE_URL
echo "🔍 Recupero IP della GPU VM..."
GPU_VM_IP=$(gcloud compute instances describe ${GPU_VM_NAME} --zone=${GPU_ZONE} --project=${PROJECT_ID} --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null || echo "")
if [ -z "${GPU_VM_IP}" ]; then
    echo "   ⚠️  Impossibile recuperare IP della VM, uso variabile d'ambiente GPU_SERVICE_URL se disponibile"
    GPU_SERVICE_URL="${GPU_SERVICE_URL:-}"
else
    GPU_SERVICE_URL="http://${GPU_VM_IP}:8080"
    echo "   ✓ GPU Service URL: ${GPU_SERVICE_URL}"
fi

# 1. Build and Deploy Backend
echo "🔨 Building and Deploying backend..."
gcloud builds submit --tag gcr.io/${PROJECT_ID}/vertigo-ai-backend:latest .
gcloud run deploy vertigo-ai-backend \
    --image gcr.io/${PROJECT_ID}/vertigo-ai-backend:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 6Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars MONGODB_URI="${MONGODB_URI}",AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT}",AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY}",AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION}",AZURE_OPENAI_DEPLOYMENT_NAME="${AZURE_OPENAI_DEPLOYMENT_NAME}",JWT_SECRET="${JWT_SECRET}",PYTHON_ENV=production,AZURE_OPENAI_BATCH_ENDPOINT="${AZURE_OPENAI_BATCH_ENDPOINT}",AZURE_OPENAI_BATCH_API_KEY="${AZURE_OPENAI_BATCH_API_KEY}",AZURE_OPENAI_BATCH_API_VERSION="${AZURE_OPENAI_BATCH_API_VERSION}",AZURE_OPENAI_BATCH_DEPLOYMENT_NAME="${AZURE_OPENAI_BATCH_DEPLOYMENT_NAME}",GPU_SERVICE_URL="${GPU_SERVICE_URL}",ENABLE_GPU_SERVICE="${ENABLE_GPU_SERVICE:-true}",GPU_SERVICE_TIMEOUT="${GPU_SERVICE_TIMEOUT:-30}",GPU_SERVICE_RETRY_ATTEMPTS="${GPU_SERVICE_RETRY_ATTEMPTS:-3}",ENABLE_VM_AUTO_MANAGEMENT="${ENABLE_VM_AUTO_MANAGEMENT:-true}",VM_IDLE_TIMEOUT="${VM_IDLE_TIMEOUT:-120}",GCP_PROJECT_ID="${PROJECT_ID}",GCP_ZONE="${GPU_ZONE}",GPU_VM_NAME="${GPU_VM_NAME}"

# 2. Get backend URL
BACKEND_URL=$(gcloud run services describe vertigo-ai-backend --region=${REGION} --format="value(status.url)")
echo "✓ Backend deployed at: ${BACKEND_URL}"

# 3. Configura permessi per auto-management VM GPU
echo "🔐 Configurazione permessi per auto-management VM GPU..."
# Ottieni il service account usato da Cloud Run (default o custom)
SERVICE_ACCOUNT_EMAIL=$(gcloud run services describe vertigo-ai-backend --region=${REGION} --format="value(spec.template.spec.serviceAccountName)" 2>/dev/null || echo "")

# Se non c'è un service account custom, usa quello default di Compute Engine
if [ -z "${SERVICE_ACCOUNT_EMAIL}" ] || [ "${SERVICE_ACCOUNT_EMAIL}" = "default" ]; then
    PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
    SERVICE_ACCOUNT_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    echo "   Usando service account default: ${SERVICE_ACCOUNT_EMAIL}"
else
    echo "   Usando service account custom: ${SERVICE_ACCOUNT_EMAIL}"
fi

# Assegna il ruolo per gestire le VM
echo "   Assegnazione ruolo roles/compute.instanceAdmin.v1..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/compute.instanceAdmin.v1" \
    2>/dev/null && echo "   ✓ Permessi configurati con successo" || echo "   ⚠️  Permessi già configurati o errore (verifica manualmente se necessario)"

# 4. Build HR Frontend
echo "Building HR frontend..."
gcloud builds submit --config cloudbuild-hr.yaml --substitutions=_BACKEND_URL=${BACKEND_URL} .

# 5. Build Candidate Frontend
echo "Building candidate frontend..."
gcloud builds submit --config cloudbuild-candidate.yaml --substitutions=_BACKEND_URL=${BACKEND_URL} .

# 6. Deploy HR Frontend
gcloud run deploy vertigo-ai-hr \
    --image gcr.io/${PROJECT_ID}/vertigo-ai-hr:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 5 \
    --min-instances 0 \
    --set-env-vars BACKEND_URL="${BACKEND_URL}"

# 7. Deploy Candidate Frontend
gcloud run deploy vertigo-ai-candidate \
    --image gcr.io/${PROJECT_ID}/vertigo-ai-candidate:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 5 \
    --min-instances 0 \
    --set-env-vars BACKEND_URL="${BACKEND_URL}"

# Get service URLs
HR_URL=$(gcloud run services describe vertigo-ai-hr --region=${REGION} --format="value(status.url)")
CANDIDATE_URL=$(gcloud run services describe vertigo-ai-candidate --region=${REGION} --format="value(status.url)")

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Service URLs:"
echo "   Backend API: ${BACKEND_URL}"
echo "   HR Interface: ${HR_URL}"
echo "   Candidate Interface: ${CANDIDATE_URL}"
if [ -n "${GPU_SERVICE_URL}" ]; then
    echo "   GPU Service: ${GPU_SERVICE_URL}"
fi
echo ""
echo "📋 Next steps:"
echo "   1. Set up custom domains (optional)"
echo "   2. Configure SSL certificates"
echo "   3. Set up monitoring and logging"
echo "   4. Test the application"
