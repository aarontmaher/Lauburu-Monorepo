from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from typing import List, Dict, Any

app = FastAPI()

class ChatReq(BaseModel):
    messages: List[Dict[str, Any]]

@app.post("/v1/chat/completions")
async def mock_chat(req: ChatReq):
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": 1234567890,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "[HERMES TOOL ROUTER / MOCK LLM] Evaluated request. No context overflow detected. The Tri-Vault Storage Specialist and RAM governor are active. How can I help you code?"
            },
            "finish_reason": "stop"
        }]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8090)
