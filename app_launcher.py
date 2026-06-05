"""
Drunks POS — App unificada.
Shell nativa con barra de navegación, detección de updates y ventana de progreso.
"""
import os
import sys
import time
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
PORT       = 8000

_main_window   = None
_update_window = None
_server_error  = ""

# ── HTML de la ventana de actualización ──────────────────────────────────────
UPDATE_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Actualizando Drunks POS</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d0d1a;color:#fff;font-family:'Segoe UI',sans-serif;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  height:100vh;gap:1.1rem;text-align:center;padding:2rem}
.emoji{font-size:2.8rem}
h2{font-size:1.25rem;font-weight:700}
.sub{color:#8b8ba8;font-size:.88rem;min-height:1.2em}
.bar-wrap{width:100%;max-width:380px;background:#1e1e35;border-radius:99px;height:7px;overflow:hidden}
.bar{height:100%;background:#7c3aed;border-radius:99px;width:0%;transition:width .4s ease}
.pct{color:#8b8ba8;font-size:.78rem}
.err{color:#f87171;font-size:.8rem;max-width:380px;word-break:break-word}
</style>
</head>
<body>
  <div class="emoji">🍺</div>
  <h2>Instalando actualización...</h2>
  <p class="sub" id="sub">Preparando descarga</p>
  <div class="bar-wrap"><div class="bar" id="bar"></div></div>
  <p class="pct" id="pct">0%</p>
  <p class="err" id="err" style="display:none"></p>
<script>
function setProgress(pct, msg) {
  document.getElementById('bar').style.width = pct + '%';
  document.getElementById('pct').textContent  = pct + '%';
  if (msg) document.getElementById('sub').textContent = msg;
}
function setDone() {
  document.getElementById('bar').style.width = '100%';
  document.getElementById('pct').textContent  = '100%';
  document.getElementById('sub').textContent  = 'Reiniciando Drunks POS...';
}
function setError(msg) {
  document.getElementById('bar').style.background = '#ef4444';
  document.getElementById('sub').textContent = 'Error al actualizar';
  var e = document.getElementById('err');
  e.textContent = msg; e.style.display = 'block';
}
</script>
</body>
</html>"""


# ── API expuesta a JS vía window.pywebview.api ────────────────────────────────
class AppAPI:
    def open_update_window(self):
        global _update_window
        if _update_window:
            return
        import webview as _wv
        _update_window = _wv.create_window(
            "Drunks POS — Actualizando",
            html=UPDATE_HTML,
            width=520, height=340,
            resizable=False,
        )
        threading.Thread(target=_run_update, daemon=True, name="updater").start()


# ── Lógica de actualización con progreso ─────────────────────────────────────
def _run_update():
    global _update_window
    try:
        from updater import _update_info, download_and_apply

        def on_progress(pct: int, msg: str = ""):
            if _update_window:
                safe = msg.replace("'", "\\'")
                _update_window.evaluate_js(f"setProgress({pct},'{safe}')")

        url = _update_info.get("url")
        if not url:
            _log("update: URL no encontrada en _update_info")
            return

        on_progress(5, "Iniciando descarga...")
        download_and_apply(url, progress_cb=on_progress)  # llama os._exit(0) al terminar

    except Exception:
        err = traceback.format_exc()
        _log(f"update error:\n{err}")
        if _update_window:
            short = err.strip().splitlines()[-1]
            _update_window.evaluate_js(f"setError('{short}')")
        _update_window = None


# ── Polling: notifica al main_window cuando hay update disponible ─────────────
def _poll_updates():
    time.sleep(3)  # darle tiempo al chequeo de background
    for _ in range(120):
        time.sleep(0.5)
        try:
            from updater import _update_info
            if _update_info.get("has_update") and _update_info.get("latest"):
                latest = _update_info["latest"]
                if _main_window:
                    _main_window.evaluate_js(f"showUpdate('{latest}')")
                return
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
        from main import app  # noqa: F401
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
