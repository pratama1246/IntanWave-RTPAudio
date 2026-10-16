using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;
using Color = System.Windows.Media.Color;
using Brush = System.Windows.Media.Brush;
using MessageBox = System.Windows.MessageBox;
using Path = System.IO.Path;
using IntanWave.Node.Models;
using IntanWave.Node.Services;

namespace IntanWave.Node;

public partial class MainWindow : Window
{
    private readonly NodeCoordinator _coordinator = NodeCoordinator.Instance;
    private bool _isExplicitExit = false;

    // Segmented LED Meter elements
    private const int TotalLedSegments = 24;
    private readonly Border[] _ledBorders = new Border[TotalLedSegments];
    private readonly Color[] _ledActiveColors = new Color[TotalLedSegments];
    private readonly SolidColorBrush _ledOffBrush = new(Color.FromRgb(22, 32, 50));

    public MainWindow()
    {
        InitializeComponent();
        InitializeLedSegments();
        Loaded += MainWindow_Loaded;
    }

    private void InitializeLedSegments()
    {
        VuMeterGrid.Children.Clear();

        for (int i = 0; i < TotalLedSegments; i++)
        {
            Color activeColor;
            if (i >= 20)
                activeColor = Color.FromRgb(239, 68, 68);    // Red (Clip 0dB)
            else if (i >= 15)
                activeColor = Color.FromRgb(245, 158, 11);  // Amber (-6dB)
            else
                activeColor = Color.FromRgb(16, 185, 129);  // Green (Normal)

            _ledActiveColors[i] = activeColor;

            var led = new Border
            {
                Background = _ledOffBrush,
                CornerRadius = new CornerRadius(1.5),
                Margin = new Thickness(1.5, 0, 1.5, 0)
            };

            _ledBorders[i] = led;
            VuMeterGrid.Children.Add(led);
        }
    }

    private void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        // 1. Auto-Detect Windows Version & Apply Adaptive Theme
        WindowsVersionHelper.ApplyAdaptiveStyling(this);
        OsBadgeText.Text = $"{WindowsVersionHelper.OsDisplayName.ToUpper()} • NATIVE";

        if (WindowsVersionHelper.Family == WindowsFamily.Windows11)
        {
            OsBadge.Background = new SolidColorBrush(Color.FromRgb(22, 38, 65));
            OsBadge.BorderBrush = new SolidColorBrush(Color.FromRgb(0, 210, 255));
            OsLedDot.Fill = new SolidColorBrush(Color.FromRgb(0, 210, 255));
            OsBadgeText.Foreground = new SolidColorBrush(Color.FromRgb(0, 210, 255));
        }
        else if (WindowsVersionHelper.Family == WindowsFamily.Windows10)
        {
            OsBadge.Background = new SolidColorBrush(Color.FromRgb(26, 37, 54));
            OsBadge.BorderBrush = new SolidColorBrush(Color.FromRgb(56, 189, 248));
            OsLedDot.Fill = new SolidColorBrush(Color.FromRgb(56, 189, 248));
            OsBadgeText.Foreground = new SolidColorBrush(Color.FromRgb(56, 189, 248));
        }
        else
        {
            // Windows 8 / 8.1
            OsBadge.Background = new SolidColorBrush(Color.FromRgb(30, 41, 59));
            OsBadge.BorderBrush = new SolidColorBrush(Color.FromRgb(100, 116, 139));
            OsLedDot.Fill = new SolidColorBrush(Color.FromRgb(148, 163, 184));
            OsBadgeText.Foreground = new SolidColorBrush(Color.FromRgb(226, 232, 240));
        }

        // 2. Load Config into UI
        var cfg = _coordinator.ConfigService.CurrentConfig;
        ServerUrlBox.Text = cfg.ServerUrl;
        DeviceNameBox.Text = cfg.DeviceName;
        ZoneBox.Text = cfg.Zone;
        ZoneText.Text = cfg.Zone;
        NodeIdText.Text = cfg.NodeId;
        NodeIpText.Text = "127.0.0.1";

