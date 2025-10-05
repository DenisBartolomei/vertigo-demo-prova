#!/bin/bash

set -e

echo "🔧 Setting up Google Cloud Platform for Vertigo AI"
echo "=================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud CLI is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "🔐 Please log in to Google Cloud:"
    gcloud auth login
fi

# Get project ID from user
read -p "Enter your Google Cloud Project ID: " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID cannot be empty"
    exit 1
fi

# Set the project
echo "📋 Setting project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "📋 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com

# Create service account for deployment
echo "👤 Creating service account..."
gcloud iam service-accounts create vertigo-ai-deploy \
    --display-name="Vertigo AI Deployment Service Account" \
    --description="Service account for deploying Vertigo AI to Cloud Run"

# Grant necessary permissions
echo "🔑 Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vertigo-ai-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vertigo-ai-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:vertigo-ai-deploy@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

# Create and download service account key
echo "🔐 Creating service account key..."
gcloud iam service-accounts keys create vertigo-ai-key.json \
    --iam-account=vertigo-ai-deploy@$PROJECT_ID.iam.gserviceaccount.com

# Update deploy.sh with project ID
echo "📝 Updating deployment script..."
sed -i "s/your-gcp-project-id/$PROJECT_ID/g" deploy.sh

echo "✅ Google Cloud Platform setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Update env.production with your actual values:"
echo "   - MONGODB_URI"
echo "   - OPENAI_API_KEY"
echo "   - JWT_SECRET"
echo ""
echo "2. Run: chmod +x deploy.sh"
echo "3. Run: ./deploy.sh"
echo ""
echo "🔐 Service account key saved as: vertigo-ai-key.json"
echo "⚠️  Keep this file secure and never commit it to version control!"

