# 🚀 Vertigo AI - Google Cloud Deployment

This repository contains all the necessary files to deploy Vertigo AI to Google Cloud Platform using Cloud Run in the Milan datacenter (europe-west8).

## 📁 Files Created

### Docker Configuration
- `Dockerfile` - Backend container configuration
- `Dockerfile.hr` - HR frontend container configuration  
- `Dockerfile.candidate` - Candidate frontend container configuration
- `nginx-hr.conf` - Nginx configuration for HR frontend
- `nginx-candidate.conf` - Nginx configuration for candidate frontend

### Deployment Scripts
- `deploy.sh` - Linux/Mac deployment script
- `deploy.bat` - Windows deployment script
- `setup-gcp.sh` - Linux/Mac GCP setup script
- `setup-gcp.bat` - Windows GCP setup script

### Configuration Files
- `env.production` - Environment variables template
- `cloud-run-backend.yaml` - Cloud Run service definition for backend
- `cloud-run-hr.yaml` - Cloud Run service definition for HR frontend
- `cloud-run-candidate.yaml` - Cloud Run service definition for candidate frontend
- `frontend/hr/src/config.ts` - HR frontend API configuration
- `frontend/candidate/src/config.ts` - Candidate frontend API configuration

### Documentation
- `DEPLOYMENT_GUIDE.md` - Complete step-by-step deployment guide
- `.gitignore` - Git ignore file for deployment

## 🎯 Quick Start

### For Windows Users:
1. Run `setup-gcp.bat` to set up Google Cloud
2. Edit `env.production` with your values
3. Run `deploy.bat` to deploy

### For Linux/Mac Users:
1. Run `./setup-gcp.sh` to set up Google Cloud
2. Edit `env.production` with your values  
3. Run `./deploy.sh` to deploy

## 📋 Prerequisites

- Google Cloud CLI installed
- Docker installed
- Node.js 18+ installed
- MongoDB Atlas cluster
- OpenAI API key
- Google Cloud project with billing enabled

## 🌐 Deployment Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HR Frontend   │    │ Candidate Front │    │   Backend API   │
│  (Cloud Run)    │    │   (Cloud Run)   │    │  (Cloud Run)    │
│                 │    │                 │    │                 │
│ Port: 8080      │    │ Port: 8080      │    │ Port: 8080      │
│ Memory: 1Gi     │    │ Memory: 1Gi     │    │ Memory: 4Gi     │
│ CPU: 1          │    │ CPU: 1          │    │ CPU: 2          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   MongoDB       │
                    │   Atlas         │
                    │   (Cloud)       │
                    └─────────────────┘
```

## 🔧 Environment Variables

Required environment variables:
- `MONGODB_URI` - MongoDB Atlas connection string
- `OPENAI_API_KEY` - OpenAI API key
- `JWT_SECRET` - JWT signing secret
- `GCP_PROJECT_ID` - Google Cloud project ID

## 💰 Estimated Costs

- **Backend**: $50-100/month
- **Frontend**: $20-40/month  
- **Build**: $10-20/month
- **Total**: ~$80-160/month

## 🚀 Features

- ✅ Auto-scaling infrastructure
- ✅ HTTPS endpoints
- ✅ Health monitoring
- ✅ Logging and debugging
- ✅ Cost-effective serverless
- ✅ Italian datacenter (Milan)
- ✅ Multi-tenant architecture
- ✅ JWT authentication
- ✅ MongoDB integration
- ✅ OpenAI integration

## 📞 Support

For deployment issues:
1. Check the `DEPLOYMENT_GUIDE.md` for detailed instructions
2. Review Google Cloud Run documentation
3. Check the logs using `gcloud logs read`

## 🎉 Ready to Deploy!

Your Vertigo AI application is ready for cloud deployment. Follow the `DEPLOYMENT_GUIDE.md` for complete instructions.

Happy deploying! 🚀

