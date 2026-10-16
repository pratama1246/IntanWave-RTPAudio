using System;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace IntanWave.Node.Services;

public class WebSocketNodeClient : IDisposable
{
    private ClientWebSocket? _ws;
    private CancellationTokenSource? _cts;
    private bool _isConnected;

    public bool IsConnected
    {
        get => _isConnected;
        private set
        {
            if (_isConnected != value)
            {
                _isConnected = value;
                ConnectionChanged?.Invoke(_isConnected);
            }
        }
    }

    public event Action<bool>? ConnectionChanged;
    public event Action<string, string, string, string, int>? PlayTriggered;
    public event Action<string>? StopTriggered;
    public event Action? SyncTriggered;
    public event Action<ReadOnlyMemory<byte>>? BinaryAudioReceived;

    public void Start(string serverUrl, string nodeId)
    {
        Stop();
        _cts = new CancellationTokenSource();
        var token = _cts.Token;
        Task.Run(() => ConnectionLoop(serverUrl, nodeId, token), token);
    }

    private async Task ConnectionLoop(string serverUrl, string nodeId, CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                string wsUrl = serverUrl.TrimEnd('/').Replace("http://", "ws://").Replace("https://", "wss://");
                var uri = new Uri($"{wsUrl}/ws/node/{Uri.EscapeDataString(nodeId)}");

                _ws = new ClientWebSocket();
                _ws.Options.KeepAliveInterval = TimeSpan.FromSeconds(15);
                _ws.Options.SetRequestHeader("User-Agent", "IntanWaveNodeCSharp/1.0");

                using var timeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
                using var linkedCts = CancellationTokenSource.CreateLinkedTokenSource(token, timeoutCts.Token);

                await _ws.ConnectAsync(uri, linkedCts.Token);
                IsConnected = true;

                byte[] buffer = new byte[16384];
                while (_ws.State == WebSocketState.Open && !token.IsCancellationRequested)
                {
                    var result = await _ws.ReceiveAsync(new ArraySegment<byte>(buffer), token);
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        break;
                    }

                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        string json = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        HandleTextMessage(json);
                    }
                    else if (result.MessageType == WebSocketMessageType.Binary)
                    {
                        var chunk = new ReadOnlyMemory<byte>(buffer, 0, result.Count);
                        BinaryAudioReceived?.Invoke(chunk);
                    }
                }
            }
            catch
            {
                // Disconnected or connection error
            }
            finally
            {
                IsConnected = false;
                try { _ws?.Dispose(); } catch { }
                _ws = null;
            }

            if (!token.IsCancellationRequested)
            {
                await Task.Delay(3000, token);
            }
        }
    }

    private void HandleTextMessage(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            string action = root.TryGetProperty("action", out var actProp) ? actProp.GetString() ?? "" : "";

            if (action == "play")
            {
                string sessionId = root.TryGetProperty("session_id", out var sid) ? sid.GetString() ?? "" : "";
                string filename = root.TryGetProperty("filename", out var fn) ? fn.GetString() ?? "" : "";
                string title = root.TryGetProperty("title", out var tit) ? tit.GetString() ?? filename : filename;
                string category = root.TryGetProperty("category", out var cat) ? cat.GetString() ?? "biasa" : "biasa";
                int delayMs = root.TryGetProperty("delay_ms", out var del) ? del.GetInt32() : 0;

                PlayTriggered?.Invoke(sessionId, filename, title, category, delayMs);
            }
            else if (action == "stop")
            {
                string sessionId = root.TryGetProperty("session_id", out var sid) ? sid.GetString() ?? "" : "";
                StopTriggered?.Invoke(sessionId);
            }
            else if (action == "sync")
            {
                SyncTriggered?.Invoke();
            }
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error parsing WS message: {ex.Message}");
        }
    }

    public void Stop()
    {
        _cts?.Cancel();
        _cts?.Dispose();
        _cts = null;

        try { _ws?.Dispose(); } catch { }
        _ws = null;
        IsConnected = false;
    }

    public void Dispose()
    {
        Stop();
    }
}
