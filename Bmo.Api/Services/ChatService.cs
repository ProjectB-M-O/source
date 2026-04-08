namespace Bmo.Api.Services;

public class ChatService(PythonClient pythonClient)
{
    public async Task<string> ProcessMessageAsync(string message) =>
        await pythonClient.SendMessageAsync(message);

    public async Task StreamAsync(string message, Stream outputStream, CancellationToken ct) =>
        await pythonClient.StreamMessageAsync(message, outputStream, ct);

    public IAsyncEnumerable<string> ReadStreamLinesAsync(string message, CancellationToken ct) =>
        pythonClient.ReadStreamLinesAsync(message, ct);

    public async Task ResetAsync() =>
        await pythonClient.ResetSessionAsync();

    public async Task<string> GetHistoryAsync() =>
        await pythonClient.GetHistoryAsync();
}
