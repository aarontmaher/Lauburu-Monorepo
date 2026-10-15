import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import datetime
from pathlib import Path

ARTIFACT_PATH = "/Users/aaron/.gemini/antigravity/brain/cdca10c9-e3ec-4303-aabd-7860383dd9a8/ad_metrics.md"
metrics = {"fb": {"clicks": "0", "status": "Waiting for ping..."}, "ebay": {"views": "0", "watchers": "0", "status": "Waiting for ping..."}}

class HTTPServerV6(HTTPServer):
    address_family = socket.AF_INET6

class MetricsHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            source = data.get("source")
            if source == "facebook":
                metrics["fb"]["clicks"] = data.get("clicks", "0")
                metrics["fb"]["status"] = "Active"
            elif source == "ebay":
                metrics["ebay"]["views"] = data.get("views", "0")
                metrics["ebay"]["watchers"] = data.get("watchers", "0")
                metrics["ebay"]["status"] = "Active"
                
            self._write_artifact()
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        except Exception as e:
            print(f"Error parsing POST: {e}")
            self.send_response(400)
            self.end_headers()
            
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass # Silent logging

    def _write_artifact(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        md_content = f"""# 📊 Live Ad Campaign Metrics
*Last Updated: {now}*

> [!NOTE]
> This artifact is updated automatically by the continuous background daemon injected into the live browser tabs.

### 🔵 Facebook Marketplace (iPhone 16 Pro Max)
* **Status:** {metrics["fb"]["status"]}
* **Listing Clicks:** {metrics["fb"]["clicks"]}

### 🟡 eBay Australia (iPhone 16 Pro)
* **Status:** {metrics["ebay"]["status"]}
* **Views:** {metrics["ebay"]["views"]}
* **Watchers:** {metrics["ebay"]["watchers"]}
"""
        Path(ARTIFACT_PATH).write_text(md_content)

if __name__ == "__main__":
    server_address = ('::', 3103)
    httpd = HTTPServerV6(server_address, MetricsHandler)
    print("Metrics server running on [::]:3103...")
    httpd.serve_forever()