        // 3. Subscribe to Audio Peak for Segmented VU Meter
        _coordinator.AudioEngine.PeakLevelUpdated += peak =>
        {
            Dispatcher.Invoke(() =>
            {
                int activeCount = (int)Math.Round(peak * TotalLedSegments);
                if (activeCount > TotalLedSegments) activeCount = TotalLedSegments;

                for (int i = 0; i < TotalLedSegments; i++)
                {
                    if (i < activeCount)
                    {
                        _ledBorders[i].Background = new SolidColorBrush(_ledActiveColors[i]);
                    }
                    else
                    {
                        _ledBorders[i].Background = _ledOffBrush;
                    }
                }

                if (peak > 0.0001f)
                {
                    float db = (float)(20 * Math.Log10(peak));
                    VuLevelDbText.Text = $"{db:0.0} dB";
                    VuLevelDbText.Foreground = db >= -3f 
                        ? new SolidColorBrush(Color.FromRgb(239, 68, 68)) 
                        : new SolidColorBrush(Color.FromRgb(0, 210, 255));
                }
                else
                {
                    VuLevelDbText.Text = "-INF dB";
                    VuLevelDbText.Foreground = new SolidColorBrush(Color.FromRgb(100, 116, 139));
                }
            });
        };

        // 4. Subscribe to Status Changes
        _coordinator.StatusChanged += (status, category, title) =>
        {
            Dispatcher.Invoke(() =>
            {
                if (status == "STREAMING")
                {
                    bool isEmergency = (category == "darurat");

                    StatusText.Text = isEmergency ? "🚨 ON AIR: EMERGENCY" : "● ON AIR: LIVE";
                    StatusBadge.Background = isEmergency 
                        ? (Brush)FindResource("CrimsonOnAirBrush") 
                        : (Brush)FindResource("CyanAccentBrush");
                    HeroCard.BorderBrush = isEmergency 
                        ? (Brush)FindResource("CrimsonOnAirBrush") 
                        : (Brush)FindResource("CyanAccentBrush");

                    BroadcastTitleText.Text = string.IsNullOrWhiteSpace(title) ? "Menerima siaran audio aktif..." : title;
                    ActiveCategoryText.Text = isEmergency ? "PAGING DARURAT" : "SIARAN OPERASIONAL";
                    ActiveCategoryText.Foreground = isEmergency 
                        ? (Brush)FindResource("CrimsonOnAirBrush") 
                        : (Brush)FindResource("CyanAccentBrush");

                    SourceBadge.Visibility = Visibility.Visible;
                    SourceText.Text = _coordinator.ActiveSource.ToUpper();
                }
                else
                {
                    StatusText.Text = "STANDBY";
                    StatusBadge.Background = (Brush)FindResource("EmeraldOnlineBrush");
                    HeroCard.BorderBrush = (Brush)FindResource("PanelBorderBrush");
                    BroadcastTitleText.Text = "Standby mendengarkan paket siaran audio multicast...";
                    ActiveCategoryText.Text = "STANDBY MONITORING";
                    ActiveCategoryText.Foreground = (Brush)FindResource("TextDimBrush");
                    SourceBadge.Visibility = Visibility.Collapsed;
                }
            });
        };

        // 5. Subscribe to Heartbeat Server State
        _coordinator.HeartbeatService.HeartbeatStateChanged += (online, ip, zone) =>
        {
            Dispatcher.Invoke(() =>
            {
                if (online)
                {
                    ServerStatusText.Text = $"● Online ({ip})";
                    ServerStatusText.Foreground = (Brush)FindResource("EmeraldOnlineBrush");
                    NodeIpText.Text = string.IsNullOrWhiteSpace(ip) ? "127.0.0.1" : ip;
                    if (!string.IsNullOrWhiteSpace(zone))
                    {
                        ZoneText.Text = zone;
                    }
                }
                else
                {
                    ServerStatusText.Text = "○ Terputus dari Server";
                    ServerStatusText.Foreground = (Brush)FindResource("CrimsonOnAirBrush");
                }
            });
        };
    }

    private void VolumeSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (VolumePercentText == null) return;
        int pct = (int)e.NewValue;
        VolumePercentText.Text = $"{pct}%";
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

    private void SaveConfig_Click(object sender, RoutedEventArgs e)
    {
        var cfg = _coordinator.ConfigService.CurrentConfig;
        cfg.ServerUrl = ServerUrlBox.Text.Trim();
        cfg.DeviceName = DeviceNameBox.Text.Trim();
        cfg.Zone = ZoneBox.Text.Trim();
        cfg.Groups = new List<string>(
            ZoneBox.Text.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
        );

        _coordinator.ConfigService.SaveConfig(cfg);
        _coordinator.RestartListeners();

        MessageBox.Show("Pengaturan audio berhasil disimpan dan koneksi diperbarui!", 
            "IntanWave Pro Audio", MessageBoxButton.OK, MessageBoxImage.Information);
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

    private void Window_Closing(object sender, CancelEventArgs e)
    {
        if (!_isExplicitExit)
        {
            e.Cancel = true;
            Hide();
        }
    }
}
