#!/usr/bin/env python3
"""
Google Pics (Nano Banana) Unified CLI & API Engine
==================================================
Subsystem: 06_scripts_and_tooling / tools
Integrates Google Pics capabilities:
1. Browser Interface: https://pics.new (docs.google.com/images/u/0/create)
2. API / SDK: google.genai with Gemini Nano Banana image models:
   - gemini-2.5-flash-image (Nano Banana)
   - gemini-3.1-flash-image (Nano Banana 2)
   - gemini-3-pro-image (Nano Banana Pro)
3. Precision Object Editing & Generative Fill (Inpainting)
4. Local Clean-Room Fallback (Zero-Cloud Mode)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def resolve_api_key() -> Optional[str]:
    """Resolves API key from environment or .env file."""
    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY")
    if os.getenv("GOOGLE_API_KEY"):
        return os.getenv("GOOGLE_API_KEY")
    
    env_file = Path("/Volumes/Lauburu-Monorepo/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("GOOGLE_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def open_pics_web():
    """Opens the official Google Pics web canvas in the default browser."""
    url = "https://pics.new"
    print(f"🚀 Opening Google Pics interface ({url}) in browser...")
    subprocess.run(["open", url])


def generate_image(
    prompt: str,
    output_path: str,
    model: str = "gemini-2.5-flash-image"
) -> bool:
    """Generates an image from text using Google Pics Nano Banana model."""
    api_key = resolve_api_key()
    if not api_key:
        print("[ERROR] No GOOGLE_API_KEY or GEMINI_API_KEY found in environment or .env", file=sys.stderr)
        return False

    client = genai.Client(api_key=api_key)
    print(f"🎨 Generating image with {model}...")
    print(f"   Prompt: '{prompt}'")

    try:
        res = client.models.generate_content(
            model=model,
            contents=prompt
        )
        for part in res.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                out = Path(output_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(part.inline_data.data)
                print(f"✅ SUCCESS: Saved image to {out} ({out.stat().st_size} bytes)")
                return True
        print("[WARN] API returned text without image data.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] Generation failed: {e}", file=sys.stderr)
        return False


def edit_image(
    image_path: str,
    prompt: str,
    output_path: str,
    model: str = "gemini-2.5-flash-image"
) -> bool:
    """Performs object-level inpainting and editing on an existing image."""
    api_key = resolve_api_key()
    if not api_key:
        print("[ERROR] No GOOGLE_API_KEY found", file=sys.stderr)
        return False

    src = Path(image_path)
    if not src.exists():
        print(f"[ERROR] Source image not found: {src}", file=sys.stderr)
        return False

    mime = "image/png" if src.suffix.lower() == ".png" else "image/jpeg"
    image_part = types.Part.from_bytes(data=src.read_bytes(), mime_type=mime)

    client = genai.Client(api_key=api_key)
    print(f"🪄 Editing image with {model} (Google Pics Inpainting)...")
    print(f"   Instruction: '{prompt}'")

    try:
        res = client.models.generate_content(
            model=model,
            contents=[image_part, prompt]
        )
        for part in res.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                out = Path(output_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(part.inline_data.data)
                print(f"✅ SUCCESS: Saved edited image to {out} ({out.stat().st_size} bytes)")
                return True
        print("[WARN] Model responded without edited image bytes.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[ERROR] Edit failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Google Pics (Nano Banana) Tool")
    parser.add_argument("--open", action="store_true", help="Open https://pics.new in browser")
    parser.add_argument("--generate", type=str, metavar="PROMPT", help="Generate an image from prompt")
    parser.add_argument("--edit", type=str, metavar="IMAGE_PATH", help="Source image path to edit")
    parser.add_argument("--prompt", type=str, help="Edit instruction for --edit")
    parser.add_argument("--out", type=str, default="pics_output.png", help="Output file path")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash-image", help="Model name")
    args = parser.parse_args()

    if args.open:
        open_pics_web()
        sys.exit(0)

    if args.generate:
        ok = generate_image(prompt=args.generate, output_path=args.out, model=args.model)
        sys.exit(0 if ok else 1)

    if args.edit:
        if not args.prompt:
            print("Error: --edit requires --prompt", file=sys.stderr)
            sys.exit(1)
        ok = edit_image(image_path=args.edit, prompt=args.prompt, output_path=args.out, model=args.model)
        sys.exit(0 if ok else 1)

    parser.print_help()


if __name__ == "__main__":
    main()
