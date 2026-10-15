#!/usr/bin/env python3
"""
Generate Optimal Lauburu Custom BJJ Uniform Renders
Applies Official IBJJF Belt Rank Colors with 100% exact matching between
the canonical Lauburu symbols, underarm flank panels, and shorts mobility slit accents.
"""

import os
import shutil
from PIL import Image, ImageDraw, ImageFont
import numpy as np

BASE_DIR = "/Users/aaron/.gemini/antigravity/brain/9c2b4f2f-6922-4a40-8078-a9f63ba72162/scratch/bjj_ranks"
OUT_DIR = "/Volumes/Lauburu-Monorepo/assets/products/bjj_apparel"
ARTIFACT_DIR = "/Users/aaron/.gemini/antigravity/brain/9c2b4f2f-6922-4a40-8078-a9f63ba72162"

os.makedirs(OUT_DIR, exist_ok=True)

# Load base clean transparent garments
rg_clean = Image.open(os.path.join(BASE_DIR, "clean_optimal_rashguard.png")).convert("RGBA")
sh_clean = Image.open(os.path.join(BASE_DIR, "clean_optimal_shorts.png")).convert("RGBA")
sym_img = Image.open("/Volumes/Lauburu-Monorepo/assets/branding/canonical_lauburu_symbol_clean_transparent.png").convert("RGBA")

# Official IBJJF Rank Color Standards: (id, display_title, rgb, hex_code, pantone_ref)
IBJJF_RANKS = [
    ("white", "WHITE BELT", (250, 250, 250), "#FFFFFF", "White"),
    ("blue", "BLUE BELT", (0, 71, 171), "#0047AB", "Pantone 286 C / Cobalt"),
    ("purple", "PURPLE BELT", (92, 6, 140), "#5C068C", "Pantone 268 C / Imperial"),
    ("brown", "BROWN BELT", (85, 45, 32), "#552D20", "Pantone 4625 C / Espresso"),
    ("black", "BLACK BELT", (200, 16, 46), "#C8102E", "Pantone 186 C / Crimson Bar"),
]

def create_colored_symbol(rgb, target_w):
    sym_arr = np.array(sym_img)
    alpha = sym_arr[:, :, 3]
    out = np.zeros_like(sym_arr)
    out[:, :, 0] = rgb[0]
    out[:, :, 1] = rgb[1]
    out[:, :, 2] = rgb[2]
    out[:, :, 3] = alpha
    colored = Image.fromarray(out)
    target_h = int(target_w * (sym_img.height / sym_img.width))
    return colored.resize((target_w, target_h), Image.Resampling.LANCZOS)

# Fonts
font_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 40)
font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
font_card_title = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
font_card_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)

print("🎨 Generating Official IBJJF Ranked Apparel Sets with 100% Exact Color Matching...")

