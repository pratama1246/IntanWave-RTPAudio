using System;
using System.IO;
using System.Threading;
using System.Windows;
using Forms = System.Windows.Forms;
using IntanWave.Node.Services;

namespace IntanWave.Node;

public partial class App : System.Windows.Application
{
    private static Mutex? _mutex;
    private const string MutexName = "Global\\IntanWaveNode_SingleInstance_Mutex";
    private Forms.NotifyIcon? _notifyIcon;
    private MainWindow? _mainWindow;

    private void Application_Startup(object sender, StartupEventArgs e)
    {
        // Single Instance Lock
        _mutex = new Mutex(true, MutexName, out bool isNewInstance);
        if (!isNewInstance)
        {
            Forms.MessageBox.Show("Aplikasi IntanWave Node sudah berjalan di background (System Tray).",
                "IntanWave Node", Forms.MessageBoxButtons.OK, Forms.MessageBoxIcon.Information);
            Shutdown();
            return;
        }

        // Initialize Services
        NodeCoordinator.Instance.Initialize();

        // Setup System Tray Icon
        SetupTrayIcon();

        // Wire Up Notifications
        NodeCoordinator.Instance.NotificationRequested += (title, message) =>
        {
            if (NodeCoordinator.Instance.ConfigService.CurrentConfig.EnableToast)
            {
                _notifyIcon?.ShowBalloonTip(3000, title, message, Forms.ToolTipIcon.Info);
            }
        };

        bool startMinimized = false;
        foreach (var arg in e.Args)
        {
            if (arg.Equals("--minimized", StringComparison.OrdinalIgnoreCase) || arg.Equals("-minimized", StringComparison.OrdinalIgnoreCase))
            {
                startMinimized = true;
            }
        }

        _mainWindow = new MainWindow();
        if (!startMinimized)
        {
            _mainWindow.Show();
        }
    }

    private void SetupTrayIcon()
    {
        string iconPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Assets", "app_icon.ico");
        System.Drawing.Icon appIcon;
        if (File.Exists(iconPath))
        {
            appIcon = new System.Drawing.Icon(iconPath);
        }
        else
        {
            appIcon = System.Drawing.SystemIcons.Application;
        }

        _notifyIcon = new Forms.NotifyIcon
        {
            Icon = appIcon,
            Text = "IntanWave Node — Universal IP Audio Receiver",
            Visible = true
        };

        var contextMenu = new Forms.ContextMenuStrip();
        contextMenu.Items.Add("Buka Panel Kontrol", null, (s, e) => ShowMainWindow());
        contextMenu.Items.Add("Tes Bunyi Ampli", null, (s, e) => NodeCoordinator.Instance.PlayTestChime());
        contextMenu.Items.Add("-");
        contextMenu.Items.Add("Keluar", null, (s, e) => ExitApplication());

        _notifyIcon.ContextMenuStrip = contextMenu;
        _notifyIcon.DoubleClick += (s, e) => ShowMainWindow();
    }

    public void ShowMainWindow()
    {
        if (_mainWindow == null)
        {
            _mainWindow = new MainWindow();
        }
        _mainWindow.Show();
        _mainWindow.WindowState = WindowState.Normal;
        _mainWindow.Activate();
    }

    private void ExitApplication()
    {
        _notifyIcon?.Dispose();
        _notifyIcon = null;
        NodeCoordinator.Instance.Dispose();
        _mutex?.ReleaseMutex();
        Shutdown();
    }

    private void Application_Exit(object sender, ExitEventArgs e)
    {
        _notifyIcon?.Dispose();
        _notifyIcon = null;
    }
}
