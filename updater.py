"""
Módulo de auto-actualización para Drunks POS.
Consulta GitHub Releases y aplica la actualización sin intervención técnica.
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

# Versión de este build — se actualiza en cada release.
# Hardcodeada aquí para que nunca dependa de un archivo externo.
APP_VERSION = "1.0.5"

_update_info: dict = {
    "has_update": False,
    "latest":     None,
    "current":    "0.0.0",
    "url":        None,
    "checking":   False,
    "error":      None,
}


def get_app_root() -> Path:
    """Raíz del proyecto (directorio del exe o del script)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_current_version() -> str:
    """Retorna la versión de este build (constante hardcodeada en APP_VERSION)."""
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
            _update_info["error"] = f"GitHub respondió {r.status_code}"
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
    """Lanza el chequeo de actualización en un hilo daemon (no bloquea el arranque)."""
    _update_info["current"] = get_current_version()
    t = threading.Thread(target=check_for_update, daemon=True, name="update-check")
    t.start()


def download_and_apply(url: str, progress_cb=None) -> None:
    """
    Descarga el ZIP, copia los archivos con shutil (más confiable que robocopy),
    y usa un .bat mínimo solo para reemplazar Drunks.exe (que está bloqueado).
    progress_cb(pct: int, msg: str) se llama con 0-100 durante el proceso.
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

        # 3. Localizar el nuevo Drunks.exe en los archivos extraídos
        _prog(80, "Preparando instalación...")
        app_root = get_app_root()
        exe_name = "Drunks.exe"

        # Buscar Drunks.exe dentro del zip extraído (puede estar en raíz o subcarpeta)
        new_exe_src = next(
            (f for f in extract_dir.rglob(exe_name) if f.is_file()),
            None
        )
        if not new_exe_src:
            raise FileNotFoundError(f"No se encontró {exe_name} en el archivo descargado.")

        _prog(92, "Preparando reinicio...")

        # 4. Bat mínimo: espera a que cierre el proceso, reemplaza el exe, reinicia
        main_exe  = app_root / exe_name
        bat_path  = app_root / "_update_exe.bat"

        bat_lines = [
            "@echo off",
            "ping 127.0.0.1 -n 5 > nul",          # esperar ~4 s a que cierre
            f'copy /Y "{new_exe_src}" "{main_exe}"',
            f'if exist "{TEMP_UPDATE_DIR}" rmdir /S /Q "{TEMP_UPDATE_DIR}"',
            f'start "" "{main_exe}"',
            'del "%~f0"',
        ]
        bat_path.write_text("\n".join(bat_lines), encoding="utf-8")

        _prog(98, "Reiniciando...")
        subprocess.Popen(
            ["cmd", "/c", str(bat_path)],
            creationflags=(
                subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.CREATE_NO_WINDOW
            ),
        )
        _prog(100, "Cerrando...")

    except Exception as exc:
        _update_info["error"] = f"Error al aplicar actualización: {exc}"
        raise

    time.sleep(1)
    os._exit(0)
