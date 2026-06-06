"""
Drunks POS — App unificada.
Shell nativa con barra de navegación, detección de updates y ventana de progreso.
"""
import os
import sys
import time
import socket
import threading
import traceback
import urllib.request
from pathlib import Path

# ── Directorio raíz ───────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).parent
    os.chdir(APP_DIR)
else:
    APP_DIR = Path(__file__).parent

LOG_PATH = APP_DIR / "drunks_error.log"

# ── Credenciales Supabase ─────────────────────────────────────────────────────
os.environ.setdefault("SUPABASE_URL", "https://crqfohuwvbebyugxodqe.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNycWZvaHV3dmJlYnl1Z3hvZHFlIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3ODA1ODgyMTgsImV4cCI6MjA5NjE2NDIxOH0"
    ".F5RAHHnBt722dm9-yfe8bZw6J0wAJWh01fJfh3pf4lM",
)

BIND_HOST  = "0.0.0.0"
LOCAL_HOST = "127.0.0.1"

def _pick_port(preferred: int = 8000) -> int:
    """Usa el puerto preferido si está libre, si no busca uno disponible."""
    for port in [preferred] + list(range(8001, 8020)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((LOCAL_HOST, port))
                return port
            except OSError:
                continue
    # último recurso: puerto asignado por el OS
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((LOCAL_HOST, 0))
        return s.getsockname()[1]

PORT = _pick_port(8000)

_main_window   = None
_update_window = None
_server_error  = ""

# ── Ventana de progreso de actualización (tkinter, no webview) ────────────────
class _UpdateProgressWindow:
    """Ventana tkinter simple para mostrar el progreso de la actualización."""
    def __init__(self):
        import tkinter as tk
        from tkinter import ttk
        self._tk = tk
        self._root = tk.Tk()
        self._root.title("Drunks POS — Actualizando")
        self._root.geometry("420x160")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", lambda: None)  # no cerrar manualmente

        # Centrar
        self._root.update_idletasks()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(f"420x160+{(sw-420)//2}+{(sh-160)//2}")

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            style.theme_use("default")

        frame = ttk.Frame(self._root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Instalando actualización de Drunks POS...",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)

        self._status_var = tk.StringVar(value="Preparando descarga...")
        ttk.Label(frame, textvariable=self._status_var,
                  font=("Segoe UI", 9)).pack(anchor=tk.W, pady=(6, 4))

        self._progress = ttk.Progressbar(frame, mode="determinate", maximum=100, length=380)
        self._progress.pack(fill=tk.X)

        self._pct_var = tk.StringVar(value="0%")
        ttk.Label(frame, textvariable=self._pct_var,
                  font=("Segoe UI", 8)).pack(anchor=tk.E, pady=(2, 0))

    def set_progress(self, pct: int, msg: str = ""):
        def _apply():
            self._progress["value"] = pct
            self._pct_var.set(f"{pct}%")
            if msg:
                self._status_var.set(msg)
        try:
            self._root.after(0, _apply)
        except Exception:
            pass

    def set_error(self, msg: str):
        def _apply():
            self._status_var.set(f"Error: {msg}")
            self._progress["value"] = 0
        try:
            self._root.after(0, _apply)
        except Exception:
            pass

    def run(self):
        self._root.mainloop()

    def close(self):
        try:
            self._root.after(0, self._root.destroy)
        except Exception:
            pass


# ── API expuesta a JS vía window.pywebview.api ────────────────────────────────
class AppAPI:
    def open_update_window(self):
        threading.Thread(target=_run_update_with_ui, daemon=True, name="updater").start()


# ── Lógica de actualización con ventana tkinter ───────────────────────────────
def _run_update_with_ui():
    global _update_window
    win = _UpdateProgressWindow()
    _update_window = win

    def do_update():
        try:
            from updater import _update_info, download_and_apply

            url = _update_info.get("url")
            if not url:
                _log("update: URL no encontrada en _update_info")
                win.set_error("No se encontró la URL de descarga.")
                return

            download_and_apply(url, progress_cb=win.set_progress)
            # download_and_apply llama os._exit(0) al terminar — no llega aquí

        except Exception:
            err = traceback.format_exc()
            _log(f"update error:\n{err}")
            short = err.strip().splitlines()[-1]
            win.set_error(short)
            _update_window = None

    threading.Thread(target=do_update, daemon=True, name="update-worker").start()
    win.run()  # bloquea este hilo con el mainloop de tkinter
    _update_window = None


# ── Polling: notifica al main_window cuando hay update disponible ─────────────
def _poll_updates():
    """Chequea en startup y re-chequea cada 2 horas mientras la app está abierta."""
    notified: set = set()

    while True:
        time.sleep(5)  # gracia inicial para que el chequeo de background termine
        for _ in range(120):  # poll hasta 60 s por cada ciclo
            time.sleep(0.5)
            try:
                from updater import _update_info
                latest = _update_info.get("latest")
                if _update_info.get("has_update") and latest and latest not in notified:
                    if _main_window:
                        _main_window.evaluate_js(f"showUpdate('{latest}')")
                    notified.add(latest)
                    break
            except Exception:
                pass

        time.sleep(7200)  # esperar 2 horas antes del siguiente chequeo

        try:
            from updater import check_for_update
            check_for_update()
        except Exception:
            pass


# ── Servidor ──────────────────────────────────────────────────────────────────
def _log(msg: str) -> None:
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _start_server() -> None:
    global _server_error
    try:
        _log("Importando módulos del servidor...")
        import uvicorn
        from backend.main import app  # noqa: F401
        _log("Módulos OK — arrancando uvicorn en 0.0.0.0:" + str(PORT))
        uvicorn.run(app, host=BIND_HOST, port=PORT, log_level="warning")
    except Exception:
        _server_error = traceback.format_exc()
        _log(f"ERROR servidor:\n{_server_error}")


def _wait_ready(timeout: float = 25.0) -> bool:
    url = f"http://{LOCAL_HOST}:{PORT}/"
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


# ── Punto de entrada ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import webview

    _log("=== Drunks POS iniciando ===")

    server_thread = threading.Thread(target=_start_server, daemon=True, name="uvicorn")
    server_thread.start()

    ready = _wait_ready()
    _log(f"Servidor listo={ready}  error={bool(_server_error)}")

    api = AppAPI()

    if not ready or _server_error:
        error_html = f"""<!DOCTYPE html><html><body style="background:#0d0d1a;color:#fff;
            font-family:'Segoe UI',sans-serif;display:flex;flex-direction:column;
            align-items:center;justify-content:center;height:100vh;gap:1rem;padding:2rem;text-align:center">
            <div style="font-size:2rem">⚠️</div>
            <h2>No se pudo iniciar el servidor</h2>
            <pre style="background:#1a1a2e;padding:1rem;border-radius:.5rem;
                font-size:.72rem;max-width:90%;overflow:auto;color:#f87171;text-align:left">
{_server_error or "Tiempo de espera agotado (25 s)"}
            </pre>
            <p style="color:#8b8ba8;font-size:.82rem">Revisa <b>drunks_error.log</b> en la carpeta de instalación.</p>
        </body></html>"""
        _main_window = webview.create_window(
            "Drunks POS — Error", html=error_html, width=860, height=520
        )
    else:
        _main_window = webview.create_window(
            "Drunks POS",
            f"http://{LOCAL_HOST}:{PORT}/app",
            width=1366, height=768,
            min_size=(1024, 600),
            js_api=api,
        )
        # Iniciar polling de updates cuando la ventana cargue
        _main_window.events.loaded += lambda: threading.Thread(
            target=_poll_updates, daemon=True, name="upd-poll"
        ).start()

    webview.start()
