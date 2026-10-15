import os
from fastapi import FastAPI, Request, HTTPException
from google.cloud import pubsub_v1

app = FastAPI()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "lauburu-project")
TOPIC_ID = os.environ.get("PUBSUB_TOPIC_ID", "google-chat-inbound")

# Initialize Pub/Sub publisher client
# In Cloud Run, it automatically uses the default service account credentials.
try:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
except Exception as e:
    print(f"Warning: Failed to init PubSub client. Is this running locally without credentials? Error: {e}")
    publisher = None

@app.post("/google-chat/webhook")
async def google_chat_webhook(request: Request):
    """Catches Google Chat webhooks and publishes them to GCP Pub/Sub."""
    payload = await request.body()
    
    if not publisher:
        raise HTTPException(status_code=500, detail="PubSub publisher not initialized")
    
    try:
        # Publish to Pub/Sub
        future = publisher.publish(topic_path, payload)
        message_id = future.result()
        print(f"📦 Published message to Pub/Sub. Message ID: {message_id}")
        return {"status": "published", "message_id": message_id}
    except Exception as e:
        print(f"❌ Failed to publish to Pub/Sub: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish message to Pub/Sub")

@app.get("/")
def health_check():
    return {"status": "Cloud Run Pub/Sub Proxy Active"}
