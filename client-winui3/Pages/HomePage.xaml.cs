using System;
using System.Diagnostics;
using System.IO;
using Microsoft.UI;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Windows.UI;
using IntanWaveNode.Services;

namespace IntanWaveNode.Pages;

public sealed partial class HomePage : Page
{
    private readonly NodeCoordinator _coordinator = NodeCoordinator.Instance;
    private const int TotalLedSegments = 24;
    private readonly Border[] _ledBorders = new Border[TotalLedSegments];
    private readonly Color[] _ledActiveColors = new Color[TotalLedSegments];
    private readonly SolidColorBrush _ledOffBrush = new(Color.FromArgb(255, 30, 41, 59));

    public HomePage()
    {
        InitializeComponent();
        InitializeLedSegments();
        Loaded += HomePage_Loaded;
    }

    private void InitializeLedSegments()
    {
        VuSegmentsContainer.Children.Clear();
        VuSegmentsContainer.ColumnDefinitions.Clear();

        for (int i = 0; i < TotalLedSegments; i++)
        {
            VuSegmentsContainer.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            Color activeColor;
            if (i >= 20)
                activeColor = Color.FromArgb(255, 239, 68, 68);    // Red (Clip)
            else if (i >= 15)
                activeColor = Color.FromArgb(255, 245, 158, 11);  // Amber (Warning)
            else
                activeColor = Color.FromArgb(255, 16, 185, 129);  // Green (Normal)

            _ledActiveColors[i] = activeColor;

            var led = new Border
            {
                Background = _ledOffBrush,
                CornerRadius = new CornerRadius(1.5),
                Margin = new Thickness(1, 0, 1, 0)
            };

            Grid.SetColumn(led, i);
            _ledBorders[i] = led;
            VuSegmentsContainer.Children.Add(led);
        }
    }

    private void HomePage_Loaded(object sender, RoutedEventArgs e)
    {
        var cfg = _coordinator.ConfigService.CurrentConfig;
        ZoneText.Text = cfg.Zone;
        NodeIdText.Text = cfg.NodeId;
        NodeIpText.Text = "127.0.0.1";

        // Subscribe to audio peak VU level
        _coordinator.AudioEngine.PeakLevelUpdated += peak =>
        {
            DispatcherQueue.TryEnqueue(() =>
            {
                int activeCount = (int)Math.Round(peak * TotalLedSegments);
                if (activeCount > TotalLedSegments) activeCount = TotalLedSegments;

                for (int i = 0; i < TotalLedSegments; i++)
                {
                    _ledBorders[i].Background = i < activeCount 
                        ? new SolidColorBrush(_ledActiveColors[i]) 
                        : _ledOffBrush;
                }

                if (peak > 0.0001f)
                {
                    float db = (float)(20 * Math.Log10(peak));
                    VuDbText.Text = $"{db:0.0} dB";
                }
                else
                {
                    VuDbText.Text = "-INF dB";
                }
            });
        };

        // Subscribe to Status Changes
        _coordinator.StatusChanged += (status, category, title) =>
        {
            DispatcherQueue.TryEnqueue(() =>
            {
                if (status == "STREAMING")
                {
                    bool isEmergency = (category == "darurat");
                    BroadcastInfoBar.Severity = isEmergency ? InfoBarSeverity.Error : InfoBarSeverity.Informational;
                    BroadcastInfoBar.Title = isEmergency ? "🚨 ON AIR: PAGING DARURAT" : "● ON AIR: SIARAN AKTIF";
                    BroadcastInfoBar.Message = string.IsNullOrWhiteSpace(title) ? "Memutar siaran audio..." : title;
                }
                else
                {
                    BroadcastInfoBar.Severity = InfoBarSeverity.Success;
                    BroadcastInfoBar.Title = "STANDBY";
                    BroadcastInfoBar.Message = "Standby mendengarkan paket siaran audio multicast (239.255.0.1:5004)";
                }
            });
        };

        // Subscribe to Heartbeat Server State
        _coordinator.HeartbeatService.HeartbeatStateChanged += (online, ip, zone) =>
        {
            DispatcherQueue.TryEnqueue(() =>
            {
                if (online)
                {
                    ServerStatusText.Text = $"● Online ({ip})";
                    ServerStatusText.Foreground = new SolidColorBrush(Color.FromArgb(255, 16, 185, 129));
                    NodeIpText.Text = string.IsNullOrWhiteSpace(ip) ? "127.0.0.1" : ip;
                    if (!string.IsNullOrWhiteSpace(zone))
                    {
                        ZoneText.Text = zone;
                    }
                }
                else
                {
                    ServerStatusText.Text = "○ Terputus dari Server";
                    ServerStatusText.Foreground = new SolidColorBrush(Color.FromArgb(255, 239, 68, 68));
                }
            });
        };
    }

    private void VolumeSlider_ValueChanged(object sender, Microsoft.UI.Xaml.Controls.Primitives.RangeBaseValueChangedEventArgs e)
    {
        if (VolumePctText == null) return;
        int pct = (int)e.NewValue;
        VolumePctText.Text = $"{pct}%";
        _coordinator.AudioEngine.Volume = (float)(pct / 100.0);
    }

    private void TestChime_Click(object sender, RoutedEventArgs e)
    {
        _coordinator.PlayTestChime();
    }

    private void StopAudio_Click(object sender, RoutedEventArgs e)
    {
        _coordinator.StopAudio();
    }

    private void OpenMediaFolder_Click(object sender, RoutedEventArgs e)
    {
        string dir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "media");
        Directory.CreateDirectory(dir);
        Process.Start(new ProcessStartInfo
        {
            FileName = dir,
            UseShellExecute = true
        });
    }
}
