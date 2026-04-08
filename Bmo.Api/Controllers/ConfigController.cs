using System.Text.Json;
using Microsoft.AspNetCore.Mvc;

namespace Bmo.Api.Controllers;

[ApiController]
[Route("api/config")]
public class ConfigController(IWebHostEnvironment env) : ControllerBase
{
    private string ConfigPath => Path.Combine(env.ContentRootPath, "bmo_config.json");

    [HttpGet]
    public async Task<IActionResult> Get()
    {
        if (!System.IO.File.Exists(ConfigPath))
            return NotFound(new { error = "bmo_config.json non trovato." });

        var json = await System.IO.File.ReadAllTextAsync(ConfigPath);
        return Content(json, "application/json");
    }

    [HttpPut]
    public async Task<IActionResult> Put([FromBody] JsonDocument config)
    {
        var options = new JsonSerializerOptions { WriteIndented = true };
        var json    = JsonSerializer.Serialize(config, options);
        await System.IO.File.WriteAllTextAsync(ConfigPath, json);
        return Ok(new { status = "saved" });
    }

    private string EnvPath
    {
        get
        {
            var path = Path.GetFullPath(Path.Combine(env.ContentRootPath, "..", "AI.Brain", ".env"));
            var root = Path.GetFullPath(Path.Combine(env.ContentRootPath, "..")) + Path.DirectorySeparatorChar;
            if (!path.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Resolved .env path escapes project root");
            return path;
        }
    }

    private static Dictionary<string, string> ParseEnvFile(string path)
    {
        var dict = new Dictionary<string, string>();
        if (!System.IO.File.Exists(path))
            return dict;

        foreach (var line in System.IO.File.ReadLines(path))
        {
            if (string.IsNullOrWhiteSpace(line) || line.TrimStart().StartsWith('#'))
                continue;

            var idx = line.IndexOf('=');
            if (idx < 1) continue;

            var key   = line[..idx].Trim();
            var value = line[(idx + 1)..];
            if (!string.IsNullOrEmpty(key))
                dict[key] = value;
        }

        return dict;
    }

    private static string MaskValue(string key, string value)
    {
        var upper = key.ToUpperInvariant();
        if (upper.Contains("KEY") || upper.Contains("SECRET") ||
            upper.Contains("TOKEN") || upper.Contains("PASSWORD"))
        {
            return value.Length <= 4 ? "****" : $"****{value[^4..]}";
        }
        return value;
    }

    [HttpGet("env")]
    public IActionResult GetEnv()
    {
        var dict = ParseEnvFile(EnvPath);
        var masked = dict.ToDictionary(
            kvp => kvp.Key,
            kvp => MaskValue(kvp.Key, kvp.Value)
        );
        return Ok(masked);
    }

    [HttpPut("env")]
    public async Task<IActionResult> PutEnv([FromBody] JsonDocument body)
    {
        var updates = new Dictionary<string, string>();
        foreach (var prop in body.RootElement.EnumerateObject())
        {
            if (prop.Value.ValueKind == JsonValueKind.String)
            {
                var value = prop.Value.GetString() ?? "";
                if (!value.StartsWith("****") && !string.IsNullOrEmpty(value))
                    updates[prop.Name] = value;
            }
        }

        var existingContent = System.IO.File.Exists(EnvPath) ? await System.IO.File.ReadAllTextAsync(EnvPath) : "";
        var newContent = UpdateEnvContent(existingContent, updates);
        await System.IO.File.WriteAllTextAsync(EnvPath, newContent);

        return Ok(new { status = "saved" });
    }

    private static string UpdateEnvContent(string existingContent, Dictionary<string, string> updates)
    {
        var lines = existingContent.Split('\n').ToList();
        var updated = new HashSet<string>();

        // Update existing key lines in-place
        for (int i = 0; i < lines.Count; i++)
        {
            var line = lines[i];
            var trimmed = line.TrimEnd();
            if (trimmed.Length == 0 || trimmed.StartsWith('#') || !trimmed.Contains('='))
                continue;
            var key = trimmed.Split('=', 2)[0].Trim();
            if (updates.TryGetValue(key, out var newValue))
            {
                lines[i] = $"{key}={newValue}";
                updated.Add(key);
            }
        }

        // Append new keys not already in file
        foreach (var (key, value) in updates)
        {
            if (!updated.Contains(key))
                lines.Add($"{key}={value}");
        }

        return string.Join('\n', lines);
    }
}
