# B.M.O.

Sistema multi-servizio per un assistente conversazionale con:
- motore AI in Python (FastAPI) con streaming SSE e tool-calls
- gateway API in .NET (ASP.NET Core) che gestisce workspace + strumenti + memoria SQLite
- dashboard Next.js per la chat
- server TTS opzionale (Flask + Piper) con voce custom tramite modello ONNX

L'avvio è pensato per essere "one command": `start.py` installa le dipendenze (anche .NET/Node in locale se servono) e apre ogni servizio in un terminale separato.

Dalla v0.4 è disponibile anche il CLI globale `bmo` per gestire il progetto da terminale.

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
├── bmo_cli.py                # CLI globale (bmo --help / -onboard / -config / --dev)
├── bmo.bat                   # wrapper Windows per il CLI
├── bmo                       # wrapper bash per il CLI
├── AI.Brain/                 # FastAPI + loop LLM + tool calling
│   ├── app.py                # + persistenza SQLite sessioni (workspace/brain.db)
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
    └── package.json          # + @monaco-editor/react per la tab Skills
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

> **Nota v0.4:** `start.py` registra automaticamente il comando `bmo` nel PATH utente. Riapri il terminale per usarlo.
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

## CLI `bmo`

Dalla v0.4 il progetto espone un CLI globale. Dopo il primo avvio di `start.py` (che registra il PATH), puoi usare:

```bash
bmo --help              # mostra tutti i comandi
bmo -onboard            # ri-wizard di configurazione (preserva dati e sessioni)
bmo -config             # editor interattivo del config (live / restart / credenziali)
bmo --dev on|off        # toggle dev_mode senza restart
bmo start               # avvia tutti i servizi (modalità gestita: log in workspace/logs)
bmo reload              # restart di tutti i servizi (quit + start)
bmo quit                # ferma i servizi avviati tramite `bmo start`
```

`bmo -config` mostra un menu numerato con tre sezioni:
- **LIVE** — modifiche applicate senza restart
- **⚠ RICHIEDE RESTART** — porte, workspace_path (restart automatico se modificate)
- **🔑 CREDENZIALI** — valori di `AI.Brain/.env` (API key mascherata)

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

## Dashboard — tab e funzionalità

| Tab | Descrizione |
|---|---|
| **Chat** | Conversazione con BMO. Streaming SSE, tool calls visibili, audio TTS inline (dev_mode). `/new` per nuova sessione |
| **Skills** | Lista delle skill dell'agente. Monaco editor per modificare i file `.md`. Pulsante “＋ Nuova Skill” per crearne di nuove |
| **Impostazioni** | Config live (agente, tool, contesto), sezione Servizi (read-only), AI Voice, e Credenziali (API key con show/hide) |

**Persistenza sessione (v0.4):** i messaggi sopravvivono al refresh della pagina. La sessione viene azzerata solo con `/new` nella chat.

---

## Troubleshooting rapido

- `OPENROUTER_API_KEY non configurata` → usa `bmo -config` oppure aggiorna `AI.Brain/.env` direttamente.
- Porta occupata → `bmo -config` → sezione ⚠ RICHIEDE RESTART → modifica la porta → restart automatico.
- TTS non parte → verifica che `model.onnx` e `model.onnx.json` siano in `AI.Voice/models/bmo/`.
- Sessione non persistita → verifica che `workspace/brain.db` esista e sia scrivibile.

---

## Version

**v0.4** — Session persistence (SQLite in AI.Brain), Skills tab con Monaco editor, settings aggiornati (Servizi/AI Voice/Credenziali), CLI globale `bmo` con `-onboard`, `-config`, `--dev`.

**v0.3** — Trained Piper model for BMO + implemented/fixed onboarding that fully installs and boots the whole app end-to-end.

**v0.2** — Added optional AI.Voice TTS server (Piper + RVC BMO voice model).

**v0.1** — Initial release with onboarding, streaming chat, tool execution, and persistent workspace.

