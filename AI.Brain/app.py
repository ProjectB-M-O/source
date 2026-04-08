import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from models.ChatRequest import ChatRequest
from models.ChatResponse import ChatResponse
from AInterface.request import run, run_streaming, OPENROUTER_API_KEY, WORKSPACE_PATH

app = FastAPI()

# ── DB setup ──────────────────────────────────────────────────────────────────

_db_path = str(WORKSPACE_PATH / "brain.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );
        """)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_session() -> str:
    session_id = str(uuid.uuid4())
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_at, is_active) VALUES (?, ?, 1)",
            (session_id, _now_iso()),
        )
    return session_id


def _get_active_session() -> str | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM sessions WHERE is_active=1 ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    return row["id"] if row else None


def _get_session_messages(session_id: str) -> list[sqlite3.Row]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM conversation_history "
            "WHERE session_id=? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return rows


def _save_message(session_id: str, role: str, content: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO conversation_history (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, _now_iso()),
        )


def _deactivate_session(session_id: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET is_active=0 WHERE id=?",
            (session_id,),
        )


# ── Startup: init DB and restore session ─────────────────────────────────────

_init_db()

_session_id: str = _get_active_session() or _create_session()

# Load history (user + assistant only — tool rows not stored)
_history: list[dict] = [
    {"role": row["role"], "content": row["content"]}
    for row in _get_session_messages(_session_id)
    if row["role"] in ("user", "assistant")
]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global _history
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY non configurata.")
    reply, _history = await run(request.message, _history)
    _save_message(_session_id, "user", request.message)
    _save_message(_session_id, "assistant", reply)
    return ChatResponse(reply=reply)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY non configurata.")

    async def _streaming_wrapper():
        async for chunk in run_streaming(request.message, _history):
            yield chunk
        # After generator exhausts, history has been mutated by run_streaming.
        # Save user message and last assistant message.
        _save_message(_session_id, "user", request.message)
        # The last assistant entry is the final item with role=assistant in _history.
        assistant_content = ""
        for entry in reversed(_history):
            if entry.get("role") == "assistant" and isinstance(entry.get("content"), str):
                assistant_content = entry["content"]
                break
        if assistant_content:
            _save_message(_session_id, "assistant", assistant_content)

    return StreamingResponse(
        _streaming_wrapper(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/reset")
async def chat_reset():
    global _history, _session_id
    _deactivate_session(_session_id)
    _session_id = _create_session()
    _history = []
    return {"status": "ok"}


@app.get("/chat/history")
async def chat_history():
    return {
        "session_id": _session_id,
        "messages": [
            {"role": row["role"], "content": row["content"], "created_at": row["created_at"]}
            for row in _get_session_messages(_session_id)
        ],
    }
