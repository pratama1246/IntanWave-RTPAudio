using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using IntanWaveNode.Models;

namespace IntanWaveNode.Services;

public class NodeCoordinator : IDisposable
{
    private static readonly Lazy<NodeCoordinator> _lazy = new(() => new NodeCoordinator());
    public static NodeCoordinator Instance => _lazy.Value;

    public ConfigService ConfigService { get; } = new();
    public AudioPlaybackEngine AudioEngine => AudioPlaybackEngine.Instance;
    public RtpMulticastListener RtpListener { get; } = new();
    public WebSocketNodeClient WsClient { get; } = new();
    public NodeHeartbeatService HeartbeatService { get; } = new();

    public string Status { get; private set; } = "STANDBY";
    public string CurrentCategory { get; private set; } = "biasa";
    public string CurrentTitle { get; private set; } = "";
    public string ActiveSource { get; private set; } = "";

    public event Action<string, string, string>? StatusChanged;
    public event Action<string, string>? NotificationRequested;

    private readonly object _stateLock = new();

    public void Initialize()
    {
        var config = ConfigService.CurrentConfig;

        // Wire Up WebSocket
        WsClient.PlayTriggered += (sessionId, filename, title, category, delayMs) =>
        {
            HandleServerPlay(filename, title, category, delayMs);
        };

        WsClient.StopTriggered += (sessionId) =>
        {
            StopAudio();
        };

        WsClient.SyncTriggered += () =>
        {
            _ = HeartbeatService.SyncSchedulesAsync(ConfigService.CurrentConfig);
        };

        // Wire Up RTP Multicast
        RtpListener.AudioPacketReceived += (chName, isEmergency, pt, payload) =>
        {
            lock (_stateLock)
            {
                if (ActiveSource == "LOCAL") return;

                if (ActiveSource != "RTP")
                {
                    ActiveSource = "RTP";
                    string cat = isEmergency ? "darurat" : "biasa";
                    SetStatus("STREAMING", cat, chName);
                    NotificationRequested?.Invoke($"IntanWave — {chName}", $"Menerima siaran RTP Multicast ({chName})");
                }
            }

            AudioEngine.FeedRtpChunk(pt, payload);
        };

        RtpListener.StreamEnded += () =>
        {
            lock (_stateLock)
            {
                if (ActiveSource == "RTP")
                {
                    ActiveSource = "";
                    SetStatus("STANDBY", "biasa", "");
                    AudioEngine.Stop();
                }
            }
        };

        AudioEngine.PlaybackStopped += () =>
        {
            lock (_stateLock)
            {
                if (ActiveSource == "LOCAL")
                {
                    ActiveSource = "";
                    SetStatus("STANDBY", "biasa", "");
                }
            }
        };

        RestartListeners();
    }

    public void RestartListeners()
    {
        var config = ConfigService.CurrentConfig;
        RtpListener.Start(config.Channels);
        WsClient.Start(config.ServerUrl, config.NodeId);
        HeartbeatService.Start(config);
    }

    private void HandleServerPlay(string filename, string title, string category, int delayMs)
    {
        if (filename == "test_chime.wav")
        {
            PlayTestChime();
            return;
        }

        string mediaPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "media", filename);
        if (!File.Exists(mediaPath))
        {
            mediaPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Assets", filename);
        }

        if (File.Exists(mediaPath))
        {
            if (delayMs > 0) Thread.Sleep(delayMs);

            lock (_stateLock)
            {
                ActiveSource = "LOCAL";
                SetStatus("STREAMING", category, title);
                NotificationRequested?.Invoke("IntanWave — Siaran Audio", $"Memutar: {title}");
            }

            AudioEngine.PlayLocalFile(mediaPath);
        }
    }

    public void PlayTestChime()
    {
        string chimePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Assets", "test_chime.wav");
        if (!File.Exists(chimePath))
        {
            chimePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "test_chime.wav");
        }

        if (File.Exists(chimePath))
        {
            lock (_stateLock)
            {
                ActiveSource = "LOCAL";
                SetStatus("STREAMING", "biasa", "Tes Bunyi Ampli (Ding-Dong)");
                NotificationRequested?.Invoke("IntanWave — Tes Audio", "Memutar nada bel pengujian soundcard amplifier");
            }
            AudioEngine.PlayLocalFile(chimePath);
        }
    }

    public void StopAudio()
    {
        lock (_stateLock)
        {
            ActiveSource = "";
            SetStatus("STANDBY", "biasa", "");
        }
        AudioEngine.Stop();
    }

    private void SetStatus(string status, string category, string title)
    {
        Status = status;
        CurrentCategory = category;
        CurrentTitle = title;
        StatusChanged?.Invoke(status, category, title);
    }

    public void Dispose()
    {
        AudioEngine.Dispose();
        RtpListener.Dispose();
        WsClient.Dispose();
        HeartbeatService.Dispose();
    }
}
