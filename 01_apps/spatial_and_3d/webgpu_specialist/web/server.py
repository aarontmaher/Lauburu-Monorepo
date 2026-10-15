#!/usr/bin/env python3
"""WebGPU Spatial Visualizer HTTP Server on Port 8090."""

import http.server
import socketserver
import os
from pathlib import Path

PORT = int(os.getenv("PORT", "8090"))
WEB_DIR = Path(__file__).parent.resolve()

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        # Add COOP/COEP headers for SharedArrayBuffer / WebGPU Wasm multithreading
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🚀 Lauburu WebGPU 3D Spatial Visualizer serving on http://0.0.0.0:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
