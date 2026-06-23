"""
Modulo de auto-actualizacion para Drunks POS.
Consulta GitHub Releases y aplica la actualizacion sin intervencion tecnica.
"""
import os
import sys
import time
import zipfile
import threading
import tempfile
import subprocess
from pathlib import Path

GITHUB_REPO = "TheWiche/Drunks-POS"
TEMP_UPDATE_DIR = Path(tempfile.gettempdir()) / "drunks_update"

# Version de este build -- se actualiza en cada release.
# Hardcodeada aqui para que nunca dependa de un archivo externo.
APP_VERSION = "1.0.28"

_update_info: dict = {
    "has_update": False,
    "latest":     None,
    "current":    "0.0.0",
    "url":        None,
    "checking":   False,
    "error":      None,
}


def get_app_root() -> Path:
    """Raiz del proyecto (directorio del exe o del script)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_current_version() -> str:
    """Retorna la version de este build (constante hardcodeada en APP_VERSION)."""
    return APP_VERSION


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0, 0, 0)


def check_for_update() -> None:
    """Consulta la API de GitHub Releases. Actualiza _update_info."""
    _update_info["checking"] = True
    _update_info["error"] = None
    try:
        import httpx
        r = httpx.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=8.0,
            follow_redirects=True,
        )
        if r.status_code != 200:
            _update_info["error"] = f"GitHub respondio {r.status_code}"
            return

        data = r.json()
        latest = data.get("tag_name", "").lstrip("v")
        current = get_current_version()

        asset_url = next(
            (a["browser_download_url"] for a in data.get("assets", [])
             if a["name"].endswith(".zip")),
            None,
        )

        _update_info.update({
            "has_update": _version_tuple(latest) > _version_tuple(current),
            "latest":     latest,
            "current":    current,
            "url":        asset_url,
        })

    except ImportError:
        _update_info["error"] = "httpx no disponible"
    except Exception as exc:
        _update_info["error"] = str(exc)
    finally:
        _update_info["checking"] = False


def start_background_check() -> None:
    """Lanza el chequeo de actualizacion en un hilo daemon (no bloquea el arranque)."""
    _update_info["current"] = get_current_version()
    t = threading.Thread(target=check_for_update, daemon=True, name="update-check")
    t.start()


_download_progress: dict = {
    "active": False,
    "pct": 0,
    "msg": "",
    "error": None,
    "done": False,
}


def get_progress() -> dict:
    return dict(_download_progress)


def download_and_apply(url: str, progress_cb=None) -> None:
    """
    Descarga el ZIP, extrae los archivos y usa un script PowerShell para
    reemplazar la instalacion completa y reiniciar — sin VBScript ni robocopy.
    """
    import shutil

    _download_progress.update({"active": True, "pct": 0, "msg": "", "error": None, "done": False})

    def _prog(pct: int, msg: str = "") -> None:
        _download_progress["pct"] = pct
        _download_progress["msg"] = msg
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass

    try:
        import httpx

        if TEMP_UPDATE_DIR.exists():
            shutil.rmtree(TEMP_UPDATE_DIR, ignore_errors=True)
        TEMP_UPDATE_DIR.mkdir(parents=True, exist_ok=True)

        zip_path = TEMP_UPDATE_DIR / "update.zip"

        # 1. Descargar
        _prog(5, "Conectando con el servidor...")
        with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(zip_path, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = 5 + int(downloaded * 65 / total)
                        _prog(pct, f"Descargando... {downloaded // (1024*1024)} MB")

        # 2. Extraer
        _prog(72, "Extrayendo archivos...")
        extract_dir = TEMP_UPDATE_DIR / "extracted"
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        zip_path.unlink(missing_ok=True)

        # 3. Localizar la carpeta del update
        _prog(80, "Preparando instalacion...")
        app_root = get_app_root()
        exe_name = "Drunks.exe"

        new_exe_src = next(
            (f for f in extract_dir.rglob(exe_name) if f.is_file()),
            None
        )
        if not new_exe_src:
            raise FileNotFoundError(f"No se encontro {exe_name} en el archivo descargado.")

        src_folder = new_exe_src.parent
        main_exe   = app_root / exe_name

        _prog(92, "Preparando script de instalacion...")

        # 4. PowerShell: espera, copia todos los archivos, reinicia.
        #    Copy-Item -Recurse -Force es mas confiable que robocopy en este contexto.
        src_str = str(src_folder).replace("'", "''")
        dst_str = str(app_root).replace("'", "''")
        tmp_str = str(TEMP_UPDATE_DIR).replace("'", "''")
        exe_str = str(main_exe).replace("'", "''")

        ps_script = (
            "Start-Sleep -Seconds 6\r\n"
            "try {\r\n"
            f"    Copy-Item -Path '{src_str}\\*' -Destination '{dst_str}' -Recurse -Force -ErrorAction Stop\r\n"
            "} catch {\r\n"
            f"    $_ | Out-File '{tmp_str}\\update_error.log' -Force\r\n"
            "}\r\n"
            f"Remove-Item -Path '{tmp_str}' -Recurse -Force -ErrorAction SilentlyContinue\r\n"
            f"Start-Process -FilePath '{exe_str}'\r\n"
        )
        ps_path = app_root / "_update.ps1"
        ps_path.write_text(ps_script, encoding="utf-8")

        _prog(98, "Reiniciando en 6 segundos...")
        subprocess.Popen(
            [
                "powershell",
                "-ExecutionPolicy", "Bypass",
                "-NonInteractive",
                "-WindowStyle", "Hidden",
                "-File", str(ps_path),
            ],
            creationflags=(
                subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.CREATE_NO_WINDOW
            ),
        )
        _prog(100, "Cerrando aplicacion...")
        _download_progress["done"] = True
        time.sleep(2.5)
        os._exit(0)

    except Exception as exc:
        _update_info["error"] = f"Error al aplicar actualizacion: {exc}"
        _download_progress["error"] = str(exc)
        _download_progress["active"] = False
        raise
