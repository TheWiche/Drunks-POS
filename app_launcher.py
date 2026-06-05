"""
Drunks POS — App unificada.
Arranca uvicorn en un hilo daemon y abre la UI en un webview nativo.
Sin CMD visible, sin browser externo. Un solo .exe.
"""
import os
import sys
import time
import threading
import traceback
import urllib.request
from pathlib import Path

# ── Directorio raíz cuando corre como exe congelado ───────────────────────────
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
    os.chdir(APP_DIR)
else:
    APP_DIR = Path(__file__).parent

LOG_PATH = APP_DIR / "drunks_error.log"

# ── Credenciales Supabase (se setean antes de importar main) ──────────────────
os.environ.setdefault("SUPABASE_URL", "https://crqfohuwvbebyugxodqe.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNycWZvaHV3dmJlYnl1Z3hvZHFlIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3ODA1ODgyMTgsImV4cCI6MjA5NjE2NDIxOH0"
    ".F5RAHHnBt722dm9-yfe8bZw6J0wAJWh01fJfh3pf4lM",
)

HOST = "127.0.0.1"
PORT = 8000

_server_error: str = ""


def _log(msg: str) -> None:
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _start_server() -> None:
    global _server_error
    try:
        _log("Importando uvicorn y main...")
        import uvicorn
        from main import app  # noqa: F401 — PyInstaller necesita ver este import
        _log("Módulos importados OK. Arrancando uvicorn...")
        uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
    except Exception:
        _server_error = traceback.format_exc()
        _log(f"ERROR en servidor:\n{_server_error}")


def _wait_ready(timeout: float = 25.0) -> bool:
    url = f"http://{HOST}:{PORT}/"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            if _server_error:
                return False
            time.sleep(0.2)
    return False


if __name__ == "__main__":
    import webview  # aquí para que PyInstaller lo detecte correctamente

    _log("=== Drunks POS iniciando ===")

    server_thread = threading.Thread(target=_start_server, daemon=True, name="uvicorn")
    server_thread.start()

    ready = _wait_ready()
    _log(f"Servidor listo: {ready}  |  error: {bool(_server_error)}")

    if not ready or _server_error:
        error_html = f"""<!DOCTYPE html><html><body style="background:#0d0d1a;color:#fff;
            font-family:Segoe UI,sans-serif;display:flex;flex-direction:column;
            align-items:center;justify-content:center;height:100vh;gap:1rem">
            <div style="font-size:2rem">⚠️</div>
            <h2>No se pudo iniciar el servidor</h2>
            <pre style="background:#1a1a2e;padding:1rem;border-radius:.5rem;
                font-size:.75rem;max-width:80%;overflow:auto;color:#f87171">
{_server_error or 'Tiempo de espera agotado (25 s)'}
            </pre>
            <p style="color:#8b8ba8;font-size:.85rem">
                Revisa <b>drunks_error.log</b> en la carpeta de instalación.
            </p>
        </body></html>"""
        window = webview.create_window("Drunks POS — Error", html=error_html,
                                       width=860, height=500)
    else:
        window = webview.create_window(
            "Drunks POS",
            f"http://{HOST}:{PORT}/",
            width=1366,
            height=768,
            min_size=(1024, 600),
        )

    webview.start()
