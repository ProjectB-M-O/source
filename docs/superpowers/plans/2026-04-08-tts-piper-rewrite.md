# TTS Piper Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sostituire il server TTS RVC+Piper con un server Piper-only che usa un modello ONNX custom, aggiungere supporto audio SSE nel gateway C#, e mostrare player audio inline nella chat web (solo in dev_mode).

**Architecture:** AI.Voice diventa un wrapper Piper puro (flask + piper-tts). Bmo.Api intercetta l'evento `done` dallo stream SSE di AI.Brain, chiama AI.Voice se `tts=true`, e inietta un evento `audio` con WAV in base64 (solo se `dev_mode=true`). AI.Brain include `voice_text` nell'evento `done` per dare al gateway il controllo esplicito su cosa vocalizzare.

**Tech Stack:** Python Flask + piper-tts (AI.Voice), C# .NET 10 (Bmo.Api), Next.js/TypeScript (dashboard), Python FastAPI (AI.Brain)

---

## File Map

**Creati:**
- `AI.Voice/models/bmo/.gitkeep` — cartella per .onnx + .onnx.json utente
- `AI.Voice/audio_out/.gitkeep` — cartella WAV generati (rolling cleanup)
- `Bmo.Api/Services/VoiceClient.cs` — HTTP client verso AI.Voice

**Modificati:**
- `AI.Voice/requirements.txt` — rimuovi rvc/torch/faiss; solo flask + piper-tts
- `AI.Voice/config.py` — rewrite, no torch, punta a models/bmo/
- `AI.Voice/pipeline.py` — rewrite, solo Piper, salva in audio_out/
- `AI.Voice/server.py` — piccola modifica, chiama cleanup prima di ogni sintesi
- `AI.Brain/AInterface/request.py` — aggiungi `voice_text` all'evento `done`
- `Bmo.Api/Models/ChatRequest.cs` — aggiungi `Tts bool`
- `Bmo.Api/Program.cs` — registra VoiceClient HttpClient
- `Bmo.Api/Controllers/ChatController.cs` — logica intercept TTS nel path streaming
- `Bmo.Api/bmo_config.json` — aggiungi `dev_mode`, `audio_max_files`
- `dashboard-bmo/app/page.tsx` — TTS checkbox, audio SSE event, player inline, dev_mode settings
- `start.py` — semplifica setup AI.Voice, aggiungi model check interattivo

**Eliminati:**
- `AI.Voice/patch_fairseq.py`
- `AI.Voice/download_models.py`
- `AI.Voice/convert_model.py`

**Docs:**
- `CLAUDE.md`, `README.md`, `.gitignore`

---

## Task 1: AI.Voice — cartelle modello e audio

**Files:**
- Create: `AI.Voice/models/bmo/.gitkeep`
- Create: `AI.Voice/audio_out/.gitkeep`

- [ ] **Step 1: Crea le cartelle con gitkeep**

```bash
mkdir -p AI.Voice/models/bmo AI.Voice/audio_out
touch AI.Voice/models/bmo/.gitkeep AI.Voice/audio_out/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add AI.Voice/models/bmo/.gitkeep AI.Voice/audio_out/.gitkeep
git commit -m "feat(AI.Voice): add models/bmo/ and audio_out/ folders"
```

---

## Task 2: AI.Voice — requirements.txt e file da eliminare

**Files:**
- Modify: `AI.Voice/requirements.txt`
- Delete: `AI.Voice/patch_fairseq.py`, `AI.Voice/download_models.py`, `AI.Voice/convert_model.py`

- [ ] **Step 1: Riscrivi requirements.txt**

Sostituisci l'intero file con:
```
flask>=3.0.0
piper-tts>=1.2.0
```

- [ ] **Step 2: Elimina i file obsoleti**

```bash
rm AI.Voice/patch_fairseq.py AI.Voice/download_models.py AI.Voice/convert_model.py
```

- [ ] **Step 3: Commit**

```bash
git add AI.Voice/requirements.txt
git rm AI.Voice/patch_fairseq.py AI.Voice/download_models.py AI.Voice/convert_model.py
git commit -m "feat(AI.Voice): remove RVC/torch/fairseq deps and scripts"
```

---

## Task 3: AI.Voice — config.py (rewrite)

**Files:**
- Modify: `AI.Voice/config.py`

- [ ] **Step 1: Riscrivi config.py**

