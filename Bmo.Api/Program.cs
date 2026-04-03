using Bmo.Api.Services;

var builder = WebApplication.CreateBuilder(args);

// ── Config ───────────────────────────────────────────────────────────────────
builder.Configuration.AddJsonFile("bmo_config.json", optional: false, reloadOnChange: true);

// ── Services ─────────────────────────────────────────────────────────────────

builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddCors(options =>
{
    options.AddPolicy("Frontend", policy =>
    {
        policy
            .WithOrigins(
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8080"
            )
            .AllowAnyHeader()
            .AllowAnyMethod();
    });
});

// Workspace + Tools (singleton: il DB va inizializzato una volta sola)
builder.Services.AddSingleton<WorkspaceService>();
builder.Services.AddSingleton<ToolService>();

// Chat
builder.Services.AddScoped<ChatService>();

var pythonBaseUrl = builder.Configuration["PythonApi:BaseUrl"] ?? "http://localhost:8000/";
builder.Services.AddHttpClient<PythonClient>(client =>
{
    client.BaseAddress = new Uri(pythonBaseUrl);
    client.Timeout = TimeSpan.FromSeconds(60);
});

// ── Pipeline ─────────────────────────────────────────────────────────────────

var app = builder.Build();

// Forza l'inizializzazione della workspace all'avvio
app.Services.GetRequiredService<WorkspaceService>();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();
app.UseCors("Frontend");
app.MapControllers();
app.Run();
