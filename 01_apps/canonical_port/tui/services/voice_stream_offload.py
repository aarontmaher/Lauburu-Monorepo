import socket
import asyncio
import logging

class VoiceStreamOffloader:
    """
    Captures raw audio from the Linux tablet microphone and streams it 
    over UDP to the Mac Mini host for continuous Wake-Word detection and STT.
    """
    def __init__(self, target_ip: str = "192.168.8.230", target_port: int = 12000):
        self.target_ip = target_ip
        self.target_port = target_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._running = False
        
    async def start_streaming(self):
        if self._running: return
        self._running = True
        
        logging.info(f"Starting Voice UDP Stream to {self.target_ip}:{self.target_port}")
        asyncio.create_task(self._capture_and_stream())
        
    def stop_streaming(self):
        self._running = False
        
    async def _capture_and_stream(self):
        # In a real environment, this reads from pyaudio or ALSA (arecord)
        # Here we mock the stream loop for the TUI architecture
        chunk_size = 4096
        mock_audio_data = b'\x00' * chunk_size
        
        while self._running:
            try:
                # Simulate audio capture latency
                await asyncio.sleep(0.1) 
                
                # Send to Mac Mini
                self.sock.sendto(mock_audio_data, (self.target_ip, self.target_port))
            except Exception as e:
                logging.error(f"UDP Stream Error: {e}")
                break
