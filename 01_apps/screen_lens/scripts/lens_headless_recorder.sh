#!/bin/bash
DURATION=${1:-5}
OUTPUT=${2:-"/Users/aaron/Desktop/Lens_VLA_Record.mp4"}
FPS=2
TOTAL_FRAMES=$((DURATION * FPS))
TMP_DIR="/tmp/lens_frames_$$"

mkdir -p "$TMP_DIR"
echo "📸 Screen Lens Headless Recorder Active. Compiling $DURATION seconds of video..."

for (( i=1; i<=TOTAL_FRAMES; i++ ))
do
    FRAME_NUM=$(printf "%03d" $i)
    # Correctly quoted AppleScript, run synchronously to avoid Apple Event overloading
    osascript -e "tell application \"System Events\" to do shell script \"/usr/sbin/screencapture -x -t jpg -C $TMP_DIR/frame_$FRAME_NUM.jpg\""
    sleep 0.1
done

echo "🎞️ Stitching frames via FFmpeg..."
ffmpeg -y -framerate $FPS -i "$TMP_DIR/frame_%03d.jpg" \
    -c:v libx264 -pix_fmt yuv420p -preset ultrafast \
    -loglevel warning "$OUTPUT"

rm -rf "$TMP_DIR"
echo "✅ Video compiled and saved to: $OUTPUT"
