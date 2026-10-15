#!/usr/bin/env python3
"""
Screen Lens Sovereign & E-Commerce Models: Marketplace Listing Photo Analysis
Queries Qwen 3.8 Max (8082) and Qwen 3.8 Max Abliterated (8083) to benchmark
photo presentation on Gumtree, eBay Australia, and Facebook Marketplace.
"""
import urllib.request
import json
import time

prompt = """
You are the Lead E-Commerce Conversion Specialist and Screen Lens Sovereign Market Auditor for high-value consumer electronics (specifically Apple iPhone 16 Pro 512GB) on Australian platforms: Gumtree Australia, Facebook Marketplace, and eBay Australia.

The user asked:
"no the text looks bad - is that normal to have on these apps? /screen-lens-sovereign and e commerce models use lens to analyse other listings on phones and create suggestions"

Analyze the following:
1. Is having digital text overlays, graphic badges, marketing banners, or infographic cards normal on Gumtree, Facebook Marketplace, or eBay for smartphones?
   - What does eBay's official Picture Policy state about watermarks, borders, and text overlays?
   - How do private buyers on Gumtree and Facebook Marketplace perceive listings with marketing text overlays vs. raw, authentic photos?
2. What does the photo gallery of a top 1% sold/high-conversion private listing look like? (List the exact sequence of 5-6 photos that genuine buyers expect).
3. How should cosmetic screen flaws (such as an outer bezel dead pixel cluster) be photographed to build maximum trust, avoid disputes, and close sales quickly?
4. What are the specific, actionable instructions for the seller to capture winning photos today using their smartphone in 2 minutes?

Provide a sharp, authoritative, empirical analysis.
"""

payload = json.dumps({
    "model": "qwen_38_max_abliterated",
    "messages": [
        {"role": "system", "content": "You are the Sovereign Master E-Commerce Conversion Strategist and Market Auditor."},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.2,
    "max_tokens": 1200
}).encode("utf-8")

req = urllib.request.Request("http://127.0.0.1:8082/v1/chat/completions", data=payload, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(res["choices"][0]["message"]["content"])
except Exception as e:
    print(f"Error querying local model: {e}")
