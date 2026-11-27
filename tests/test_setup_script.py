"""
tests/test_setup_script.py
TDD: Verifikasi file setup portabilitas ada dan valid.
"""
import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_setup_bat_exists():
    """setup.bat harus ada di root project."""
    path = os.path.join(PROJECT_ROOT, "setup.bat")
    assert os.path.isfile(path), "setup.bat tidak ditemukan di root project"


def test_setup_bat_checks_python():
    """setup.bat harus mengecek ketersediaan Python."""
    path = os.path.join(PROJECT_ROOT, "setup.bat")
    content = open(path, encoding="utf-8").read()
    assert "python" in content.lower(), "setup.bat harus memeriksa Python"


def test_setup_bat_installs_requirements():
    """setup.bat harus menjalankan pip install -r requirements.txt."""
    path = os.path.join(PROJECT_ROOT, "setup.bat")
    content = open(path, encoding="utf-8").read()
    assert "requirements.txt" in content, "setup.bat harus install requirements.txt"


def test_setup_bat_handles_env():
    """setup.bat harus menangani konfigurasi .env."""
    path = os.path.join(PROJECT_ROOT, "setup.bat")
    content = open(path, encoding="utf-8").read()
    assert ".env" in content, "setup.bat harus membuat/mengisi .env"


def test_setup_bat_handles_telegram_token():
    """setup.bat harus meminta TELEGRAM_BOT_TOKEN."""
    path = os.path.join(PROJECT_ROOT, "setup.bat")
    content = open(path, encoding="utf-8").read()
    assert "TELEGRAM_BOT_TOKEN" in content, "setup.bat harus meminta Telegram Bot Token"


def test_setup_bat_has_anti_close_pause():
    """setup.bat harus memiliki pause agar CMD tidak langsung menutup."""
    path = os.path.join(PROJECT_ROOT, "setup.bat")
    content = open(path, encoding="utf-8").read()
    assert "pause" in content.lower(), "setup.bat harus memiliki pause penahan jendela"


def test_distribusi_md_exists():
    """DISTRIBUSI.md harus ada sebagai panduan apa yang dizip."""
    path = os.path.join(PROJECT_ROOT, "DISTRIBUSI.md")
    assert os.path.isfile(path), "DISTRIBUSI.md tidak ditemukan"


def test_distribusi_md_mentions_model_files():
    """DISTRIBUSI.md harus menyebut file model .pt."""
    path = os.path.join(PROJECT_ROOT, "DISTRIBUSI.md")
    content = open(path, encoding="utf-8").read()
    assert ".pt" in content, "DISTRIBUSI.md harus menyebut file model yolov8*.pt"


def test_requirements_txt_exists():
    """requirements.txt harus ada."""
    path = os.path.join(PROJECT_ROOT, "requirements.txt")
    assert os.path.isfile(path), "requirements.txt tidak ditemukan"


def test_env_example_exists():
    """.env.example harus ada sebagai template konfigurasi."""
    path = os.path.join(PROJECT_ROOT, ".env.example")
    assert os.path.isfile(path), ".env.example tidak ditemukan"


def test_launch_py_exists():
    """launch.py harus ada sebagai launcher cross-platform."""
    path = os.path.join(PROJECT_ROOT, "launch.py")
    assert os.path.isfile(path), "launch.py tidak ditemukan"


def test_model_files_exist():
    """File model YOLOv8 (.pt) harus ada di root project."""
    for model in ["yolov8n.pt", "yolov8n-pose.pt"]:
        path = os.path.join(PROJECT_ROOT, model)
        assert os.path.isfile(path), f"Model {model} tidak ditemukan — wajib ikut dalam distribusi zip"


def test_setup_bat_auto_installs_python_when_missing():
    """setup.bat harus memiliki kemampuan mengunduh/memasang Python otomatis jika belum ada."""
    path = os.path.join(PROJECT_ROOT, "setup.bat")
    content = open(path, encoding="utf-8").read().lower()
    assert "powershell" in content and ("python-3.11" in content or "winget" in content), (
        "setup.bat harus memiliki mekanisme otomatis untuk mengunduh/memasang Python 3.11"
    )


def test_setup_bat_refreshes_path_for_installed_python():
    """setup.bat harus me-refresh PATH atau mendeteksi folder instalasi Python pengguna."""
    path = os.path.join(PROJECT_ROOT, "setup.bat")
    content = open(path, encoding="utf-8").read()
    assert "localappdata" in content.lower() or "programs\\python" in content.lower(), (
        "setup.bat harus mendeteksi folder instalasi Python di LocalAppData"
    )

