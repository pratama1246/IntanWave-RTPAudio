using System;
using System.IO;
using System.Threading;
using NAudio.Codecs;
using NAudio.Wave;

namespace IntanWaveNode.Services;

public class AudioPlaybackEngine : IDisposable
{
    private static readonly Lazy<AudioPlaybackEngine> _lazy = new(() => new AudioPlaybackEngine());
    public static AudioPlaybackEngine Instance => _lazy.Value;

    private WasapiOut? _wasapiOut;
    private WaveOutEvent? _waveOut;
    private BufferedWaveProvider? _bufferedWaveProvider;
    private AudioFileReader? _audioFileReader;
    private readonly object _lock = new();

    private float _volume = 1.0f;
    public float Volume
    {
        get => _volume;
        set
        {
            _volume = Math.Clamp(value, 0f, 1f);
            if (_wasapiOut != null)
            {
                try { _wasapiOut.Volume = _volume; } catch { }
            }
            if (_waveOut != null)
            {
                try { _waveOut.Volume = _volume; } catch { }
            }
        }
    }

    public event Action<float>? PeakLevelUpdated;
    public event Action? PlaybackStopped;

    private System.Threading.Timer? _peakTimer;
    private float _currentPeak = 0f;

    public AudioPlaybackEngine()
    {
        _peakTimer = new System.Threading.Timer(_ =>
        {
            float peak = _currentPeak;
            _currentPeak = Math.Max(0f, _currentPeak - 0.1f);
            PeakLevelUpdated?.Invoke(peak);
        }, null, 50, 50);
    }

    public void PlayLocalFile(string filePath)
    {
        lock (_lock)
        {
            StopCurrentPlaybackLocked();

            if (!File.Exists(filePath)) return;

            try
            {
                _audioFileReader = new AudioFileReader(filePath)
                {
                    Volume = _volume
                };

                try
                {
                    _wasapiOut = new WasapiOut(NAudio.CoreAudioApi.AudioClientShareMode.Shared, 100);
                    _wasapiOut.Init(_audioFileReader);
                    _wasapiOut.PlaybackStopped += (s, e) => PlaybackStopped?.Invoke();
                    _wasapiOut.Play();
                }
                catch
                {
                    _waveOut = new WaveOutEvent();
                    _waveOut.Init(_audioFileReader);
                    _waveOut.Volume = _volume;
                    _waveOut.PlaybackStopped += (s, e) => PlaybackStopped?.Invoke();
                    _waveOut.Play();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error PlayLocalFile: {ex.Message}");
            }
        }
    }

    public void EnsureRtpStream(byte payloadType)
    {
        lock (_lock)
        {
            bool isPlaying = (_wasapiOut != null && _wasapiOut.PlaybackState == PlaybackState.Playing) ||
                             (_waveOut != null && _waveOut.PlaybackState == PlaybackState.Playing);

            if (_bufferedWaveProvider != null && isPlaying)
            {
                return;
            }

            StopCurrentPlaybackLocked();

            var waveFormat = new WaveFormat(8000, 16, 1);
            _bufferedWaveProvider = new BufferedWaveProvider(waveFormat)
            {
                BufferDuration = TimeSpan.FromSeconds(2),
                DiscardOnBufferOverflow = true
            };

            try
            {
                _wasapiOut = new WasapiOut(NAudio.CoreAudioApi.AudioClientShareMode.Shared, 60);
                _wasapiOut.Init(_bufferedWaveProvider);
                _wasapiOut.Volume = _volume;
                _wasapiOut.Play();
            }
            catch
            {
                _waveOut = new WaveOutEvent();
                _waveOut.Init(_bufferedWaveProvider);
                _waveOut.Volume = _volume;
                _waveOut.Play();
            }
        }
    }

    public void FeedRtpChunk(byte payloadType, ReadOnlyMemory<byte> payload)
    {
        EnsureRtpStream(payloadType);

        var span = payload.Span;
        byte[] pcm = new byte[span.Length * 2];
        float maxSample = 0f;

        bool isMuLaw = (payloadType == 0);

        for (int i = 0; i < span.Length; i++)
        {
            short sample = isMuLaw ? MuLawDecoder.MuLawToLinearSample(span[i]) : ALawDecoder.ALawToLinearSample(span[i]);
            pcm[i * 2] = (byte)(sample & 0xFF);
            pcm[i * 2 + 1] = (byte)((sample >> 8) & 0xFF);

            float abs = Math.Abs(sample / 32768f);
            if (abs > maxSample) maxSample = abs;
        }

        _currentPeak = Math.Max(_currentPeak, maxSample);

        lock (_lock)
        {
            _bufferedWaveProvider?.AddSamples(pcm, 0, pcm.Length);
        }
    }

    public void Stop()
    {
        lock (_lock)
        {
            StopCurrentPlaybackLocked();
        }
    }

    private void StopCurrentPlaybackLocked()
    {
        try
        {
            if (_wasapiOut != null)
            {
                _wasapiOut.Stop();
                _wasapiOut.Dispose();
                _wasapiOut = null;
            }

            if (_waveOut != null)
            {
                _waveOut.Stop();
                _waveOut.Dispose();
                _waveOut = null;
            }

            if (_audioFileReader != null)
            {
                _audioFileReader.Dispose();
                _audioFileReader = null;
            }

            if (_bufferedWaveProvider != null)
            {
                _bufferedWaveProvider.ClearBuffer();
                _bufferedWaveProvider = null;
            }
        }
        catch { }
    }

    public void Dispose()
    {
        Stop();
        _peakTimer?.Dispose();
    }
}
