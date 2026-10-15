import zmq
import json
import subprocess

def execute_isolated_action(command, node):
    """
    Executes actions purely in the background via tmux to guarantee zero collision
    with the user's active desktop session.
    """
    print(f"\n[LENS BRAIN] Decision generated for node {node}: {command}")
    print(f"[LENS BRAIN] Executing in headless isolated tmux namespace...")
    
    tmux_cmd = [
        "tmux", "new-session", "-d", "-s", f"lens_isolated_{node}", 
        f"{command}; sleep 10"
    ]
    try:
        subprocess.run(tmux_cmd, check=True)
        print(f"[LENS BRAIN] Action successfully dispatched to background tmux session.")
    except Exception as e:
        print(f"[LENS BRAIN] Action dispatch failed: {e}")

def main():
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://127.0.0.1:5555")
    
    # Subscribe to ALL Lens edge sensors across the mesh
    subscriber.setsockopt(zmq.SUBSCRIBE, b"LENS.OBS")
    
    print("Omni-Lens Headless Brain started.")
    print("Listening for multi-device state changes on tcp://127.0.0.1:5555...")
    
    while True:
        try:
            topic, payload = subscriber.recv_multipart()
            topic_str = topic.decode()
            data = json.loads(payload.decode())
            
            node_id = topic_str.split('.')[-1]
            active_window = data.get("active_window", "Unknown")
            
            print(f"[{data['timestamp']}] {node_id} | Active: {active_window} | CPU: {data.get('cpu_load')}")
            
            # Example of an automated, collision-free background action:
            # If the user opens a specific app, Lens can background-fetch docs or prep a workspace
            if active_window == "Terminal":
                print(f"[LENS BRAIN] Detected Terminal on {node_id}. Speculatively preparing environment...")
                execute_isolated_action("echo 'Lens preemptively warming up terminal cache...'", node_id)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Brain error: {e}")

if __name__ == "__main__":
    main()
