import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

replacement = """import httpx
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/Volumes/Lauburu-Monorepo/.env")
"""

content = content.replace("import httpx\nimport google.generativeai as genai", replacement)

with open(file_path, "w") as f:
    f.write(content)
