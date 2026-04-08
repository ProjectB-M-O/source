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

    private string EnvPath => Path.GetFullPath(Path.Combine(env.ContentRootPath, "..", "AI.Brain", ".env"));

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
        var dict = ParseEnvFile(EnvPath);

        foreach (var prop in body.RootElement.EnumerateObject())
        {
            var key   = prop.Name;
            var value = prop.Value.GetString() ?? string.Empty;

            if (string.IsNullOrEmpty(key))
                continue;

            // Skip masked values — keep existing
            if (value.StartsWith("****"))
                continue;

            dict[key] = value;
        }

        var lines = dict.Select(kvp => $"{kvp.Key}={kvp.Value}");
        await System.IO.File.WriteAllTextAsync(EnvPath, string.Join("\n", lines) + "\n");

        return Ok(new { status = "saved" });
    }
}
