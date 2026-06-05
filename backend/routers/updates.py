from fastapi import APIRouter, BackgroundTasks, HTTPException

router = APIRouter()

try:
    import updater as _updater
    APP_VERSION = _updater.get_current_version()
    _updater.start_background_check()
except Exception:
    _updater = None
    APP_VERSION = "0.0.0"


@router.get("/update/check")
def api_check_update():
    if _updater is None:
        return {"has_update": False, "current": APP_VERSION, "latest": None, "url": None}
    return _updater._update_info


@router.post("/update/apply")
async def api_apply_update(background_tasks: BackgroundTasks):
    if _updater is None:
        raise HTTPException(503, "Módulo de actualización no disponible")
    info = _updater._update_info
    if not info.get("has_update") or not info.get("url"):
        raise HTTPException(400, "No hay actualización disponible o URL no encontrada")
    background_tasks.add_task(_updater.download_and_apply, info["url"])
    return {"ok": True, "message": "Descargando actualización, la app se reiniciará en breve..."}
