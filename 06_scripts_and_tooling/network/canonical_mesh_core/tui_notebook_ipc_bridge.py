import zmq
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class TuiNotebookIPCBridge:
    """
    Robust IPC daemon proxy to stream TUI blackboard_store live mesh state 
    directly to Jupyter/Marimo notebooks via PyZMQ PULL/PUB.
    """
    def __init__(self, frontend_address="tcp://127.0.0.1:5554", backend_address="tcp://127.0.0.1:5555"):
        self.context = zmq.Context()
        self.frontend_address = frontend_address
        self.backend_address = backend_address
        self.running = False

    def run_daemon(self):
        """Run as a background daemon streaming state."""
        self.running = True
        
        frontend = self.context.socket(zmq.PULL)
        frontend.bind(self.frontend_address)
        
        backend = self.context.socket(zmq.PUB)
        backend.bind(self.backend_address)
        
        logging.info(f"TUI IPC Frontend (PULL) bound to {self.frontend_address}")
        logging.info(f"Notebook IPC Backend (PUB) bound to {self.backend_address}")
        
        try:
            zmq.proxy(frontend, backend)
        except zmq.ContextTerminated:
            pass
        except Exception as e:
            logging.error(f"Error in ZMQ proxy: {e}")
            
    def stop(self):
        self.running = False
        self.context.term()

if __name__ == "__main__":
    bridge = TuiNotebookIPCBridge()
    try:
        bridge.run_daemon()
    except KeyboardInterrupt:
        bridge.stop()
        logging.info("IPC Bridge stopped.")
