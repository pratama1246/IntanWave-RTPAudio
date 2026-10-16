using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using Microsoft.Win32;

namespace IntanWave.Node.Services;

public enum WindowsFamily
{
    Windows8OrOlder,
    Windows10,
    Windows11
}

public static class WindowsVersionHelper
{
    [DllImport("dwmapi.dll", PreserveSig = true)]
    private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);

    private const int DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19;
    private const int DWMWA_USE_IMMERSIVE_DARK_MODE = 20;
    private const int DWMWA_WINDOW_CORNER_PREFERENCE = 33;
    private const int DWMWA_SYSTEMBACKDROP_TYPE = 38;

    public static WindowsFamily Family { get; private set; }
    public static string OsDisplayName { get; private set; } = "Windows";
    public static int BuildNumber { get; private set; }

    static WindowsVersionHelper()
    {
        DetectWindowsVersion();
    }

    private static void DetectWindowsVersion()
    {
        try
        {
            using var key = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows NT\CurrentVersion");
            if (key != null)
            {
                string? currentBuild = key.GetValue("CurrentBuild")?.ToString();
                string? productName = key.GetValue("ProductName")?.ToString();

                if (int.TryParse(currentBuild, out int build))
                {
                    BuildNumber = build;
                    if (build >= 22000)
                    {
                        Family = WindowsFamily.Windows11;
                        OsDisplayName = productName ?? "Windows 11";
                        return;
                    }
                    if (build >= 10240)
                    {
                        Family = WindowsFamily.Windows10;
                        OsDisplayName = productName ?? "Windows 10";
                        return;
                    }
                }
            }
        }
        catch { }

        // Fallback to Environment.OSVersion
        var version = Environment.OSVersion.Version;
        if (version.Major == 6 && version.Minor == 2)
        {
            Family = WindowsFamily.Windows8OrOlder;
            OsDisplayName = "Windows 8";
        }
        else if (version.Major == 6 && version.Minor == 3)
        {
            Family = WindowsFamily.Windows8OrOlder;
            OsDisplayName = "Windows 8.1";
        }
        else if (version.Major >= 10)
        {
            Family = WindowsFamily.Windows10;
            OsDisplayName = "Windows 10+";
        }
        else
        {
            Family = WindowsFamily.Windows8OrOlder;
            OsDisplayName = $"Windows ({version.Major}.{version.Minor})";
        }
    }

    /// <summary>
    /// Menerapkan styling DWM sesuai versi Windows secara adaptif
    /// </summary>
    public static void ApplyAdaptiveStyling(Window window)
    {
        var helper = new WindowInteropHelper(window);
        IntPtr hwnd = helper.EnsureHandle();

        if (Family == WindowsFamily.Windows11)
        {
            // Windows 11: Aktifkan Dark Mode, Rounded Corners & Mica
            int darkMode = 1;
            DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ref darkMode, sizeof(int));

            int cornerPreference = 2; // DWMWCP_ROUND
            DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ref cornerPreference, sizeof(int));

            int backdropType = 2; // DWMSBT_MAINWINDOW (Mica)
            DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ref backdropType, sizeof(int));
        }
        else if (Family == WindowsFamily.Windows10)
        {
            // Windows 10: Aktifkan Immersive Dark Mode jika didukung
            int darkMode = 1;
            if (BuildNumber >= 18985)
            {
                DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ref darkMode, sizeof(int));
            }
            else
            {
                DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1, ref darkMode, sizeof(int));
            }
        }
        // Di Windows 8 / 8.1: Tidak memanggil DwmSetWindowAttribute modern agar tidak crash
    }
}
