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
    """Lee version.txt — usa utf-8-sig para ignorar el BOM si está presente."""
    candidates = [
        Path(getattr(sys, "_MEIPASS", "")) / "version.txt",
        get_app_root() / "version.txt",
        Path(__file__).parent / "version.txt",
    ]
    for path in candidates:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8-sig").strip()
        except Exception:
            pass
    return "0.0.0"


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
    Descarga el ZIP de la nueva versión, lo extrae y lanza un .bat
    que reemplaza los archivos mientras la app está cerrada.
    progress_cb(pct: int, msg: str) se llama con 0-100 durante el proceso.
    """
    def _prog(pct: int, msg: str = "") -> None:
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass

    try:
        import httpx

        if TEMP_UPDATE_DIR.exists():
            import shutil
            shutil.rmtree(TEMP_UPDATE_DIR, ignore_errors=True)
        TEMP_UPDATE_DIR.mkdir(parents=True, exist_ok=True)

        zip_path = TEMP_UPDATE_DIR / "update.zip"

        _prog(5, "Conectando con el servidor...")
        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(zip_path, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = 5 + int(downloaded * 70 / total)  # 5-75%
                        _prog(pct, f"Descargando... {downloaded // (1024*1024)} MB")

        _prog(76, "Extrayendo archivos...")
        extract_dir = TEMP_UPDATE_DIR / "extracted"
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
        zip_path.unlink(missing_ok=True)

        _prog(88, "Preparando instalación...")
        app_root = get_app_root()
        bat_path = app_root / "_apply_update.bat"

        # El exe principal ahora es Drunks.exe (app unificada)
        main_exe = app_root / "Drunks.exe"
        restart_cmd = (
            f'start "" "{main_exe}"' if main_exe.exists()
            else f'start "" "{app_root}\\INICIAR_SISTEMA.bat"'
        )

        bat_content = (
            "@echo off\n"
            "title Drunks POS - Aplicando actualizacion...\n"
            "echo Aplicando actualizacion, espera un momento...\n"
            "timeout /t 3 /nobreak >nul\n"
            f'robocopy "{extract_dir}" "{app_root}" /E /IS /IT /NFL /NDL /NJH /NJS /nc /ns /np\n'
            f'if exist "{TEMP_UPDATE_DIR}" rmdir /S /Q "{TEMP_UPDATE_DIR}"\n'
            "echo Actualizacion aplicada. Reiniciando Drunks POS...\n"
            "timeout /t 1 /nobreak >nul\n"
            f'{restart_cmd}\n'
            'del "%~f0"\n'
        )
        bat_path.write_text(bat_content, encoding="utf-8")

        _prog(96, "Aplicando actualización...")
        subprocess.Popen(
            ["cmd", "/c", str(bat_path)],
            creationflags=(
                subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.CREATE_NO_WINDOW
            ),
        )
        _prog(100, "Reiniciando...")

    except Exception as exc:
        _update_info["error"] = f"Error al aplicar actualización: {exc}"
        raise

    time.sleep(1)
    os._exit(0)
