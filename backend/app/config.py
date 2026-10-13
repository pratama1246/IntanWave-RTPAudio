import os
import sys
from pathlib import Path

# Refresh PATH dari Windows Registry agar ffmpeg/ffplay/ffprobe langsung terdeteksi
if sys.platform == "win32":
    try:
        import winreg
        paths = []
        for root, subkey in [
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            (winreg.HKEY_CURRENT_USER, r"Environment")
        ]:
            try:
                with winreg.OpenKey(root, subkey) as k:
                    val, _ = winreg.QueryValueEx(k, "Path")
                    paths.append(val)
            except Exception:
                pass
        if paths:
            os.environ["PATH"] = ";".join(paths) + ";" + os.environ.get("PATH", "")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
AUDIO_DIR = STORAGE_DIR / "audio"
DB_PATH = STORAGE_DIR / "pa_system.db"

# Pastikan folder storage ada
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Default Settings
DEFAULT_MULTICAST_IP = os.getenv("MULTICAST_IP", "239.255.0.1")
DEFAULT_MULTICAST_PORT = int(os.getenv("MULTICAST_PORT", "5004"))
DEFAULT_ENABLE_MULTICAST = True
DEFAULT_ENABLE_LOCAL = False
