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
}
