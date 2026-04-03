using Bmo.Api.Models;
using Bmo.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace Bmo.Api.Controllers;

[ApiController]
[Route("api/chat")]
public class ChatController(ChatService chatService) : ControllerBase
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
        Response.Headers["Cache-Control"]      = "no-cache";
        Response.Headers["X-Accel-Buffering"]  = "no";

        await chatService.StreamAsync(request.Message, Response.Body, ct);
    }

    // ── Session reset ────────────────────────────────────────────────────────

    [HttpPost("reset")]
    public async Task<IActionResult> Reset()
    {
        await chatService.ResetAsync();
        return Ok(new { status = "ok" });
    }
}
