# B.M.O. — AI Agent System

B.M.O. is a multi-component conversational AI agent with a distributed architecture. It combines a Python AI engine, a .NET API gateway, and a Next.js dashboard into a single system launched from one command.

The agent has a persistent workspace (files, memory, skills, identity), supports real-time streaming responses via SSE, and can execute sandboxed tools to read/write files and query a local SQLite memory store.

---

## Architecture

```
User (Browser)
    ↓ HTTP
dashboard-bmo       → Next.js frontend (port 3000)
    ↓ HTTP
Bmo.Api             → .NET API gateway (port 5271)
    ↓ HTTP
AI.Brain            → Python FastAPI agent engine (port 8000)
    ↓ API
OpenRouter          → LLM provider (Gemini 2.0 / 2.5 or any model)

AI.Voice (opt.)     → Flask TTS server (port 5050)
    Piper TTS → RVC (BMO voice model) → WAV audio
```

All services run in separate terminals, launched automatically by `start.py`. AI.Voice is optional and must be enabled during first-run setup.

---

## Stack

| Layer | Technology |
|---|---|
| AI Engine | Python 3, FastAPI, OpenAI SDK (via OpenRouter) |
| API Gateway | .NET 10, ASP.NET Core, SQLite |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Database | SQLite (memory + tool audit log) |
| LLM Provider | OpenRouter (default: `google/gemini-2.0-flash-001`) |
| TTS (optional) | Python 3, Flask, Piper TTS, RVC (custom BMO voice model) |

---

## Project Structure

```
B.M.O.Project/
├── AI.Brain/                   # Python agent engine
│   ├── app.py                  # FastAPI entry point
│   ├── requirements.txt
│   ├── .env                    # Runtime config (API key, ports)
│   └── AInterface/
│       └── request.py          # LLM loop, tool execution, streaming
│
├── Bmo.Api/                    # .NET API gateway
│   ├── Program.cs
│   ├── bmo_config.json         # Global config (model, ports, tools)
│   ├── Controllers/            # chat, tools, config, health
│   ├── Services/               # ChatService, ToolService, WorkspaceService
│   └── Models/
│
├── dashboard-bmo/              # Next.js frontend
│   ├── app/
│   │   ├── page.tsx            # Main chat UI
│   │   └── layout.tsx
│   └── package.json
│
├── AI.Voice/                   # Python TTS server (optional)
│   ├── server.py               # Flask entry point — POST /speak → WAV
│   ├── pipeline.py             # Piper TTS → RVC pipeline
│   ├── config.py               # Paths, ports, model settings
│   ├── download_models.py      # Downloads Piper TTS model (~61MB)
│   ├── patch_fairseq.py        # Applies Python 3.11 compat patches to fairseq
│   ├── convert_model.py        # Converts RVC training checkpoint → inference format
│   └── requirements.txt
│
├── export/                     # External model files (NOT in git — see below)
│   └── bmo_rvc_model/
│       ├── bmo_infer.pth       # RVC inference model ← must be copied manually
│       └── bmo.index           # FAISS index        ← must be copied manually
│
├── workspace/                  # Runtime data (auto-created on first run)
│   ├── files/                  # Agent file sandbox
│   ├── identity.json           # Agent name and persona
│   ├── skills.json             # Agent capabilities
│   └── bmo_agent.db            # SQLite database
│
├── start.py                    # Main launcher
├── start.sh                    # Linux/macOS wrapper
├── start.bat                   # Windows wrapper
└── B.M.O.Project.sln
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- .NET 10 SDK *(auto-installed by start.py if missing)*
- Node.js 18+ *(auto-installed by start.py if missing)*
- An [OpenRouter](https://openrouter.ai) API key

### First Run

```bash
python start.py
```

On the first run, an onboarding wizard will ask for:
- Your OpenRouter API key
- The AI model to use (default: `google/gemini-2.0-flash-001`)
- Service ports (default: 8000, 5271, 3000)
- Whether to install the **AI.Voice TTS server** (optional — requires ~700MB PyTorch download and the BMO RVC model files)

The launcher then installs all dependencies and starts all services in separate terminal windows.

### AI.Voice — BMO Voice (optional)

The TTS server synthesizes speech using [Piper TTS](https://github.com/rhasspy/piper) and converts it to BMO's voice with a custom [RVC](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) model.

**Endpoint:** `POST http://localhost:5050/speak`
```json
{ "text": "Hello! I am BMO!" }
```
Returns raw WAV audio bytes.

**Model files (not in git — store externally):**

The RVC model is too large for git. After cloning the repo, copy these files manually:
```
export/bmo_rvc_model/bmo_infer.pth   ← RVC inference model
export/bmo_rvc_model/bmo.index       ← FAISS retrieval index
```

The Piper TTS model (~61MB) is downloaded automatically by `start.py`.

If you have the original training checkpoint (`bmo.pth`), you can convert it:
```bash
cd AI.Voice
python convert_model.py
```

### Manual Start (development)

```bash
# Terminal 1 — AI Brain
cd AI.Brain
python -m uvicorn app:app --reload --port 8000

# Terminal 2 — API Gateway
cd Bmo.Api
dotnet run --urls "http://localhost:5271"

# Terminal 3 — Dashboard
cd dashboard-bmo
npm install
npm run dev
```

### Access

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| Swagger UI | http://localhost:5271/swagger |
| AI Brain docs | http://localhost:8000/docs |
| AI.Voice health | http://localhost:5050/health *(if enabled)* |

---

## Configuration

All runtime settings live in `Bmo.Api/bmo_config.json`:

```json
{
  "version": "0.1",
  "agent": {
    "name": "B.M.O.",
    "model": "google/gemini-2.0-flash-001",
    "max_tool_iterations": 5
  },
  "services": {
    "ai_brain":  { "port": 8000 },
    "bmo_api":   { "port": 5271 },
    "dashboard": { "port": 3000 },
    "ai_voice":  { "enabled": false, "port": 5050 }
  },
  "context": {
    "max_tokens": 8000,
    "pruning_threshold": 0.8
  }
}
```

The AI.Brain service also reads from `AI.Brain/.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-...
DOTNET_API_URL=http://localhost:5271
WORKSPACE_PATH=../workspace
CONFIG_PATH=../Bmo.Api/bmo_config.json
```

---

## Agent Tools

The AI engine has access to 8 built-in tools, executed via the .NET gateway with sandboxing:

| Tool | Description |
|---|---|
| `read_file` | Read a file from the workspace sandbox |
| `write_file` | Write a file to the workspace sandbox |
| `list_files` | List files in the workspace |
| `query_memory` | Query the SQLite memory store |
| `save_memory` | Save a key-value entry to memory |
| `read_identity` | Read the agent's identity/persona |
| `update_identity` | Update the agent's identity |
| `read_skills` / `update_skills` | Read or update agent capabilities |

Tool calls and results are shown in the chat UI and logged to the `tool_logs` table in SQLite.

---

## Chat Flow

```
User message
    → POST /api/chat/stream (.NET)
    → POST /chat/stream (Python FastAPI)
    → LLM call with tools (OpenRouter)
    → If tool_calls: POST /api/tools/execute (.NET)
    → Stream SSE events back to UI (delta, tool_call, tool_result, done)
```

Context is managed automatically: conversation history is pruned when it approaches the token limit (`max_tokens` × `pruning_threshold`).

---

## Version

**v0.2** — Added optional AI.Voice TTS server (Piper + RVC BMO voice model).

**v0.1** — Initial release with onboarding, streaming chat, tool execution, and persistent workspace.
