import urllib.request
import json
import sys
import os

DART_FILE = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/lauburu_showrunner/mobile_app/lib/main.dart"

with open(DART_FILE, 'r') as f:
    dart_code = f.read()

prompt = f"""
You are Qwen 2.5 Coder 7B, the Subordinate Syntax Worker.
Refactor the following Flutter code to create a highly optimized, cyberpunk-themed glassmorphic UI. 
- Use neon green (#00FF00) and hot pink (#FF00FF) accents.
- Make the background very dark (almost black).
- Add a glowing border or glassmorphic styling to the ListView container.
- Keep the WebSocket logic intact.
- Return ONLY the raw valid Dart code without markdown backticks.

```dart
{dart_code}
```
"""

data = {
    "model": "qwen2.5-coder-7b-instruct-q4_k_m",
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0.2,
    "max_tokens": 4096
}

req = urllib.request.Request(
    'http://127.0.0.1:8081/v1/chat/completions',
    data=json.dumps(data).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        code = result['choices'][0]['message']['content']
        # Strip backticks if present
        if code.startswith("```"):
            code = "\n".join(code.split("\n")[1:-1])
        
        with open(DART_FILE, 'w') as f:
            f.write(code)
        print("Success! Qwen 2.5 Coder 7B has optimized the UI.")
except Exception as e:
    print(f"Error calling Qwen Coder: {e}")
