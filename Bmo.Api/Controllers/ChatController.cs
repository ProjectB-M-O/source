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

        // Se TTS non richiesto: path diretto senza overhead
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
                    // JSON non parsabile
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

    // ── History retrieval ────────────────────────────────────────────────────

    [HttpGet("history")]
    public async Task<IActionResult> History()
    {
        var json = await chatService.GetHistoryAsync();
        return Content(json, "application/json");
    }
}
