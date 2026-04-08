"""
AInterface/request.py
Engine dell'agente B.M.O.:
- Loop LLM con tool calls reali (streaming per la risposta finale)
- Context management (pruning)
- System prompt da identity.json + skills MD files
"""

import json
import os
from pathlib import Path
from typing import AsyncGenerator

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
DOTNET_API_URL     = os.getenv("DOTNET_API_URL", "http://localhost:5271")
WORKSPACE_PATH     = Path(os.getenv("WORKSPACE_PATH", "../workspace")).resolve()
CONFIG_PATH        = Path(os.getenv("CONFIG_PATH", "../Bmo.Api/bmo_config.json")).resolve()

_client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# ── Runtime config ────────────────────────────────────────────────────────────

def _load_bmo_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
    except Exception:
        return {}

def _get_model() -> str:
    return _load_bmo_config().get("agent", {}).get("model", "google/gemini-2.5-flash-lite")

def _get_max_iterations() -> int:
    return int(_load_bmo_config().get("agent", {}).get("max_tool_iterations", 5))

def _get_context_config() -> dict:
    return _load_bmo_config().get("context", {"max_tokens": 8000, "pruning_threshold": 0.8})

# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the agent workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to workspace/files/"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path":    {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Optional subfolder"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_memory",
            "description": "Search the agent's persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save or update an entry in persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key":      {"type": "string"},
                    "value":    {"type": "string"},
                    "category": {"type": "string", "description": "e.g. 'user', 'task', 'note'"}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_identity",
            "description": "Read the agent's identity.json.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_identity",
            "description": "Update a field in identity.json.",
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {"type": "string"},
                    "value": {"description": "New value (any JSON type)"}
                },
                "required": ["field", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_skills",
            "description": "Read the agent's skills.json.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_skills",
            "description": "Add or remove a skill. Automatically creates a dedicated MD file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action":          {"type": "string", "enum": ["add", "remove"]},
                    "skill_name":      {"type": "string", "description": "Skill name"},
                    "description":     {"type": "string", "description": "Short description (for add)"},
                    "initial_content": {"type": "string", "description": "Full Markdown content for the skill file (for add)"}
                },
                "required": ["action", "skill_name"]
            }
        }
    }
]

# ── System prompt ─────────────────────────────────────────────────────────────

def _load_json_file(filename: str) -> dict:
    p = WORKSPACE_PATH / filename
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def _build_system_prompt() -> str:
    identity = _load_json_file("identity.json")
    skills   = _load_json_file("skills.json")

    name    = identity.get("name", "B.M.O.")
    persona = identity.get("persona", "You are an AI assistant.")

    # Carica ogni skill dal suo file MD
    skills_text = ""
    for cap in skills.get("capabilities", []):
        if isinstance(cap, dict):
            skill_name = cap.get("name", "")
            skill_file = cap.get("file", "")
            md_path    = WORKSPACE_PATH / skill_file if skill_file else None
            if md_path and md_path.exists():
                skills_text += f"\n{md_path.read_text(encoding='utf-8')}\n"
            else:
                skills_text += f"\n- {skill_name}: {cap.get('description', '')}\n"
        elif isinstance(cap, str):
            skills_text += f"\n- {cap}\n"

    learned = skills.get("learned_behaviors", [])
    learned_text = "\n".join(f"  - {b}" for b in learned) or "  (none)"

    return (
        f"You are {name}.\n{persona}\n\n"
        "Output rules: respond in English only; do not use emojis or emoticons.\n\n"
        f"== Your capabilities ==\n{skills_text}\n"
        f"== Learned behaviors ==\n{learned_text}\n\n"
        "== TOOL USE RULE ==\n"
        "When you want to use a tool, call it DIRECTLY via function calling. "
        "Do NOT write Python code in your message text (e.g. `print(write_file(...))`). "
        "Always use native tool calls — the system will execute them and return the result. "
        "When you learn relevant information about the user, store it with save_memory."
    )

# ── Context management ────────────────────────────────────────────────────────

