from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from models.ChatRequest import ChatRequest
from models.ChatResponse import ChatResponse
from AInterface.request import run, run_streaming, OPENROUTER_API_KEY

app = FastAPI()

# Conversazione in memoria (single-user)
_history: list[dict] = []


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global _history
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY non configurata.")
    reply, _history = await run(request.message, _history)
    return ChatResponse(reply=reply)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY non configurata.")

    # run_streaming muta _history direttamente
    return StreamingResponse(
        run_streaming(request.message, _history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/reset")
async def chat_reset():
    global _history
    _history = []
    return {"status": "ok"}
