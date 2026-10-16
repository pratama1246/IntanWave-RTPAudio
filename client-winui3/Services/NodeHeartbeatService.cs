using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using IntanWaveNode.Models;

namespace IntanWaveNode.Services;

public class NodeHeartbeatService : IDisposable
{
    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(5) };
    private CancellationTokenSource? _cts;
    private readonly string _mediaDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "media");

    public bool IsServerConnected { get; private set; }
    public string RegisteredIp { get; private set; } = "";
    public string RegisteredZone { get; private set; } = "";

    public event Action<bool, string, string>? HeartbeatStateChanged;
    public event Action<List<ScheduleItem>>? SchedulesUpdated;

    public NodeHeartbeatService()
    {
        try { Directory.CreateDirectory(_mediaDir); } catch { }
    }

    public void Start(NodeConfig config)
    {
        Stop();
        _cts = new CancellationTokenSource();
        var token = _cts.Token;
        Task.Run(() => Loop(config, token), token);
    }

    private async Task Loop(NodeConfig config, CancellationToken token)
    {
        await SendHeartbeatAsync(config, forceUpdate: true, token);
        await SyncSchedulesAsync(config, token);

        while (!token.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(15000, token);
                await SendHeartbeatAsync(config, forceUpdate: false, token);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch { }
        }
    }

    public async Task<bool> SendHeartbeatAsync(NodeConfig config, bool forceUpdate, CancellationToken token = default)
    {
        if (string.IsNullOrWhiteSpace(config.ServerUrl) || string.IsNullOrWhiteSpace(config.NodeId))
            return false;

        string url = $"{config.ServerUrl.TrimEnd('/')}/api/nodes/heartbeat";
        string clientIp = GetLocalIpAddress(config.ServerUrl);

        var payload = new
        {
            node_id = config.NodeId,
            device_name = config.DeviceName,
            groups = config.Groups,
            group = config.Zone,
            zone = config.Zone,
            port = config.MulticastPort,
            hostname = Environment.MachineName,
            force_update = forceUpdate,
            client_ip = clientIp
        };

        try
        {
            string json = JsonSerializer.Serialize(payload);
            using var content = new StringContent(json, Encoding.UTF8, "application/json");
            var res = await _http.PostAsync(url, content, token);

            if (res.IsSuccessStatusCode)
            {
                string resJson = await res.Content.ReadAsStringAsync(token);
                using var doc = JsonDocument.Parse(resJson);
                var nodeData = doc.RootElement.TryGetProperty("node", out var n) ? n : default;

                RegisteredIp = nodeData.TryGetProperty("ip_address", out var ip) ? ip.GetString() ?? clientIp : clientIp;
                RegisteredZone = nodeData.TryGetProperty("zone", out var z) ? z.GetString() ?? config.Zone : config.Zone;

                IsServerConnected = true;
                HeartbeatStateChanged?.Invoke(true, RegisteredIp, RegisteredZone);
                return true;
            }
        }
        catch
        {
            // Heartbeat failed
        }

        IsServerConnected = false;
        HeartbeatStateChanged?.Invoke(false, "", "");
        return false;
    }

    public async Task SyncSchedulesAsync(NodeConfig config, CancellationToken token = default)
    {
        if (string.IsNullOrWhiteSpace(config.ServerUrl) || string.IsNullOrWhiteSpace(config.NodeId))
            return;

        try
        {
            string url = $"{config.ServerUrl.TrimEnd('/')}/api/nodes/{Uri.EscapeDataString(config.NodeId)}/schedules";
            var res = await _http.GetAsync(url, token);
            if (!res.IsSuccessStatusCode) return;

            string json = await res.Content.ReadAsStringAsync(token);
            var schedules = JsonSerializer.Deserialize<List<ScheduleItem>>(json) ?? new();

            foreach (var s in schedules)
            {
                if (!string.IsNullOrWhiteSpace(s.AudioFilename))
                {
                    string targetFile = Path.Combine(_mediaDir, s.AudioFilename);
                    if (!File.Exists(targetFile) || new FileInfo(targetFile).Length == 0)
                    {
                        await DownloadMediaAsync(config.ServerUrl, s.AudioFilename, targetFile, token);
                    }
                }
            }

            SchedulesUpdated?.Invoke(schedules);
        }
        catch { }
    }

    private async Task DownloadMediaAsync(string serverUrl, string filename, string targetPath, CancellationToken token)
    {
        try
        {
            string url = $"{serverUrl.TrimEnd('/')}/api/audio/stream-file/{Uri.EscapeDataString(filename)}";
            var bytes = await _http.GetByteArrayAsync(url, token);
            if (bytes.Length > 0)
            {
                await File.WriteAllBytesAsync(targetPath, bytes, token);
            }
        }
        catch { }
    }

    private string GetLocalIpAddress(string serverUrl)
    {
        try
        {
            var uri = new Uri(serverUrl);
            using var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, 0);
            socket.Connect(uri.Host, 80);
            if (socket.LocalEndPoint is IPEndPoint endPoint)
                return endPoint.Address.ToString();
        }
        catch { }
        return "127.0.0.1";
    }

    public void Stop()
    {
        _cts?.Cancel();
        _cts?.Dispose();
        _cts = null;
    }

    public void Dispose()
    {
        Stop();
        _http.Dispose();
    }
}
