#!/usr/bin/env python3
"""
iPhone 16 Pro 512GB - Professional Multi-Platform Photo Enhancement Suite (v2.0)
Generates high-conversion, pixel-perfect marketplace listing images (1200x1200)
for Gumtree, eBay, and Facebook Marketplace.
"""
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont

ASSETS_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets")
ENHANCED_DIR = ASSETS_DIR / "enhanced"
ENHANCED_DIR.mkdir(parents=True, exist_ok=True)

src_front = ASSETS_DIR / "iphone_16_pro_512gb_front.jpg"
src_screen = ASSETS_DIR / "iphone_16_pro_512gb_screen.jpg"

im_front = Image.open(src_front).convert("RGB")
im_screen = Image.open(src_screen).convert("RGB")

FONT_HELVETICA = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

font_hero_title = ImageFont.truetype(FONT_BOLD, 38)
font_hero_sub = ImageFont.truetype(FONT_HELVETICA, 24)
font_badge_title = ImageFont.truetype(FONT_BOLD, 26)
font_badge_sub = ImageFont.truetype(FONT_BOLD, 20)
font_card_header = ImageFont.truetype(FONT_BOLD, 30)
font_card_sub = ImageFont.truetype(FONT_HELVETICA, 22)
font_card_title = ImageFont.truetype(FONT_BOLD, 24)
font_card_val = ImageFont.truetype(FONT_BOLD, 34)
font_card_desc = ImageFont.truetype(FONT_HELVETICA, 18)
font_bullet = ImageFont.truetype(FONT_HELVETICA, 21)
font_bullet_bold = ImageFont.truetype(FONT_BOLD, 21)

CANVAS_SZ = (1200, 1200)

def create_gradient_canvas(top_rgb, bot_rgb):
    bg = Image.new("RGB", CANVAS_SZ)
    draw = ImageDraw.Draw(bg)
    for y in range(CANVAS_SZ[1]):
        ratio = y / CANVAS_SZ[1]
        r = int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * ratio)
        g = int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * ratio)
        b = int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * ratio)
        draw.line([(0, y), (CANVAS_SZ[0], y)], fill=(r, g, b))
    return bg

def draw_checkmark(draw, x, y, color=(25, 135, 84), size=14):
    draw.line([(x, y + int(size*0.5)), (x + int(size*0.4), y + size)], fill=color, width=3)
    draw.line([(x + int(size*0.4), y + size), (x + size, y)], fill=color, width=3)

# --- ROTATION & CROPPING ---
rot = im_front.rotate(2.8, resample=Image.BICUBIC, expand=True)
phone_cut = rot.crop((165, 160, 575, 985))
phone_cut = ImageEnhance.Contrast(phone_cut).enhance(1.16)
phone_cut = ImageEnhance.Color(phone_cut).enhance(1.12)
phone_cut = ImageEnhance.Sharpness(phone_cut).enhance(1.30)

p_w, p_h = phone_cut.size
mask = Image.new("L", (p_w, p_h), 0)
mdraw = ImageDraw.Draw(mask)
mdraw.rounded_rectangle([0, 0, p_w, p_h], radius=44, fill=255)
phone_cut.putalpha(mask)

# ==============================================================================
# SLIDE 1: HERO MARKETPLACE SHOT
# ==============================================================================
hero = create_gradient_canvas((246, 248, 251), (220, 224, 230))
h_scale = 920 / p_h
new_w = int(p_w * h_scale)
new_h = int(p_h * h_scale)
phone_hero = phone_cut.resize((new_w, new_h), Image.LANCZOS)

paste_x = (CANVAS_SZ[0] - new_w) // 2
paste_y = 155

shadow = Image.new("RGBA", (new_w + 80, new_h + 80), (0, 0, 0, 0))
sdraw = ImageDraw.Draw(shadow)
sdraw.rounded_rectangle([40, 40, new_w + 40, new_h + 40], radius=50, fill=(0, 0, 0, 85))
shadow = shadow.filter(ImageFilter.GaussianBlur(26))
hero.paste(shadow, (paste_x - 40, paste_y - 20), shadow)
hero.paste(phone_hero, (paste_x, paste_y), phone_hero)

hdraw = ImageDraw.Draw(hero)

# Top Left Header Card
hdraw.rounded_rectangle([40, 35, 630, 130], radius=16, fill=(18, 22, 28))
hdraw.text((65, 48), "Apple iPhone 16 Pro • 512GB", font=font_hero_title, fill=(255, 255, 255))
hdraw.text((65, 94), "Black Titanium | Factory Unlocked | A18 Pro Bionic", font=font_hero_sub, fill=(160, 180, 205))

