#!/data/data/com.termux/files/usr/bin/bash
# Samsung S20 Voice Coding Streamer (Termux)
# Captures ambient mic continuously and streams raw 16kHz PCM to the Mac Mini
# Audio Receiver for HeyNeo transcription and Screen Lens execution.

MAC_MINI_IP="192.168.8.230"
PORT="19999"

echo "🎙️ Starting Samsung S20 Ambient Voice Coder..."
echo "🔗 Streaming to Mac Mini Audio Receiver at TCP $MAC_MINI_IP:$PORT"

# Ensure wakelock to prevent Android 15 Doze
termux-wake-lock

# Setup FIFO pipe for continuous streaming
rm -f /data/local/tmp/samsung_mic_pipe
mkfifo /data/local/tmp/samsung_mic_pipe

# Start recording continuously into the pipe (in the background)
echo "[*] Initializing termux-microphone-record..."
termux-microphone-record -d -f /data/local/tmp/samsung_mic_pipe &
REC_PID=$!

# Stream the pipe via ffmpeg (converting to 16kHz 16-bit Mono PCM) and send via Netcat
echo "[*] Connecting to TCP Port $PORT..."
ffmpeg -y -i /data/local/tmp/samsung_mic_pipe -f s16le -acodec pcm_s16le -ar 16000 -ac 1 pipe:1 2>/dev/null | nc $MAC_MINI_IP $PORT

# Cleanup on exit
kill $REC_PID 2>/dev/null
rm -f /data/local/tmp/samsung_mic_pipe
echo "🛑 Stream ended."
