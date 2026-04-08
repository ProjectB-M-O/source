using System.Text.Json;
using Bmo.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace Bmo.Api.Controllers;

[ApiController]
[Route("api/skills")]
public class SkillsController(WorkspaceService workspace) : ControllerBase
{
    // GET /api/skills → return skills.json content
    [HttpGet]
    public async Task<IActionResult> GetSkills()
    {
        var json = await workspace.GetSkillsJsonAsync();
        return Content(json, "application/json");
    }

    // GET /api/skills/content?file=filename.md → return MD content
    [HttpGet("content")]
    public async Task<IActionResult> GetContent([FromQuery] string file)
    {
        if (string.IsNullOrWhiteSpace(file))
            return BadRequest(new { error = "file parameter required" });
        try
        {
            var content = await workspace.GetSkillContentAsync(file);
            return Ok(new { content });
        }
        catch (FileNotFoundException)
        {
            return NotFound(new { error = $"Skill file not found: {file}" });
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }

    // PUT /api/skills/content?file=filename.md — body: {"content": "..."}
    [HttpPut("content")]
    public async Task<IActionResult> SaveContent([FromQuery] string file, [FromBody] SkillContentRequest body)
    {
        if (string.IsNullOrWhiteSpace(file))
            return BadRequest(new { error = "file parameter required" });
        try
        {
            await workspace.SaveSkillContentAsync(file, body.Content);
            return Ok(new { status = "saved" });
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }

    // POST /api/skills — body: {"name": "...", "description": "...", "filename": "..."}
    [HttpPost]
    public async Task<IActionResult> CreateSkill([FromBody] CreateSkillRequest body)
    {
        if (string.IsNullOrWhiteSpace(body.Name) || string.IsNullOrWhiteSpace(body.Filename))
            return BadRequest(new { error = "name and filename are required" });

        try
        {
            // Create empty MD file
            await workspace.SaveSkillContentAsync(body.Filename, $"# {body.Name}\n\n");

            // Update skills.json
            var json = await workspace.GetSkillsJsonAsync();
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            // Build updated capabilities array
            var capabilities = root.GetProperty("capabilities")
                .EnumerateArray()
                .Select(e => e.GetRawText())
                .ToList();

            var newEntry = JsonSerializer.Serialize(new
            {
                name = body.Name,
                description = body.Description ?? "",
                file = $"skills/{body.Filename}"
            });
            capabilities.Add(newEntry);

            var learnedBehaviors = root.TryGetProperty("learned_behaviors", out var lb)
                ? lb.GetRawText()
                : "[]";

            var updatedJson = $"{{\"capabilities\":[{string.Join(",", capabilities)}],\"learned_behaviors\":{learnedBehaviors}}}";

            // Pretty-print
            var pretty = JsonSerializer.Serialize(
                JsonDocument.Parse(updatedJson).RootElement,
                new JsonSerializerOptions { WriteIndented = true });

            await workspace.SaveSkillsJsonAsync(pretty);

            return Ok(new { status = "created", filename = body.Filename });
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }
}

public record SkillContentRequest(string Content);
public record CreateSkillRequest(string Name, string Description, string Filename);
