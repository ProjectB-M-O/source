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
