using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using IntanWaveNode.Services;

namespace IntanWaveNode.Pages;

public sealed partial class SettingsPage : Page
{
    private readonly NodeCoordinator _coordinator = NodeCoordinator.Instance;

    public SettingsPage()
    {
        InitializeComponent();
        Loaded += SettingsPage_Loaded;
    }

    private void SettingsPage_Loaded(object sender, RoutedEventArgs e)
    {
        var cfg = _coordinator.ConfigService.CurrentConfig;
        ServerUrlBox.Text = cfg.ServerUrl;
        DeviceNameBox.Text = cfg.DeviceName;
        ZoneBox.Text = cfg.Zone;
        ToastSwitch.IsOn = cfg.EnableToast;
    }

    private void SaveButton_Click(object sender, RoutedEventArgs e)
    {
        var cfg = _coordinator.ConfigService.CurrentConfig;
        cfg.ServerUrl = ServerUrlBox.Text.Trim();
        cfg.DeviceName = DeviceNameBox.Text.Trim();
        cfg.Zone = ZoneBox.Text.Trim();
        cfg.EnableToast = ToastSwitch.IsOn;
        cfg.Groups = new List<string>(
            ZoneBox.Text.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
        );

        _coordinator.ConfigService.SaveConfig(cfg);
        _coordinator.RestartListeners();

        SaveFeedbackBar.IsOpen = true;
    }

    private void OpenFolderButton_Click(object sender, RoutedEventArgs e)
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