# Top Right Liquidation Badge (Width 520)
hdraw.rounded_rectangle([CANVAS_SZ[0] - 520, 35, CANVAS_SZ[0] - 40, 130], radius=16, fill=(215, 35, 45))
hdraw.text((CANVAS_SZ[0] - 500, 48), "LIQUIDATION: UNDER $1,000", font=font_badge_title, fill=(255, 255, 255))
hdraw.text((CANVAS_SZ[0] - 500, 88), "$890 Cash Pickup • $980 eBay Buy It Now", font=font_badge_sub, fill=(255, 235, 235))

# Bottom Spec Strip
hdraw.rounded_rectangle([60, CANVAS_SZ[1] - 95, CANVAS_SZ[0] - 60, CANVAS_SZ[1] - 25], radius=16, fill=(18, 22, 28))
bullet_items = ["512GB NVMe Storage", "100% Battery Health", "Flawless Face ID & Touch", "Clean iCloud Reset"]
for i, item in enumerate(bullet_items):
    bx = 90 + i * 275
    by = CANVAS_SZ[1] - 68
    draw_checkmark(hdraw, bx, by - 2, color=(35, 195, 110), size=16)
    hdraw.text((bx + 26, by - 5), item, font=ImageFont.truetype(FONT_BOLD, 18), fill=(240, 245, 255))

hero_path = ENHANCED_DIR / "01_hero_iphone16pro_512gb.jpg"
hero.convert("RGB").save(hero_path, quality=95)
print(f"Refined: {hero_path}")

# ==============================================================================
# SLIDE 2: TRANSPARENT CONDITION & BEZEL CALLOUT
# ==============================================================================
macro = create_gradient_canvas((242, 245, 249), (220, 225, 232))
mdraw = ImageDraw.Draw(macro)

mdraw.rounded_rectangle([40, 35, CANVAS_SZ[0] - 40, 125], radius=18, fill=(18, 22, 28))
mdraw.text((65, 45), "TRANSPARENT CONDITION DISCLOSURE (ZERO SURPRISE)", font=font_card_header, fill=(255, 255, 255))
mdraw.text((65, 88), "Authentic macro inspection of the outer bezel edge mark.", font=font_card_sub, fill=(160, 180, 205))

scr = im_screen.copy()
scr = ImageEnhance.Contrast(scr).enhance(1.18)
scr = ImageEnhance.Color(scr).enhance(1.10)
scr = ImageEnhance.Sharpness(scr).enhance(1.35)
scr_scaled = scr.resize((600, 980), Image.LANCZOS)

s_macro = Image.new("RGBA", (620, 1000), (0, 0, 0, 0))
smdraw = ImageDraw.Draw(s_macro)
smdraw.rounded_rectangle([10, 10, 610, 990], radius=20, fill=(0, 0, 0, 65))
s_macro = s_macro.filter(ImageFilter.GaussianBlur(16))
macro.paste(s_macro, (35, 150), s_macro)
macro.paste(scr_scaled, (45, 160))

# Correct position of the crescent mark in 600x980 crop:
# In source 771x1024, crescent apex is at x=382, y=600.
# In scaled crop: x = 45 + (382 * 600 / 771) = 45 + 297 = 342
# y = 160 + (600 * 980 / 1024) = 160 + 574 = 734.
c_x = 342
c_y = 734
mdraw.ellipse([c_x - 42, c_y - 42, c_x + 42, c_y + 42], outline=(225, 30, 45), width=5)
mdraw.line([(c_x + 42, c_y), (675, c_y)], fill=(225, 30, 45), width=3)

# Right Side Panels (Width 475)
panel_x = 675
panel_w = CANVAS_SZ[0] - panel_x - 40

# Panel 1: Bezel Detail
mdraw.rounded_rectangle([panel_x, 160, panel_x + panel_w, 510], radius=18, fill=(255, 255, 255), outline=(205, 212, 220), width=2)
mdraw.text((panel_x + 25, 185), "OLED BEZEL DETAIL", font=font_card_title, fill=(20, 25, 35))
bezel_notes = [
    "Small black crescent mark on outer right bezel.",
    "Front glass is 100% scratch-free & crack-free.",
    "Touch digitizer is 100% responsive everywhere.",
    "Stable cosmetic flaw — does not spread or flicker.",
    "Over $1,150 OFF retail ($2,149 Apple Store)!"
]
for i, note in enumerate(bezel_notes):
    col = (215, 35, 45) if i == 4 else (45, 50, 60)
    mdraw.text((panel_x + 25, 230 + i * 46), f"• {note}", font=font_bullet_bold if i in [2, 4] else font_bullet, fill=col)

