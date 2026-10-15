#!/usr/bin/env python3
"""
Sync Lauburu Rashguards & Shorts to Shopify via Admin API
Requires: SHOPIFY_ADMIN_TOKEN in environment
"""

import os
import requests
import json
import base64
from pathlib import Path

SHOPIFY_STORE = "lauburu-grappling.myshopify.com"
ADMIN_TOKEN = os.getenv("SHOPIFY_ADMIN_TOKEN", "YOUR_ADMIN_TOKEN_HERE")
ASSETS_DIR = Path(__file__).parent / "assets" / "bjj_ranks"

def encode_image(filepath):
    """Returns base64 encoded string of an image file."""
    if not filepath.exists():
        print(f"⚠️ Warning: Image not found at {filepath}")
        return None
    with open(filepath, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def create_rashguard_product():
    if ADMIN_TOKEN == "YOUR_ADMIN_TOKEN_HERE" or ADMIN_TOKEN == "shpat_lens_automated_retrieval_success":
        print("❌ Error: SHOPIFY_ADMIN_TOKEN is invalid or stubbed. Please run automate_shopify_admin_token.py locally.")
        return

    headers = {
        "X-Shopify-Access-Token": ADMIN_TOKEN,
        "Content-Type": "application/json"
    }
    
    url = f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json"
    
    print("📸 Preparing Image Payloads...")
    
    # Preload base64 images for the main gallery
    images = []
    
    gallery_files = [
        "lauburu_master_5belt_collection.png",
        "lauburu_rashguard_white_belt.png",
        "lauburu_rashguard_blue_belt.png",
        "lauburu_rashguard_purple_belt.png",
        "lauburu_rashguard_brown_belt.png",
        "lauburu_rashguard_black_belt.png"
    ]
    
    for filename in gallery_files:
        b64 = encode_image(ASSETS_DIR / filename)
        if b64:
            images.append({"attachment": b64, "filename": filename})
    
    # Define the product with all belt rank variants
    product_data = {
        "product": {
            "title": "Lauburu Belt-Ranked Competition Rashguard",
            "body_html": "<strong>Premium IBJJF Approved Rashguard</strong><br>Represent your rank with the official Lauburu No-Gi gear.",
            "vendor": "Lauburu Athletics",
            "product_type": "Rashguard",
            "status": "draft", # Set to draft until fulfillment is attached
            "images": images,
            "options": [
                {
                    "name": "Belt Rank",
                    "values": ["White", "Blue", "Purple", "Brown", "Black"]
                },
                {
                    "name": "Size",
                    "values": ["S", "M", "L", "XL", "XXL"]
                }
            ],
            "variants": []
        }
    }

    # Generate variants dynamically (5 ranks x 5 sizes)
    ranks = ["White", "Blue", "Purple", "Brown", "Black"]
    sizes = ["S", "M", "L", "XL", "XXL"]
    
    for rank in ranks:
        for size in sizes:
            product_data["product"]["variants"].append({
                "option1": rank,
                "option2": size,
                "price": "49.99",
                "sku": f"LAU-RASH-{rank[:3].upper()}-{size}"
            })

    print("🚀 Pushing Rashguard configurations + Images to Shopify Admin API...")
    response = requests.post(url, headers=headers, json=product_data)
    
    if response.status_code == 201:
        print("✅ Success! Product & Images created in DRAFT state.")
        product_id = response.json()["product"]["id"]
        print(f"🔗 Product ID: {product_id}")
    else:
        print(f"❌ Failed to create product: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    create_rashguard_product()
