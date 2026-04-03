using System.Text.Json;

namespace Bmo.Api.Models;

public class ToolExecuteRequest
{
    public string ToolName { get; set; } = string.Empty;
    public Dictionary<string, JsonElement> Arguments { get; set; } = new();
}

public class ToolExecuteResponse
{
    public bool Success { get; set; }
    public string Result { get; set; } = string.Empty;
    public string? Error { get; set; }
}
