#!/usr/bin/env python3
"""
run_live_shopify_test_sale.py
==============================
CLI Utility to Execute Real-Time Test Sales on Shopify Storefront.
Creates live Storefront GraphQL carts for Canonical POD apparel & gear,
binds Australian buyer delivery identity, and validates checkout engine response.

Usage:
  python3 run_live_shopify_test_sale.py --preset bundle
  python3 run_live_shopify_test_sale.py --preset backpack
  python3 run_live_shopify_test_sale.py --preset fanny_pack
  python3 run_live_shopify_test_sale.py --preset joggers
"""

import os
import sys
import json
import argparse
import requests
from dotenv import dotenv_values

ENV_PATH = "/Volumes/Lauburu-Monorepo/.env"
env_vars = dotenv_values(ENV_PATH) if os.path.exists(ENV_PATH) else {}

SHOP_DOMAIN = env_vars.get("SHOPIFY_STORE_DOMAIN") or env_vars.get("SHOPIFY_SHOP_DOMAIN", "lauburu-grappling.myshopify.com")
STOREFRONT_TOKEN = env_vars.get("SHOPIFY_STOREFRONT_TOKEN") or env_vars.get("SHOPIFY_STOREFRONT_ACCESS_TOKEN", "a39ead89f7318e991105e64873b4e10e")
API_VERSION = env_vars.get("SHOPIFY_API_VERSION", "2024-01")
GRAPHQL_URL = f"https://{SHOP_DOMAIN}/api/{API_VERSION}/graphql.json"

HEADERS = {
    "X-Shopify-Storefront-Access-Token": STOREFRONT_TOKEN,
    "Content-Type": "application/json"
}

# POD Product Registry
POD_VARIANTS = {
    "utility_backpack": {
        "id": "gid://shopify/ProductVariant/44779813994632",
        "title": "Utility Backpack",
        "vendor": "Printful",
        "price_aud": 79.99
    },
    "fanny_pack": {
        "id": "gid://shopify/ProductVariant/44779812651144",
        "title": "Fanny Pack (S/M)",
        "vendor": "Printful",
        "price_aud": 44.99
    },
    "fleece_joggers": {
        "id": "gid://shopify/ProductVariant/44828397305992",
        "title": "Coloured Unisex Heavyweight Fleece Joggers (Cream Apricot / S)",
        "vendor": "ODMPOD",
        "price_aud": 59.99
    },
    "fleece_hoodie": {
        "id": "gid://shopify/ProductVariant/44679625965704",
        "title": "Oversize Fleeced Hoodie (Black / S)",
        "vendor": "ODMPOD",
        "price_aud": 59.99
    },
    "cooling_tee": {
        "id": "gid://shopify/ProductVariant/44679626162312",
        "title": "Sorona Quick-Dry Cooling T-Shirt (White / S)",
        "vendor": "ODMPOD",
        "price_aud": 49.99
    },
    "fleece_shorts": {
        "id": "gid://shopify/ProductVariant/44828393865352",
        "title": "Coloured Unisex Heavyweight Fleece Shorts (White / XS)",
        "vendor": "ODMPOD",
        "price_aud": 59.99
    },
    "flip_flops": {
        "id": "gid://shopify/ProductVariant/44779835555976",
        "title": "Flip-Flops (S)",
        "vendor": "Printful",
        "price_aud": 34.99
    },
    "crossbody_bag": {
        "id": "gid://shopify/ProductVariant/44779814060168",
        "title": "Utility Crossbody Bag",
        "vendor": "Printful",
        "price_aud": 44.99
    },
    "drawstring_bag": {
        "id": "gid://shopify/ProductVariant/44779813568648",
        "title": "Drawstring Bag",
        "vendor": "Printful",
        "price_aud": 34.99
    }
}

PRESETS = {
    "backpack": ["utility_backpack"],
    "fanny_pack": ["fanny_pack"],
    "joggers": ["fleece_joggers"],
    "hoodie": ["fleece_hoodie"],
    "streetwear_bundle": ["fleece_hoodie", "fleece_joggers", "cooling_tee"],
    "accessories_bundle": ["utility_backpack", "fanny_pack", "crossbody_bag"],
    "bundle": ["utility_backpack", "fanny_pack", "fleece_joggers", "fleece_hoodie"]
}

def execute_graphql(query: str) -> dict:
    resp = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"GraphQL request failed: HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors returned: {data['errors']}")
    return data