# Panel 2: Sensor Health
mdraw.rounded_rectangle([panel_x, 535, panel_x + panel_w, 915], radius=18, fill=(255, 255, 255), outline=(205, 212, 220), width=2)
mdraw.text((panel_x + 25, 560), "HARDWARE HEALTH: 100% VERIFIED", font=font_card_title, fill=(20, 25, 35))
sensors = [
    "Face ID: Verified Working Instantly",
    "120Hz ProMotion & HDR: Ultra Smooth",
    "Dynamic Island: Flawless Functionality",
    "Rear Triple Cameras: Pristine Optics",
    "Back Matte Glass & Titanium: Immaculate",
    "Factory Restored: iCloud Free & Ready"
]
for i, s in enumerate(sensors):
    sy = 605 + i * 44
    draw_checkmark(mdraw, panel_x + 25, sy + 3, color=(20, 130, 70), size=14)
    mdraw.text((panel_x + 50, sy), s, font=font_bullet_bold, fill=(20, 130, 70))

# Panel 3: In-Person Guarantee
mdraw.rounded_rectangle([panel_x, 940, panel_x + panel_w, 1140], radius=18, fill=(18, 22, 28))
mdraw.text((panel_x + 25, 965), "IN-PERSON INSPECTION WELCOME", font=font_card_title, fill=(255, 255, 255))
mdraw.text((panel_x + 25, 1005), "Test Face ID, cameras, screen & touch on-site.", font=font_card_desc, fill=(180, 195, 215))
mdraw.text((panel_x + 25, 1035), "Take all the time you need before paying.", font=font_card_desc, fill=(180, 195, 215))
mdraw.text((panel_x + 25, 1075), "Altona North 3025 • Cash or PayID on inspection.", font=font_bullet_bold, fill=(255, 215, 0))

macro_path = ENHANCED_DIR / "02_condition_transparency_callout.jpg"
macro.convert("RGB").save(macro_path, quality=95)
print(f"Refined: {macro_path}")

# ==============================================================================
# SLIDE 3: HARDWARE SPECIFICATIONS INFOGRAPHIC
# ==============================================================================
specs = create_gradient_canvas((18, 22, 28), (28, 34, 44))
sdraw = ImageDraw.Draw(specs)

sdraw.rounded_rectangle([40, 35, CANVAS_SZ[0] - 40, 125], radius=18, fill=(28, 34, 44), outline=(45, 55, 70), width=2)
sdraw.text((65, 45), "APPLE iPHONE 16 PRO — HARDWARE SPECIFICATIONS", font=font_card_header, fill=(255, 255, 255))
sdraw.text((65, 88), "Authentic Apple Silicon • 512GB Storage Tier • Premium Black Titanium", font=font_card_sub, fill=(160, 180, 205))

spec_items = [
    ("STORAGE CAPACITY", "512 GB", "4x Standard Base Storage\nMassive headroom for 4K 120fps Dolby Vision video & ProRAW."),
    ("PROCESSOR & NEURAL", "Apple A18 Pro", "6-Core CPU with 2 performance and 4 efficiency cores.\n6-Core GPU + 16-Core Neural Engine for Apple Intelligence."),
    ("CHASSIS & FINISH", "Black Titanium", "Grade 5 Aerospace Titanium with textured matte glass back.\nCeramic Shield front glass (tougher than any smartphone glass)."),
    ("PRO DISPLAY", "6.3\" Super Retina XDR", "2622x1206 OLED at 460 ppi, 120Hz ProMotion adaptive refresh,\nAlways-On display, True Tone, 2000 nits peak outdoor brightness."),
    ("PRO CAMERA SYSTEM", "48MP Fusion Triple", "48MP Main (24mm & 48mm), 48MP Ultra-Wide (macro),\n12MP 5x Optical Telephoto (120mm), Camera Control sensor."),
    ("AUTHENTICITY & LOCKS", "100% Unlocked", "Serial: G0WR66YPCQ. iCloud Activation Lock removed.\nFactory restored to Hello screen. Compatible with all AU telcos.")
]

for idx, (head, val, desc) in enumerate(spec_items):
    row = idx // 2
    col = idx % 2
    x1 = 50 + col * 560
    y1 = 160 + row * 280
    x2 = x1 + 540
    y2 = y1 + 250
    
    sdraw.rounded_rectangle([x1, y1, x2, y2], radius=18, fill=(24, 29, 38), outline=(45, 55, 70), width=2)
    sdraw.text((x1 + 30, y1 + 20), head, font=font_card_title, fill=(140, 165, 195))
    sdraw.text((x1 + 30, y1 + 60), val, font=font_card_val, fill=(255, 255, 255))
    sdraw.text((x1 + 30, y1 + 130), desc, font=font_card_desc, fill=(180, 195, 210))

