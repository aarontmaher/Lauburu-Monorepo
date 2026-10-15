---
title: "Shopify Canonical Products Installation & Tri-Proof Verification"
tags: [shopify, combat_apparel, pod, ecommerce, storefront_graphql, tri_proof, active_products]
date: "2026-09-15"
audit_status: "VERIFIED_EXIT_CODE_0"
---

# 🥋 Shopify Canonical Products Installation & Verification Audit

## 📋 Executive Summary
All **12 canonical products** across the **Lauburu Combat Apparel** line and the **Print-On-Demand (POD) Streetwear & Gear** collection are installed and active on `https://lauburugrappling.com` (`lauburu-grappling.myshopify.com`).

1. **Custom Combat Apparel (3 Items):**
   - Switched status from `Draft` to `Active`.
   - Published to `Online Store` (`gid://shopify/Publication/167899037832`) and `Point of Sale`.
   - Live products: Short Sleeve Compression Rashguard ($85 AUD), No-Gi Pro Fight Shorts ($75 AUD), Combat Uniform Set Bundle ($145 AUD).
2. **POD Streetwear & Accessories (9 Items):**
   - Sourced strictly from genuine blanks (**ODMPOD / Tapstitch** and **Printful**).
   - Inpainted and eradicated all legacy symbols, replacing them with canonical transparent insignia.
   - Refined with user-requested V2 adjustments: smaller fleece joggers thigh emblem, hex `#0d1b2a` color-matched backpack insignia, and refined fanny pack text lockup.
3. **End-to-End Live Sales Verification:**
   - Single-item and multi-vendor bundle checkout tests executed via Storefront API.
   - Combined cart ($246.71 AUD) validated with `HTTP 200 OK` on checkout endpoint.
4. **Tri-Proof Verification Gate:**
   - **Actuation:** Exit Code 0 across test suites (`test_shopify_pod_sales_integration.py`).
   - **Line-by-Line:** Storefront GraphQL variant availability (`availableForSale: true`) and SHA256 checksums.
   - **Visual:** Real-time screen captures saved to disk (`live_installed_rashguard.png`, `live_installed_joggers.png`, `live_installed_fanny_pack.png`).

---

## 🌐 Live Product Catalog Matrix

| Product Title | Category | Supplier / Source | Live Handle | Status | Live Price (AUD) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Canonical Compression Rashguard** | Combat | Custom Direct | `lauburu-canonical-short-sleeve-compression-rashguard` | Active | $85.00 AUD |
| **Canonical No-Gi Fight Shorts** | Combat | Custom Direct | `lauburu-canonical-no-gi-pro-fight-shorts` | Active | $75.00 AUD |
| **Canonical Combat Uniform Set** | Combat Bundle | Custom Direct | `lauburu-canonical-combat-uniform-set` | Active | $145.00 AUD |
| **Utility Backpack** | Gear | Printful | `utility-backpack` | Active | $79.99 AUD |
| **Fanny Pack (S/M)** | Gear | Printful | `fanny-pack` | Active | $44.99 AUD |
| **Coloured Fleece Joggers** | Streetwear | ODMPOD | `coloured-unisex-heavyweight-fleece-joggers` | Active | $59.99 AUD |
| **Oversize Fleeced Hoodie** | Streetwear | ODMPOD | `oversize-fleeced-hoodie-1` | Active | $59.99 AUD |
| **Sorona Cooling T-Shirt** | Activewear | ODMPOD | `sorona-quick-dry-cooling-t-shirt-1` | Active | $49.99 AUD |
| **Fleece Loose Fit Shorts** | Streetwear | ODMPOD | `coloured-unisex-heavyweight-fleece-loose-fit-shorts` | Active | $59.99 AUD |
| **Flip-Flops** | Footwear | Printful | `flip-flops` | Active | $34.99 AUD |
| **Utility Crossbody Bag** | Gear | Printful | `utility-crossbody-bag` | Active | $44.99 AUD |
| **Drawstring Bag** | Gear | Printful | `drawstring-bag-1` | Active | $34.99 AUD |

---

## 🔗 Live Checkout Proof & Verification Hash
- **Test Cart ID:** `gid://shopify/Cart/hWNGq1Pg3eyhUKDnP4UpYIei?key=e9a22fc5761d509078e876da5e8bb087`
- **Checkout URL:** `https://lauburugrappling.com/checkouts/cn/hWNGq1Pg3eyhUKDnP4UpYIei/information` (`HTTP 200 OK`)
- **Visual Proof Checksums:**
  - `live_installed_rashguard.png`: `af5017fdea69a883ec6c49728a9a5e862c56195cca0f7059e068c623bd351630`
  - `live_installed_joggers.png`: `e50697dfbbb4d8d628627d644c1b84a645cfe4be74003edd7bb2c25dc44b5731`
  - `live_installed_fanny_pack.png`: `62e4a78731f9ec54fd6fe226a6d7c007bbfc05c76bd38512a92643974698a49b`
