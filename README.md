# B.M.O.

Sistema multi-servizio per un assistente conversazionale con:
- motore AI in Python (FastAPI) con streaming SSE e tool-calls
- gateway API in .NET (ASP.NET Core) che gestisce workspace + strumenti + memoria SQLite
- dashboard Next.js per la chat
- server TTS opzionale (Flask + Piper) con voce custom tramite modello ONNX

L'avvio è pensato per essere "one command": `start.py` installa le dipendenze (anche .NET/Node in locale se servono) e apre ogni servizio in un terminale separato.

---

## Architettura

```
Browser (dashboard-bmo)  → Next.js (default 3000)
        │
        ▼
Bmo.Api                 → .NET 10 (default 5271)
        │
        ▼
AI.Brain                → FastAPI (default 8000)
        │
        ▼
OpenRouter              → LLM provider (modello configurabile)

AI.Voice (opzionale)    → Flask TTS (default 5050)
                          Piper (modello custom ONNX) → WAV
```

---

## Struttura progetto

```
source/
├── start.py
├── start.bat
├── start.sh
├── AI.Brain/                 # FastAPI + loop LLM + tool calling
│   ├── app.py
│   ├── requirements.txt
│   ├── .env                  # OPENROUTER_API_KEY, DOTNET_API_URL, ecc.
│   └── AInterface/request.py
├── Bmo.Api/                  # API gateway + workspace + tools + memoria
│   ├── Program.cs
│   ├── bmo_config.json        # config centralizzata (porte, modello, feature)
│   ├── Controllers/
│   └── Services/
├── AI.Voice/                 # TTS opzionale (Flask + Piper)
│   ├── server.py              # POST /speak, GET /health
│   ├── pipeline.py
│   ├── config.py
│   ├── requirements.txt
│   ├── models/bmo/            # model.onnx + model.onnx.json (forniti a mano)
│   └── audio_out/             # WAV generati (cleanup "rolling")
└── dashboard-bmo/            # Next.js UI
    └── package.json
```

---

## Requisiti

- Python >= 3.10
- Connessione Internet al primo avvio (per installare dipendenze e/o scaricare toolchain)
- API key OpenRouter: https://openrouter.ai/keys

Note:
- Se mancano, `start.py` può installare in locale:
  - .NET SDK 10 in `.dotnet/`
  - Node.js (portable) in `.node/`

---

## Avvio rapido

Windows:
```bat
start.bat
```

Cross-platform:
```bash
python start.py
```

Al primo avvio parte un wizard che chiede:
- `agent.model` (modello OpenRouter)
- `OPENROUTER_API_KEY` (obbligatoria, salvata in `AI.Brain/.env`)
- porte dei servizi (AI.Brain, Bmo.Api, dashboard)
- se abilitare `AI.Voice` (TTS) e, opzionalmente, la sua porta

Alla fine, `start.py`:
- installa dipendenze Python per `AI.Brain` in `AI.Brain/.venv/`
- se `AI.Voice` è abilitato, crea `AI.Voice/venv/` e installa `flask` + `piper-tts`
- installa (se serve) `.NET` e `Node.js` localmente
- esegue `npm install` per `dashboard-bmo/` (prima volta)
- avvia i servizi in terminali separati e apre il browser sul dashboard

---

## Configurazione

La config principale è in `Bmo.Api/bmo_config.json`. Alcuni valori chiave:
- `services.*.port` → porte dei servizi
- `services.ai_voice.enabled` → abilita/disabilita il TTS
- `services.ai_voice.audio_max_files` → quanti WAV mantenere in `AI.Voice/audio_out/`
- `dev_mode` → se `true`, l'audio viene inviato al browser via SSE (evento `audio`)

`start.py` sincronizza anche:
- `AI.Brain/.env` (es. `OPENROUTER_API_KEY`, `DOTNET_API_URL`)
- `dashboard-bmo/.env.local` (`NEXT_PUBLIC_BMO_API_URL`)

