@echo off
setlocal enabledelayedexpansion

echo 🚀 Deploying Vertigo AI to Google Cloud Platform
echo ================================================

REM Configuration
set PROJECT_ID=poetic-orb-474016-q7
set REGION=europe-west8
set SERVICE_ACCOUNT=vertigo-ai-deploy@%PROJECT_ID%.iam.gserviceaccount.com

echo 📍 Region: %REGION% (Milan, Italy)
echo 🏗️  Project: %PROJECT_ID%

REM Enable required APIs
echo 📋 Enabling required APIs...
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

REM Build and push images
echo 🔨 Building Docker images...

REM Backend
echo Building backend...
gcloud builds submit --tag gcr.io/%PROJECT_ID%/vertigo-ai-backend:latest .

REM HR Frontend
echo Building HR frontend...
gcloud builds submit --tag gcr.io/%PROJECT_ID%/vertigo-ai-hr:latest -f Dockerfile.hr .

REM Candidate Frontend
echo Building candidate frontend...
gcloud builds submit --tag gcr.io/%PROJECT_ID%/vertigo-ai-candidate:latest -f Dockerfile.candidate .

REM Deploy to Cloud Run
echo 🚀 Deploying to Cloud Run...

REM Deploy Backend
gcloud run deploy vertigo-ai-backend ^
    --image gcr.io/%PROJECT_ID%/vertigo-ai-backend:latest ^
    --platform managed ^
    --region %REGION% ^
    --allow-unauthenticated ^
    --memory 4Gi ^
    --cpu 2 ^
    --timeout 300 ^
    --max-instances 10 ^
    --min-instances 1 ^
    --set-env-vars MONGODB_URI="%MONGODB_URI%",OPENAI_API_KEY="%OPENAI_API_KEY%",JWT_SECRET="%JWT_SECRET%",PYTHON_ENV=production

REM Get backend URL
for /f "tokens=*" %%i in ('gcloud run services describe vertigo-ai-backend --region=%REGION% --format="value(status.url)"') do set BACKEND_URL=%%i

REM Deploy HR Frontend
gcloud run deploy vertigo-ai-hr ^
    --image gcr.io/%PROJECT_ID%/vertigo-ai-hr:latest ^
    --platform managed ^
    --region %REGION% ^
    --allow-unauthenticated ^
    --memory 1Gi ^
    --cpu 1 ^
    --max-instances 5 ^
    --min-instances 1 ^
    --set-env-vars BACKEND_URL="%BACKEND_URL%"

REM Deploy Candidate Frontend
gcloud run deploy vertigo-ai-candidate ^
    --image gcr.io/%PROJECT_ID%/vertigo-ai-candidate:latest ^
    --platform managed ^
    --region %REGION% ^
    --allow-unauthenticated ^
    --memory 1Gi ^
    --cpu 1 ^
    --max-instances 5 ^
    --min-instances 1 ^
    --set-env-vars BACKEND_URL="%BACKEND_URL%"

REM Get service URLs
for /f "tokens=*" %%i in ('gcloud run services describe vertigo-ai-hr --region=%REGION% --format="value(status.url)"') do set HR_URL=%%i
for /f "tokens=*" %%i in ('gcloud run services describe vertigo-ai-candidate --region=%REGION% --format="value(status.url)"') do set CANDIDATE_URL=%%i

echo ✅ Deployment completed successfully!
echo.
echo 🌐 Service URLs:
echo    Backend API: %BACKEND_URL%
echo    HR Interface: %HR_URL%
echo    Candidate Interface: %CANDIDATE_URL%
echo.
echo 📋 Next steps:
echo    1. Set up custom domains (optional)
echo    2. Configure SSL certificates
echo    3. Set up monitoring and logging
echo    4. Test the application

pause

