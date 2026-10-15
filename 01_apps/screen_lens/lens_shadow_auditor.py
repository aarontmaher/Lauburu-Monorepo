import zmq
import json
import time

def evaluate_safety_with_shadow_ai(draft_action):
    """
    Simulates the Sovereign Master Orchestrator (Qwen 3.8 Max Abliterated on 8082)
    analyzing the drafted UI action to prevent catastrophic mistakes.
    """
    cmd = draft_action.get("proposed_command", "").lower()
    
    # Heuristic safety gates (In production, this routes to http://127.0.0.1:8082)
    unsafe_keywords = ["rm -rf", "delete", "factory_reset", "drop table", "reboot"]
    
    for word in unsafe_keywords:
        if word in cmd:
            return False, f"Shadow AI Blocked: Catastrophic keyword '{word}' detected."
            
    return True, "Shadow AI Approved: Action structurally safe."

def main():
    context = zmq.Context()
    
    # Listen to Drafts on the Broker Frontend
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://127.0.0.1:5555")
    subscriber.setsockopt(zmq.SUBSCRIBE, b"LENS.DRAFT_ACTION")
    
    # Publish Approvals to the Broker Backend
    publisher = context.socket(zmq.PUB)
    publisher.connect("tcp://127.0.0.1:5550")
    
    print("🛡️ Shadow AI Auditor Online. Intercepting LENS.DRAFT_ACTION...")
    
    while True:
        try:
            topic, payload = subscriber.recv_multipart()
            data = json.loads(payload.decode('utf-8'))
            
            print(f"\n[SHADOW] Intercepted Draft from {data.get('source')}: {data.get('proposed_command')}")
            
            is_safe, reason = evaluate_safety_with_shadow_ai(data)
            
            if is_safe:
                print(f"[SHADOW] ✅ {reason} Forwarding to execution.")
                data["audit_status"] = "APPROVED"
                data["shadow_reasoning"] = reason
                publisher.send_multipart([b"LENS.APPROVED_ACTION", json.dumps(data).encode('utf-8')])
            else:
                print(f"[SHADOW] ❌ {reason} Halting execution and logging penalty.")
                data["audit_status"] = "REJECTED"
                data["shadow_reasoning"] = reason
                # Publish to penalty topic for the LoRA optimizer to learn from the mistake
                publisher.send_multipart([b"LENS.REJECTED_ACTION", json.dumps(data).encode('utf-8')])
                
        except Exception as e:
            print(f"Shadow Auditor Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