Esempio (ridotto):
```json
{
  "dev_mode": true,
  "services": {
    "ai_brain": { "port": 8000 },
    "bmo_api": { "port": 5271 },
    "dashboard": { "port": 3000 },
    "ai_voice": { "enabled": false, "port": 5050, "audio_max_files": 10 }
  },
  "agent": {
    "model": "google/gemini-2.0-flash-001",
    "max_tool_iterations": 5
  },
  "context": {
    "max_tokens": 8000,
    "pruning_threshold": 0.8,
    "compaction_enabled": true
  }
}
```

---

## AI.Voice (TTS) — modello Piper ONNX

`AI.Voice` è opzionale e usa Piper per generare WAV.

Prerequisito: copia manualmente il modello custom in `AI.Voice/models/bmo/`:
```
AI.Voice/models/bmo/model.onnx
AI.Voice/models/bmo/model.onnx.json
```

Quando `AI.Voice` è abilitato, `start.py` controlla la presenza del modello e, se manca, si ferma in attesa che i file vengano copiati.

Endpoint utili:
- `POST http://localhost:5050/speak` body: `{ "text": "ciao" }` → bytes WAV
- `GET  http://localhost:5050/health`

Nota sulla porta:
- al momento il server Flask usa `5050` di default (vedi `AI.Voice/config.py`). Se imposti una porta diversa in config, assicurati che sia coerente anche lato `AI.Voice`.

---

## Streaming + TTS (come funziona)

- Il frontend chiama `POST /api/chat/stream` con `{ message, tts: true }`.
- `Bmo.Api` fa proxy dello stream SSE da `AI.Brain`.
- Quando arriva l'evento `done` con `voice_text`, `Bmo.Api` chiama `AI.Voice /speak`.
- Se `dev_mode=true`, `Bmo.Api` inietta un evento SSE `audio` con WAV in base64 (riproducibile inline nella chat).
- Se `dev_mode=false`, l'audio non viene inviato al browser (ma `AI.Voice` continua a salvare i WAV su disco).

---

## Tool dell'agente

Il loop LLM in `AI.Brain` può chiamare tool “whitelistati” eseguiti da `Bmo.Api` (sandbox su `workspace/files/`) e loggati su SQLite (`workspace/bmo_agent.db`).

Tool disponibili:
- `read_file`, `write_file`, `list_files`
- `query_memory`, `save_memory`
- `read_identity`, `update_identity`
- `read_skills`, `update_skills`

---

## URL utili

- Dashboard: http://localhost:3000
- Swagger (solo in Development): http://localhost:5271/swagger
- AI.Brain docs: http://localhost:8000/docs
- AI.Voice health (se abilitato): http://localhost:5050/health

---

## Avvio manuale (dev)

Se preferisci avviare i servizi a mano:

Suggerimento: usa i virtual environment creati da `start.py`.

Windows (PowerShell):
```powershell
# AI.Brain
Set-Location AI.Brain
.\.venv\Scripts\python.exe -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Bmo.Api
Set-Location ..\Bmo.Api
dotnet run --launch-profile http --urls "http://localhost:5271"

# (opzionale) AI.Voice
Set-Location ..\AI.Voice
.\venv\Scripts\python.exe server.py

# Dashboard
Set-Location ..\dashboard-bmo
npm install
npm run dev -- --port 3000
```

Linux/macOS (bash):
```bash
# AI.Brain
cd AI.Brain
./.venv/bin/python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Bmo.Api
cd ../Bmo.Api
dotnet run --launch-profile http --urls "http://localhost:5271"

# (opzionale) AI.Voice
cd ../AI.Voice
./venv/bin/python server.py

# Dashboard
cd ../dashboard-bmo
npm install
npm run dev -- --port 3000
```

---

## Troubleshooting rapido

- `OPENROUTER_API_KEY non configurata` → rilancia `start.py` e scegli “modifica impostazioni”, oppure aggiorna `AI.Brain/.env`.
- Porta occupata → cambia `services.*.port` in `Bmo.Api/bmo_config.json` e rilancia `start.py`.
- TTS non parte → verifica che `model.onnx` e `model.onnx.json` siano in `AI.Voice/models/bmo/`.

---

## Version

**v0.3** — Trained Piper model for BMO + implemented/fixed onboarding that fully installs and boots the whole app end-to-end.

**v0.2** — Added optional AI.Voice TTS server (Piper + RVC BMO voice model).

**v0.1** — Initial release with onboarding, streaming chat, tool execution, and persistent workspace.

