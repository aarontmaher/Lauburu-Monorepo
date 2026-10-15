import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess

MODEL_PATH = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/router_governor_fused"

class GovernorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        diag = data.get("diag", "")
        print(f"\n[GOVERNOR] Received Distress Signal from Router:\n{diag}")
        
        prompt = f"<|im_start|>system\nYou are the Autonomous Mesh Governor running on an OpenWrt GL.iNet router. When a node connection fails, output a strict JSON object with 'diagnosis' and 'healing_chain'. The healing_chain must escalate starting from the lowest required physical layer.<|im_end|>\n<|im_start|>user\n{diag}<|im_end|>\n<|im_start|>assistant\n"
        
        cmd = [
            "python3", "-m", "mlx_lm.generate", 
            "--model", MODEL_PATH, 
            "--max-tokens", "300", 
            "--temp", "0.0", 
            "--prompt", prompt
        ]
        
        res = subprocess.run(cmd, capture_output=True, text=True)
        try:
            output_lines = res.stdout.split("==========")
            generated_json = output_lines[1].strip()
        except:
            generated_json = '{"diagnosis": "Model execution error.", "healing_chain": []}'
            
        print(f"[GOVERNOR] Replied with Healing Chain:\n{generated_json}")
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(generated_json.encode('utf-8'))

def run(server_class=HTTPServer, handler_class=GovernorHandler, port=19004):
    server_address = ('0.0.0.0', port)
    httpd = server_class(server_address, handler_class)
    print(f"🔥 Lauburu Mesh Governor Active! Listening on port {port}...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