sdraw.rounded_rectangle([50, CANVAS_SZ[1] - 140, CANVAS_SZ[0] - 50, CANVAS_SZ[1] - 40], radius=18, fill=(215, 35, 45))
sdraw.text((80, CANVAS_SZ[1] - 125), "PRICE DROPPED ACROSS ALL PLATFORMS: UNDER $1,000", font=font_badge_title, fill=(255, 255, 255))
sdraw.text((80, CANVAS_SZ[1] - 80), "Gumtree / Marketplace: $890 AUD Cash | eBay Buy It Now: $980 AUD (Express Insured)", font=font_badge_sub, fill=(255, 235, 235))

specs_path = ENHANCED_DIR / "03_specifications_summary.jpg"
specs.convert("RGB").save(specs_path, quality=95)
print(f"Refined: {specs_path}")

# ==============================================================================
# SLIDE 4: MULTI-PLATFORM PRICING BREAKDOWN CARD
# ==============================================================================
pricing = create_gradient_canvas((245, 247, 250), (220, 225, 232))
pdraw = ImageDraw.Draw(pricing)

pdraw.rounded_rectangle([40, 35, CANVAS_SZ[0] - 40, 125], radius=18, fill=(18, 22, 28))
pdraw.text((65, 45), "CHOOSE YOUR PURCHASE PLATFORM — ALL UNDER $1,000", font=font_card_header, fill=(255, 255, 255))
pdraw.text((65, 88), "Immediate liquidation pricing for genuine Australian buyers.", font=font_card_sub, fill=(160, 180, 205))

channels = [
    ("GUMTREE & MARKETPLACE", "$890 AUD", "LOCAL CASH PICKUP", [
        "Best price: Lowest cash price available.",
        "Pick up in person at Altona North 3025.",
        "Inspect and test every function on-site.",
        "Pay via Cash or Instant PayID/OSKO.",
        "Zero waiting, take it home immediately."
    ], (25, 135, 84)),
    ("EBAY AUSTRALIA", "$980 AUD", "BUY IT NOW / POSTED", [
        "Under $1,000 Buy It Now price.",
        "Includes Australia Post Express Insured Post.",
        "Signature on delivery + tracking included.",
        "Covered by eBay Money Back Guarantee.",
        "Dispatched within 24 hours."
    ], (13, 110, 253))
]

for idx, (title, price_str, subtitle, points, accent_col) in enumerate(channels):
    x1 = 50 + idx * 560
    y1 = 160
    x2 = x1 + 540
    y2 = 780
    
    pdraw.rounded_rectangle([x1, y1, x2, y2], radius=20, fill=(255, 255, 255), outline=(205, 212, 220), width=2)
    pdraw.rounded_rectangle([x1, y1, x2, y1 + 18], radius=20, fill=accent_col)
    
    pdraw.text((x1 + 35, y1 + 35), title, font=font_card_title, fill=(20, 25, 35))
    pdraw.text((x1 + 35, y1 + 75), price_str, font=ImageFont.truetype(FONT_BOLD, 54), fill=accent_col)
    pdraw.text((x1 + 35, y1 + 145), subtitle, font=font_badge_sub, fill=(100, 110, 125))
    
    pdraw.line([(x1 + 35, y1 + 185), (x2 - 35, y1 + 185)], fill=(225, 230, 238), width=2)
    
    for p_idx, pt in enumerate(points):
        py = y1 + 215 + p_idx * 52
        draw_checkmark(pdraw, x1 + 35, py + 3, color=accent_col, size=15)
        pdraw.text((x1 + 60, py), pt, font=font_bullet, fill=(40, 45, 55))

# Bottom Trade & Liquidation Box
pdraw.rounded_rectangle([50, 815, CANVAS_SZ[0] - 50, 1145], radius=20, fill=(18, 22, 28))
pdraw.text((80, 845), "OPEN TO TRADES & OFFERS", font=font_card_title, fill=(255, 255, 255))
pdraw.text((80, 895), "• Open to trades for laptops (M-series MacBooks / Windows laptops), cameras, audio gear, or consoles.", font=font_bullet, fill=(210, 220, 235))
pdraw.text((80, 940), "• Trade equity calculated transparently against the $990 trade valuation.", font=font_bullet, fill=(210, 220, 235))
pdraw.text((80, 985), "• Fast, polite responses to genuine inquiries.", font=font_bullet, fill=(210, 220, 235))
pdraw.text((80, 1045), "Location: Altona North 3025 (Safe residential / daylight meetup)", font=font_bullet_bold, fill=(255, 215, 0))

pricing_path = ENHANCED_DIR / "04_multiplatform_pricing_card.jpg"
pricing.convert("RGB").save(pricing_path, quality=95)
print(f"Refined: {pricing_path}")

print("All 4 refined images successfully generated!")
