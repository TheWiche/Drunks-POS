"""
Drunks POS — App unificada.
Arranca uvicorn en un hilo daemon y abre la UI en un webview nativo.
Sin CMD visible, sin browser externo. Un solo .exe.
"""
import os
import sys
import time
import threading
import urllib.request
from pathlib import Path

# ── Credenciales Supabase (se setean antes de importar main) ──────────────────
os.environ.setdefault("SUPABASE_URL", "https://crqfohuwvbebyugxodqe.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNycWZvaHV3dmJlYnl1Z3hvZHFlIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3ODA1ODgyMTgsImV4cCI6MjA5NjE2NDIxOH0"
    ".F5RAHHnBt722dm9-yfe8bZw6J0wAJWh01fJfh3pf4lM",
)

# ── Directorio raíz cuando corre como exe congelado ───────────────────────────
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
    os.chdir(APP_DIR)

HOST = "127.0.0.1"
PORT = 8000


def _start_server() -> None:
    import uvicorn
    from main import app
    uvicorn.run(app, host=HOST, port=PORT, log_level="error")


def _wait_ready(timeout: float = 20.0) -> bool:
    url = f"http://{HOST}:{PORT}/"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.15)
    return False


if __name__ == "__main__":
    import webview  # importar aquí para que PyInstaller lo detecte correctamente

    # Iniciar servidor en background
    server_thread = threading.Thread(target=_start_server, daemon=True, name="uvicorn")
    server_thread.start()

    # Esperar a que levante
    _wait_ready()

    # Abrir ventana nativa
    webview.create_window(
        "Drunks POS",
        f"http://{HOST}:{PORT}/vendedor",
        width=1366,
        height=768,
        min_size=(1024, 600),
    )
    webview.start()
