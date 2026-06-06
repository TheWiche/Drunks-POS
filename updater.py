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
APP_VERSION = "1.0.15"

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


def download_and_apply(url: str, progress_cb=None) -> None:
    """
    Descarga el ZIP, extrae Drunks.exe y usa VBScript silencioso para reemplazarlo.
    progress_cb(pct: int, msg: str) se llama con 0-100 durante el proceso.
    El llamador (app_launcher._run_update_with_ui) maneja el cierre del proceso.
    """
    import shutil

    def _prog(pct: int, msg: str = "") -> None:
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
                        pct = 5 + int(downloaded * 65 / total)  # 5-70%
                        _prog(pct, f"Descargando... {downloaded // (1024*1024)} MB")

        # 2. Extraer
        _prog(72, "Extrayendo archivos...")
        extract_dir = TEMP_UPDATE_DIR / "extracted"
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        zip_path.unlink(missing_ok=True)

        # 3. Localizar la carpeta del update (build COLLECT: carpeta con Drunks.exe + DLLs)
        _prog(80, "Preparando instalacion...")
        app_root = get_app_root()
        exe_name = "Drunks.exe"

        new_exe_src = next(
            (f for f in extract_dir.rglob(exe_name) if f.is_file()),
            None
        )
        if not new_exe_src:
            raise FileNotFoundError(f"No se encontro {exe_name} en el archivo descargado.")

        src_folder = new_exe_src.parent  # carpeta que contiene el exe y las DLLs

        _prog(92, "Preparando reinicio...")

        # 4. VBScript silencioso: espera, copia toda la carpeta, reinicia -- sin ventana CMD
        main_exe = app_root / exe_name
        vbs_path = app_root / "_update_exe.vbs"

        src_str = str(src_folder)
        dst_str = str(app_root)
        tmp_str = str(TEMP_UPDATE_DIR)

        vbs_lines = [
            'WScript.Sleep 6000',
            'Dim fso, sh',
            'Set fso = CreateObject("Scripting.FileSystemObject")',
            f'fso.CopyFolder "{src_str}\\", "{dst_str}\\", True',
            f'If fso.FolderExists("{tmp_str}") Then fso.DeleteFolder "{tmp_str}", True',
            'Set sh = CreateObject("WScript.Shell")',
            f'sh.Run Chr(34) & "{main_exe}" & Chr(34)',
            'fso.DeleteFile WScript.ScriptFullName',
        ]
        vbs_path.write_text("\r\n".join(vbs_lines), encoding="utf-8")

        _prog(98, "Reiniciando...")
        subprocess.Popen(
            ["wscript.exe", str(vbs_path)],
            creationflags=(
                subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
            ),
        )
        _prog(100, "Cerrando...")

    except Exception as exc:
        _update_info["error"] = f"Error al aplicar actualizacion: {exc}"
        raise
    # El llamador (app_launcher._run_update_with_ui) maneja el cierre del proceso
