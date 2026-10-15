import zmq
import json
import time
import os

LORA_DATASET_PATH = "/Users/aaron/DFS_UNIFIED/lora_datasets/proven_accuracy_vla_dataset.jsonl"

def format_lora_instruction(data, success):
    """
    Formats the raw ZMQ observation and action into an OpenAI/ChatML compatible
    instruction-tuning pair for LoRA training.
    """
    system_prompt = "You are a headless VLA orchestrating a mesh topology. Output precise commands."
    user_prompt = f"Observation: {data.get('observation', 'Unknown state')}"
    
    if success:
        assistant_response = f"EXECUTE: {data.get('proposed_command')}"
    else:
        assistant_response = f"ABORT: {data.get('shadow_reasoning')}"
        
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ],
        "metadata": {
            "source": data.get("source"),
            "timestamp": data.get("timestamp"),
            "audit_status": data.get("audit_status")
        }
    }

def main():
    os.makedirs(os.path.dirname(LORA_DATASET_PATH), exist_ok=True)
    
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://127.0.0.1:5555")
    
    # Subscribe to both APPROVED (Success) and REJECTED (Failure) actions
    subscriber.setsockopt(zmq.SUBSCRIBE, b"LENS.APPROVED_ACTION")
    subscriber.setsockopt(zmq.SUBSCRIBE, b"LENS.REJECTED_ACTION")
    
    print(f"🧬 Continuous LoRA Harvester Online. Appending to {LORA_DATASET_PATH}")
    
    while True:
        try:
            topic, payload = subscriber.recv_multipart()
            topic_str = topic.decode('utf-8')
            data = json.loads(payload.decode('utf-8'))
            
            success = (topic_str == "LENS.APPROVED_ACTION")
            lora_pair = format_lora_instruction(data, success)
            
            with open(LORA_DATASET_PATH, 'a') as f:
                f.write(json.dumps(lora_pair) + "\n")
                
            status_emoji = "✅" if success else "❌ (Negative Reward)"
            print(f"[LORA] {status_emoji} Harvested execution. Appended to dataset.")
                
        except Exception as e:
            print(f"LoRA Harvester Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
