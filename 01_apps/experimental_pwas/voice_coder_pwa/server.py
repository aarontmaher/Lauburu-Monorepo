from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import subprocess
import uvicorn
import os
from pydantic import BaseModel

app = FastAPI(title="Voice Coder PWA")

class VoiceCommand(BaseModel):
    prompt: str

@app.post("/api/voice-command")
async def execute_voice_command(cmd: VoiceCommand):
    try:
        script_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/in_car_voice_coder.py"
        # Run the python script with the prompt
        res = subprocess.run(
            ["python3", script_path, "--prompt", cmd.prompt],
            capture_output=True, text=True, timeout=15
        )
        if res.returncode == 0:
            import json
            # The script prints json to stdout
            # We'll extract the JSON part
            output = res.stdout.strip()
            # find first '{' and last '}'
            start = output.find('{')
            end = output.rfind('}')
            if start != -1 and end != -1:
                json_str = output[start:end+1]
                data = json.loads(json_str)
                return JSONResponse(data)
            return JSONResponse({"error": "Failed to parse JSON", "raw": output}, status_code=500)
        else:
            return JSONResponse({"error": res.stderr}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Serve PWA static files
app.mount("/", StaticFiles(directory="public", html=True), name="public")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8085)