Sostituisci l'intero file con:
```python
import os
import json
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# Modello Piper custom (fornito dall'utente)
PIPER_MODEL_DIR = BASE_DIR / "models" / "bmo"

# Cartella output audio (rolling cleanup)
AUDIO_OUT_DIR = BASE_DIR / "audio_out"
AUDIO_OUT_DIR.mkdir(exist_ok=True)

# Numero massimo di file audio in audio_out/ (default 10, letto da bmo_config.json)
def _load_max_files() -> int:
    cfg_path = BASE_DIR / ".." / "Bmo.Api" / "bmo_config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return int(cfg.get("services", {}).get("ai_voice", {}).get("audio_max_files", 10))
    except Exception:
        return 10

AUDIO_MAX_FILES = _load_max_files()

# Server
HOST = "0.0.0.0"
PORT = 5050
```

- [ ] **Step 2: Commit**

```bash
git add AI.Voice/config.py
git commit -m "feat(AI.Voice): simplify config, remove RVC/torch references"
```

---

## Task 4: AI.Voice — pipeline.py (rewrite Piper-only)

**Files:**
- Modify: `AI.Voice/pipeline.py`

- [ ] **Step 1: Riscrivi pipeline.py**

Sostituisci l'intero file con:
```python
"""
pipeline.py — Sintesi vocale Piper TTS pura.
Cerca il primo .onnx nella cartella models/bmo/ e lo usa come modello.
"""
import io
import logging
import time
from pathlib import Path

from piper import PiperVoice

from config import PIPER_MODEL_DIR, AUDIO_OUT_DIR, AUDIO_MAX_FILES

logger = logging.getLogger(__name__)


def _find_model() -> tuple[Path, Path]:
    """Trova il primo .onnx e il corrispondente .onnx.json in models/bmo/."""
    onnx_files = list(PIPER_MODEL_DIR.glob("*.onnx"))
    if not onnx_files:
        raise FileNotFoundError(
            f"Nessun modello .onnx trovato in {PIPER_MODEL_DIR}. "
            "Copia il tuo modello Piper (model.onnx + model.onnx.json) nella cartella."
        )
    model_path = onnx_files[0]
    config_path = Path(str(model_path) + ".json")
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config Piper mancante: {config_path}. "
            "Assicurati che il file .onnx.json sia nella stessa cartella del modello."
        )
    return model_path, config_path


def _cleanup_audio_out():
    """Mantiene al massimo AUDIO_MAX_FILES file in audio_out/, rimuove i più vecchi."""
    files = sorted(AUDIO_OUT_DIR.glob("*.wav"), key=lambda f: f.stat().st_mtime)
    to_delete = len(files) - AUDIO_MAX_FILES
    if to_delete > 0:
        for f in files[:to_delete]:
            try:
                f.unlink()
                logger.info(f"Audio rimosso (cleanup): {f.name}")
            except Exception as e:
                logger.warning(f"Impossibile rimuovere {f.name}: {e}")


class PiperPipeline:
    def __init__(self):
        model_path, config_path = _find_model()
        logger.info(f"Caricamento modello Piper: {model_path.name}")
        self.voice = PiperVoice.load(str(model_path), config_path=str(config_path))
        logger.info("Modello Piper caricato.")

    def synthesize(self, text: str) -> bytes:
        """Sintetizza testo → WAV bytes, salva in audio_out/."""
        _cleanup_audio_out()

        buf = io.BytesIO()
        with self.voice.synthesize_wav(text, buf):
            pass
        wav_bytes = buf.getvalue()

        # Salva su disco
        filename = f"audio_{int(time.time() * 1000)}.wav"
        out_path = AUDIO_OUT_DIR / filename
        out_path.write_bytes(wav_bytes)
        logger.info(f"Audio salvato: {filename} ({len(wav_bytes)} bytes)")

        return wav_bytes
```

- [ ] **Step 2: Commit**

```bash
git add AI.Voice/pipeline.py
git commit -m "feat(AI.Voice): rewrite pipeline as pure Piper TTS, save to audio_out/"
```

---

## Task 5: AI.Voice — server.py (aggiorna import)

**Files:**
- Modify: `AI.Voice/server.py`

- [ ] **Step 1: Aggiorna server.py**

Sostituisci l'intero file con:
```python
import logging
import logging.handlers
import os
from flask import Flask, request, Response, jsonify
from pipeline import PiperPipeline
from config import HOST, PORT

log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

logger.info("Inizializzazione Piper TTS pipeline...")
pipeline = PiperPipeline()
logger.info("Pipeline pronta. Server in avvio...")


@app.post("/speak")
def speak():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Il campo 'text' è obbligatorio."}), 400

    logger.info(f"Sintesi: {text!r}")
    try:
        audio = pipeline.synthesize(text)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error("Errore durante la sintesi:\n" + tb)
        return jsonify({"error": str(e), "traceback": tb}), 500

    return Response(audio, mimetype="audio/wav")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, threaded=False)
```

