using System.Security;
using System.Text.Json;
using System.Text.Json.Nodes;
using Bmo.Api.Models;
using Microsoft.Data.Sqlite;

namespace Bmo.Api.Services;

public class ToolService(WorkspaceService ws)
{
    private static readonly HashSet<string> AllowedTools =
    [
        "read_file", "write_file", "list_files",
        "query_memory", "save_memory",
        "read_identity", "update_identity",
        "read_skills", "update_skills"
    ];

    private static readonly JsonSerializerOptions JsonOpts = new() { WriteIndented = true };

    // ── Public entry point ──────────────────────────────────────────────────

    public async Task<ToolExecuteResponse> ExecuteAsync(ToolExecuteRequest request)
    {
        if (!AllowedTools.Contains(request.ToolName))
        {
            var denied = Fail($"Tool '{request.ToolName}' non è nella whitelist.");
            await LogAsync(request.ToolName, request.Arguments, denied);
            return denied;
        }

        ToolExecuteResponse response;
        try
        {
            response = request.ToolName switch
            {
                "read_file"       => await ReadFileAsync(request.Arguments),
                "write_file"      => await WriteFileAsync(request.Arguments),
                "list_files"      => await ListFilesAsync(request.Arguments),
                "query_memory"    => await QueryMemoryAsync(request.Arguments),
                "save_memory"     => await SaveMemoryAsync(request.Arguments),
                "read_identity"   => await ReadJsonFileAsync("identity.json"),
                "update_identity" => await UpdateJsonFileAsync("identity.json", request.Arguments),
                "read_skills"     => await ReadJsonFileAsync("skills.json"),
                "update_skills"   => await UpdateSkillsAsync(request.Arguments),
                _                 => Fail("Tool sconosciuto.")
            };
        }
        catch (SecurityException ex)
        {
            response = Fail($"Accesso negato: {ex.Message}");
        }
        catch (Exception ex)
        {
            response = Fail(ex.Message);
        }

        await LogAsync(request.ToolName, request.Arguments, response);
        return response;
    }

    // ── File tools ──────────────────────────────────────────────────────────

    private Task<ToolExecuteResponse> ReadFileAsync(Dictionary<string, JsonElement> args)
    {
        var path = Sandbox(GetString(args, "path"));
        if (!File.Exists(path))
            return Task.FromResult(Fail("File non trovato."));
        var content = File.ReadAllText(path);
        return Task.FromResult(Ok(content));
    }

    private async Task<ToolExecuteResponse> WriteFileAsync(Dictionary<string, JsonElement> args)
    {
        var path    = Sandbox(GetString(args, "path"));
        var content = GetString(args, "content");
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        await File.WriteAllTextAsync(path, content);
        return Ok("File scritto correttamente.");
    }

    private Task<ToolExecuteResponse> ListFilesAsync(Dictionary<string, JsonElement> args)
    {
        var sub  = args.TryGetValue("path", out var p) ? p.GetString() ?? "" : "";
        var root = Sandbox(sub, allowRoot: true);
        if (!Directory.Exists(root))
            return Task.FromResult(Fail("Cartella non trovata."));

        var entries = Directory.GetFileSystemEntries(root)
            .Select(e => Path.GetRelativePath(ws.FilesPath, e)
                       + (Directory.Exists(e) ? "/" : ""))
            .ToList();

        return Task.FromResult(Ok(JsonSerializer.Serialize(entries)));
    }

    // ── Memory tools ────────────────────────────────────────────────────────

    private Task<ToolExecuteResponse> QueryMemoryAsync(Dictionary<string, JsonElement> args)
    {
        var query = GetString(args, "query");
        using var conn = ws.OpenConnection();
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            SELECT key, value, category FROM memory
            WHERE key LIKE @q OR value LIKE @q OR category LIKE @q
            ORDER BY updated_at DESC LIMIT 20
            """;
        cmd.Parameters.AddWithValue("@q", $"%{query}%");

        var results = new List<object>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
            results.Add(new { key = reader.GetString(0), value = reader.GetString(1), category = reader.GetString(2) });

        return Task.FromResult(Ok(JsonSerializer.Serialize(results)));
    }

    private Task<ToolExecuteResponse> SaveMemoryAsync(Dictionary<string, JsonElement> args)
    {
        var key      = GetString(args, "key");
        var value    = GetString(args, "value");
        var category = args.TryGetValue("category", out var c) ? c.GetString() ?? "general" : "general";
        var now      = DateTime.UtcNow.ToString("o");

        using var conn = ws.OpenConnection();
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO memory (key, value, category, created_at, updated_at)
            VALUES (@key, @value, @cat, @now, @now)
            ON CONFLICT(key) DO UPDATE SET value=@value, category=@cat, updated_at=@now
            """;
        cmd.Parameters.AddWithValue("@key",   key);
        cmd.Parameters.AddWithValue("@value", value);
        cmd.Parameters.AddWithValue("@cat",   category);
        cmd.Parameters.AddWithValue("@now",   now);
        cmd.ExecuteNonQuery();

        return Task.FromResult(Ok($"Memoria '{key}' salvata."));
    }

