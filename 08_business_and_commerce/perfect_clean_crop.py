from PIL import Image, ImageEnhance
from pathlib import Path

ASSETS_DIR = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/08_business_and_commerce/assets")
CLEAN_DIR = ASSETS_DIR / "clean_marketplace"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
brain_dir = Path("/Users/aaron/.gemini/antigravity/brain/cdca10c9-e3ec-4303-aabd-7860383dd9a8")

src_front = ASSETS_DIR / "iphone_16_pro_512gb_front.jpg"
src_screen = ASSETS_DIR / "iphone_16_pro_512gb_screen.jpg"

im_front = Image.open(src_front).convert("RGB")
im_screen = Image.open(src_screen).convert("RGB")

# 1. Front Hero Shot: Rotate slightly and crop tightly around phone with clean table margins
# Table in original: left=165, right=575, top=160, bottom=985 (phone is ~410 wide, 825 high)
# To avoid the bottom-left rotated black corner, keep crop_y2 at 985 and crop_x1 at 120
rot = im_front.rotate(2.8, resample=Image.BICUBIC, expand=True)
clean_front = rot.crop((115, 120, 625, 990))

# Gentle photographic adjustment: natural lighting, balanced contrast, zero artificial look
clean_front = ImageEnhance.Contrast(clean_front).enhance(1.05)
clean_front = ImageEnhance.Sharpness(clean_front).enhance(1.15)

front_path = CLEAN_DIR / "01_iphone_16_pro_front.jpg"
clean_front.save(front_path, quality=96)
clean_front.save(brain_dir / "01_iphone_16_pro_front.jpg", quality=96)
print(f"Saved {front_path} ({clean_front.size})")

# 2. Bezel Flaw Macro: 100% natural, unedited close-up
macro_path = CLEAN_DIR / "02_iphone_16_pro_bezel_detail.jpg"
im_screen.save(macro_path, quality=96)
im_screen.save(brain_dir / "02_iphone_16_pro_bezel_detail.jpg", quality=96)
print(f"Saved {macro_path} ({im_screen.size})")
