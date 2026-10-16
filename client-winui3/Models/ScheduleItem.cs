using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace IntanWaveNode.Models;

public class ScheduleItem
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("time")]
    public string Time { get; set; } = "";

    [JsonPropertyName("days")]
    public List<string> Days { get; set; } = new();

    [JsonPropertyName("audio_filename")]
    public string AudioFilename { get; set; } = "";

    [JsonPropertyName("is_active")]
    public bool IsActive { get; set; } = true;

    [JsonPropertyName("category")]
    public string Category { get; set; } = "biasa";

    [JsonPropertyName("media_status")]
    public string MediaStatus { get; set; } = "Siap";
}