- [ ] **Step 2: Commit**

```bash
git add AI.Voice/server.py
git commit -m "feat(AI.Voice): update server to use PiperPipeline"
```

---

## Task 6: AI.Brain — voice_text nel done event

**Files:**
- Modify: `AI.Brain/AInterface/request.py` (line 344–349 e 384)

- [ ] **Step 1: Aggiungi voice_text all'evento done nel path "risposta finale"**

Trova il blocco (intorno a riga 344–349):
```python
        # Risposta finale senza tool calls
        if finish_reason == "stop" or not tool_calls_acc:
            history.append({"role": "assistant", "content": full_content})
            history[:] = _prune_history(history)
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return
```

Sostituisci con:
```python
        # Risposta finale senza tool calls
        if finish_reason == "stop" or not tool_calls_acc:
            history.append({"role": "assistant", "content": full_content})
            history[:] = _prune_history(history)
            yield f"data: {json.dumps({'type': 'done', 'voice_text': full_content})}\n\n"
            return
```

- [ ] **Step 2: Aggiungi voice_text anche all'evento done di fallback (fine loop)**

Trova (intorno a riga 384):
```python
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
```

Sostituisci con:
```python
    yield f"data: {json.dumps({'type': 'done', 'voice_text': ''})}\n\n"
```

- [ ] **Step 3: Commit**

```bash
git add AI.Brain/AInterface/request.py
git commit -m "feat(AI.Brain): include voice_text in done SSE event"
```

---

## Task 7: Bmo.Api — bmo_config.json e ChatRequest

**Files:**
- Modify: `Bmo.Api/bmo_config.json`
- Modify: `Bmo.Api/Models/ChatRequest.cs`

- [ ] **Step 1: Aggiorna bmo_config.json**

Aggiungi `dev_mode` e `audio_max_files`:
```json
{
  "version": "0.1",
  "onboard_done": true,
  "dev_mode": true,
  "workspace_path": "../workspace",
  "services": {
    "ai_brain": {
      "port": 8000
    },
    "bmo_api": {
      "port": 5271
    },
    "dashboard": {
      "port": 3000
    },
    "ai_voice": {
      "enabled": true,
      "port": 5050,
      "audio_max_files": 10
    }
  },
  "agent": {
    "name": "B.M.O.",
    "model": "google/gemini-2.0-flash-001",
    "max_tool_iterations": 5
  },
  "tools": {
    "enabled": true,
    "log_all": true,
    "show_in_chat": true
  },
  "context": {
    "max_tokens": 8000,
    "pruning_threshold": 0.8,
    "compaction_enabled": true
  }
}
```

- [ ] **Step 2: Aggiorna ChatRequest.cs**

Sostituisci l'intero file con:
```csharp
namespace Bmo.Api.Models;

public class ChatRequest
{
    public string Message { get; set; } = string.Empty;
    public bool Tts { get; set; } = false;
}
```

- [ ] **Step 3: Commit**

```bash
git add Bmo.Api/bmo_config.json Bmo.Api/Models/ChatRequest.cs
git commit -m "feat(Bmo.Api): add dev_mode/audio_max_files config, add Tts to ChatRequest"
```

---

## Task 8: Bmo.Api — VoiceClient.cs

**Files:**
- Create: `Bmo.Api/Services/VoiceClient.cs`

- [ ] **Step 1: Crea VoiceClient.cs**

```csharp
namespace Bmo.Api.Services;

/// <summary>
/// Client HTTP per AI.Voice (Flask TTS, porta 5050).
/// Chiama POST /speak, restituisce i bytes WAV.
/// Ritorna null se il servizio non è raggiungibile o si verifica un errore.
/// </summary>
public class VoiceClient(HttpClient httpClient, ILogger<VoiceClient> logger)
{
    public async Task<byte[]?> SpeakAsync(string text, CancellationToken ct = default)
    {
        try
        {
            var resp = await httpClient.PostAsJsonAsync("speak", new { text }, ct);
            if (!resp.IsSuccessStatusCode)
            {
                logger.LogWarning("AI.Voice /speak returned {Status}", resp.StatusCode);
                return null;
            }
            return await resp.Content.ReadAsByteArrayAsync(ct);
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "AI.Voice non raggiungibile, audio saltato");
            return null;
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add Bmo.Api/Services/VoiceClient.cs
git commit -m "feat(Bmo.Api): add VoiceClient HTTP service for AI.Voice"
```

