@echo off
setlocal enabledelayedexpansion

echo 🔧 Setting up Google Cloud Platform for Vertigo AI
echo ==================================================

REM Check if gcloud is installed
gcloud version >nul 2>&1
if errorlevel 1 (
    echo ❌ Google Cloud CLI is not installed.
    echo Please install it from: https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

REM Check if user is logged in
gcloud auth list --filter=status:ACTIVE --format="value(account)" | findstr /r "." >nul
if errorlevel 1 (
    echo 🔐 Please log in to Google Cloud:
    gcloud auth login
)

REM Get project ID from user
set /p PROJECT_ID="Enter your Google Cloud Project ID: "
if "%PROJECT_ID%"=="" (
    echo ❌ Project ID cannot be empty
    pause
    exit /b 1
)

REM Set the project
echo 📋 Setting project to: %PROJECT_ID%
gcloud config set project %PROJECT_ID%

REM Enable required APIs
echo 📋 Enabling required APIs...
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com

REM Create service account for deployment
echo 👤 Creating service account...
gcloud iam service-accounts create vertigo-ai-deploy ^
    --display-name="Vertigo AI Deployment Service Account" ^
    --description="Service account for deploying Vertigo AI to Cloud Run"

REM Grant necessary permissions
echo 🔑 Granting permissions...
gcloud projects add-iam-policy-binding %PROJECT_ID% ^
    --member="serviceAccount:vertigo-ai-deploy@%PROJECT_ID%.iam.gserviceaccount.com" ^
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding %PROJECT_ID% ^
    --member="serviceAccount:vertigo-ai-deploy@%PROJECT_ID%.iam.gserviceaccount.com" ^
    --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding %PROJECT_ID% ^
    --member="serviceAccount:vertigo-ai-deploy@%PROJECT_ID%.iam.gserviceaccount.com" ^
    --role="roles/storage.admin"

REM Create and download service account key
echo 🔐 Creating service account key...
gcloud iam service-accounts keys create vertigo-ai-key.json ^
    --iam-account=vertigo-ai-deploy@%PROJECT_ID%.iam.gserviceaccount.com

REM Update deploy.bat with project ID
echo 📝 Updating deployment script...
powershell -Command "(Get-Content deploy.bat) -replace 'your-gcp-project-id', '%PROJECT_ID%' | Set-Content deploy.bat"

echo ✅ Google Cloud Platform setup completed!
echo.
echo 📋 Next steps:
echo 1. Update env.production with your actual values:
echo    - MONGODB_URI
echo    - OPENAI_API_KEY
echo    - JWT_SECRET
echo.
echo 2. Run: deploy.bat
echo.
echo 🔐 Service account key saved as: vertigo-ai-key.json
echo ⚠️  Keep this file secure and never commit it to version control!

pause

