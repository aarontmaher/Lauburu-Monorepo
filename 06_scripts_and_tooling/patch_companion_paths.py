import sys
import os
import re

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

replacement = """import os
import sys
import time
import sqlite3
import datetime
import threading
import logging
import asyncio
import json
import re
import psutil
from flask import Flask, jsonify, request
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

IS_TERMUX = "PREFIX" in os.environ and "com.termux" in os.environ.get("PREFIX", "")
HOME = os.path.expanduser("~")

if IS_TERMUX:
    DB_PATH = f"{HOME}/.lauburu/screen_lens.sqlite"
    ENV_PATH = f"{HOME}/Lauburu-Monorepo/.env"
    HANDOFF_SCRIPT = f"{HOME}/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py"
else:
    DB_PATH = "/Users/aaron/.lauburu/screen_lens.sqlite"
    ENV_PATH = "/Volumes/Lauburu-Monorepo/.env"
    HANDOFF_SCRIPT = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py"

load_dotenv(ENV_PATH)
"""

content = re.sub(
    r"import os.*?load_dotenv\(\"/Volumes/Lauburu-Monorepo/\.env\"\)",
    replacement,
    content,
    flags=re.DOTALL
)

# Also fix the subprocess.Popen call to use HANDOFF_SCRIPT
content = content.replace(
    'subprocess.Popen(["python3", "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/bt_ai_handoff_worker.py", "0", tm["content"]], start_new_session=True)',
    'subprocess.Popen(["python3", HANDOFF_SCRIPT, "0", tm["content"]], start_new_session=True)'
)

with open(file_path, "w") as f:
    f.write(content)
