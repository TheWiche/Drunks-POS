import threading

from fastapi import APIRouter, HTTPException

router = APIRouter()

try:
    import updater as _updater
    APP_VERSION = _updater.get_current_version()
    _updater.start_background_check()
except Exception:
    _updater = None
    APP_VERSION = "0.0.0"


@router.post("/update/check")
def api_trigger_check():
    if _updater and not _updater._update_info.get("checking"):
        _updater.start_background_check()
    return {"ok": True}


@router.get("/update/check")
def api_check_update():
    if _updater is None:
        return {"has_update": False, "current": APP_VERSION, "latest": None, "url": None, "checking": False, "error": None}
    return _updater._update_info


@router.get("/update/progress")
def api_update_progress():
    if _updater is None:
        return {"active": False, "pct": 0, "msg": "", "error": None, "done": False}
    return _updater.get_progress()


@router.post("/update/apply")
def api_apply_update():
    if _updater is None:
        raise HTTPException(503, "Modulo de actualizacion no disponible")
    info = _updater._update_info
    if not info.get("has_update") or not info.get("url"):
        raise HTTPException(400, "No hay actualizacion disponible o URL no encontrada")
    if _updater._download_progress.get("active"):
        return {"ok": True, "message": "Ya hay una descarga en progreso"}

    t = threading.Thread(
        target=_updater.download_and_apply,
        args=(info["url"],),
        daemon=True,
        name="update-apply",
    )
    t.start()
    return {"ok": True, "message": "Descarga iniciada"}
