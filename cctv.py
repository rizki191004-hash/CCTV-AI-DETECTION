"""
cctv.py — Smart Toggle Controller for CCTV AI Detection.

Can be run via:
  - pythonw cctv.pyw (Double-click from Desktop with no black CMD window)
  - python cctv.py
"""

import ctypes
import os
import subprocess
import sys
import time
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(PROJECT_ROOT, "data", "cctv.pid")


def get_pythonw_path() -> str:
    """Locate pythonw.exe adjacent to sys.executable, or fall back to sys.executable."""
    candidate = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if os.path.exists(candidate):
        return candidate
    return sys.executable


def is_cctv_running() -> bool:
    """Check if the CCTV system is currently running via HTTP ping and PID file."""
    # 1. Try pinging local API
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/status",
            headers={"User-Agent": "CCTV-Launcher"}
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass

    # 2. Check PID file
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            # Check if PID is alive on Windows
            if sys.platform == "win32":
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if handle:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    return True
        except Exception:
            pass

    return False


def start_cctv() -> None:
    """Start CCTV AI in the background with zero visible console windows."""
    pythonw = get_pythonw_path()
    os.chdir(PROJECT_ROOT)

    # Detached windowless flags for Windows
    creation_flags = 0
    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        creation_flags = DETACHED_PROCESS | CREATE_NO_WINDOW

    subprocess.Popen(
        [pythonw, os.path.join(PROJECT_ROOT, "src", "main.py")],
        cwd=PROJECT_ROOT,
        creationflags=creation_flags,
        close_fds=True,
    )


def stop_cctv() -> None:
    """Cleanly stop all CCTV AI processes and Cloudflare tunnels."""
    # 1. Graceful shutdown via HTTP POST /api/system/shutdown
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/system/shutdown",
            data=b"{}",
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=1.5)
        time.sleep(1.0)
    except Exception:
        pass

    # 2. Terminate recorded PID and its entire process tree (/T)
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    creationflags=0x08000000
                )
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass

    # 3. Terminate any lingering Python processes running src/main.py or run.py
    if sys.platform == "win32":
        subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*src\\main.py*' -or $_.CommandLine -like '*run.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            ],
            capture_output=True,
            creationflags=0x08000000
        )

    # 4. Terminate any residual cloudflared instances
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/IM", "cloudflared.exe"],
            capture_output=True,
            creationflags=0x08000000
        )


def main():
    """Smart controller entrypoint."""
    if is_cctv_running():
        # CCTV is running: prompt to stop
        MB_YESNO = 0x00000004
        MB_ICONQUESTION = 0x00000020
        IDYES = 6

        res = ctypes.windll.user32.MessageBoxW(
            0,
            "CCTV AI Detection sedang AKTIF di latar belakang.\n\n"
            "Apakah Anda ingin MENGHENTIKAN aplikasi sekarang?\n\n"
            "• Klik [Ya] untuk Mematikan CCTV total\n"
            "• Klik [Tidak] untuk Membuka Dashboard Web",
            "CCTV AI Controller",
            MB_YESNO | MB_ICONQUESTION
        )

        if res == IDYES:
            stop_cctv()
            ctypes.windll.user32.MessageBoxW(
                0,
                "CCTV AI Detection dan Cloudflare Tunnel telah BERHASIL DIMATIKAN.\n\n"
                "Tidak ada proses yang berjalan di latar belakang.",
                "CCTV AI Controller",
                0x00000040  # MB_ICONINFORMATION
            )
        else:
            import webbrowser
            webbrowser.open("http://localhost:8000")
    else:
        # CCTV is not running: start it!
        start_cctv()


if __name__ == "__main__":
    main()

