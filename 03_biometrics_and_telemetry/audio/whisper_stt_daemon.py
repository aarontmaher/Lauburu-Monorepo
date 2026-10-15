import zmq
import json
import time
from datetime import datetime, timezone

# Optional/Lazy import so the daemon doesn't crash if faster-whisper isn't pip installed yet
try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

class SovereignWhisperPipeline:
    def __init__(self, broker_ip="127.0.0.1"):
        self.context = zmq.Context()
        
        # Subscribe to raw audio chunks or VAD triggers from the Pixel
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(f"tcp://{broker_ip}:5555")
        self.subscriber.setsockopt(zmq.SUBSCRIBE, b"DATA.VOICE.RAW_PCM")
        
        # Publish the finalized transcripts to the Mesh Brain
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.connect(f"tcp://{broker_ip}:5550")
        
        print("🎙️ Sovereign Whisper STT Pipeline Online.")
        if HAS_WHISPER:
            print("Loading faster-whisper model (tiny.en) on Metal Compute...")
            # Run on CPU/Metal depending on CTranslate2 MacOS support
            self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        else:
            print("WARNING: faster-whisper not installed. Running in simulation mode.")
            print("To fix: pip install faster-whisper")
            self.model = None

    def process_audio_to_text(self, pcm_data):
        if self.model:
            # In a real implementation, you'd buffer the PCM bytes into a numpy array / wav file
            # segments, info = self.model.transcribe(audio_file_path, beam_size=5)
            # return "".join([segment.text for segment in segments])
            return "Simulated transcription: Open Spotify and play jazz"
        else:
            return "Simulated transcription: Open Spotify and play jazz"

    def run(self):
        while True:
            try:
                topic, payload = self.subscriber.recv_multipart()
                
                print("\n[WHISPER] Received raw audio chunk. Processing STT...")
                transcript = self.process_audio_to_text(payload)
                
                print(f"[WHISPER] Transcript: '{transcript}'")
                
                out_payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "faster_whisper_mac_mini",
                    "intent_text": transcript
                }
                
                self.publisher.send_multipart([b"LENS.INTENT.VOICE", json.dumps(out_payload).encode('utf-8')])
                
            except Exception as e:
                print(f"Whisper Error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    pipeline = SovereignWhisperPipeline()
    pipeline.run()