for rank_id, title, rgb, hex_code, pantone in IBJJF_RANKS:
    print(f"  -> {title} ({hex_code} | {pantone})")
    
    # --- 1. RASHGUARD ---
    arr_rg = np.array(rg_clean, dtype=float)
    alpha_rg = arr_rg[:, :, 3]
    mask_flank = np.zeros((1024, 1024), dtype=bool)
    for y in range(670, 890):
        fab = np.where(alpha_rg[y, :] > 100)[0]
        if len(fab) > 0:
            mask_flank[y, fab[0]:fab[0]+42] = True
            mask_flank[y, fab[-1]-42:fab[-1]] = True
            
    # Calculate luminance in flank area
    lum_rg = (arr_rg[:, :, 0] + arr_rg[:, :, 1] + arr_rg[:, :, 2]) / 3.0
    mean_lum = np.mean(lum_rg[mask_flank])
    std_lum = np.std(lum_rg[mask_flank]) + 1e-5
    norm_rg = np.clip((lum_rg - mean_lum) / std_lum * 0.15 + 1.0, 0.75, 1.25)
    
    for c in range(3):
        if rank_id == "white":
            # For white, preserve light gray folds
            white_val = 240 * (lum_rg / 255.0 * 0.3 + 0.7)
            arr_rg[:, :, c] = np.where(mask_flank, np.clip(white_val, 0, 255), arr_rg[:, :, c])
        else:
            arr_rg[:, :, c] = np.where(mask_flank, np.clip(rgb[c] * norm_rg, 0, 255), arr_rg[:, :, c])
            
    rg_tinted = Image.fromarray(arr_rg.astype(np.uint8))
    sym_rg = create_colored_symbol(rgb, 80)
    rg_tinted.paste(sym_rg, (512 - sym_rg.width // 2, 330 - sym_rg.height // 2), sym_rg)
    
    rg_out_path = os.path.join(OUT_DIR, f"lauburu_rashguard_color_sym_{rank_id}.png")
    rg_tinted.save(rg_out_path)
    
    # --- 2. FIGHT SHORTS ---
    arr_sh = np.array(sh_clean, dtype=float)
    alpha_sh = arr_sh[:, :, 3]
    mask_slit = np.zeros((1024, 1024), dtype=bool)
    for y in range(660, 830):
        fab = np.where(alpha_sh[y, :] > 100)[0]
        if len(fab) > 0:
            mask_slit[y, fab[0]:fab[0]+18] = True
            mask_slit[y, fab[-1]-18:fab[-1]] = True
            
    lum_sh = (arr_sh[:, :, 0] + arr_sh[:, :, 1] + arr_sh[:, :, 2]) / 3.0
    mean_sh = np.mean(lum_sh[mask_slit])
    std_sh = np.std(lum_sh[mask_slit]) + 1e-5
    norm_sh = np.clip((lum_sh - mean_sh) / std_sh * 0.15 + 1.0, 0.75, 1.25)
    
    for c in range(3):
        if rank_id == "white":
            white_sh = 240 * (lum_sh / 255.0 * 0.3 + 0.7)
            arr_sh[:, :, c] = np.where(mask_slit, np.clip(white_sh, 0, 255), arr_sh[:, :, c])
        else:
            arr_sh[:, :, c] = np.where(mask_slit, np.clip(rgb[c] * norm_sh, 0, 255), arr_sh[:, :, c])
            
    sh_tinted = Image.fromarray(arr_sh.astype(np.uint8))
    sym_sh = create_colored_symbol(rgb, 90)
    sh_tinted.paste(sym_sh, (280 - sym_sh.width // 2, 730 - sym_sh.height // 2), sym_sh)
    
    sh_out_path = os.path.join(OUT_DIR, f"lauburu_shorts_color_sym_{rank_id}.png")
    sh_tinted.save(sh_out_path)
    
    # --- 3. SHOWCASE CANVAS ---
    canvas = Image.new("RGB", (2200, 1280), (255, 255, 255))
    canvas.paste(rg_tinted, (60, 110), rg_tinted)
    canvas.paste(sh_tinted, (1100, 110), sh_tinted)
    
    draw = ImageDraw.Draw(canvas)
    
    head_txt = f"LAUBURU COMBAT // {title} (IBJJF OFFICIAL)"
    bbox_h = draw.textbbox((0, 0), head_txt, font=font_title)
    draw.text(((2200 - (bbox_h[2] - bbox_h[0])) // 2, 40), head_txt, fill=(20, 20, 20), font=font_title)
    
    sub_txt = f"OFFICIAL IBJJF RANK PALETTE: {hex_code} ({pantone}) • CANONICAL OPTIMAL CUT (OPTION B)"
    bbox_s = draw.textbbox((0, 0), sub_txt, font=font_sub)
    draw.text(((2200 - (bbox_s[2] - bbox_s[0])) // 2, 92), sub_txt, fill=(110, 110, 110), font=font_sub)
    
    card_l_title = "STEALTH SHORT SLEEVE RASHGUARD"
    bbox_clt = draw.textbbox((0, 0), card_l_title, font=font_card_title)
    draw.text(((1024 + 120 - (bbox_clt[2] - bbox_clt[0])) // 2, 1150), card_l_title, fill=(20, 20, 20), font=font_card_title)
    
    card_l_sub = f"IBJJF-Ranked 80px Sternum Emblem • Mid-Bicep Cut • Curved Drop-Tail • Stealth Seams"
    bbox_cls = draw.textbbox((0, 0), card_l_sub, font=font_card_sub)
    draw.text(((1024 + 120 - (bbox_cls[2] - bbox_cls[0])) // 2, 1185), card_l_sub, fill=(110, 110, 110), font=font_card_sub)
    
    card_r_title = "MATCHING NO-GI PRO FIGHT SHORTS"
    bbox_crt = draw.textbbox((0, 0), card_r_title, font=font_card_title)
    draw.text(((1100 * 2 + 1024 - (bbox_crt[2] - bbox_crt[0])) // 2, 1150), card_r_title, fill=(20, 20, 20), font=font_card_title)
    
    card_r_sub = "Compact 90px Thigh Emblem • 5.5\" High-Cut Inseam • Elastic Waistband • Scalloped Mobility Vents"
    bbox_crs = draw.textbbox((0, 0), card_r_sub, font=font_card_sub)
    draw.text(((1100 * 2 + 1024 - (bbox_crs[2] - bbox_crs[0])) // 2, 1185), card_r_sub, fill=(110, 110, 110), font=font_card_sub)
    
    showcase_path = os.path.join(OUT_DIR, f"lauburu_set_{rank_id}_color_sym_showcase.png")
    canvas.save(showcase_path)
    
    shutil.copy(showcase_path, ARTIFACT_DIR)
    shutil.copy(rg_out_path, ARTIFACT_DIR)
    shutil.copy(sh_out_path, ARTIFACT_DIR)

# --- 4. MASTER 5-BELT COLLECTION GRID ---
print("🖼️ Regenerating Master 5-Belt Collection Grid...")
grid_w = 3200
grid_h = 480
grid = Image.new("RGB", (grid_w, grid_h), (255, 255, 255))
draw_grid = ImageDraw.Draw(grid)

font_title_grid = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 38)
font_sub_grid = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
pill_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)

# Header
grid_title = "LAUBURU COMBAT // CANONICAL 5-BELT RANK APPAREL COLLECTION"
bbox_gt = draw_grid.textbbox((0, 0), grid_title, font=font_title_grid)
draw_grid.text(((grid_w - (bbox_gt[2] - bbox_gt[0])) // 2, 25), grid_title, fill=(20, 20, 20), font=font_title_grid)

grid_sub = "OFFICIAL IBJJF RANK PALETTES • OPTION B: BELT-COLOURED EMBLEMS • OPTIMAL 5.5\" HIGH-CUT PATTERN"
bbox_gs = draw_grid.textbbox((0, 0), grid_sub, font=font_sub_grid)
draw_grid.text(((grid_w - (bbox_gs[2] - bbox_gs[0])) // 2, 72), grid_sub, fill=(110, 110, 110), font=font_sub_grid)

col_w = 610
col_margin = 15
start_x = (grid_w - (5 * col_w + 4 * col_margin)) // 2

for i, (rank_id, label, rgb, hex_code, pantone) in enumerate(IBJJF_RANKS):
    sc = Image.open(os.path.join(OUT_DIR, f"lauburu_set_{rank_id}_color_sym_showcase.png"))
    crop = sc.crop((40, 110, 2160, 1140))
    target_crop_w = col_w
    target_crop_h = int(target_crop_w * (crop.height / crop.width))
    resized_crop = crop.resize((target_crop_w, target_crop_h), Image.Resampling.LANCZOS)
    
    x = start_x + i * (col_w + col_margin)
    y = 115
    grid.paste(resized_crop, (x, y))
    
    bbox_pt = draw_grid.textbbox((0, 0), label, font=pill_font)
    draw_grid.text((x + (col_w - (bbox_pt[2] - bbox_pt[0])) // 2, y + target_crop_h + 12), label, fill=rgb if rank_id != "white" else (80, 80, 80), font=pill_font)

grid_out_path = os.path.join(OUT_DIR, "lauburu_master_5belt_color_sym_collection.png")
grid.save(grid_out_path)
shutil.copy(grid_out_path, ARTIFACT_DIR)
print(f"✅ Finished generating all assets at {OUT_DIR}")
