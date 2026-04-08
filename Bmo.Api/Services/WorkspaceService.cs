using Microsoft.Data.Sqlite;

namespace Bmo.Api.Services;

public class WorkspaceService
{
    public string WorkspacePath { get; }
    public string FilesPath { get; }
    public string DbPath { get; }

    public WorkspaceService(IConfiguration config, IWebHostEnvironment env)
    {
        var raw = config["workspace_path"] ?? "../workspace";
        WorkspacePath = Path.GetFullPath(Path.Combine(env.ContentRootPath, raw));
        FilesPath = Path.Combine(WorkspacePath, "files");
        DbPath = Path.Combine(WorkspacePath, "bmo_agent.db");

        Directory.CreateDirectory(WorkspacePath);
        Directory.CreateDirectory(FilesPath);
        Directory.CreateDirectory(Path.Combine(WorkspacePath, "skills"));

        InitializeDatabase();
    }

    public string SkillsPath => Path.Combine(WorkspacePath, "skills");
    public string SkillsJsonPath => Path.Combine(WorkspacePath, "skills.json");

    public async Task<string> GetSkillsJsonAsync()
    {
        if (!File.Exists(SkillsJsonPath))
            return """{"capabilities":[],"learned_behaviors":[]}""";
        return await File.ReadAllTextAsync(SkillsJsonPath);
    }

    public async Task SaveSkillsJsonAsync(string json) =>
        await File.WriteAllTextAsync(SkillsJsonPath, json);

    public async Task<string> GetSkillContentAsync(string filename)
    {
        var safePath = SanitizeSkillPath(filename);
        if (!File.Exists(safePath))
            throw new FileNotFoundException($"Skill file not found: {filename}");
        return await File.ReadAllTextAsync(safePath);
    }

    public async Task SaveSkillContentAsync(string filename, string content)
    {
        var safePath = SanitizeSkillPath(filename);
        await File.WriteAllTextAsync(safePath, content);
    }

    private string SanitizeSkillPath(string filename)
    {
        var name = Path.GetFileName(filename);
        if (!name.EndsWith(".md", StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Skill files must be .md files");
        return Path.Combine(SkillsPath, name);
    }

    public SqliteConnection OpenConnection() =>
        new($"Data Source={DbPath}");

    private void InitializeDatabase()
    {
        using var conn = OpenConnection();
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            CREATE TABLE IF NOT EXISTS memory (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                key         TEXT NOT NULL UNIQUE,
                value       TEXT NOT NULL,
                category    TEXT NOT NULL DEFAULT 'general',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tool_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name   TEXT NOT NULL,
                arguments   TEXT NOT NULL,
                result      TEXT,
                success     INTEGER NOT NULL,
                executed_at TEXT NOT NULL
            );
            """;
        cmd.ExecuteNonQuery();
    }
}
