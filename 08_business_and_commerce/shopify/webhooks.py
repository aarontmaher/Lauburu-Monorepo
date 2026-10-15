import os
import hmac
import hashlib
import base64
import httpx
from fastapi import FastAPI, Request, HTTPException, Header
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Lauburu Shopify Webhooks", 
    description="Handles checkout webhooks for Lauburu Elite tags and hardware fulfillment"
)

SHOPIFY_API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2024-01")
SHOPIFY_STORE_DOMAIN = os.environ.get("SHOPIFY_STORE_DOMAIN", "lauburu-grappling.myshopify.com")
SHOPIFY_ADMIN_ACCESS_TOKEN = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "")
SHOPIFY_WEBHOOK_SECRET = os.environ.get("SHOPIFY_WEBHOOK_SECRET", "")

async def verify_shopify_webhook(data: bytes, hmac_header: str):
    """Verify Shopify webhook HMAC signature."""
    if not SHOPIFY_WEBHOOK_SECRET:
        logger.warning("SHOPIFY_WEBHOOK_SECRET not set, skipping verification")
        return
        
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode("utf-8"),
        data,
        hashlib.sha256
    ).digest()
    computed_hmac = base64.b64encode(digest).decode("utf-8")
    if not hmac.compare_digest(computed_hmac, hmac_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC")

async def add_customer_tag(customer_id_gid: str, tag: str):
    """Append a tag to a customer via Admin GraphQL API."""
    mutation = """
    mutation tagsAdd($id: ID!, $tags: [String!]!) {
      tagsAdd(id: $id, tags: $tags) {
        node {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    logger.info(f"Adding tag '{tag}' to customer {customer_id_gid}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url, 
            json={"query": mutation, "variables": {"id": customer_id_gid, "tags": [tag]}}, 
            headers=headers
        )
        return resp.json()

async def trigger_fulfillment(order_id_gid: str):
    """Trigger zero-touch hardware fulfillment for an order via Admin GraphQL API."""
    query = """
    query GetFulfillmentOrders($orderId: ID!) {
      order(id: $orderId) {
        fulfillmentOrders(first: 10) {
          edges {
            node {
              id
              status
            }
          }
        }
      }
    }
    """
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ADMIN_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    logger.info(f"Fetching fulfillment orders for order {order_id_gid}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"query": query, "variables": {"orderId": order_id_gid}}, headers=headers)
        data = resp.json()
        
        fulfillment_orders = data.get("data", {}).get("order", {}).get("fulfillmentOrders", {}).get("edges", [])
        
        for fo in fulfillment_orders:
            fo_node = fo.get("node", {})
            if fo_node.get("status") == "OPEN":
                fo_id = fo_node.get("id")
                logger.info(f"Triggering fulfillment for fulfillment order {fo_id}")
                mutation = """
                mutation fulfillmentCreateV2($fulfillment: FulfillmentV2Input!) {
                  fulfillmentCreateV2(fulfillment: $fulfillment) {
                    fulfillment {
                      id
                      status
                    }
                    userErrors {
                      field
                      message
                    }
                  }
                }
                """
                variables = {
                    "fulfillment": {
                        "lineItemsByFulfillmentOrder": [
                            {"fulfillmentOrderId": fo_id}
                        ],
                        "notifyCustomer": True
                    }
                }
                await client.post(url, json={"query": mutation, "variables": variables}, headers=headers)
                logger.info(f"Successfully triggered fulfillment for {fo_id}")

@app.post("/webhooks/orders/paid")
@app.post("/webhooks/orders/create")
async def handle_order_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None)
):
    """
    Shopify webhook handler for order creation and payment.
    Scans for Movesense hardware bundle to grant Lauburu Elite access
    and automatically trigger zero-touch fulfillment.
    """
    body = await request.body()
    if x_shopify_hmac_sha256:
        await verify_shopify_webhook(body, x_shopify_hmac_sha256)
    
    order = await request.json()
    
    # Check if the order contains the Movesense hardware bundle
    line_items = order.get("line_items", [])
    has_movesense = any(
        "movesense" in (str(item.get("title", "")).lower() + str(item.get("sku", "")).lower()) 
        for item in line_items
    )
    
    customer = order.get("customer", {})
    customer_id = customer.get("admin_graphql_api_id")
    order_id = order.get("admin_graphql_api_id")
    
    logger.info(f"Received webhook for order {order_id}. Has Movesense: {has_movesense}")
    
    if has_movesense:
        # 1. Append lauburu_elite tag to customer
        if customer_id:
            logger.info("Movesense bundle detected. Appending lauburu_elite tag...")
            await add_customer_tag(customer_id, "lauburu_elite")
            
        # 2. Trigger zero-touch hardware fulfillment
        if order_id:
            logger.info("Triggering zero-touch hardware fulfillment...")
            await trigger_fulfillment(order_id)
            
    return {"status": "ok", "processed": has_movesense}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