---

## Task 9: Bmo.Api — Program.cs (registra VoiceClient)

**Files:**
- Modify: `Bmo.Api/Program.cs`

- [ ] **Step 1: Aggiungi registrazione VoiceClient dopo quella di PythonClient**

Trova il blocco:
```csharp
var pythonBaseUrl = builder.Configuration["PythonApi:BaseUrl"] ?? "http://localhost:8000/";
builder.Services.AddHttpClient<PythonClient>(client =>
{
    client.BaseAddress = new Uri(pythonBaseUrl);
    client.Timeout = TimeSpan.FromSeconds(60);
});
```

Aggiungi dopo:
```csharp
var voicePort = builder.Configuration["services:ai_voice:port"] ?? "5050";
builder.Services.AddHttpClient<VoiceClient>(client =>
{
    client.BaseAddress = new Uri($"http://localhost:{voicePort}/");
    client.Timeout = TimeSpan.FromSeconds(15);
});
```

- [ ] **Step 2: Commit**

```bash
git add Bmo.Api/Program.cs
git commit -m "feat(Bmo.Api): register VoiceClient HttpClient"
```

---

## Task 10: Bmo.Api — ChatController.cs (TTS intercept)

**Files:**
- Modify: `Bmo.Api/Controllers/ChatController.cs`
- Modify: `Bmo.Api/Services/PythonClient.cs`

- [ ] **Step 1: Aggiungi ReadStreamAsync a PythonClient.cs**

Aggiungi questo metodo dopo `StreamMessageAsync`:
```csharp
/// <summary>
/// Legge lo stream SSE da AI.Brain riga per riga.
/// Usato dal ChatController per intercettare l'evento done e iniettare l'audio.
/// </summary>
public async IAsyncEnumerable<string> ReadStreamLinesAsync(
    string message,
    [System.Runtime.CompilerServices.EnumeratorCancellation] CancellationToken ct)
{
    using var req = new HttpRequestMessage(HttpMethod.Post, "chat/stream");
    req.Content = JsonContent.Create(new { message });

    using var resp = await httpClient.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
    resp.EnsureSuccessStatusCode();

    await using var stream = await resp.Content.ReadAsStreamAsync(ct);
    using var reader = new System.IO.StreamReader(stream);

    while (!reader.EndOfStream && !ct.IsCancellationRequested)
    {
        var line = await reader.ReadLineAsync(ct);
        if (line is not null)
            yield return line;
    }
}
```

Aggiungi anche `using System.Collections.Generic;` se necessario (in .NET 10 è incluso).

- [ ] **Step 2: Riscrivi ChatController.cs**

