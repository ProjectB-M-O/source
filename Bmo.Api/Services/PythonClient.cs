using System.Net.Http.Json;

namespace Bmo.Api.Services;

public class PythonClient(HttpClient httpClient)
{
    // ── Non-streaming ────────────────────────────────────────────────────────

    public async Task<string> SendMessageAsync(string message)
    {
        var response = await httpClient.PostAsJsonAsync("chat", new { message });
        response.EnsureSuccessStatusCode();
        var result = await response.Content.ReadFromJsonAsync<PythonChatResponse>();
        return result?.Reply ?? "Nessuna risposta dal backend Python.";
    }

    // ── Streaming proxy ──────────────────────────────────────────────────────

    public async Task StreamMessageAsync(string message, Stream outputStream, CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Post, "chat/stream");
        req.Content = JsonContent.Create(new { message });

        using var resp = await httpClient.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
        resp.EnsureSuccessStatusCode();

        await using var pythonStream = await resp.Content.ReadAsStreamAsync(ct);
        await pythonStream.CopyToAsync(outputStream, ct);
        await outputStream.FlushAsync(ct);
    }

    // ── Streaming line-by-line (per intercept TTS) ───────────────────────────

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

        while (!ct.IsCancellationRequested)
        {
            var line = await reader.ReadLineAsync(ct);
            if (line is null) break;
            yield return line;
        }
    }

    // ── Session reset ────────────────────────────────────────────────────────

    public async Task ResetSessionAsync()
    {
        var resp = await httpClient.PostAsync("chat/reset", null);
        resp.EnsureSuccessStatusCode();
    }

    // ── Private ──────────────────────────────────────────────────────────────

    private sealed class PythonChatResponse
    {
        public string Reply { get; set; } = string.Empty;
    }
}
