#!/bin/bash
PROJECT_ID="gen-lang-client-0982729216"
REGION="us-west1"
ZONE="us-west1-b"

echo "🚀 Beginning deployment of Lauburu Mesh Free Tier Infrastructure to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# 1. Cloud Storage Backup Bucket (5GB Free)
BUCKET_NAME="lauburu-mesh-backup-$PROJECT_ID"
echo "📦 Creating Free Tier Cloud Storage Bucket: $BUCKET_NAME"
gcloud storage buckets create gs://$BUCKET_NAME \
    --project=$PROJECT_ID \
    --location=$REGION \
    --default-storage-class=STANDARD \
    --uniform-bucket-level-access || echo "Bucket already exists."

# 2. Compute Engine Sentinel Node (e2-micro Free Tier)
INSTANCE_NAME="lauburu-sentinel-node"
echo "🛡️ Creating Free Tier Compute Engine Sentinel (e2-micro)..."
# Enable Compute API just in case
gcloud services enable compute.googleapis.com
gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --machine-type=e2-micro \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-standard \
    --tags=http-server,https-server \
    --metadata=startup-script="#!/bin/bash
echo 'Sentinel Node Initializing...'
apt-get update
curl -fsSL https://tailscale.com/install.sh | sh
echo 'Sentinel Node Ready. Run tailscale up to join mesh.'
" || echo "Instance already exists."

echo "✅ Free Tier Infrastructure Deployment Completed."

# 3. Cloud Run API Aggregator Proxies (Free Tier Routing)
# ---------------------------------------------------
# Google AI Studio (1500 RPD)
echo "🌐 Deploying Free Tier Cloud Run Proxies..."
gcloud services enable run.googleapis.com

gcloud run deploy ai-proxy-gemini \
    --image gcr.io/$PROJECT_ID/ai-proxy-generic \
    --set-env-vars="API_KEY=${GEMINI_API_KEY},RATE_LIMIT_RPD=1500" \
    --region us-central1 --allow-unauthenticated

# NVIDIA NIM (2000 RPD)
gcloud run deploy ai-proxy-nvidia \
    --image gcr.io/$PROJECT_ID/ai-proxy-generic \
    --set-env-vars="API_KEY=${NVIDIA_NIM_KEY},RATE_LIMIT_RPD=2000" \
    --region us-central1 --allow-unauthenticated

# Grok (xAI) (1000 RPD)
gcloud run deploy ai-proxy-grok \
    --image gcr.io/$PROJECT_ID/ai-proxy-generic \
    --set-env-vars="API_KEY=${XAI_API_KEY},BASE_URL=https://api.x.ai/v1,RATE_LIMIT_RPD=1000" \
    --region us-central1 --allow-unauthenticated

# Cloudflare Workers AI (800 RPD)
gcloud run deploy ai-proxy-cloudflare \
    --image gcr.io/$PROJECT_ID/ai-proxy-generic \
    --set-env-vars="API_KEY=${CLOUDFLARE_API_TOKEN},BASE_URL=https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/ai/run,RATE_LIMIT_RPD=800" \
    --region us-central1 --allow-unauthenticated

# AI21 Jules / Jamba (Large Context)
gcloud run deploy ai-proxy-ai21 \
    --image gcr.io/$PROJECT_ID/ai-proxy-generic \
    --set-env-vars="API_KEY=${AI21_API_KEY},BASE_URL=https://api.ai21.com/studio/v1,RATE_LIMIT_RPD=1000" \
    --region us-central1 --allow-unauthenticated
