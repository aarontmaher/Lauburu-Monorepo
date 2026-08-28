# Usage: mitmdump -s css_injection_addon.py --listen-port 8888
import json
import datetime
import os
from mitmproxy import http

SITE_OVERRIDES_DIR = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/dark_mode/site_overrides'
INJECTION_LOG = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/dark_mode/injection_log.jsonl'
WHITELIST = ['localhost', '192.168.', 'canonical_lauburu_symbol', 'lauburu.com']

UNIVERSAL_CSS = """
html { filter: invert(100%) hue-rotate(180deg) !important; }
img, video, canvas, svg, iframe { filter: invert(100%) hue-rotate(180deg) !important; }
"""

class DarkModeInjector:
    def response(self, flow: http.HTTPFlow):
        if not flow.response or not flow.response.headers.get("content-type", "").startswith("text/html"):
            return

        domain = flow.request.host
        
        is_whitelisted = any(w in domain for w in WHITELIST)
        if is_whitelisted:
            return

        algo = "universal"
        css_to_inject = UNIVERSAL_CSS
        
        override_path = os.path.join(SITE_OVERRIDES_DIR, f"{domain}.css")
        if os.path.exists(override_path):
            algo = "override"
            with open(override_path, 'r') as f:
                css_to_inject = f.read()

        html = flow.response.get_text()
        style_tag = f"<style>{css_to_inject}</style>"
        
        if "</head>" in html:
            html = html.replace("</head>", style_tag + "</head>", 1)
        elif "<body>" in html:
            html = html.replace("<body>", "<body>" + style_tag, 1)
            
        flow.response.set_text(html)

        log_entry = {
            "timestamp_utc": datetime.datetime.utcnow().isoformat(),
            "domain": domain,
            "algorithm": algo,
            "whitelisted": False
        }
        
        with open(INJECTION_LOG, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

addons = [DarkModeInjector()]
