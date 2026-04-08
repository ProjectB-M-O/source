namespace Bmo.Api.Models;

public class ChatRequest
{
    public string Message { get; set; } = string.Empty;
    public bool Tts { get; set; } = false;
}
