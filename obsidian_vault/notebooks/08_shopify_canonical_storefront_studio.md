---
title: "08_shopify_canonical_storefront_studio"
tags: [lauburu, notebook, dual-vault, zero-mock]
---

# 📓 08_shopify_canonical_storefront_studio
*Synchronized Dual-Vault Mirror — [[Index]]*

# 🥋 Lauburu E-Commerce & Canonical Storefront Studio
### *Headless Shopify GraphQL, 12 Canonical Products, Tri-Vendor Routing & Anti-Fraud Sentinel*

<div style="background: #0b111c; border: 1px solid #38bdf8; border-radius: 10px; padding: 16px; margin: 10px 0;">
  <span style="color: #38bdf8; font-weight: bold;">🛍️ CANONICAL E-COMMERCE LAB</span> | 
  <span style="color: #10b981;">12 Active Products Live on lauburugrappling.com</span> | 
  <span style="color: #f59e0b;">Zero-Mock Verified</span>
</div>

```python
import matplotlib
matplotlib.use('Agg')
import sys, os, json
from pathlib import Path
import pandas as pd

# Add workspace to path
REPO_ROOT = Path('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo')
sys.path.insert(0, str(REPO_ROOT / '01_apps/user_facing_and_scaling'))

from shopify_storefront.presentation.catalog import CANONICAL_PRODUCTS
from shopify_storefront.presentation.pricing import MEMBERSHIP_TIERS, HARDWARE_BUNDLES
from shopify_storefront.graphql.client import ShopifyStorefrontClient

print(f'✅ Loaded {len(CANONICAL_PRODUCTS)} canonical products and {len(MEMBERSHIP_TIERS)} membership tiers.')
```

```python
catalog_data = [
    {
        'ID': p.product_id.split('/')[-1],
        'Title': p.title,
        'Category': p.category,
        'Vendor': p.vendor,
        'Price (USD)': f'${p.price_usd:.2f}',
        'Insignia Scale': p.symbol_scale,
        'Handle': p.handle,
        'In Stock': '✅' if p.in_stock else '❌'
    }
    for p in CANONICAL_PRODUCTS
]
df_catalog = pd.DataFrame(catalog_data)
df_catalog
```

```python
summary = df_catalog.groupby(['Category', 'Vendor']).size().reset_index(name='Product Count')
print('=== VENDOR & CATEGORY ALLOCATION MATRIX ===')
print(summary.to_string(index=False))

total_catalog_value = sum(p.price_usd for p in CANONICAL_PRODUCTS)
print(f'\nTotal Catalog Unit Basket Value: ${total_catalog_value:.2f} USD')
```

```python
client = ShopifyStorefrontClient()

# Build test basket with 1 Rashguard (Subliminator) + 1 Hoodie (ODMPOD) + 1 Backpack (Printful)
test_lines = [
    {'variant_id': CANONICAL_PRODUCTS[0].product_id.replace('Product', 'ProductVariant'), 'quantity': 1},
    {'variant_id': CANONICAL_PRODUCTS[3].product_id.replace('Product', 'ProductVariant'), 'quantity': 1},
    {'variant_id': CANONICAL_PRODUCTS[7].product_id.replace('Product', 'ProductVariant'), 'quantity': 1},
]
session = client.create_checkout(test_lines)
print(f'✅ Cart ID: {session.cart_id}')
print(f'✅ Live Checkout URL: {session.checkout_url}')
print(f'✅ Total Amount: ${session.total_amount_usd:.2f} USD')
```

```python
def audit_customer_message(subject: str, body: str) -> dict:
    """Audits inbound buyer messages for off-platform diversion scam patterns."""
    triggers = ['whatsapp', 'telegram', 'courier', 'payid screenshot', 'deposit required', 'insurance fee']
    found_triggers = [t for t in triggers if t in body.lower() or t in subject.lower()]
    is_threat = len(found_triggers) > 0
    return {
        'threat_detected': is_threat,
        'risk_score': 95 if is_threat else 0,
        'triggers': found_triggers,
        'action': 'ALERT_SOVEREIGN_HUMAN' if is_threat else 'ALLOW'
    }

# Test on the actual Gumtree Lachy message
test_msg = 'Best to message me on WhatsApp: 042-01334-82. I will come pick it up.'
audit = audit_customer_message('Lachy replied to your ad', test_msg)
print('=== INBOUND MESSAGE ANTI-FRAUD AUDIT ===')
print(json.dumps(audit, indent=2))
```
