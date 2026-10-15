import zmq
context = zmq.Context()
subscriber = context.socket(zmq.SUB)
subscriber.connect("tcp://127.0.0.1:5555")
subscriber.setsockopt(zmq.SUBSCRIBE, b"LORA.DATASET")
print("Subscriber connected. Waiting for Life Companion Payload...")
topic, message = subscriber.recv_multipart()
print(f"RECEIVED ON {topic.decode()}:\n{message.decode()}")
