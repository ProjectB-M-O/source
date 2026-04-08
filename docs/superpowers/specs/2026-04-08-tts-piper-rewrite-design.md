# Design: TTS Piper Rewrite + Audio in Chat
**Date:** 2026-04-08

## Overview
Rimozione completa di RVC/torch/fairseq da AI.Voice. Il servizio diventa un semplice wrapper Piper TTS con modello ONNX custom. L'audio viene iniettato nel flusso SSE come base64 e riprodotto inline nel browser (dev mode). In produzione, l'audio viene solo salvato su disco (futuro: streaming al robot).

---

## 1. AI.Voice (complete rewrite)

### Struttura nuova
```
AI.Voice/
├── server.py          # Flask: /speak, /health
├── pipeline.py        # PiperPipeline: text → WAV bytes
├── config.py          # Percorsi, porta, max_audio_files
├── requirements.txt   # flask, piper-tts (solo 2 dipendenze core)
├── models/bmo/        # .onnx + .onnx.json (forniti dall'utente)
│   └── .gitkeep
└── audio_out/         # WAV generati (rolling cleanup)
    └── .gitkeep
```

### Dipendenze rimosse
- `torch`, `torchaudio`, `rvc-python`, `faiss-cpu`, `onnxruntime`, `soundfile`

### Dipendenze mantenute
- `flask>=3.0.0`, `piper-tts>=1.2.0`

### File eliminati
- `patch_fairseq.py`, `download_models.py`, `convert_model.py`

### Rolling cleanup audio_out/
- Configurabile: `audio_max_files` (default 10) in `bmo_config.json`
- Prima di ogni sintesi: se file presenti > max, rimuovi i più vecchi (ordinati per mtime)

### Onboarding pause
- Dopo creazione `models/bmo/`: se cartella vuota (no .onnx), stampa istruzioni e aspetta `input()` esplicito
- Se modello già presente: skip del blocco

---

## 2. AI.Brain — `voice_text` nel done event

### Modifica a `app.py` (streaming endpoint)
L'evento `done` viene esteso:
```python
# Prima
yield 'data: {"type":"done"}\n\n'

# Dopo
yield f'data: {{"type":"done","voice_text":{json.dumps(full_response_text)}}}\n\n'
```

`full_response_text` = testo accumulato da tutti i delta della risposta corrente.

**Rationale:** AI.Brain ha controllo esplicito su cosa viene vocalizzato. In futuro, quando ci sarà reasoning interno o chain-of-thought, `voice_text` conterrà solo il testo destinato all'utente.

---

## 3. Bmo.Api — Gateway TTS

### Request model esteso
```csharp
record ChatRequest(string Message, bool Tts = false);
```

### Nuovo servizio: `VoiceClient.cs`
- `Task<byte[]> SpeakAsync(string text)` — POST a AI.Voice `/speak`, ritorna WAV bytes

### `ChatController.cs` — stream intercept
1. Proxy stream da AI.Brain in real-time (delta, tool_call, tool_result)
2. Intercetta evento `done` — legge `voice_text`
3. Se `tts=true` e `voice_text` presente:
   - Chiama `VoiceClient.SpeakAsync(voice_text)`
   - Se `dev_mode=true` in config: codifica base64, inietta `{"type":"audio","data":"<base64>"}` nel SSE
   - Se `dev_mode=false`: audio salvato su disco (da VoiceClient), niente al browser
4. Inietta `{"type":"done"}` finale

### `bmo_config.json` — nuovi campi
```json
{
  "services": {
    "ai_voice": {
      "enabled": true,
      "port": 5050,
      "audio_max_files": 10
    }
  },
  "dev_mode": true
}
```

---

## 4. Dashboard — Audio inline

### TTS checkbox in chat
- Visibile solo se `dev_mode=true`
- Stato: `ttsEnabled: boolean` (default false)
- Incluso nel body della richiesta: `{ message, tts: ttsEnabled }`

### Gestione evento `audio` SSE
```typescript
case "audio":
  const blob = b64toBlob(event.data, "audio/wav");
  const url = URL.createObjectURL(blob);
  // Aggiunge url al messaggio AI corrente
  // FIFO cleanup: max 10 blob URLs attivi
```

### Player inline nel messaggio AI
- `<audio controls src={url} />` nel bubble del messaggio AI
- Stile compatto (WhatsApp-like)

### FIFO blob URLs
- Array `audioUrls: string[]` in state
- Quando > 10: `URL.revokeObjectURL(oldest)` + rimuovi dall'array

### Settings — dev_mode toggle
- Nuovo campo nel settings panel
- Salva via `PUT /api/config`
- Quando `dev_mode=false`: TTS checkbox nascosto, nessun audio player

---

## 5. start.py — Semplificazione AI.Voice setup

### Sequenza installazione nuova (sostituisce la vecchia)
```python
pip install -r requirements.txt  # flask, piper-tts
```

### Rimosse
- `pip install torch torchaudio --index-url ...`
- `pip install faiss-cpu>=1.8.0`
- `pip install --force-reinstall onnxruntime`
- `python patch_fairseq.py`
- `python download_models.py`

### Aggiunta: model check con pause interattiva
```python
bmo_model_dir = VOICE_DIR / "models" / "bmo"
bmo_model_dir.mkdir(parents=True, exist_ok=True)
onnx_files = list(bmo_model_dir.glob("*.onnx"))
if not onnx_files:
    print("\n  Nessun modello trovato in AI.Voice/models/bmo/")
    print("  Copia i file:")
    print("    model.onnx")
    print("    model.onnx.json")
    input("\n  Premi INVIO quando i file sono pronti... ")
```

---

## 6. .gitignore

### Aggiungere
```
AI.Voice/audio_out/*.wav
AI.Voice/venv/
```

### Rimuovere
```
export/bmo_rvc_model/   # non più necessario
```

---

## 7. CLAUDE.md + README

- Aggiornare struttura directory
- Aggiornare dipendenze AI.Voice (rimozione RVC/torch)
- Aggiornare flusso installazione
- Documentare nuovi campi `bmo_config.json` (`dev_mode`, `audio_max_files`)
- Documentare struttura `models/bmo/`