Sostituisci l'intero file con:
```csharp
using System.Text;
using System.Text.Json;
using Bmo.Api.Models;
using Bmo.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace Bmo.Api.Controllers;

[ApiController]
[Route("api/chat")]
public class ChatController(
    ChatService chatService,
    VoiceClient voiceClient,
    IConfiguration configuration) : ControllerBase
{
    // ── Non-streaming (retrocompatibilità) ───────────────────────────────────

    [HttpPost]
    public async Task<IActionResult> Chat([FromBody] ChatRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Message))
            return BadRequest(new { error = "Il messaggio è vuoto." });

        var reply = await chatService.ProcessMessageAsync(request.Message);
        return Ok(new ChatResponse { Reply = reply });
    }

    // ── Streaming SSE ────────────────────────────────────────────────────────

    [HttpPost("stream")]
    public async Task Stream([FromBody] ChatRequest request, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(request.Message))
        {
            Response.StatusCode = 400;
            return;
        }

        Response.ContentType = "text/event-stream";
        Response.Headers["Cache-Control"]     = "no-cache";
        Response.Headers["X-Accel-Buffering"] = "no";

        // Se TTS non richiesto: path diretto (nessun overhead)
        if (!request.Tts)
        {
            await chatService.StreamAsync(request.Message, Response.Body, ct);
            return;
        }

        // Path TTS: intercetta stream riga per riga per estrarre voice_text
        bool devMode = configuration.GetValue<bool>("dev_mode", true);

        await foreach (var line in chatService.ReadStreamLinesAsync(request.Message, ct))
        {
            // Intercetta la riga "data: {...done...}"
            if (line.StartsWith("data: "))
            {
                var raw = line[6..].Trim();
                try
                {
                    using var doc = JsonDocument.Parse(raw);
                    var root = doc.RootElement;

                    if (root.TryGetProperty("type", out var typeProp) &&
                        typeProp.GetString() == "done")
                    {
                        // Estrai voice_text
                        var voiceText = root.TryGetProperty("voice_text", out var vt)
                            ? vt.GetString() ?? string.Empty
                            : string.Empty;

                        // Chiama AI.Voice se c'è testo da vocalizzare
                        if (!string.IsNullOrWhiteSpace(voiceText))
                        {
                            var audioBytes = await voiceClient.SpeakAsync(voiceText, ct);

                            // Inietta evento audio solo in dev_mode
                            if (audioBytes is not null && devMode)
                            {
                                var b64  = Convert.ToBase64String(audioBytes);
                                var json = $"{{\"type\":\"audio\",\"data\":\"{b64}\"}}";
                                var evt  = Encoding.UTF8.GetBytes($"data: {json}\n\n");
                                await Response.Body.WriteAsync(evt, ct);
                                await Response.Body.FlushAsync(ct);
                            }
                        }

                        // Scrivi done event (senza voice_text, risparmia bandwidth)
                        var doneBytes = Encoding.UTF8.GetBytes("data: {\"type\":\"done\"}\n\n");
                        await Response.Body.WriteAsync(doneBytes, ct);
                        await Response.Body.FlushAsync(ct);
                        return;
                    }
                }
                catch
                {
                    // JSON non parsabile: passa riga così com'è
                }
            }

            // Passa la riga al client immediatamente
            var lineBytes = Encoding.UTF8.GetBytes(line + "\n");
            await Response.Body.WriteAsync(lineBytes, ct);
            await Response.Body.FlushAsync(ct);
        }
    }

    // ── Session reset ────────────────────────────────────────────────────────

    [HttpPost("reset")]
    public async Task<IActionResult> Reset()
    {
        await chatService.ResetAsync();
        return Ok(new { status = "ok" });
    }
}
```

- [ ] **Step 3: Aggiorna ChatService.cs per esporre ReadStreamLinesAsync**

Sostituisci l'intero file con:
```csharp
namespace Bmo.Api.Services;

public class ChatService(PythonClient pythonClient)
{
    public async Task<string> ProcessMessageAsync(string message) =>
        await pythonClient.SendMessageAsync(message);

    public async Task StreamAsync(string message, Stream outputStream, CancellationToken ct) =>
        await pythonClient.StreamMessageAsync(message, outputStream, ct);

    public IAsyncEnumerable<string> ReadStreamLinesAsync(string message, CancellationToken ct) =>
        pythonClient.ReadStreamLinesAsync(message, ct);

    public async Task ResetAsync() =>
        await pythonClient.ResetSessionAsync();
}
```

- [ ] **Step 4: Commit**

```bash
git add Bmo.Api/Controllers/ChatController.cs Bmo.Api/Services/PythonClient.cs Bmo.Api/Services/ChatService.cs
git commit -m "feat(Bmo.Api): add TTS SSE intercept in ChatController, ReadStreamLinesAsync"
```

---

## Task 11: Dashboard — TTS checkbox, audio player, dev_mode settings

**Files:**
- Modify: `dashboard-bmo/app/page.tsx`

Questo task modifica `page.tsx` in 5 punti separati. Fai ogni modifica nell'ordine indicato.

- [ ] **Step 1: Aggiorna il tipo BmoConfig**

Trova:
```typescript
type BmoConfig = {
    version: string;
    workspace_path: string;
    agent: { name: string; model: string; max_tool_iterations: number };
    tools: { enabled: boolean; log_all: boolean; show_in_chat: boolean };
    context: { max_tokens: number; pruning_threshold: number; compaction_enabled: boolean };
};
```

Sostituisci con:
```typescript
type BmoConfig = {
    version: string;
    workspace_path: string;
    dev_mode: boolean;
    agent: { name: string; model: string; max_tool_iterations: number };
    tools: { enabled: boolean; log_all: boolean; show_in_chat: boolean };
    context: { max_tokens: number; pruning_threshold: number; compaction_enabled: boolean };
};
```

- [ ] **Step 2: Aggiorna il tipo Message**

Trova:
```typescript
type Message = {
    id: number;
    role: "user" | "ai" | "tool";
    text: string;
    time: string;
    toolName?: string;
    toolCallId?: string;
    toolResult?: string;
};
```

Sostituisci con:
```typescript
type Message = {
    id: number;
    role: "user" | "ai" | "tool";
    text: string;
    time: string;
    toolName?: string;
    toolCallId?: string;
    toolResult?: string;
    audioUrl?: string;
};
```

