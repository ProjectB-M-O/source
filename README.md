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
```

All three services run in separate terminals, launched automatically by `start.py`.

---

## Stack

| Layer | Technology |
|---|---|
| AI Engine | Python 3, FastAPI, OpenAI SDK (via OpenRouter) |
| API Gateway | .NET 10, ASP.NET Core, SQLite |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| Database | SQLite (memory + tool audit log) |
| LLM Provider | OpenRouter (default: `google/gemini-2.0-flash-001`) |

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
- .NET 10 SDK
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) API key

### First Run

```bash
python start.py
```

On the first run, an onboarding wizard will ask for:
- Your OpenRouter API key
- The AI model to use (default: `google/gemini-2.0-flash-001`)
- Service ports (default: 8000, 5271, 3000)

The launcher then starts all three services in separate terminal windows.

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
    "dashboard": { "port": 3000 }
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

**v0.1** — Initial release with onboarding, streaming chat, tool execution, and persistent workspace.