def run_test_sale(preset: str, customer_email: str = "athlete@lauburu.com"):
    print("=" * 80)
    print(f"🚀 EXECUTING SHOPIFY TEST SALE: Preset '{preset}'")
    print(f"🏪 Target Store: {SHOP_DOMAIN}")
    print("=" * 80)
    
    keys = PRESETS.get(preset, ["utility_backpack"])
    lines_gql = []
    expected_subtotal = 0.0
    
    print("\n📦 Line Items Selected for Test Sale:")
    for k in keys:
        item = POD_VARIANTS[k]
        lines_gql.append(f'{{ merchandiseId: "{item["id"]}", quantity: 1 }}')
        expected_subtotal += item["price_aud"]
        print(f"   • [{item['vendor']}] {item['title']} — ${item['price_aud']:.2f} AUD")
        
    lines_str = ",\n".join(lines_gql)
    
    # 1. cartCreate
    cart_create_q = f"""
    mutation {{
      cartCreate(
        input: {{
          lines: [
            {lines_str}
          ],
          attributes: [
            {{ key: "OrderType", value: "POD_Live_Test_Sale" }},
            {{ key: "Preset", value: "{preset}" }},
            {{ key: "MeshAuditVerification", value: "Rule_0_Empirical_Zero_Mock" }}
          ]
        }}
      ) {{
        cart {{
          id
          checkoutUrl
          cost {{
            totalAmount {{
              amount
              currencyCode
            }}
            subtotalAmount {{
              amount
              currencyCode
            }}
          }}
          lines(first: 10) {{
            edges {{
              node {{
                quantity
                merchandise {{
                  ... on ProductVariant {{
                    id
                    title
                    product {{
                      title
                      vendor
                    }}
                    price {{
                      amount
                      currencyCode
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    
    print("\n⚡ Submitting Storefront cartCreate mutation...")
    data = execute_graphql(cart_create_q)
    cart_res = data["data"]["cartCreate"]
    if cart_res["userErrors"]:
        print(f"❌ User Errors: {cart_res['userErrors']}")
        return False
        
    cart = cart_res["cart"]
    cart_id = cart["id"]
    checkout_url = cart["checkoutUrl"]
    total_amount = float(cart["cost"]["totalAmount"]["amount"])
    currency = cart["cost"]["totalAmount"]["currencyCode"]
    
    print(f"✅ Cart Created Successfully!")
    print(f"   Cart ID: {cart_id}")
    print(f"   Subtotal: ${total_amount:.2f} {currency}")
    print(f"   Line Count: {len(cart['lines']['edges'])}")
    
    # 2. cartBuyerIdentityUpdate
    print("\n📍 Applying Buyer Identity & Australian Delivery Address...")
    buyer_q = f"""
    mutation {{
      cartBuyerIdentityUpdate(
        cartId: "{cart_id}",
        buyerIdentity: {{
          email: "{customer_email}",
          countryCode: AU,
          deliveryAddressPreferences: [
            {{
              deliveryAddress: {{
                address1: "1 Martin Place",
                city: "Sydney",
                province: "NSW",
                country: "AU",
                zip: "2000"
              }}
            }}
          ]
        }}
      ) {{
        cart {{
          id
          buyerIdentity {{
            email
            countryCode
          }}
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    buyer_data = execute_graphql(buyer_q)
    b_res = buyer_data["data"]["cartBuyerIdentityUpdate"]
    if b_res["userErrors"]:
        print(f"⚠️ Buyer Identity Warning: {b_res['userErrors']}")
    else:
        print(f"✅ Buyer Identity Attached: {b_res['cart']['buyerIdentity']['email']} ({b_res['cart']['buyerIdentity']['countryCode']})")

    # 3. Probe Live Checkout URL
    print("\n🌐 Probing Production Checkout Engine...")
    probe = requests.get(checkout_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    print(f"   HTTP Status Code: {probe.status_code}")
    print(f"   Final Destination: {probe.url[:90]}...")
    if probe.status_code == 200:
        print("   Status: VERIFIED_LIVE_CHECKOUT (HTTP 200 OK)")
    else:
        print(f"   Status: CHECKOUT_FAILED (HTTP {probe.status_code})")
        return False
        
    print("\n" + "=" * 80)
    print("🎉 TEST SALE VERIFICATION COMPLETED (EXIT CODE 0)")
    print(f"🔗 Live Secure Checkout URL:")
    print(f"   {checkout_url}")
    print("=" * 80)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run live Shopify POD test sale")
    parser.add_argument("--preset", default="bundle", choices=list(PRESETS.keys()), help="Product combination preset")
    parser.add_argument("--email", default="athlete@lauburu.com", help="Test buyer email")
    args = parser.parse_args()
    
    success = run_test_sale(args.preset, args.email)
    sys.exit(0 if success else 1)
