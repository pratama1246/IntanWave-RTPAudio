using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using IntanWaveNode.Models;

namespace IntanWaveNode.Services;

public class RtpMulticastListener : IDisposable
{
    private readonly List<UdpClient> _clients = new();
    private CancellationTokenSource? _cts;
    private readonly HashSet<ushort> _seenSeqs = new();
    private readonly Queue<ushort> _seqHistory = new();
    private const int MaxHistory = 256;
    private uint? _activeSsrc = null;
    private DateTime _lastSsrcTime = DateTime.MinValue;
    private DateTime _lastPacketTime = DateTime.MinValue;
    private System.Threading.Timer? _inactivityTimer;

    public event Action<string, bool, byte, ReadOnlyMemory<byte>>? AudioPacketReceived;
    public event Action? StreamEnded;

    public void Start(List<ChannelConfig> channels)
    {
        Stop();
        _cts = new CancellationTokenSource();
        var token = _cts.Token;

        var portMap = new Dictionary<int, List<ChannelConfig>>();
        foreach (var ch in channels)
        {
            if (!portMap.ContainsKey(ch.Port))
                portMap[ch.Port] = new List<ChannelConfig>();
            portMap[ch.Port].Add(ch);
        }

        foreach (var kvp in portMap)
        {
            int port = kvp.Key;
            var chList = kvp.Value;

            try
            {
                var client = new UdpClient();
                client.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
                client.Client.ReceiveBufferSize = 262144;
                client.Client.Bind(new IPEndPoint(IPAddress.Any, port));

                foreach (var ch in chList)
                {
                    if (IPAddress.TryParse(ch.Ip, out var ip))
                    {
                        byte firstOctet = ip.GetAddressBytes()[0];
                        if (firstOctet >= 224 && firstOctet <= 239)
                        {
                            try
                            {
                                client.JoinMulticastGroup(ip);
                            }
                            catch (Exception ex)
                            {
                                System.Diagnostics.Debug.WriteLine($"Error joining multicast {ch.Ip}: {ex.Message}");
                            }
                        }
                    }
                }

                _clients.Add(client);
                Task.Run(() => ListenLoop(client, chList, token), token);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error binding port {port}: {ex.Message}");
            }
        }

        _inactivityTimer = new System.Threading.Timer(_ =>
        {
            if (_lastPacketTime != DateTime.MinValue && (DateTime.UtcNow - _lastPacketTime).TotalSeconds > 1.5)
            {
                _lastPacketTime = DateTime.MinValue;
                _activeSsrc = null;
                StreamEnded?.Invoke();
            }
        }, null, 250, 250);
    }

    private async Task ListenLoop(UdpClient client, List<ChannelConfig> channels, CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                var result = await client.ReceiveAsync(token);
                byte[] data = result.Buffer;

                if (data.Length < 12) continue;

                byte b0 = data[0];
                int cc = b0 & 0x0F;
                int xBit = (b0 >> 4) & 0x01;
                byte pt = (byte)(data[1] & 0x7F);

                ushort seq = (ushort)((data[2] << 8) | data[3]);
                uint ssrc = (uint)((data[8] << 24) | (data[9] << 16) | (data[10] << 8) | data[11]);

                var now = DateTime.UtcNow;

                // SSRC Lock & Deduplication
                if (_activeSsrc == null || (now - _lastSsrcTime).TotalMilliseconds > 400)
                {
                    if (_activeSsrc != null && ssrc != _activeSsrc)
                    {
                        _seenSeqs.Clear();
                        _seqHistory.Clear();
                    }
                    _activeSsrc = ssrc;
                }
                else if (ssrc != _activeSsrc)
                {
                    continue;
                }
                _lastSsrcTime = now;

                if (_seenSeqs.Contains(seq)) continue;
                _seenSeqs.Add(seq);
                _seqHistory.Enqueue(seq);
                if (_seqHistory.Count > MaxHistory)
                {
                    _seenSeqs.Remove(_seqHistory.Dequeue());
                }

                int offset = 12 + (cc * 4);
                if (xBit != 0 && data.Length >= offset + 4)
                {
                    int extLen = (data[offset + 2] << 8) | data[offset + 3];
                    offset += 4 + (extLen * 4);
                }

                if (data.Length <= offset) continue;

                _lastPacketTime = now;

                string chName = channels.Count > 0 ? channels[0].Name : "Audio Channel";
                bool isEmergency = chName.Contains("Phone", StringComparison.OrdinalIgnoreCase) || chName.Contains("Control", StringComparison.OrdinalIgnoreCase);

                var payload = new ReadOnlyMemory<byte>(data, offset, data.Length - offset);
                AudioPacketReceived?.Invoke(chName, isEmergency, pt, payload);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch
            {
                await Task.Delay(50, token);
            }
        }
    }

    public void Stop()
    {
        _cts?.Cancel();
        _cts?.Dispose();
        _cts = null;

        _inactivityTimer?.Dispose();
        _inactivityTimer = null;

        foreach (var c in _clients)
        {
            try { c.Close(); c.Dispose(); } catch { }
        }
        _clients.Clear();
    }

    public void Dispose()
    {
        Stop();
    }
}
