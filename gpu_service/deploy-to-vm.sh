#!/bin/bash

# Script per deploy del GPU service su VM Compute Engine
# Usage: ./deploy-to-vm.sh <vm-name> <zone>

set -e

VM_NAME="${1:-vertigo-gpu-service}"
ZONE="${2:-europe-west8-a}"
PROJECT_ID="${GCP_PROJECT_ID:-poetic-orb-474016-q7}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/vertigo-gpu-service:latest"

echo "🚀 Deploy GPU Service su VM"
echo "==========================="
echo "VM: ${VM_NAME}"
echo "Zone: ${ZONE}"
echo "Image: ${IMAGE_NAME}"
echo ""

# Build e push dell'immagine Docker
echo "📦 Build e push immagine Docker..."
gcloud builds submit --tag ${IMAGE_NAME} --config cloudbuild-gpu-service.yaml .

# Deploy su VM via SSH
echo "📤 Deploy su VM..."
gcloud compute ssh ${VM_NAME} --zone=${ZONE} --command="
    # Pull immagine
    docker pull ${IMAGE_NAME}
    
    # Stop container esistente
    docker stop vertigo-gpu-service || true
    docker rm vertigo-gpu-service || true
    
    # Run nuovo container
    docker run -d \
        --name vertigo-gpu-service \
        --restart=always \
        --gpus all \
        -p 8080:8080 \
        -e GPU_SERVICE_HOST=0.0.0.0 \
        -e GPU_SERVICE_PORT=8080 \
        ${IMAGE_NAME}
    
    # Verifica che il container sia running
    docker ps | grep vertigo-gpu-service
"

echo "✅ Deploy completato!"
echo ""
echo "Per verificare lo stato:"
echo "  gcloud compute ssh ${VM_NAME} --zone=${ZONE} --command='docker logs vertigo-gpu-service'"

