using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace IntanWaveNode.Models;

public class ChannelConfig
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "Channel Audio";

    [JsonPropertyName("ip")]
    public string Ip { get; set; } = "239.255.0.1";

    [JsonPropertyName("port")]
    public int Port { get; set; } = 5004;
}

public class NodeConfig
{
    [JsonPropertyName("server_url")]
    public string ServerUrl { get; set; } = "http://10.183.55.114:7080";

    [JsonPropertyName("node_id")]
    public string NodeId { get; set; } = "";

    [JsonPropertyName("device_name")]
    public string DeviceName { get; set; } = "";

    [JsonPropertyName("groups")]
    public List<string> Groups { get; set; } = new() { "Kantor" };

    [JsonPropertyName("zone")]
    public string Zone { get; set; } = "Kantor";

    [JsonPropertyName("multicast_ip")]
    public string MulticastIp { get; set; } = "239.255.0.1";

    [JsonPropertyName("multicast_port")]
    public int MulticastPort { get; set; } = 5004;

    [JsonPropertyName("channels")]
    public List<ChannelConfig> Channels { get; set; } = new();

    [JsonPropertyName("playback_mode")]
    public string PlaybackMode { get; set; } = "auto";

    [JsonPropertyName("enable_toast")]
    public bool EnableToast { get; set; } = true;
}
