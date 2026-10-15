#!/usr/bin/env python3
import sys
import base64
from io import BytesIO
try:
    from PIL import Image
except ImportError:
    print("[!] Pillow not installed. Please install it.")
    sys.exit(1)

def precision_crop(image_path, x1, y1, x2, y2, out_path=None):
    """
    Crops an image exactly to the bounding box of a WebGL/Canvas element.
    Returns the base64 encoded cropped image to be sent to a Vision Language Model (VLM),
    saving up to 90% in token costs compared to full screen transmission.
    """
    try:
        with Image.open(image_path) as img:
            # Ensure coordinates are within bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img.width, x2), min(img.height, y2)
            
            cropped = img.crop((x1, y1, x2, y2))
            
            if out_path:
                cropped.save(out_path)
                print(f"[*] Precision crop saved to {out_path}")
            
            # Convert to base64 for VLM transmission
            buffered = BytesIO()
            cropped.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            print(f"[*] Crop size: {cropped.width}x{cropped.height} ({len(img_str)} bytes base64)")
            return img_str
            
    except Exception as e:
        print(f"[!] Error cropping image: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: vlm_cropper.py [image_path] [x1] [y1] [x2] [y2] [optional_out_path]")
        sys.exit(1)
        
    img_path = sys.argv[1]
    x1, y1, x2, y2 = map(int, sys.argv[2:6])
    out_path = sys.argv[6] if len(sys.argv) > 6 else None
    
    b64 = precision_crop(img_path, x1, y1, x2, y2, out_path)
