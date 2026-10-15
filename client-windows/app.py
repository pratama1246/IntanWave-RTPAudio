import os
import sys
import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image
import pystray

from receiver import AudioReceiver

# Single instance lock configuration
SINGLE_INSTANCE_PORT = 45679


def ensure_single_instance(on_show_callback):
    """
    Mencegah aplikasi dijalankan dua kali.
    Jika sudah ada instansi yang berjalan, kirim sinyal agar instansi pertama
    menampilkan jendelanya ke depan, lalu instansi kedua langsung keluar.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        # Ini instansi pertama yang aktif
        def _listen_signals():
            while True:
                try:
                    data, _ = sock.recvfrom(64)
                    if data == b"SHOW":
                        on_show_callback()
                except Exception:
                    break

        t = threading.Thread(target=_listen_signals, daemon=True)
        t.start()
        return sock
    except Exception:
        # Port sudah dipakai -> Instansi lain sudah berjalan!
        try:
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_sock.sendto(b"SHOW", ("127.0.0.1", SINGLE_INSTANCE_PORT))
            client_sock.close()
        except Exception:
            pass
        sys.exit(0)


# Enable Per-Monitor DPI Awareness on Windows
if sys.platform == "win32":
    import winreg
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

REG_STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_APP_NAME = "IntanWaveNode"


def get_startup_target() -> str:
    """Mengembalikan command line untuk dijalankan saat Windows startup."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}" --minimized'

    base_dir = Path(__file__).resolve().parent
    exe_candidates = [
        base_dir / "dist" / "IntanWave-Node" / "IntanWave-Node.exe",
        base_dir / "IntanWave-Node" / "IntanWave-Node.exe",
        base_dir / "IntanWave-Node.exe",
    ]
    for exe in exe_candidates:
        if exe.exists():
            return f'"{exe.resolve()}" --minimized'

    bat_path = base_dir / "start_client.bat"
    if bat_path.exists():
        return f'"{bat_path.resolve()}" --minimized'

    python_exe = sys.executable
    pythonw = Path(python_exe).parent / "pythonw.exe"
    if pythonw.exists():
        python_exe = str(pythonw)
    return f'"{python_exe}" "{Path(__file__).resolve()}" --minimized'


def is_startup_enabled() -> bool:
    """Cek apakah IntanWave Node terdaftar di Windows Run Registry."""
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_STARTUP_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, REG_APP_NAME)
            return True
    except Exception:
        return False


