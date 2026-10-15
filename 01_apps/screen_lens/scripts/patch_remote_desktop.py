import re
from pathlib import Path

file_path = Path("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/sovereign_remote_desktop_server.py")
content = file_path.read_text()

# Fix screencapture absolute path
content = content.replace('"screencapture", "-x"', '"/usr/sbin/screencapture", "-x"')

# Extract the get_single_frame inner logic to a helper function
get_frame_logic = """
async def get_single_frame_data(target: str) -> bytes:
    if target in ["l1_mac_mini", None]:
        return latest_frame
    if target == "l7_samsung":
        serial = get_adb_serial_for_node("l7_samsung")
        if serial:
            try:
                await asyncio.to_thread(subprocess.run, ["adb", "-s", serial, "shell", "input", "keyevent", "4"], capture_output=True, timeout=1.5)
                res = await asyncio.to_thread(subprocess.run, ["adb", "-s", serial, "exec-out", "screencap", "-p"], capture_output=True, timeout=4.0)
                if res.returncode == 0 and len(res.stdout) > 5000:
                    return res.stdout
            except Exception as e:
                logger.warning(f"S20 frame capture error: {e}")
    elif target in ["l2_macbook_pro", "l5_macbook_air"]:
        host = NODES.get(target, {}).get("ssh_host", "macbook-pro")
        try:
            res = await asyncio.to_thread(subprocess.run, ["ssh", "-o", "ConnectTimeout=3", host, "screencapture -x -t jpg /tmp/mbp_screen.jpg && cat /tmp/mbp_screen.jpg"], capture_output=True, timeout=5.0)
            if res.returncode == 0 and len(res.stdout) > 5000: return res.stdout
        except: pass
    elif target in ["l3_linux", "l4_tablet", "l6_pixel"]:
        host = NODES.get(target, {}).get("ssh_host", "linux-ts")
        if target == "l6_pixel": host = "pixel"
        try:
            if target == "l6_pixel":
                res = await asyncio.to_thread(subprocess.run, ["ssh", "-o", "ConnectTimeout=3", host, "screencap -p"], capture_output=True, timeout=5.0)
            else:
                py_cmd = "python3 -c 'from PIL import Image; raw = open(\"/dev/fb0\", \"rb\").read(1920*1080*4); img = Image.frombytes(\"RGBA\", (1920, 1080), raw, \"raw\", \"BGRA\"); import io, sys; buf = io.BytesIO(); img.convert(\"RGB\").save(buf, \"JPEG\", quality=80); sys.stdout.buffer.write(buf.getvalue())'"
                res = await asyncio.to_thread(subprocess.run, ["ssh", "-o", "ConnectTimeout=3", host, py_cmd], capture_output=True, timeout=5.0)
            if res.returncode == 0 and len(res.stdout) > 5000: return res.stdout
        except: pass
    return latest_frame

@app.get("/api/frame")
@app.get("/frame.jpg")
@app.get("/api/node/{node_id}/frame")
async def get_single_frame(request: Request, node_id: str = None):
    target = node_id or request.query_params.get("node", active_node)
    data = await get_single_frame_data(target)
    return Response(content=data, media_type="image/jpeg" if target != "l7_samsung" and target != "l6_pixel" else "image/png", headers={"Cache-Control": "no-cache"})
"""

# Replace the old get_single_frame
content = re.sub(r'@app\.get\("/api/frame"\).*?# Fallback to local live frame\n    return Response[^\n]+\n', get_frame_logic + "\n", content, flags=re.DOTALL)


# Fix the stream.mjpg endpoint to support node switching
stream_logic = """
@app.get("/stream.mjpg")
async def stream_mjpg(request: Request):
    async def frame_generator():
        try:
            sub_q = broadcaster.subscribe()
            yield (b"--frame\\r\\nContent-Type: image/jpeg\\r\\nContent-Length: " + str(len(latest_frame)).encode() + b"\\r\\n\\r\\n" + latest_frame + b"\\r\\n")
            
            while True:
                if await request.is_disconnected(): break
                if active_node == "l1_mac_mini":
                    frame = await sub_q.get()
                    yield (b"--frame\\r\\nContent-Type: image/jpeg\\r\\nContent-Length: " + str(len(frame)).encode() + b"\\r\\n\\r\\n" + frame + b"\\r\\n")
                else:
                    frame = await get_single_frame_data(active_node)
                    if frame:
                        yield (b"--frame\\r\\nContent-Type: image/jpeg\\r\\nContent-Length: " + str(len(frame)).encode() + b"\\r\\n\\r\\n" + frame + b"\\r\\n")
                    await asyncio.sleep(0.5)
        except asyncio.CancelledError: pass
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")
"""
content = re.sub(r'@app\.get\("/stream\.mjpg"\).*?return StreamingResponse[^\n]+\n', stream_logic + "\n", content, flags=re.DOTALL)


# Fix HTML node-selector to use JavaScript template literal from NODES
html_fix = """
    <!-- Central Control / Target Selector -->
    <div class="flex items-center space-x-2">
      <select id="node-selector" class="bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 font-mono focus:outline-none focus:border-sky-500" onchange="changeNode(this.value)">
        <option value="l1_mac_mini">L1: Mac Mini (M4 Pro Host)</option>
        <option value="l2_macbook_pro">L2: MacBook Pro (Intel Core i7)</option>
        <option value="l3_linux">L3: Linux Head Node (AMD Ryzen 7)</option>
        <option value="l4_tablet">L4: Linux Tablet (Debian)</option>
        <option value="l5_macbook_air">L5: MacBook Air (M4)</option>
        <option value="l6_pixel">L6: Pixel 10 Pro XL</option>
        <option value="l7_samsung">L7: Samsung S20+</option>
      </select>
"""
content = re.sub(r'<!-- Central Control / Target Selector -->.*?</select>', html_fix, content, flags=re.DOTALL)

# Also fix changeNode to update the img src just in case it stalls
content = content.replace("async function changeNode(node) {", """async function changeNode(node) {
      document.getElementById('screen-stream').src = '/stream.mjpg?r=' + Math.random();""")

file_path.write_text(content)
print("Patched sovereign_remote_desktop_server.py")
