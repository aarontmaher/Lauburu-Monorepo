# 🥋 Shopify Canonical Symbol & Storefront Development Walkthrough

This document establishes empirical Tri-Proof verification for the full rollout of the **updated canonical symbol** across the live Shopify storefront ([`lauburugrappling.com`](https://lauburugrappling.com)). Every occurrence of the legacy 4-bladed swirl has been systematically purged from theme code, sections, and public catalog, while preserving legacy products in draft status for Sovereign sign-off.

---

## 🏛️ 1. Verification Matrix & Tri-Proof Results

| Subsystem / Surface | Legacy Asset / State | Canonical Replacement | Empirical Proof Type | Verification Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Header Brand Logo** | `image_19c6e28d...jpg` (old swirl) | `lauburu_canonical_brand_logo.png` | Visual Screen + JSON Match (0 old) | **VERIFIED** |
| **Footer Brand Logo** | `image_19c6e28d...jpg` (old swirl) | `lauburu_canonical_brand_logo.png` | Visual Screen + JSON Match (0 old) | **VERIFIED** |
| **Favicon** | `F1ACF8ED-0C70...png` (old swirl) | `lauburu_canonical_story_card.png` | Line-by-line in `settings_data.json` | **VERIFIED** |
| **Category 1 (Rashguards)** | `collection_1.png` (old swirl rashguard) | `lauburu_canonical_cat_rashguard.png` | Visual Screen + `index.json` | **VERIFIED** |
| **Category 2 (Streetwear)** | `hoodies.png` (old swirl hoodie) | `lauburu_canonical_cat_hoodie.png` | Visual Screen + `index.json` | **VERIFIED** |
| **Category 3 (Accessories)**| `Untitled_design_38.png` (text only) | `lauburu_canonical_cat_accessories.png`| Visual Screen + `index.json` | **VERIFIED** |
| **Our Story Brand Card** | `Untitled_design_20.png` (giant swirl) | `lauburu_canonical_story_card.png` | Visual Screen + `index.json` | **VERIFIED** |
| **Featured All Products** | 21 mixed Subliminator products | 12 Canonical POD & Combat items | Live GraphQL + Swiper Carousel | **VERIFIED** |
| **Public Collections** | 10 collections with legacy items | 10 collections strictly canonical | REST / JSON API Audit (10/10) | **VERIFIED** |
| **20 Legacy Products** | Active on storefront | Set to `Draft` (Hidden from buyers) | Bulk status API + Admin Audit | **VERIFIED** |
| **Storefront POD Sales** | Untested live checkout | 6/6 Multi-Vendor Pytest suite | Actuation (`Exit Code 0`) | **VERIFIED** |

---

## 📸 2. Visual Proof Gallery (Live Storefront Verification)

````carousel
![Canonical Header Brand Logo & Category Cards](/Users/aaron/.gemini/antigravity/brain/e18a2c0a-90e7-4879-b8d8-aab71a489465/live_storefront_header_canonical.png)
<!-- slide -->
![Accessories Category & Canonical Our Story Card](/Users/aaron/.gemini/antigravity/brain/e18a2c0a-90e7-4879-b8d8-aab71a489465/live_storefront_categories_and_story.png)
<!-- slide -->
![All Products Carousel: Canonical Flip-Flops & Utility Crossbody Bag](/Users/aaron/.gemini/antigravity/brain/e18a2c0a-90e7-4879-b8d8-aab71a489465/live_storefront_carousel_accessories.png)
<!-- slide -->
![All Products Carousel: Canonical Oversize Hoodie & Heavyweight Fleece Joggers](/Users/aaron/.gemini/antigravity/brain/e18a2c0a-90e7-4879-b8d8-aab71a489465/live_storefront_carousel_apparel.png)
<!-- slide -->
![All Products Carousel: Canonical Sorona Tee & Combat Uniform Set](/Users/aaron/.gemini/antigravity/brain/e18a2c0a-90e7-4879-b8d8-aab71a489465/live_storefront_carousel_combat_set.png)
<!-- slide -->
![Live Footer with Canonical Brand Logo](/Users/aaron/.gemini/antigravity/brain/e18a2c0a-90e7-4879-b8d8-aab71a489465/live_storefront_footer_canonical.png)
````

---

## 🛠️ 3. Line-by-Line Code & Asset Modifications

### Theme Architecture Files Modified

#### 1. [`sections/header-group.json`](file:///Volumes/Lauburu-Monorepo)
```diff
- "logo": "shopify://shop_images/image_19c6e28d-7c25-4047-ba59-40ee5bca9ea3.jpg"
+ "logo": "shopify://shop_images/lauburu_canonical_brand_logo.png"
```

#### 2. [`sections/footer-group.json`](file:///Volumes/Lauburu-Monorepo)
```diff
- "image": "shopify://shop_images/image_19c6e28d-7c25-4047-ba59-40ee5bca9ea3.jpg"
+ "image": "shopify://shop_images/lauburu_canonical_brand_logo.png"
```

#### 3. [`templates/index.json`](file:///Volumes/Lauburu-Monorepo)
```diff
- "item_image": "shopify://shop_images/collection_1.png"
+ "item_image": "shopify://shop_images/lauburu_canonical_cat_rashguard.png"

- "item_image": "shopify://shop_images/hoodies.png"
+ "item_image": "shopify://shop_images/lauburu_canonical_cat_hoodie.png"

- "item_image": "shopify://shop_images/Untitled_design_38.png"
+ "item_image": "shopify://shop_images/lauburu_canonical_cat_accessories.png"

- "image": "shopify://shop_images/Untitled_design_20.png"
+ "image": "shopify://shop_images/lauburu_canonical_story_card.png"
```

#### 4. [`config/settings_data.json`](file:///Volumes/Lauburu-Monorepo)
```diff
- "favicon": "shopify://shop_images/F1ACF8ED-0C70-47CC-B020-5E87D0EF90B7.png"
+ "favicon": "shopify://shop_images/lauburu_canonical_story_card.png"
```

---

## 📦 4. Public Collections & Catalog State

| Collection Title | Handle | Canonical Product Count | Included Items |
| :--- | :--- | :--- | :--- |
| **Home page** | `frontpage` | 12 | All 12 canonical POD apparel & combat gear |
| **Top Selling** | `all-products` | 12 | All 12 canonical POD apparel & combat gear |
| **Accessories** | `accessories` | 5 | Flip-Flops, Crossbody Bag, Backpack, Fanny Pack, Drawstring Bag |
| **No-Gi Jiu Jitsu Apparel Men** | `no-gi-jiu-jitsu-apparel` | 3 | Short Sleeve Rashguard, Fight Shorts, Uniform Set |
| **No-Gi Jiu Jitsu Apparel Women** | `no-gi-jiu-jitsu-apparel-women` | 3 | Short Sleeve Rashguard, Fight Shorts, Uniform Set |
| **No-Gi Rashguards** | `rashguards` | 2 | Short Sleeve Rashguard, Uniform Set |
| **No-Gi Shorts** | `shorts` | 3 | Pro Fight Shorts, Uniform Set, Fleece Shorts |
| **Streetwear** | `streetwear-apparel` | 4 | Hoodie, Joggers, Cooling Tee, Loose Fit Shorts |
| **Streetwear Men** | `street-wear-apparel-men` | 4 | Hoodie, Joggers, Cooling Tee, Loose Fit Shorts |
| **Streetwear Women** | `streetwear-women` | 4 | Hoodie, Joggers, Cooling Tee, Loose Fit Shorts |

> [!NOTE]
> All 20 legacy products (the old 4-bladed swirl Subliminator/Merchize items) are currently set to **`Draft`** in Shopify Admin. They do not appear anywhere on the public storefront, search results, or collections. Per your explicit instructions, they are preserved safely until you confirm permanent deletion.

---

## ⚡ 5. Automated Sales Engine Integration Verification

Physical test run via `01_apps/commerce_and_business/tests/test_shopify_pod_sales_integration.py`:

```
============================= test session starts ==============================
collected 6 items

test_shopify_pod_sales_integration.py::test_shop_metadata_and_currency PASSED
test_shopify_pod_sales_integration.py::test_pod_catalog_variant_availability PASSED
test_shopify_pod_sales_integration.py::test_single_item_backpack_test_sale PASSED
test_shopify_pod_sales_integration.py::test_multi_vendor_bundle_test_sale PASSED
test_shopify_pod_sales_integration.py::test_buyer_identity_update PASSED
test_shopify_pod_sales_integration.py::test_pod_order_webhook_fulfillment_routing PASSED

============================== 6 passed in 10.41s ==============================
Exit Code: 0
```

---

## 🥋 6. Custom Combat Apparel & Physical Sample Order Telemetry

* **Master Tech Pack:** [`07_docs_and_architecture/LAUBURU_COMBAT_APPAREL_TECH_PACK.md`](file:///Volumes/Lauburu-Monorepo/07_docs_and_architecture/LAUBURU_COMBAT_APPAREL_TECH_PACK.md)
* **Physical Reference Baseline:** Absolute MMA baseline garments (Size M rashguard & fight shorts, parcel tracking `EJ350397089AU`) delivered to Shaoxing Sred Apparel Co. pattern room on May 30, 2026.
* **Direct Threaded Dispatch:** Sent Monday, Sept 14, 2026 at ~1:00 PM AEST to Hicham Amrani (`hicham@subliminator.com`), CEO of Subliminator / Shaoxing Sred Apparel Co.:
  - **Thread Subject:** `Re: Absolute MMA: confirmed production terms and pricing`
  - **Message-ID:** `<178935477391.47749.8415478914821241277@lauburugrappling.com>`
  - **Directive:** Black Belt Sample ONLY (Size M: 1x Short Sleeve Compression Rashguard + 1x No-Gi Pro Fight Shorts), requesting $200 USD sample fee invoice (citing ticket `#50573`).
* **Live Inbound Probing (IMAP SSL):** Zero responses received across INBOX, Spam, and All Mail. 0 draft orders in Shopify Admin, 0 orders in Subliminator dashboard (~35 hours elapsed).

---

## ⚖️ 7. Multi-Channel Commerce & ELO Penalty Enforcement

* **The Incident:** Prospective buyer `Lachy` (`buyer-3m9qvv12225w@users.gumtree.com.au`) replied to Aaron's Gumtree ad (`Apple iPhone 16 Pro 512GB - Black Titanium - Unlocked`) with an off-platform WhatsApp redirection request (`042-01334-82`).
* **Disciplinary Action:** Pursuant to `waste_tax.py`, docked ELO across all commerce contenders for failing to flag the buyer inquiry:
  - `ROLE_08_BUSINESS_COMMERCE` (`qwen_coder_7b`): 2,798.9 ➔ 2,748.9 (-50.0 pts)
  - `ROLE_08_BUSINESS_COMMERCE` (`llama_1b`): 2,155.4 ➔ 2,120.4 (-35.0 pts)
  - `ROLE_SPEC_SHOPIFY_COMMERCE_ANALYST` (`gemma-2-2b-it`): 2,982.9 ➔ 2,922.9 (-60.0 pts)
  - `Team Combined E-Com Swarm`: 2,915.0 ➔ 2,850.0 (-65.0 pts, Policy Risk 4.5%)
* **Ledgers & DPO:** Logged event `tax_gumtree_iphone_omission_20260915` to `04_data_and_memory/session_logs/waste_tax_ledger.jsonl` and appended an anti-fraud classified training pair to `lora_datasets/continuous_lora_dataset.jsonl`.
* **Port 4004 Live UI:** Reloaded `training_stream_server.py`; the leaderboards reflect the penalized rankings.

---

## 💻 8. Pixel Storefront TUI & Interactive Notebook Studio

* **12-Product Catalog Module:** [`01_apps/user_facing_and_scaling/shopify_storefront/presentation/catalog.py`](file:///Volumes/Lauburu-Monorepo/01_apps/user_facing_and_scaling/shopify_storefront/presentation/catalog.py)
* **Interactive Storefront TUI:** [`01_apps/user_facing_and_scaling/shopify_storefront/presentation/tui.py`](file:///Volumes/Lauburu-Monorepo/01_apps/user_facing_and_scaling/shopify_storefront/presentation/tui.py)
  - Interactive Textual TUI supporting membership plans, 12 canonical gear items, and headless GraphQL cart generation.
* **Storefront Studio Notebook:** [`01_apps/notebooks/08_shopify_canonical_storefront_studio.ipynb`](file:///Volumes/Lauburu-Monorepo/01_apps/notebooks/08_shopify_canonical_storefront_studio.ipynb)
  - Validated with automated unit tests: `Ran 6 tests in 1.094s — OK` (Exit Code 0).
  - Synchronized to Tri-Vault (`obsidian_vault/notebooks/08_shopify_canonical_storefront_studio.ipynb`).

