---
title: "Shopify POD Sales Integration & Test Sales Audit"
tags: [shopify, pod, ecommerce, storefront_graphql, test_sales, printful, odmpod, tri_proof]
date: "2026-09-15"
audit_status: "VERIFIED_EXIT_CODE_0"
---

# 🛒 Shopify POD Sales Integration & Test Sales Audit

## 📋 Executive Summary
This document records the empirical verification and end-to-end test sales execution for the **Lauburu Canonical Print-On-Demand (POD) Apparel & Gear** collection on Shopify (`lauburu-grappling.myshopify.com` / `https://lauburugrappling.com`).

All 9 canonical POD products from **ODMPOD / Tapstitch** and **Printful** were audited against Shopify's production Storefront GraphQL API (`2024-01`). Real-time multi-item test sales were generated, verified, and probed against Shopify's live checkout gateway.

---

## 🌐 1. Live Catalog Audit & Variant Mapping

Every canonical POD product is active in the live store catalog, marked `availableForSale: true`, and priced in **AUD**:

| Product Name | POD Supplier | Live Handle | Variant ID | Live Price (AUD) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Utility Backpack** | Printful | `utility-backpack` | `gid://shopify/ProductVariant/44779813994632` | $79.99 AUD | In Stock |
| **Fanny Pack (S/M)** | Printful | `fanny-pack` | `gid://shopify/ProductVariant/44779812651144` | $44.99 AUD | In Stock |
| **Fleece Joggers** | ODMPOD | `coloured-unisex-heavyweight-fleece-joggers` | `gid://shopify/ProductVariant/44828397305992` | $59.99 AUD | In Stock |
| **Oversize Hoodie** | ODMPOD | `oversize-fleeced-hoodie-1` | `gid://shopify/ProductVariant/44679625965704` | $59.99 AUD | In Stock |
| **Cooling Tee** | ODMPOD | `sorona-quick-dry-cooling-t-shirt-1` | `gid://shopify/ProductVariant/44679626162312` | $49.99 AUD | In Stock |
| **Fleece Shorts** | ODMPOD | `coloured-unisex-heavyweight-fleece-loose-fit-shorts` | `gid://shopify/ProductVariant/44828393865352` | $59.99 AUD | In Stock |
| **Flip-Flops (S)** | Printful | `flip-flops` | `gid://shopify/ProductVariant/44779835555976` | $34.99 AUD | In Stock |
| **Crossbody Bag** | Printful | `utility-crossbody-bag` | `gid://shopify/ProductVariant/44779814060168` | $44.99 AUD | In Stock |
| **Drawstring Bag** | Printful | `drawstring-bag-1` | `gid://shopify/ProductVariant/44779813568648` | $34.99 AUD | In Stock |

---

## ⚡ 2. End-to-End Test Sales Execution

### A. Multi-Vendor POD Complete Kit Test Sale
- **Preset:** `bundle` (Utility Backpack + Fanny Pack + Fleece Joggers + Oversize Hoodie)
- **Vendors Represented:** Printful (2 items) + ODMPOD (2 items)
- **Subtotal Calculated:** **$244.96 AUD**
- **Cart ID:** `gid://shopify/Cart/hWNGpv4CoOPcgIHKejIZ8JNs?key=4e5673a7085e74da3d5f82f0573d01af`
- **Buyer Identity Attached:** `athlete@lauburu.com` (AU - 1 Martin Place, Sydney, NSW 2000)
- **Checkout Engine Probe:** `HTTP 200 OK` (Destination: `https://lauburugrappling.com/checkouts/cn/...`)

### B. Single-Item Joggers Test Sale
- **Preset:** `joggers` (ODMPOD Coloured Heavyweight Fleece Joggers)
- **Subtotal Calculated:** **$59.99 AUD**
- **Cart ID:** `gid://shopify/Cart/hWNGpv504xzWagQFdku9HoDE?key=def36294714007923fe34c36e0613ab0`
- **Buyer Identity Attached:** `athlete@lauburu.com` (AU - 1 Martin Place, Sydney, NSW 2000)
- **Checkout Engine Probe:** `HTTP 200 OK` (Destination: `https://lauburugrappling.com/checkouts/cn/...`)

---

## 🛡️ 3. Empirical Test Suite Results

Test Suite: `01_apps/commerce_and_business/tests/test_shopify_pod_sales_integration.py`
- `test_shop_metadata_and_currency`: PASSED (`AUD` active)
- `test_pod_catalog_variant_availability`: PASSED (9/9 items verified active & in-stock)
- `test_single_item_backpack_test_sale`: PASSED (Total $79.99 AUD verified)
- `test_multi_vendor_bundle_test_sale`: PASSED (Total $244.96 AUD verified across ODMPOD & Printful)
- `test_buyer_identity_update`: PASSED (Australian address Sydney 2000 attached)
- `test_pod_order_webhook_fulfillment_routing`: PASSED (Fulfillment segregated into ODMPOD & Printful queues + HMAC-SHA256 verified)

**Total Test Suite Result:** `6 passed in 8.16s` (Exit Code 0).

---

## 🔗 Related Knowledge Nodes
- [[Index]]
- [[CANONICAL_POD_APPAREL_SHOWCASE]]
- [[CANONICAL_PROJECT_AND_STORAGE_RULE]]
