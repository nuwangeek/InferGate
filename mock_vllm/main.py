"""Minimal FastAPI app that mimics vLLM's OpenAI-compatible chat completions API.

Purpose: lets the full Docker Compose stack run on any machine without a GPU.
The response shape is identical to real vLLM so the API layer can't tell the
difference — which is exactly the point of the gateway pattern.
"""

import time
import uuid

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock vLLM")


class _Message(BaseModel):
    role: str
    content: str


class _ChatRequest(BaseModel):
    model: str
    messages: list[_Message]
    temperature: float = 1.0
    max_tokens: int | None = None
    stream: bool = False


@app.post("/v1/chat/completions")
async def chat_completions(request: _ChatRequest) -> dict[str, object]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"[mock] You said: {request.messages[-1].content}",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