def set_startup_enabled(enabled: bool) -> bool:
    """Tambah atau hapus IntanWave Node dari Windows Run Registry."""
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_STARTUP_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                cmd = get_startup_target()
                winreg.SetValueEx(key, REG_APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, REG_APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Error set_startup_enabled: {e}")
        return False

# Path resolution for standalone exe and development
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    EXE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    EXE_DIR = BUNDLE_DIR

ICO_PATH = BUNDLE_DIR / "app_icon.ico"
if not ICO_PATH.exists():
    ICO_PATH = EXE_DIR / "app_icon.ico"

PNG_PATH = BUNDLE_DIR / "app_icon.png"
if not PNG_PATH.exists():
    PNG_PATH = EXE_DIR / "app_icon.png"


class IntanWaveNodeWindow:
    """
    IntanWave Node — Terminal Audio Receiver
    Native Windows Default UI, minimalis, efisien, terhubung ke sistem audio pelabuhan.
    """

    def __init__(self, root: tk.Tk, receiver: AudioReceiver):
        self.root = root
        self.receiver = receiver
        self.tray_icon = None

        self.root.title("IntanWave Node")
        self.root.resizable(False, False)

        # Set Window Icon
        if ICO_PATH.exists():
            try:
                self.root.iconbitmap(str(ICO_PATH.resolve()))
            except Exception:
                pass

        # Apply Windows Native Theme
        self.style = ttk.Style()
        themes = self.style.theme_names()
        if "vista" in themes:
            self.style.theme_use("vista")
        elif "winnative" in themes:
            self.style.theme_use("winnative")

        # Configure font and button styles with proper Windows native padding
        self.style.configure(".", font=("Segoe UI", 9))
        self.style.configure("HeaderTitle.TLabel", font=("Segoe UI", 12, "bold"), foreground="#1c1c1c")
        self.style.configure("HeaderSub.TLabel", font=("Segoe UI", 8), foreground="#555555")
        self.style.configure("Save.TButton", font=("Segoe UI", 9, "bold"), padding=(10, 5))
        self.style.configure("Action.TButton", font=("Segoe UI", 9), padding=(8, 5))

        self.init_ui()
        self.setup_tray()

        # Dynamic window geometry calculation: prevents clipping on high-DPI displays
        self.root.update_idletasks()
        req_w = max(420, self.root.winfo_reqwidth() + 20)
        req_h = max(440, self.root.winfo_reqheight() + 20)
        self.root.geometry(f"{req_w}x{req_h}")

        # Handle window close (X) -> minimize to tray
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        # Jika dijalankan dari startup / flag --minimized, sembunyikan ke tray
        if "--minimized" in sys.argv or "-m" in sys.argv:
            self.root.withdraw()


    def init_ui(self):
        main_frame = ttk.Frame(self.root, padding="18 14 18 14")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Header (Bersih & Elegan)
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 8))

        lbl_title = ttk.Label(header_frame, text="IntanWave Node", style="HeaderTitle.TLabel")
        lbl_title.pack(anchor=tk.W)

        lbl_sub = ttk.Label(
            header_frame, 
            text="IP Multicast Audio Receiver & Auto-Discovery",
            style="HeaderSub.TLabel"
        )
        lbl_sub.pack(anchor=tk.W, pady=(1, 0))

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))

        # --- COLOR BAR STREAMING (STATUS INDIKATOR AUDIO) ---
        # Biru untuk Biasa (#2563eb), Merah untuk Darurat (#dc2626), Abu-abu untuk Standby (#f1f5f9)
        self.bar_frame = tk.Frame(main_frame, bg="#f1f5f9", padx=10, pady=7, highlightthickness=1, highlightbackground="#e2e8f0")
        self.bar_frame.pack(fill=tk.X, pady=(0, 10))

        self.lbl_bar_icon = tk.Label(
            self.bar_frame, 
            text="●", 
            font=("Segoe UI", 10), 
            bg="#f1f5f9", 
            fg="#64748b"
        )
        self.lbl_bar_icon.pack(side=tk.LEFT, padx=(0, 6))

        self.lbl_bar_text = tk.Label(
            self.bar_frame, 
            text="Standby • Menunggu Siaran", 
            font=("Segoe UI", 9, "bold"), 
            bg="#f1f5f9", 
            fg="#64748b",
            anchor=tk.W
        )
        self.lbl_bar_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 2. Form Server & Node Identity
        srv_frame = ttk.LabelFrame(main_frame, text=" Server & Identitas Node ", padding="12 10 12 10")
        srv_frame.pack(fill=tk.X, pady=(0, 10))

        srv_grid = ttk.Frame(srv_frame)
        srv_grid.pack(fill=tk.X)
        srv_grid.columnconfigure(1, weight=1)

        ttk.Label(srv_grid, text="Server PA Audio:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.entry_server = ttk.Entry(srv_grid)
        self.entry_server.insert(0, self.receiver.server_url)
        self.entry_server.grid(row=0, column=1, sticky=tk.EW, padx=(8, 0), pady=3)

        ttk.Label(srv_grid, text="Nama Perangkat:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.entry_name = ttk.Entry(srv_grid)
        self.entry_name.insert(0, self.receiver.device_name)
        self.entry_name.grid(row=1, column=1, sticky=tk.EW, padx=(8, 0), pady=3)

        ttk.Label(srv_grid, text="Group Audio:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.entry_zone = ttk.Entry(srv_grid)
        self.entry_zone.insert(0, ", ".join(self.receiver.groups))
        self.entry_zone.grid(row=2, column=1, sticky=tk.EW, padx=(8, 0), pady=3)

        # 3. Form Channel IP Phone Darurat (Opsional)
        cfg_frame = ttk.LabelFrame(main_frame, text=" Channel Telepon Darurat (Opsional) ", padding="12 10 12 10")
        cfg_frame.pack(fill=tk.X, pady=(0, 10))

        cfg_grid = ttk.Frame(cfg_frame)
        cfg_grid.pack(fill=tk.X)
        cfg_grid.columnconfigure(1, weight=1)

        ttk.Label(cfg_grid, text="IP Phone Multicast:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.entry_secondary_ip = ttk.Entry(cfg_grid)
        self.entry_secondary_ip.insert(0, self.receiver.secondary_channel_str)
        self.entry_secondary_ip.grid(row=0, column=1, sticky=tk.EW, padx=(8, 0), pady=3)

        lbl_hint = ttk.Label(
            cfg_grid, 
            text="*Khusus panggilan darurat dari Control Room (misal: 239.255.0.2)", 
            font=("Segoe UI", 7), 
            foreground="#64748b"
        )
        lbl_hint.grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=(1, 0))

        # 4. Status Indikator Server (Live Heartbeat Badge)
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 6))

        self.lbl_server_status = ttk.Label(
            status_frame,
            text="Menghubungkan ke Server PA...",
            font=("Segoe UI", 8, "bold"),
            foreground="#b45309"
        )
        self.lbl_server_status.pack(anchor=tk.W)

        # 5. Opsi Windows Startup (Auto-start tanpa butuh installer)
        self.var_startup = tk.BooleanVar(value=is_startup_enabled())
        self.chk_startup = ttk.Checkbutton(
            main_frame,
            text="Jalankan otomatis saat Windows dinyalakan (Startup)",
            variable=self.var_startup,
            command=self.on_toggle_startup
        )
        self.chk_startup.pack(anchor=tk.W, pady=(0, 10))

        # 6. Tombol Simpan
        self.btn_save = ttk.Button(
            main_frame, 
            style="Save.TButton",
            text="Simpan & Terapkan Konfigurasi", 
            command=self.save_settings
        )
        self.btn_save.pack(fill=tk.X, pady=(0, 10))

        # 7. Action Buttons (Tes Bunyi Ampli & Sembunyikan)
        btn_box = ttk.Frame(main_frame)
        btn_box.pack(fill=tk.X)

        self.btn_test = ttk.Button(
            btn_box, 
            text="Tes Bunyi Ampli", 
            style="Action.TButton",
            command=self.receiver.play_test_chime
        )
        self.btn_test.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.btn_hide = ttk.Button(
            btn_box, 
            text="Sembunyikan ke Tray", 
            style="Action.TButton",
            command=self.hide_window
        )
        self.btn_hide.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))


    def on_toggle_startup(self):
        """Handler saat checkbox startup diklik."""
        enabled = self.var_startup.get()
        success = set_startup_enabled(enabled)
        if not success:
            self.var_startup.set(not enabled)
            messagebox.showwarning("Peringatan", "Gagal memperbarui pengaturan Windows Startup.", parent=self.root)

    def save_settings(self):
        new_server = self.entry_server.get().strip()
        new_name = self.entry_name.get().strip()
        new_zone = self.entry_zone.get().strip()
        new_sec = self.entry_secondary_ip.get().strip()

        if not new_server:
            messagebox.showwarning("Peringatan", "URL Server PA Audio tidak boleh kosong.", parent=self.root)
            return
        if not new_name:
            messagebox.showwarning("Peringatan", "Nama Perangkat tidak boleh kosong.", parent=self.root)
            return
        if not new_zone:
            messagebox.showwarning("Peringatan", "Group Audio tidak boleh kosong.\n(Pisahkan koma jika > 1, misal: Kantor, Satpam)", parent=self.root)
            return

        # Sinkronkan status startup jika berbeda
        if self.var_startup.get() != is_startup_enabled():
            set_startup_enabled(self.var_startup.get())

        self.receiver.save_config(new_server, new_name, new_zone, secondary_channel=new_sec)
        sec_msg = f"\nIP Phone: rtp://{new_sec}" if new_sec else ""
        messagebox.showinfo(
            "Berhasil", 
            f"Konfigurasi disimpan!\nNode mendaftar ke: {new_server}\nGroup: {new_zone}{sec_msg}",
            parent=self.root
        )

    def update_heartbeat_status(self, connected: bool, info: dict):
        """Thread-safe status update untuk telemetri heartbeat dari server."""
        def _apply():
            if connected:
                registered_ip = info.get("ip_address", self.receiver.registered_ip)
                grps = info.get("groups")
                grps_str = ", ".join(grps) if isinstance(grps, list) else (info.get("zone") or self.receiver.zone)
                self.lbl_server_status.config(
                    text=f"Terdaftar di Server ({registered_ip}) • Group: {grps_str}",
                    foreground="#0d7a3e"
                )
            else:
                self.lbl_server_status.config(
                    text=f"Belum Terhubung ke Server ({self.receiver.server_url})",
                    foreground="#c22525"
                )
        self.root.after(0, _apply)

    def update_status(self, status: str, category: str = "biasa", title: str = ""):
        """Thread-safe status update callback dari receiver dengan color bar visual."""
        def _apply():
            if status == "STREAMING":
                is_emergency = (category == "darurat")
                bg_color = "#dc2626" if is_emergency else "#2563eb"
                border_color = "#b91c1c" if is_emergency else "#1d4ed8"
                fg_color = "#ffffff"
                icon = "[DARURAT]" if is_emergency else "[SIARAN]"
                disp_title = f": {title}" if title else ""
                bar_text = f"SIARAN DARURAT{disp_title}" if is_emergency else f"SEDANG MENERIMA SIARAN{disp_title}"

                self.bar_frame.config(bg=bg_color, highlightbackground=border_color)
                self.lbl_bar_icon.config(text=icon, bg=bg_color, fg=fg_color)
                self.lbl_bar_text.config(text=bar_text, bg=bg_color, fg=fg_color)

                self.root.title(f"IntanWave Node [{'DARURAT' if is_emergency else 'STREAMING'}]")
                if self.tray_icon:
                    self.tray_icon.title = f"IntanWave Node — {'SIARAN DARURAT' if is_emergency else 'SEDANG SIARAN'}"

                # Bawa jendela ke depan jika darurat agar operator langsung melihat
                if is_emergency:
                    self.show_window()
            else:
                self.bar_frame.config(bg="#f1f5f9", highlightbackground="#e2e8f0")
                self.lbl_bar_icon.config(text="●", bg="#f1f5f9", fg="#64748b")
                self.lbl_bar_text.config(text="Standby • Menunggu Siaran", bg="#f1f5f9", fg="#64748b")
                self.root.title("IntanWave Node")
                if self.tray_icon:
                    self.tray_icon.title = "IntanWave Node — Standby"

        self.root.after(0, _apply)

    def setup_tray(self):
        """Inisialisasi Windows System Tray Icon via pystray."""
        try:
            if PNG_PATH.exists():
                icon_image = Image.open(str(PNG_PATH.resolve()))
            elif ICO_PATH.exists():
                icon_image = Image.open(str(ICO_PATH.resolve()))
            else:
                icon_image = Image.new("RGB", (64, 64), color="#0055ff")
        except Exception:
            icon_image = Image.new("RGB", (64, 64), color="#0055ff")

        menu = pystray.Menu(
            pystray.MenuItem("IntanWave Node", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Buka Panel Kontrol", self.on_tray_show, default=True),
            pystray.MenuItem("Tes Bunyi Ampli", lambda: self.receiver.play_test_chime()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Keluar", self.on_tray_quit)
        )

        self.tray_icon = pystray.Icon("IntanWave_Node", icon_image, "IntanWave Node — Standby", menu)
        self.tray_icon.run_detached()

    def on_tray_show(self, icon=None, item=None):
        self.root.after(0, self.show_window)

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_window(self):
        self.root.withdraw()

    def on_window_close(self):
        """Saat user klik tanda silang (X), sembunyikan jendela ke tray."""
        self.hide_window()

    def on_tray_quit(self, icon=None, item=None):
        """Keluar aplikasi sepenuhnya."""
        def _do_quit():
            self.receiver.stop()
            if self.tray_icon:
                self.tray_icon.stop()
            self.root.quit()
            self.root.destroy()
            sys.exit(0)

        self.root.after(0, _do_quit)


class ClientApp:
    def __init__(self):
        # Cegah aplikasi dijalankan dua kali
        self.lock_socket = ensure_single_instance(self.restore_existing_window)

        self.root = tk.Tk()
        self.receiver = AudioReceiver()
        self.window = IntanWaveNodeWindow(self.root, self.receiver)
        self.receiver.on_status_change = self.window.update_status
        self.receiver.on_heartbeat_change = self.window.update_heartbeat_status


    def restore_existing_window(self):
        """Callback dipanggil saat user mencoba membuka aplikasi kedua kali."""
        if hasattr(self, "root") and self.root:
            self.root.after(0, self.window.show_window)

    def run(self):
        self.receiver.start()
        self.root.mainloop()


def main():
    app = ClientApp()
    app.run()


if __name__ == "__main__":
    main()
