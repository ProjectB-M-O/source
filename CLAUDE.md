# B.M.O. Project — CLAUDE.md

## Panoramica

Progetto AI assistant "B.M.O." composto da 4 servizi che partono tutti da `start.bat` → `start.py`.

## Struttura

```
source/
├── start.py              # Launcher principale: installa dipendenze e avvia tutto
├── start.bat             # Entry point Windows (chiama start.py)
├── start.sh              # Entry point Linux/Mac
├── Bmo.Api/              # Backend C# .NET 10 (porta 5271) — API principale
│   └── bmo_config.json   # Config centralizzata (porte, modello AI, feature flags)
├── AI.Brain/             # Backend Python FastAPI (porta 8000) — logica AI/LLM
│   ├── .venv/            # Virtual environment Python
│   └── requirements.txt  # fastapi, uvicorn, openai, httpx, pydantic, python-dotenv
├── AI.Voice/             # Server TTS Flask (porta 5050) — Piper TTS con modello custom
│   ├── venv/             # Virtual environment Python
│   ├── requirements.txt  # flask, piper-tts
│   ├── server.py         # Flask server (/speak, /health)
│   ├── pipeline.py       # Pipeline TTS pura (Piper)
│   ├── config.py         # Config: percorsi modello, porta, max audio files
│   ├── models/bmo/       # Modello Piper custom (.onnx + .onnx.json) — da fornire
│   └── audio_out/        # File WAV generati (rolling cleanup, max configurabile)
├── dashboard-bmo/        # Frontend Next.js (porta 3000)
│   └── package.json
└── workspace/            # Dati runtime (identity, skills)
```

## Config principale: `Bmo.Api/bmo_config.json`

- `services.ai_voice.enabled` → abilita/disabilita l'intero setup AI.Voice
- `services.ai_voice.audio_max_files` → numero massimo di WAV tenuti in `audio_out/` (default 10)
- `dev_mode` → `true` = audio inviato al browser (player inline in chat); `false` = solo salvataggio su disco (produzione)
- `agent.model` → modello LLM usato (es. `google/gemini-2.0-flash-001`)
- Porte configurabili per ogni servizio

## Flusso di installazione (`start.py`)

Il launcher fa tutto automaticamente in ordine:
1. Check Python ≥ 3.10
2. Setup venv `AI.Brain/.venv` + installa requirements
3. **Se `ai_voice.enabled`**: setup venv `AI.Voice/venv` (vedi sotto)
4. Check/install .NET SDK 10 locale in `.dotnet/`
5. Check/install Node.js locale in `.node/`
6. `npm install` dashboard
7. Avvia i 4 servizi in terminali separati

### Setup AI.Voice (step 3 - solo se abilitato)

Installazione semplificata (niente torch/RVC/fairseq):
1. `pip install -r requirements.txt` (flask, piper-tts)
2. Verifica presenza modello in `models/bmo/` → **attende prompt interattivo** se mancante

## Dipendenze AI.Voice

- **piper-tts**: wrapper Python per inferenza ONNX — nessuna dipendenza da torch/CUDA
- Nessuna dipendenza da rvc-python, fairseq, faiss, onnxruntime, soundfile
- Il venv usa il Python di sistema (testato con 3.11)

## Modello Piper custom (non incluso nel repo)

Va copiato manualmente in `AI.Voice/models/bmo/`:
- `model.onnx`      — modello ONNX addestrato con Piper trainer
- `model.onnx.json` — config Piper del modello (generata dal trainer)

Lo script di onboarding attende esplicitamente che questi file siano presenti prima di continuare.

## Flusso audio TTS

```
Frontend (checkbox 🔊 attiva, solo se dev_mode=true)
  → POST /api/chat/stream { message, tts: true }
      → Bmo.Api intercetta stream SSE
          → AI.Brain: delta events proxied in real-time
          → done event con voice_text → Bmo.Api chiama AI.Voice /speak
              → AI.Voice sintetizza → salva in audio_out/ → ritorna WAV
          → se dev_mode: SSE event { type:"audio", data:"<base64>" }
          → SSE event { type:"done" }
  → Frontend: player <audio> inline nel bubble AI
```

In produzione (`dev_mode=false`): audio generato e salvato su disco, non inviato al browser.

## Ambiente di sviluppo

- OS: Windows 11
- Shell: bash (Git Bash / WSL)
- Python sistema: 3.11.9 (`C:\Users\matte\AppData\Local\Programs\Python\Python311`)
- Tool C#: .NET 10 SDK
- Frontend: Next.js/TypeScript
