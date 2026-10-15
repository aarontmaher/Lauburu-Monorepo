import requests
import json
import sys

URL = "http://127.0.0.1:8082/v1/chat/completions"

print("======================================================")
print("=== Lauburu Local Chat (prima.cpp / Qwen 3.8 Max) ===")
print("======================================================")
print("Type 'exit' or 'quit' to end.\\n")

messages = [
    {"role": "system", "content": "You are Qwen 3.8 Max, the Sovereign Master Local Orchestrator of the Lauburu Mesh Ecosystem."}
]

while True:
    try:
        user_input = input("You: ")
        if user_input.strip().lower() in ['exit', 'quit']:
            break
        if not user_input.strip():
            continue
            
        messages.append({"role": "user", "content": user_input})
        
        payload = {
            "model": "qwen_38_max",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
            "stream": False
        }
        
        response = requests.post(URL, json=payload)
        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content']
            print(f"\nAI: {reply}\n")
            messages.append({"role": "assistant", "content": reply})
        else:
            print(f"\n[!] API Error: {response.status_code}")
            print(response.text)
            messages.pop()
            
    except KeyboardInterrupt:
        break
    except requests.exceptions.ConnectionError:
        print(f"\n[!] Connection Error: Is prima.cpp running on {URL}?")
        messages.pop()
    except Exception as e:
        print(f"\n[!] Error: {e}")
        if messages[-1]["role"] == "user":
            messages.pop()
