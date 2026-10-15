import time
import json
import httpx
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess

AVF_TINYLM_API = "http://10.86.187.34:8080/completion"
MACRODROID_WEBHOOK_PORT = 8085

async def optimize_macro(macro_data):
    """Feeds MacroDroid data to AVF TinyLM and fires Shizuku intent if optimization is found."""
    print(f"[MacroDroid Specialist] Analyzing: {macro_data}")
    payload = {
        "prompt": f"Analyze this MacroDroid trigger and suggest a faster UI sequence or intent: {macro_data}",
        "n_predict": 64
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(AVF_TINYLM_API, json=payload, timeout=5.0)
            suggestion = resp.json().get("content", "").strip()
            print(f"[TinyLM Optimization] {suggestion}")
            
            # Fire an intent back to MacroDroid via Shizuku (rish) to update/run optimized macro
            cmd = f"/data/data/com.termux/files/home/rish -c \"am broadcast -a com.arlosoft.macrodroid.action.OPTIMIZE -e optimized '{suggestion}'\""
            subprocess.run(cmd, shell=True, capture_output=True)
            
            # Auto-reconnect the Kai Morich terminal
            subprocess.run("/data/data/com.termux/files/home/rish -c 'am start -n de.kai_morich.serial_bluetooth_terminal/.MainActivity'", shell=True, capture_output=True)
            
    except Exception as e:
        print(f"[TinyLM] Offline or Timeout: {e}")

class MacroDroidHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        asyncio.run(optimize_macro(post_data))
        self.send_response(200)
        self.end_headers()

def run_server():
    server_address = ('127.0.0.1', MACRODROID_WEBHOOK_PORT)
    httpd = HTTPServer(server_address, MacroDroidHandler)
    print(f"[MacroDroid Specialist] Webhook server active on Port {MACRODROID_WEBHOOK_PORT}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
