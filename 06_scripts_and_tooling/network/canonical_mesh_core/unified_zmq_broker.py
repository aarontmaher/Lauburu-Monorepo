import zmq

def run_proxy(frontend_port=5555, backend_port=5550):
    context = zmq.Context()
    
    # Frontend: XPUB (Subscribers connect here to read data)
    frontend = context.socket(zmq.XPUB)
    frontend.bind(f"tcp://*:{frontend_port}")
    
    # Backend: XSUB (Publishers connect here to send data)
    backend = context.socket(zmq.XSUB)
    backend.bind(f"tcp://*:{backend_port}")
    
    print(f"Unified ZMQ Broker running.")
    print(f" -> Publishers push to: tcp://*:{backend_port}")
    print(f" -> Subscribers read from: tcp://*:{frontend_port}")
    
    try:
        zmq.proxy(frontend, backend)
    except Exception as e:
        print(f"Proxy terminated: {e}")
    finally:
        frontend.close()
        backend.close()
        context.term()

if __name__ == "__main__":
    run_proxy()