def _estimate_tokens(messages: list[dict]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            total += len(content) // 4
    return total


def _prune_history(history: list[dict]) -> list[dict]:
    cfg       = _get_context_config()
    max_tok   = int(cfg.get("max_tokens", 8000))
    threshold = float(cfg.get("pruning_threshold", 0.8))
    limit     = int(max_tok * threshold)

    while _estimate_tokens(history) > limit and len(history) > 2:
        history = history[2:]  # Remove the oldest user+assistant pair
    return history

# ── Tool execution via .NET gatekeeper ───────────────────────────────────────

async def _call_tool(tool_name: str, arguments: dict) -> str:
    payload = {"toolName": tool_name, "arguments": arguments}
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(f"{DOTNET_API_URL}/api/tools/execute", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", "") if data.get("success") else f"[Error] {data.get('error', 'unknown')}"
    except Exception as e:
        return f"[.NET error] {e}"

# ── Non-streaming run (retrocompatibilità) ────────────────────────────────────

async def run(message: str, history: list[dict]) -> tuple[str, list[dict]]:
    history = list(history) + [{"role": "user", "content": message}]
    model   = _get_model()
    max_it  = _get_max_iterations()

    for _ in range(max_it):
        response = await _client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": _build_system_prompt()}] + history,
            tools=TOOLS,
            tool_choice="auto",
        )
        choice = response.choices[0]
        msg    = choice.message

        if not msg.tool_calls:
            content = msg.content or ""
            history.append({"role": "assistant", "content": content})
            history = _prune_history(history)
            return content, history

        history.append(msg.model_dump(exclude_unset=False))
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            result = await _call_tool(tc.function.name, args)
            history.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return "I reached the maximum number of tool iterations.", history

# ── Streaming run ─────────────────────────────────────────────────────────────

async def run_streaming(message: str, history: list[dict]) -> AsyncGenerator[str, None]:
    """
    Async generator che emette eventi SSE:
      {"type": "tool_call",   "id": "...", "name": "...", "args": {...}}
      {"type": "tool_result", "id": "...", "result": "..."}
      {"type": "delta",       "content": "..."}
      {"type": "done"}
    """
    # Nota: muta la lista globale di history passata — app.py gestisce la reference
    history.append({"role": "user", "content": message})

    model  = _get_model()
    max_it = _get_max_iterations()

    for _ in range(max_it):
        stream = await _client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": _build_system_prompt()}] + history,
            tools=TOOLS,
            tool_choice="auto",
            stream=True,
        )

        full_content    = ""
        tool_calls_acc: dict[int, dict] = {}
        finish_reason   = None

        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta  = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            # Testo in streaming → invia subito al client
            if delta.content:
                full_content += delta.content
                yield f"data: {json.dumps({'type': 'delta', 'content': delta.content})}\n\n"

            # Accumula tool calls (arrivano a pezzi nello streaming)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                    if tc.id:
                        tool_calls_acc[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        tool_calls_acc[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_calls_acc[idx]["arguments"] += tc.function.arguments

        # Risposta finale senza tool calls
        if finish_reason == "stop" or not tool_calls_acc:
            history.append({"role": "assistant", "content": full_content})
            history[:] = _prune_history(history)
            yield f"data: {json.dumps({'type': 'done', 'voice_text': full_content})}\n\n"
            return

        # Esegui tool calls e invia eventi
        tool_calls_list = []
        tool_results    = {}

        for idx in sorted(tool_calls_acc.keys()):
            tc = tool_calls_acc[idx]
            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except json.JSONDecodeError:
                args = {}

            yield f"data: {json.dumps({'type': 'tool_call', 'id': tc['id'], 'name': tc['name'], 'args': args})}\n\n"

            result = await _call_tool(tc["name"], args)
            tool_results[tc["id"]] = result

            yield f"data: {json.dumps({'type': 'tool_result', 'id': tc['id'], 'result': result})}\n\n"

            tool_calls_list.append({
                "id":       tc["id"],
                "type":     "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]}
            })

        # Aggiorna history
        history.append({
            "role":       "assistant",
            "content":    None,
            "tool_calls": tool_calls_list
        })
        for tc_id, res in tool_results.items():
            history.append({"role": "tool", "tool_call_id": tc_id, "content": res})

    yield f"data: {json.dumps({'type': 'done', 'voice_text': ''})}\n\n"