    // ── Identity / Skills tools ─────────────────────────────────────────────

    private async Task<ToolExecuteResponse> ReadJsonFileAsync(string filename)
    {
        var path = Path.Combine(ws.WorkspacePath, filename);
        if (!File.Exists(path))
            return Fail($"{filename} non trovato.");
        return Ok(await File.ReadAllTextAsync(path));
    }

    private async Task<ToolExecuteResponse> UpdateJsonFileAsync(
        string filename,
        Dictionary<string, JsonElement> args)
    {
        var field = GetString(args, "field");
        if (!args.TryGetValue("value", out var val))
            return Fail("Parametro 'value' mancante.");

        var path = Path.Combine(ws.WorkspacePath, filename);
        var raw  = File.Exists(path) ? await File.ReadAllTextAsync(path) : "{}";
        var node = JsonNode.Parse(raw) as JsonObject ?? new JsonObject();

        node[field] = JsonNode.Parse(val.GetRawText());
        await File.WriteAllTextAsync(path, node.ToJsonString(JsonOpts));
        return Ok($"Campo '{field}' aggiornato in {filename}.");
    }

    private async Task<ToolExecuteResponse> UpdateSkillsAsync(Dictionary<string, JsonElement> args)
    {
        var action      = GetString(args, "action");       // "add" | "remove"
        var skillName   = GetString(args, "skill_name");
        var description = args.TryGetValue("description", out var d) ? d.GetString() ?? skillName : skillName;
        var skillsPath  = Path.Combine(ws.WorkspacePath, "skills.json");

        var raw   = File.Exists(skillsPath) ? await File.ReadAllTextAsync(skillsPath) : "{}";
        var node  = JsonNode.Parse(raw) as JsonObject ?? new JsonObject();
        var array = node["capabilities"] as JsonArray ?? new JsonArray();

        // File path for this skill's MD
        var slug      = string.Concat(skillName.ToLower().Select(c => char.IsLetterOrDigit(c) ? c : '_'));
        var mdRelPath = $"skills/{slug}.md";
        var mdAbsPath = Path.Combine(ws.WorkspacePath, mdRelPath);

        if (action == "add")
        {
            var exists = array.Any(x => x?["name"]?.GetValue<string>() == skillName);
            if (!exists)
            {
                // Create MD file
                var initialContent = args.TryGetValue("initial_content", out var ic)
                    ? ic.GetString() ?? ""
                    : $"# {skillName}\n\n{description}\n";
                await File.WriteAllTextAsync(mdAbsPath, initialContent);

                array.Add(new JsonObject
                {
                    ["name"]        = skillName,
                    ["description"] = description,
                    ["file"]        = mdRelPath
                });
            }
        }
        else if (action == "remove")
        {
            var toRemove = array.FirstOrDefault(x => x?["name"]?.GetValue<string>() == skillName);
            if (toRemove != null)
            {
                array.Remove(toRemove);
                if (File.Exists(mdAbsPath)) File.Delete(mdAbsPath);
            }
        }
        else
        {
            return Fail("action deve essere 'add' o 'remove'.");
        }

        node["capabilities"] = array;
        await File.WriteAllTextAsync(skillsPath, node.ToJsonString(JsonOpts));
        return Ok($"Skill '{skillName}' {(action == "add" ? "aggiunta" : "rimossa")}.");
    }

    // ── Logging ─────────────────────────────────────────────────────────────

    private async Task LogAsync(
        string toolName,
        Dictionary<string, JsonElement> arguments,
        ToolExecuteResponse response)
    {
        await using var conn = ws.OpenConnection();
        await conn.OpenAsync();
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO tool_logs (tool_name, arguments, result, success, executed_at)
            VALUES (@tool, @args, @result, @success, @at)
            """;
        cmd.Parameters.AddWithValue("@tool",    toolName);
        cmd.Parameters.AddWithValue("@args",    JsonSerializer.Serialize(arguments));
        cmd.Parameters.AddWithValue("@result",  (object?)response.Error ?? response.Result);
        cmd.Parameters.AddWithValue("@success", response.Success ? 1 : 0);
        cmd.Parameters.AddWithValue("@at",      DateTime.UtcNow.ToString("o"));
        await cmd.ExecuteNonQueryAsync();
    }

    // ── Helpers ─────────────────────────────────────────────────────────────

    private string Sandbox(string userPath, bool allowRoot = false)
    {
        if (string.IsNullOrWhiteSpace(userPath) && allowRoot)
            return ws.FilesPath;

        var full = Path.GetFullPath(Path.Combine(ws.FilesPath, userPath));
        if (!full.StartsWith(ws.FilesPath, StringComparison.OrdinalIgnoreCase))
            throw new SecurityException("Path traversal rilevato.");
        return full;
    }

    private static string GetString(Dictionary<string, JsonElement> args, string key) =>
        args.TryGetValue(key, out var el) ? el.GetString() ?? string.Empty : string.Empty;

    private static ToolExecuteResponse Ok(string result)   => new() { Success = true,  Result = result };
    private static ToolExecuteResponse Fail(string error)  => new() { Success = false, Error  = error  };
}
