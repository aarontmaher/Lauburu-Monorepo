import asyncio
import websockets
import socket
import logging

logging.basicConfig(level=logging.INFO)

HTML = """<!DOCTYPE html>
<html>
<head><title>Lauburu Voice Coder</title></head>
<body style="background:#000;color:#0f0;font-family:monospace;text-align:center;padding:50px;">
    <h1>Lauburu Mesh Mic</h1>
    <button id="start" style="padding:20px;font-size:24px;background:#0f0;color:#000;border:none;border-radius:10px;">START MIC</button>
    <div id="status" style="margin-top:20px;">Waiting...</div>
    <script>
        let ws;
        document.getElementById('start').onclick = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                ws = new WebSocket(`ws://${location.host}/ws`);
                ws.onopen = () => {
                    document.getElementById('status').innerText = "Streaming to Mac Mini...";
                    const audioContext = new AudioContext({ sampleRate: 16000 });
                    const source = audioContext.createMediaStreamSource(stream);
                    const processor = audioContext.createScriptProcessor(4096, 1, 1);
                    
                    source.connect(processor);
                    processor.connect(audioContext.destination);
                    
                    processor.onaudioprocess = (e) => {
                        const float32Array = e.inputBuffer.getChannelData(0);
                        const int16Array = new Int16Array(float32Array.length);
                        for (let i = 0; i < float32Array.length; i++) {
                            int16Array[i] = Math.max(-32768, Math.min(32767, float32Array[i] * 32768));
                        }
                        if (ws.readyState === WebSocket.OPEN) {
                            ws.send(int16Array.buffer);
                        }
                    };
                };
            } catch (err) {
                document.getElementById('status').innerText = "Error: " + err.message;
            }
        };
    </script>
</body>
</html>
"""

from aiohttp import web

async def handle_root(request):
    return web.Response(text=HTML, content_type='text/html')

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    logging.info("Browser connected to mic bridge")
    
    # Connect to Mac Mini Mic Receiver
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        tcp_sock.connect(("127.0.0.1", 19999))
        logging.info("Connected to local Port 19999")
    except Exception as e:
        logging.error(f"Failed to connect to 19999: {e}")
        return ws

    async for msg in ws:
        if msg.type == web.WSMsgType.BINARY:
            try:
                tcp_sock.sendall(msg.data)
            except Exception as e:
                logging.error(f"TCP send error: {e}")
                break

    tcp_sock.close()
    return ws

app = web.Application()
app.add_routes([web.get('/', handle_root), web.get('/ws', websocket_handler)])

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=19998)
