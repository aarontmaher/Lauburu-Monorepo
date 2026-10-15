#!/usr/bin/env python3
"""
Generate 100% text-free, natural, high-trust marketplace photos
Complies strictly with eBay Picture Policy & Gumtree/Marketplace private seller standards.
Zero text overlays, zero watermarks, zero graphic borders.
"""
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

ASSETS_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets")
CLEAN_DIR = ASSETS_DIR / "clean_marketplace"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

src_front = ASSETS_DIR / "iphone_16_pro_512gb_front.jpg"
src_screen = ASSETS_DIR / "iphone_16_pro_512gb_screen.jpg"

im_front = Image.open(src_front).convert("RGB")
im_screen = Image.open(src_screen).convert("RGB")

# 1. CLEAN HERO SHOT (Front):
# Straighten by 2.8 degrees
rot = im_front.rotate(2.8, resample=Image.BICUBIC, expand=True)

# Crop to center phone naturally with a clean, balanced margin
# Phone is at x=165..575, y=160..985
# Give a natural photographic margin around the phone
crop_x1 = max(0, 165 - 80)
crop_y1 = max(0, 160 - 70)
crop_x2 = min(rot.width, 575 + 80)
crop_y2 = min(rot.height, 985 + 70)

clean_hero = rot.crop((crop_x1, crop_y1, crop_x2, crop_y2))

# Enhance subtle lighting: reduce glare harshness, slight contrast and natural color boost
clean_hero = ImageEnhance.Contrast(clean_hero).enhance(1.08)
clean_hero = ImageEnhance.Color(clean_hero).enhance(1.06)
clean_hero = ImageEnhance.Sharpness(clean_hero).enhance(1.20)

clean_hero_path = CLEAN_DIR / "01_iphone_16_pro_front_clean.jpg"
clean_hero.save(clean_hero_path, quality=96)
print(f"Generated clean text-free hero: {clean_hero_path}")

# 2. CLEAN MACRO FLAW SHOT:
# Pure, honest macro close-up of the bezel mark with zero text, zero arrows, zero circles
# Let the macro detail speak for itself with 100% transparency
scr_enhanced = ImageEnhance.Contrast(im_screen).enhance(1.08)
scr_enhanced = ImageEnhance.Color(scr_enhanced).enhance(1.05)
scr_enhanced = ImageEnhance.Sharpness(scr_enhanced).enhance(1.25)

clean_macro_path = CLEAN_DIR / "02_iphone_16_pro_bezel_flaw_clean.jpg"
scr_enhanced.save(clean_macro_path, quality=96)
print(f"Generated clean text-free macro: {clean_macro_path}")

# Copy to brain artifact directory for instant viewing
brain_dir = Path("/Users/aaron/.gemini/antigravity/brain/cdca10c9-e3ec-4303-aabd-7860383dd9a8")
clean_hero.save(brain_dir / "01_iphone_16_pro_front_clean.jpg", quality=96)
scr_enhanced.save(brain_dir / "02_iphone_16_pro_bezel_flaw_clean.jpg", quality=96)
print("Copied clean photos to artifact directory.")
