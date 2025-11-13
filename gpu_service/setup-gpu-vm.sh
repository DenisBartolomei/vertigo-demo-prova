#!/bin/bash

# Script per setup Compute Engine VM con GPU T4
# Questo script crea una VM con GPU, installa i driver NVIDIA e deploya il GPU service

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-poetic-orb-474016-q7}"
REGION="${GCP_REGION:-europe-west8}"
ZONE="${GCP_ZONE:-europe-west8-a}"
VM_NAME="${GPU_VM_NAME:-vertigo-gpu-service}"
MACHINE_TYPE="${GPU_MACHINE_TYPE:-n1-standard-4}"
GPU_TYPE="${GPU_TYPE:-nvidia-tesla-t4}"
GPU_COUNT="${GPU_COUNT:-1}"
IMAGE_FAMILY="${IMAGE_FAMILY:-ubuntu-2204-lts}"
IMAGE_PROJECT="${IMAGE_PROJECT:-ubuntu-os-cloud}"
BOOT_DISK_SIZE="${BOOT_DISK_SIZE:-50GB}"
SERVICE_PORT="${SERVICE_PORT:-8080}"

echo "🚀 Setup GPU VM per Vertigo AI"
echo "================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Zone: ${ZONE}"
echo "VM Name: ${VM_NAME}"
echo "Machine Type: ${MACHINE_TYPE}"
echo "GPU: ${GPU_TYPE} x${GPU_COUNT}"
echo ""

# Verifica che gcloud sia configurato
if ! command -v gcloud &> /dev/null; then
    echo "❌ Errore: gcloud CLI non trovato. Installa Google Cloud SDK."
    exit 1
fi

# Imposta il progetto
echo "📋 Impostazione progetto GCP..."
gcloud config set project ${PROJECT_ID}

# Abilita API necessarie
echo "📋 Abilitazione API necessarie..."
gcloud services enable compute.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Crea la VM con GPU
echo "🖥️  Creazione VM con GPU..."
gcloud compute instances create ${VM_NAME} \
    --zone=${ZONE} \
    --machine-type=${MACHINE_TYPE} \
    --accelerator=type=${GPU_TYPE},count=${GPU_COUNT} \
    --maintenance-policy=TERMINATE \
    --image-family=${IMAGE_FAMILY} \
    --image-project=${IMAGE_PROJECT} \
    --boot-disk-size=${BOOT_DISK_SIZE} \
    --boot-disk-type=pd-standard \
    --metadata=install-nvidia-driver=True \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --tags=gpu-service,http-server \
    --project=${PROJECT_ID}

echo "✅ VM creata con successo"

# Attendi che la VM sia pronta
echo "⏳ Attesa che la VM sia pronta (30 secondi)..."
sleep 30

# Crea firewall rule per permettere traffico HTTP sulla porta del servizio
echo "🔥 Configurazione firewall..."
gcloud compute firewall-rules create allow-gpu-service \
    --allow tcp:${SERVICE_PORT} \
    --source-ranges 0.0.0.0/0 \
    --target-tags gpu-service \
    --description "Allow traffic to GPU service" \
    --project=${PROJECT_ID} || echo "Firewall rule già esistente"

# Ottieni IP esterno della VM
EXTERNAL_IP=$(gcloud compute instances describe ${VM_NAME} --zone=${ZONE} --format="get(networkInterfaces[0].accessConfigs[0].natIP)")
echo "✅ VM IP esterno: ${EXTERNAL_IP}"

echo ""
echo "📝 Prossimi passi:"
echo "1. SSH nella VM: gcloud compute ssh ${VM_NAME} --zone=${ZONE}"
echo "2. Installa Docker e NVIDIA Container Toolkit"
echo "3. Deploy del GPU service usando il Dockerfile"
echo ""
echo "Per deploy automatico, esegui:"
echo "  ./gpu_service/deploy-to-vm.sh ${VM_NAME} ${ZONE}"

