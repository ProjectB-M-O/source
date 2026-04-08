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
├── AI.Voice/             # Server TTS Flask (porta 5050) — Piper TTS + RVC voice
│   ├── venv/             # Virtual environment Python (Python 3.11)
│   ├── requirements.txt  # flask, piper-tts, rvc-python, soundfile, numpy
│   ├── server.py         # Flask server
│   ├── pipeline.py       # Pipeline TTS→RVC
│   ├── patch_fairseq.py  # Patch Python 3.11+ compat per fairseq/hydra
│   ├── download_models.py
│   └── models/piper/     # Modelli Piper TTS (.onnx)
├── dashboard-bmo/        # Frontend Next.js (porta 3000)
│   └── package.json
├── workspace/            # Dati runtime (identity, skills)
└── export/bmo_rvc_model/ # Modello RVC BMO (bmo_infer.pth + bmo.index)
```

## Config principale: `Bmo.Api/bmo_config.json`

- `services.ai_voice.enabled` → abilita/disabilita l'intero setup AI.Voice
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

Sequenza pip installazioni:
1. `torch torchaudio --index-url https://download.pytorch.org/whl/cpu` (CPU build)
2. `pip install -r requirements.txt` (flask, piper-tts, **rvc-python**, soundfile, numpy)
3. `pip install faiss-cpu>=1.8.0`
4. `pip install --force-reinstall onnxruntime`
5. `python patch_fairseq.py` (patcha fairseq e hydra per Python 3.11+)
6. `python download_models.py` (scarica modello Piper TTS ~61MB)

## Dipendenze critiche e note

- **rvc-python**: max versione disponibile su PyPI è `0.1.5` — NON usare `>=0.1.7`. Richiede `numpy<=1.23.5`
- **numpy**: NON pinnare a `>=1.24.0` — rvc-python forza `numpy<=1.23.5`, pip risolve automaticamente a 1.23.5
- **fairseq**: libreria vecchia, non compatibile Python 3.11+ out-of-the-box → `patch_fairseq.py` la patcha
- **piper-tts**: dipende da `piper-phonemize` (binari nativi) — wheel disponibile per Python 3.9+ abi3 su Windows x64
- **onnxruntime**: deve essere reinstallato forzatamente per evitare conflitti con `onnxruntime-dml` che installa rvc-python
- Il venv AI.Voice usa Python 3.11 (da `AI.Voice/venv/pyvenv.cfg`)

## Modelli RVC BMO (non inclusi nel repo)

Vanno copiati manualmente in `export/bmo_rvc_model/`:
- `bmo_infer.pth` — modello inferenza
- `bmo.index` — indice FAISS

Senza questi file il server parte ma la voce RVC non funziona.

## Ambiente di sviluppo

- OS: Windows 11
- Shell: bash (Git Bash / WSL)
- Python sistema: 3.11.9 (`C:\Users\matte\AppData\Local\Programs\Python\Python311`)
- Tool C#: .NET 10 SDK
- Frontend: Next.js/TypeScript
