import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys

def heal_mesh_background():
    try:
        print("[HEAL] Executing Mesh Healing Routine...", flush=True)
        subprocess.run(["python3", "/Volumes/Lauburu-Monorepo/06_scripts_and_tooling/notifications/mesh_cross_device_chat_agent.py", "--send"])
        print("[HEAL] Mesh Healing Complete.", flush=True)
    except Exception as e:
        print(f"[HEAL ERROR] {e}", flush=True)

class GoogleChatHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            print(f"Received from Google Chat: {payload.get('type')}", flush=True)
            
            response_data = {"text": "Acknowledged."}
            
            if payload.get("type") == "ADDED_TO_SPACE":
                response_data = {"text": "Hello! I am the Lauburu Mesh Two-Way Bot. Type `@Mesh heal the mesh` to trigger a system resurrection."}
                
            elif payload.get("type") == "MESSAGE":
                message_text = payload.get("message", {}).get("text", "").lower()
                if "heal the mesh" in message_text or "heal" in message_text:
                    threading.Thread(target=heal_mesh_background, daemon=True).start()
                    response_data = {"text": "🩺 **Mesh Healing Protocol Initiated...** \nWaking up offline nodes and sweeping telemetry. (Card will follow shortly)."}
                else:
                    response_data = {"text": "Unrecognized command. Try `@Mesh heal the mesh`."}
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        except Exception as e:
            print(f"Error handling POST: {e}", flush=True)
            self.send_response(500)
            self.end_headers()

if __name__ == "__main__":
    server_address = ('', 8090)
    httpd = HTTPServer(server_address, GoogleChatHandler)
    print("Starting Lauburu Google Chat App Listener on port 8090...", flush=True)
    httpd.serve_forever()
