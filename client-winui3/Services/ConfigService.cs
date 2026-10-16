using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using IntanWaveNode.Models;

namespace IntanWaveNode.Services;

public class ConfigService
{
    private static readonly string ConfigPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.json");
    private readonly JsonSerializerOptions _jsonOptions = new() { WriteIndented = true };

    public NodeConfig CurrentConfig { get; private set; } = new();

    public event Action<NodeConfig>? ConfigChanged;

    public ConfigService()
    {
        LoadConfig();
    }

    public NodeConfig LoadConfig()
    {
        NodeConfig? cfg = null;
        if (File.Exists(ConfigPath))
        {
            try
            {
                string json = File.ReadAllText(ConfigPath);
                cfg = JsonSerializer.Deserialize<NodeConfig>(json);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error reading config: {ex.Message}");
            }
        }

        cfg ??= new NodeConfig();
        bool changed = false;

        string hostName = Environment.MachineName;
        string cleanHost = hostName.ToLower().Replace(" ", "_").Replace("-", "_");
        string stableNodeId = $"node_{cleanHost}";

        if (string.IsNullOrWhiteSpace(cfg.NodeId) || cfg.NodeId == "node_client_01" || !cfg.NodeId.StartsWith($"node_{cleanHost}"))
        {
            cfg.NodeId = stableNodeId;
            changed = true;
        }

        if (string.IsNullOrWhiteSpace(cfg.DeviceName) || cfg.DeviceName.Contains("Terminal Audio Node (Amplifier)"))
        {
            cfg.DeviceName = $"Terminal Audio ({hostName})";
            changed = true;
        }

        if (cfg.Channels == null || cfg.Channels.Count == 0)
        {
            cfg.Channels = new List<ChannelConfig>
            {
                new() { Name = "Server PA Pelindo", Ip = cfg.MulticastIp, Port = cfg.MulticastPort },
                new() { Name = "Control Room IP Phone", Ip = "239.255.0.2", Port = 5004 }
            };
            changed = true;
        }

        CurrentConfig = cfg;

        if (changed || !File.Exists(ConfigPath))
        {
            SaveConfig(cfg);
        }

        return CurrentConfig;
    }

    public void SaveConfig(NodeConfig config)
    {
        CurrentConfig = config;
        try
        {
            string json = JsonSerializer.Serialize(config, _jsonOptions);
            File.WriteAllText(ConfigPath, json);
            ConfigChanged?.Invoke(CurrentConfig);
        }
        catch (Exception ex)
        {
            System.Diagnostics.Debug.WriteLine($"Error saving config: {ex.Message}");
        }
    }
}
