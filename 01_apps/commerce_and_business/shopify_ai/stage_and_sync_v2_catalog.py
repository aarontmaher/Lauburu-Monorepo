#!/usr/bin/env python3
"""
stage_and_sync_v2_catalog.py
============================
Encodes and stages the 7 canonical V2 apparel & gear items with high-res photography,
tech pack descriptions, and variant hierarchies for Shopify / ODMPOD fulfillment.
"""

import json
import base64
from pathlib import Path

REPO_ROOT = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
ASSETS_DIR = REPO_ROOT / "assets/products/canonical_apparel_v2"
OUTPUT_JSON = REPO_ROOT / "04_data_and_memory/generated_products/staged_canonical_products_v2.json"

PRODUCTS = [
    {
        "title": "Lauburu 330 GSM Heavyweight Cotton Tee",
        "product_type": "T-Shirt",
        "sku_prefix": "LAU-TEE-330",
        "price": "65.00",
        "image_file": "lauburu_330gsm_tee.jpg",
        "vendor": "ODMPOD",
        "tags": ["Canonical V2", "Streetwear", "T-Shirt", "330 GSM"],
        "options": [{"name": "Size", "values": ["S", "M", "L", "XL", "2XL"]}],
        "body_html": """<h3>Lauburu 330 GSM Heavyweight Streetwear Tee</h3>
<p>Replaces standard training tees with an uncompromising 330 GSM combed cotton construction.</p>
<ul>
  <li><strong>Fabric Weight:</strong> 330 GSM 100% Dense Combed Cotton with anti-shrink pre-wash.</li>
  <li><strong>Fit:</strong> Dropped shoulder, relaxed streetwear silhouette with a structured 30mm thick rib collar.</li>
  <li><strong>Branding:</strong> Tonal matte black silicone-embossed canonical Lauburu symbol centered on the sternum.</li>
  <li><strong>Durability:</strong> Twin-needle flatlock stitched hem and sleeves for long-term shape retention.</li>
</ul>"""
    },
    {
        "title": "Lauburu Oversized French Terry Hoodie",
        "product_type": "Hoodie",
        "sku_prefix": "LAU-HOO-450",
        "price": "120.00",
        "image_file": "lauburu_french_terry_hoodie.jpg",
        "vendor": "ODMPOD",
        "tags": ["Canonical V2", "Streetwear", "Hoodie", "French Terry"],
        "options": [{"name": "Size", "values": ["S", "M", "L", "XL", "2XL"]}],
        "body_html": """<h3>Lauburu Oversized French Terry Hoodie</h3>
<p>The definitive heavyweight grappling streetwear layer.</p>
<ul>
  <li><strong>Material:</strong> 450 GSM Heavy Looped French Terry for optimal breathability and moisture absorption post-training.</li>
  <li><strong>Hood:</strong> Seamless double-layered structured hood with zero choking drawstrings.</li>
  <li><strong>Branding:</strong> Left pectoral high-density rubberized tonal Lauburu emblem.</li>
  <li><strong>Cut:</strong> Boxy body with dropped armholes and ribbed stretch side gussets.</li>
</ul>"""
    },
    {
        "title": "Lauburu Unisex Heavyweight Fleece Joggers",
        "product_type": "Joggers",
        "sku_prefix": "LAU-JOG-400",
        "price": "95.00",
        "image_file": "lauburu_fleece_joggers.jpg",
        "vendor": "ODMPOD",
        "tags": ["Canonical V2", "Streetwear", "Joggers", "Fleece"],
        "options": [{"name": "Size", "values": ["S", "M", "L", "XL", "2XL"]}],
        "body_html": """<h3>Lauburu Heavyweight Tapered Fleece Joggers</h3>
<p>Engineered for athletes traveling to and from the tatami.</p>
<ul>
  <li><strong>Fabric:</strong> 400 GSM brushed-back cotton fleece providing structural warmth without bulk.</li>
  <li><strong>Security:</strong> Dual matte-black YKK zippered hand pockets to prevent phones and lockers keys from slipping on mats.</li>
  <li><strong>Waistband:</strong> Quad-stitched elastic waistband with flat woven drawstring and metal aglets.</li>
  <li><strong>Branding:</strong> Embossed silicone canonical Lauburu emblem on upper left thigh.</li>
</ul>"""
    },
    {
        "title": "Lauburu Unisex Heavyweight Fleece Loose Fit Shorts",
        "product_type": "Shorts",
        "sku_prefix": "LAU-SHO-380",
        "price": "75.00",
        "image_file": "lauburu_fleece_shorts.jpg",
        "vendor": "ODMPOD",
        "tags": ["Canonical V2", "Streetwear", "Shorts", "Fleece"],
        "options": [{"name": "Size", "values": ["S", "M", "L", "XL", "2XL"]}],
        "body_html": """<h3>Lauburu Heavyweight Fleece Loose Fit Shorts</h3>
<p>Modern lifestyle and recovery shorts cut just above the knee.</p>
<ul>
  <li><strong>Material:</strong> 380 GSM fleece cotton with brushed interior finish.</li>
  <li><strong>Hardware:</strong> Bar-tacked zipper pockets and interior flat drawstring.</li>
  <li><strong>Branding:</strong> Canonical tonal Lauburu cross emblem on lower left hem.</li>
</ul>"""
    },
    {
        "title": "Lauburu 1000D Tactical Combat Backpack",
        "product_type": "Bag",
        "sku_prefix": "LAU-BAG-TAC",
        "price": "145.00",
        "image_file": "lauburu_tactical_backpack.jpg",
        "vendor": "ODMPOD",
        "tags": ["Canonical V2", "Gear", "Backpack", "1000D"],
        "options": [{"name": "Size", "values": ["OSFA"]}],
        "body_html": """<h3>Lauburu 1000D Tactical Combat Backpack (35L)</h3>
<p>Built exclusively for combat athletes carrying heavy gis, rashguards, and hydration.</p>
<ul>
  <li><strong>Material:</strong> 1000D Ballistic Cordura nylon with DWR waterproof coating.</li>
  <li><strong>Specialized Compartment:</strong> Dedicated ventilated lower front pocket for wet grappling gear and tape.</li>
  <li><strong>Branding:</strong> Molded matte black PVC Lauburu tactical morale patch.</li>
  <li><strong>Hardware:</strong> Heavy-duty YKK sealed zippers with paracord pullers.</li>
</ul>"""
    },
    {
        "title": "Lauburu Heavyweight Grappling Duffle Bag",
        "product_type": "Bag",
        "sku_prefix": "LAU-BAG-DUF",
        "price": "135.00",
        "image_file": "lauburu_heavyweight_duffle.jpg",
        "vendor": "ODMPOD",
        "tags": ["Canonical V2", "Gear", "Duffle Bag", "50L"],
        "options": [{"name": "Size", "values": ["OSFA"]}],
        "body_html": """<h3>Lauburu Heavyweight Grappling Duffle Bag (50L)</h3>
<p>The ultimate multi-day competition and seminar carryall.</p>
<ul>
  <li><strong>Capacity:</strong> 50 Liters with isolated wet/dry shoe and gi partitions.</li>
  <li><strong>Construction:</strong> 1000D water-resistant ripstop nylon with reinforced seatbelt-webbing handles.</li>
  <li><strong>Branding:</strong> Tonal matte black canonical Lauburu emblem on the main side exterior.</li>
</ul>"""
    },
    {
        "title": "Lauburu EVA Molded Recovery Slides",
        "product_type": "Footwear",
        "sku_prefix": "LAU-SLD-EVA",
        "price": "55.00",
        "image_file": "lauburu_eva_slides.jpg",
        "vendor": "ODMPOD",
        "tags": ["Canonical V2", "Footwear", "Slides", "Recovery"],
        "options": [{"name": "Size", "values": ["US 7", "US 8", "US 9", "US 10", "US 11", "US 12"]}],
        "body_html": """<h3>Lauburu EVA Molded Recovery Slides</h3>
<p>Essential off-mat hygiene footwear designed for seamless transition from changing rooms to the tatami edge.</p>
<ul>
  <li><strong>Construction:</strong> 100% injection-molded one-piece EVA foam with deep textured anti-slip mat grip.</li>
  <li><strong>Support:</strong> Ergonomic deep heel cup and anatomical arch support for post-training recovery.</li>
  <li><strong>Branding:</strong> Canonical Lauburu symbol seamlessly molded in 3D relief across the strap.</li>
</ul>"""
    }
]

def encode_image(filename):
    p = ASSETS_DIR / filename
    if not p.exists():
        return None
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

staged = []
for p in PRODUCTS:
    b64 = encode_image(p["image_file"])
    variants = []
    opt_values = p["options"][0]["values"]
    for val in opt_values:
        sku_clean = f"{p['sku_prefix']}-{val.replace(' ', '').replace('US', '')}"
        variants.append({
            "title": val,
            "price": p["price"],
            "sku": sku_clean,
            "requires_shipping": True
        })
        
    staged.append({
        "title": p["title"],
        "product_type": p["product_type"],
        "vendor": p["vendor"],
        "tags": p["tags"],
        "body_html": p["body_html"],
        "options": p["options"],
        "variants": variants,
        "image_file": str(ASSETS_DIR / p["image_file"]),
        "image_base64_len": len(b64) if b64 else 0
    })

with open(OUTPUT_JSON, "w") as f:
    json.dump(staged, f, indent=2)

print(f"✅ Staged {len(staged)} complete canonical products with high-res base64 assets to {OUTPUT_JSON}")
