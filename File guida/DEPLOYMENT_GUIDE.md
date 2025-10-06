# 🚀 Vertigo AI - Google Cloud Deployment Guide

This guide will help you deploy Vertigo AI to Google Cloud Platform using Cloud Run in the Milan datacenter (europe-west8).

## 📋 Prerequisites

### 1. Install Required Tools

#### Google Cloud CLI
```bash
# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows
# Download from: https://cloud.google.com/sdk/docs/install
```

#### Docker
```bash
# macOS
brew install docker

# Linux
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Windows
# Download Docker Desktop from: https://www.docker.com/products/docker-desktop
```

#### Node.js (18+)
```bash
# macOS
brew install node

# Linux
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Windows
# Download from: https://nodejs.org/
```

### 2. MongoDB Atlas Setup
1. Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create a new cluster
3. Choose a region close to Italy (e.g., Europe - Milan)
4. Create a database user
5. Get your connection string

### 3. OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an API key
3. Make sure you have credits available

## 🏗️ Step-by-Step Deployment

### Step 1: Google Cloud Project Setup

```bash
# 1. Login to Google Cloud
gcloud auth login

# 2. Create a new project (or use existing)
gcloud projects create vertigo-ai-beta --name="Vertigo AI Beta"

# 3. Set the project
gcloud config set project vertigo-ai-beta

# 4. Enable billing (REQUIRED for Cloud Run)
# Go to: https://console.cloud.google.com/billing
```

### Step 2: Run the Setup Script

```bash
# Make the setup script executable
chmod +x setup-gcp.sh

# Run the setup script
./setup-gcp.sh
```

This script will:
- Enable required APIs
- Create a service account
- Set up permissions
- Generate authentication keys

### Step 3: Configure Environment Variables

Edit the `env.production` file with your actual values:

```bash
# Copy the template
cp env.production .env

# Edit with your values
nano .env
```

Required values:
- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `MONGODB_URI`: Your MongoDB Atlas connection string
- `OPENAI_API_KEY`: Your OpenAI API key
- `JWT_SECRET`: Generate a strong secret (use: `openssl rand -base64 32`)

### Step 4: Update Frontend Configuration

Update the API URLs in the frontend config files:

```bash
# Update HR frontend
nano frontend/hr/src/config.ts

# Update candidate frontend  
nano frontend/candidate/src/config.ts
```

Replace `XXXXX` with your actual project ID in the URLs.

### Step 5: Add Health Check to Backend

Add this to your `backend/app.py`:

```python
@app.get("/health")
def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
```

### Step 6: Deploy to Google Cloud

```bash
# Make the deployment script executable
chmod +x deploy.sh

# Set environment variables
export MONGODB_URI="your_mongodb_uri_here"
export OPENAI_API_KEY="your_openai_key_here"
export JWT_SECRET="your_jwt_secret_here"

# Run the deployment
./deploy.sh
```

The deployment script will:
1. Build Docker images for all services
2. Push images to Google Container Registry
3. Deploy to Cloud Run in Milan datacenter
4. Configure auto-scaling
5. Set up health checks
6. Provide you with the service URLs

### Step 7: Test the Deployment

After deployment, you'll get URLs like:
- Backend API: `https://vertigo-ai-backend-XXXXX-uc.a.run.app`
- HR Interface: `https://vertigo-ai-hr-XXXXX-uc.a.run.app`
- Candidate Interface: `https://vertigo-ai-candidate-XXXXX-uc.a.run.app`

Test each URL to ensure they're working:
1. Visit the HR interface URL
2. Try logging in
3. Test the candidate interface
4. Check the backend health endpoint: `https://your-backend-url/health`

## 🔧 Optional: Custom Domain Setup

### 1. Purchase a Domain
Buy a domain from any registrar (e.g., Namecheap, GoDaddy)

### 2. Configure DNS
Add these DNS records:
```
hr.yourdomain.com    CNAME    vertigo-ai-hr-XXXXX-uc.a.run.app
candidate.yourdomain.com    CNAME    vertigo-ai-candidate-XXXXX-uc.a.run.app
api.yourdomain.com    CNAME    vertigo-ai-backend-XXXXX-uc.a.run.app
```

### 3. Map Custom Domains
```bash
# Map HR domain
gcloud run domain-mappings create \
    --service vertigo-ai-hr \
    --domain hr.yourdomain.com \
    --region europe-west8

# Map candidate domain
gcloud run domain-mappings create \
    --service vertigo-ai-candidate \
    --domain candidate.yourdomain.com \
    --region europe-west8

# Map API domain
gcloud run domain-mappings create \
    --service vertigo-ai-backend \
    --domain api.yourdomain.com \
    --region europe-west8
```

## 📊 Monitoring and Logging

### View Logs
```bash
# Backend logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=vertigo-ai-backend" --limit=50

# HR frontend logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=vertigo-ai-hr" --limit=50
```

### Monitor Performance
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "Monitoring" > "Dashboards"
3. Create custom dashboards for your services

## 💰 Cost Management

### Estimated Monthly Costs
- **Cloud Run Backend**: $50-100 (depending on usage)
- **Cloud Run Frontend**: $20-40 (static content)
- **Cloud Build**: $10-20 (builds)
- **Total**: ~$80-160/month for beta testing

### Set Up Billing Alerts
1. Go to [Billing Console](https://console.cloud.google.com/billing)
2. Set up budget alerts
3. Configure spending limits

## 🔄 Updates and Maintenance

### Deploy Updates
```bash
# Make changes to your code
# Then run the deployment script again
./deploy.sh
```

### Scale Services
```bash
# Scale backend
gcloud run services update vertigo-ai-backend \
    --region=europe-west8 \
    --min-instances=2 \
    --max-instances=20

# Scale frontend
gcloud run services update vertigo-ai-hr \
    --region=europe-west8 \
    --min-instances=1 \
    --max-instances=10
```

## 🆘 Troubleshooting

### Common Issues

#### 1. Build Failures
```bash
# Check build logs
gcloud builds list
gcloud builds log [BUILD_ID]
```

#### 2. Service Not Starting
```bash
# Check service logs
gcloud run services describe vertigo-ai-backend --region=europe-west8
```

#### 3. Environment Variables
```bash
# Update environment variables
gcloud run services update vertigo-ai-backend \
    --region=europe-west8 \
    --set-env-vars NEW_VAR=value
```

#### 4. CORS Issues
Make sure your backend has proper CORS configuration for your frontend URLs.

### Getting Help
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Google Cloud Support](https://cloud.google.com/support)
- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)

## ✅ Deployment Checklist

- [ ] Google Cloud CLI installed and configured
- [ ] Docker installed and running
- [ ] Node.js 18+ installed
- [ ] MongoDB Atlas cluster created
- [ ] OpenAI API key obtained
- [ ] Google Cloud project created with billing enabled
- [ ] Setup script run successfully
- [ ] Environment variables configured
- [ ] Frontend config files updated
- [ ] Health check endpoint added to backend
- [ ] Deployment script run successfully
- [ ] All services tested and working
- [ ] Custom domains configured (optional)
- [ ] Monitoring set up
- [ ] Billing alerts configured

## 🎉 Congratulations!

Your Vertigo AI application is now deployed to Google Cloud Platform in the Milan datacenter! 

The application is ready for beta testing with:
- ✅ Auto-scaling infrastructure
- ✅ HTTPS endpoints
- ✅ Health monitoring
- ✅ Logging and debugging
- ✅ Cost-effective serverless architecture

Happy testing! 🚀