- [ ] **Step 3: Aggiungi stato ttsEnabled e audioUrls nel componente Home**

Trova (dopo le dichiarazioni di stato esistenti):
```typescript
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
```

Aggiungi prima di quelle righe:
```typescript
    const [ttsEnabled, setTtsEnabled] = useState(false);
    const audioUrlsRef = useRef<string[]>([]);
```

- [ ] **Step 4: Aggiungi helper b64ToUrl e aggiorna handleSend per TTS**

Aggiungi questa funzione helper subito sopra `handleSend`:
```typescript
    function b64ToUrl(b64: string): string {
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const blob = new Blob([bytes], { type: "audio/wav" });
        const url = URL.createObjectURL(blob);
        // FIFO: max 10 blob URLs in memoria
        audioUrlsRef.current.push(url);
        if (audioUrlsRef.current.length > 10) {
            const old = audioUrlsRef.current.shift()!;
            URL.revokeObjectURL(old);
        }
        return url;
    }
```

Poi trova nel body della fetch stream:
```typescript
            const res = await fetch(`${API_URL}/api/chat/stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
                cache: "no-store",
            });
```

Sostituisci con:
```typescript
            const res = await fetch(`${API_URL}/api/chat/stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text, tts: ttsEnabled && (config?.dev_mode ?? false) }),
                cache: "no-store",
            });
```

- [ ] **Step 5: Aggiungi case "audio" nello switch SSE**

Trova nel blocco switch degli eventi SSE:
```typescript
                        case "done":
                            break;
```

Sostituisci con:
```typescript
                        case "audio": {
                            const url = b64ToUrl(event.data as string);
                            setMessages(prev => prev.map(m =>
                                m.id === aiMsgId ? { ...m, audioUrl: url } : m
                            ));
                            break;
                        }
                        case "done":
                            break;
```

- [ ] **Step 6: Aggiungi player audio nel render del messaggio AI**

Trova nel render dei messaggi (nel branch `!isUser && !isTool`):
```typescript
                        <span>{msg.text}</span>
                        {loading && !isUser && i === messages.length - 1 && msg.text === "" && (
                            <span style={{ color: "var(--text-muted)", animation: "pulse 1s infinite" }}>▌</span>
                        )}
```

Sostituisci con:
```typescript
                        <span>{msg.text}</span>
                        {loading && !isUser && i === messages.length - 1 && msg.text === "" && (
                            <span style={{ color: "var(--text-muted)", animation: "pulse 1s infinite" }}>▌</span>
                        )}
                        {!isUser && msg.audioUrl && (
                            <div style={{ marginTop: "6px" }}>
                                <audio
                                    controls
                                    src={msg.audioUrl}
                                    style={{ height: "32px", width: "100%", maxWidth: "260px", borderRadius: "16px" }}
                                />
                            </div>
                        )}
```

- [ ] **Step 7: Aggiungi TTS checkbox nell'area input (visibile solo in dev_mode)**

Trova l'area input, il div wrapper che contiene la textarea e il pulsante send. Trova:
```typescript
                    {/* Input */}
                    <div style={{
                        padding: "12px 16px 14px", background: "var(--sidebar-bg)",
                        borderTop: "1px solid var(--border)",
                        display: "flex", alignItems: "flex-end", gap: "10px",
                    }}>
```

Subito dopo questo div di apertura, aggiungi il checkbox TTS (prima della textarea wrapper):
```typescript
                        {/* TTS toggle — visibile solo in dev_mode */}
                        {config?.dev_mode && (
                            <div style={{
                                display: "flex", alignItems: "center", gap: "6px",
                                flexShrink: 0, paddingBottom: "10px",
                            }}>
                                <Toggle value={ttsEnabled} onChange={setTtsEnabled}/>
                                <span style={{ fontSize: "11px", color: ttsEnabled ? "var(--accent)" : "var(--text-muted)", whiteSpace: "nowrap" }}>
                                    🔊
                                </span>
                            </div>
                        )}
```

- [ ] **Step 8: Aggiungi dev_mode nel settings panel**

Trova nella funzione `SettingsView`, il blocco delle sezioni. Aggiungi una nuova sezione "Sistema" prima delle sezioni esistenti. Trova:
```typescript
                <Section title="Agente"/>
```

Aggiungi prima:
```typescript
                <Section title="Sistema"/>
                <Row label="Dev mode (audio in chat)">
                    <Toggle value={local.dev_mode ?? true} onChange={v => setLocal(p => ({ ...p, dev_mode: v }))}/>
                </Row>

```

- [ ] **Step 9: Commit**

```bash
git add dashboard-bmo/app/page.tsx
git commit -m "feat(dashboard): TTS checkbox, audio player, dev_mode setting"
```

---

## Task 12: start.py — semplifica setup AI.Voice

**Files:**
- Modify: `start.py`

- [ ] **Step 1: Sostituisci la funzione setup_voice_venv()**

Trova l'intera funzione `setup_voice_venv()` (da `def setup_voice_venv():` fino alla riga `print(f"  Il server AI.Voice partirà ma fallirà senza questi file.")`) e sostituiscila con:

```python
def setup_voice_venv():
    """Crea il venv per AI.Voice e installa le dipendenze (solo flask + piper-tts)."""
    venv_dir = VOICE_DIR / "venv"
    req_file = VOICE_DIR / "requirements.txt"
    py_exe   = _voice_py_exe()

    if SYSTEM == "Windows":
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_dir / "bin" / "pip"

    # Crea il venv se non esiste
    if not venv_dir.exists():
        _step("Creazione virtual environment AI.Voice...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        _ok("Virtual environment AI.Voice creato")

    # Controlla se le dipendenze sono già installate
    probe = subprocess.run(
        [str(py_exe), "-c", "import flask; import piper"],
        capture_output=True
    )
    if probe.returncode == 0:
        _ok("Dipendenze AI.Voice già installate")
    else:
        _require_internet()
        _step("Installazione dipendenze AI.Voice (flask + piper-tts)...")
        subprocess.run([str(pip_exe), "install", "-r", str(req_file)], check=True)
        _ok("Dipendenze AI.Voice installate")

    # Verifica modello Piper custom in models/bmo/
    bmo_model_dir = VOICE_DIR / "models" / "bmo"
    bmo_model_dir.mkdir(parents=True, exist_ok=True)
    onnx_files = list(bmo_model_dir.glob("*.onnx"))

    if not onnx_files:
        print(f"\n  {CR2}Nessun modello Piper trovato in AI.Voice/models/bmo/{CR}")
        print(f"  {CY}Copia i file del tuo modello addestrato:{CR}")
        print(f"    {CYL}  model.onnx{CR}       — il modello ONNX")
        print(f"    {CYL}  model.onnx.json{CR}  — la config Piper")
        print(f"\n  Il server AI.Voice non partirà senza questi file.\n")
        input(f"  {CG}Premi INVIO quando i file sono pronti...{CR} ")
        # Verifica di nuovo dopo il prompt
        onnx_files = list(bmo_model_dir.glob("*.onnx"))
        if not onnx_files:
            _warn("Modello ancora non trovato — il server TTS potrebbe non funzionare.")
        else:
            _ok(f"Modello Piper trovato: {onnx_files[0].name}")
    else:
        _ok(f"Modello Piper trovato: {onnx_files[0].name}")
```

- [ ] **Step 2: Aggiorna il testo dell'onboarding AI.Voice**

Trova:
```python
    # AI.Voice — server TTS opzionale
    print(f"\n  {CY}AI.Voice — Server TTS (Piper + RVC voce BMO):{CR}")
    print( "  Richiede PyTorch (~700MB download) e ~2GB RAM durante l'uso.")
    print( "  Necessario solo se vuoi che BMO parli con la voce addestrata.")
```

Sostituisci con:
```python
    # AI.Voice — server TTS opzionale
    print(f"\n  {CY}AI.Voice — Server TTS (Piper voce custom):{CR}")
    print( "  Richiede un modello Piper ONNX addestrato (model.onnx + model.onnx.json).")
    print( "  Necessario solo se vuoi che BMO risponda con la voce sintetizzata.")
```

- [ ] **Step 3: Commit**

```bash
git add start.py
git commit -m "feat(start.py): simplify AI.Voice setup, add Piper model interactive check"
```

---

## Task 13: .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Aggiorna .gitignore**

Trova la sezione AI.Voice (o aggiungila se non c'è) e assicurati che contenga:
```
# AI.Voice
AI.Voice/venv/
AI.Voice/audio_out/*.wav
AI.Voice/models/bmo/*.onnx
AI.Voice/models/bmo/*.json
AI.Voice/server.log
```

Rimuovi eventuali riferimenti a `export/bmo_rvc_model/` se presenti.

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore for new AI.Voice structure"
```

---

## Task 14: Documentazione — CLAUDE.md e README.md

**Files:**
- Modify: `CLAUDE.md`
- Modify: `README.md` (se esiste)

- [ ] **Step 1: Aggiorna CLAUDE.md**

Sezioni da aggiornare:
1. **Struttura**: rimuovi `export/bmo_rvc_model/`, aggiungi `AI.Voice/models/bmo/` e `AI.Voice/audio_out/`
2. **Setup AI.Voice**: rimpiazza la sequenza 6-step con quella semplificata (solo `pip install -r requirements.txt` + model check)
3. **Dipendenze critiche**: rimuovi tutto il blocco su rvc-python/numpy/fairseq/onnxruntime; aggiungi nota su modello Piper custom
4. **Modelli RVC**: rimpiazza sezione con "Modello Piper custom"
5. **Config**: aggiungi `dev_mode` e `audio_max_files`

Il contenuto aggiornato della sezione struttura:
```
├── AI.Voice/             # Server TTS Flask (porta 5050) — Piper TTS custom
│   ├── venv/             # Virtual environment Python
│   ├── requirements.txt  # flask, piper-tts
│   ├── server.py         # Flask server
│   ├── pipeline.py       # Pipeline TTS (Piper puro)
│   ├── config.py         # Config: percorsi modello, porta, max audio files
│   ├── models/bmo/       # Modello Piper custom (.onnx + .onnx.json) — da fornire
│   └── audio_out/        # File WAV generati (rolling cleanup, max 10)
```

Sezione dipendenze:
```
## Dipendenze AI.Voice

- **piper-tts**: wrapper Python per inferenza Piper ONNX
- Nessuna dipendenza da torch/RVC/fairseq/CUDA
- Installazione: solo `pip install -r requirements.txt`
```

Sezione modello:
```
## Modello Piper custom

Vanno copiati manualmente in `AI.Voice/models/bmo/`:
- `model.onnx`      — modello ONNX addestrato con Piper
- `model.onnx.json` — config Piper del modello

Lo script di onboarding attende che questi file siano presenti prima di continuare.
```

Nuovi config:
```
- `dev_mode` → true = player audio in chat (web); false = solo salvataggio su disco
- `services.ai_voice.audio_max_files` → max WAV tenuti in audio_out/ (default 10)
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for Piper-only TTS, remove RVC references"
```

---

## Task 15: Verifica finale e PR

- [ ] **Step 1: Verifica build C#**

```bash
cd Bmo.Api && dotnet build
```
Atteso: Build succeeded, 0 Warning(s), 0 Error(s)

- [ ] **Step 2: Verifica sintassi Python AI.Voice**

```bash
cd AI.Voice && python -c "import ast; ast.parse(open('config.py').read()); ast.parse(open('pipeline.py').read()); ast.parse(open('server.py').read()); print('OK')"
```
Atteso: `OK`

- [ ] **Step 3: Verifica sintassi Python AI.Brain**

```bash
cd AI.Brain && python -c "import ast; ast.parse(open('AInterface/request.py').read()); print('OK')"
```
Atteso: `OK`

- [ ] **Step 4: Verifica TypeScript dashboard**

```bash
cd dashboard-bmo && npx tsc --noEmit
```
Atteso: nessun errore TypeScript

- [ ] **Step 5: Crea PR**

```bash
git push -u origin claude/youthful-kalam
gh pr create \
  --title "feat: Replace RVC+Piper TTS with Piper-only, add audio in chat" \
  --body "$(cat <<'EOF'
## Summary
- Rimozione completa di RVC, torch, fairseq, faiss da AI.Voice
- AI.Voice ora usa solo Piper TTS con modello ONNX custom (cartella models/bmo/)
- Audio generati salvati in audio_out/ con rolling cleanup (max 10 file)
- AI.Brain include voice_text nell'evento done per controllo esplicito TTS
- Bmo.Api intercetta done event, chiama AI.Voice, inietta evento audio nel SSE
- Dashboard: TTS checkbox (solo in dev_mode), player audio inline stile WhatsApp
- start.py semplificato: installazione 1-step + pausa interattiva per model check
- Aggiornati CLAUDE.md, .gitignore

## Test plan
- [ ] Avviare con `start.bat`, verificare che AI.Voice parta correttamente
- [ ] Attivare spunta TTS, inviare messaggio, verificare player audio nel bubble
- [ ] Disattivare dev_mode nelle impostazioni, verificare che checkbox TTS scompaia
- [ ] Verificare rolling cleanup: generare >10 audio, verificare rimozione vecchi
- [ ] Verificare che senza modello in models/bmo/ lo script si fermi con prompt

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
