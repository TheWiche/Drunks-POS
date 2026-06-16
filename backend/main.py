import asyncio
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIR, IS_CLOUD
from .database import init_db
from .supabase import pull_config_from_supabase, download_from_supabase, sync_pending_loop
from .routers import (
    pedidos, productos, bases, notas,
    settings, updates, dashboard, sync,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(download_from_supabase())
    asyncio.create_task(pull_config_from_supabase())
    asyncio.create_task(sync_pending_loop())
    if IS_CLOUD:
        asyncio.create_task(_cloud_sync_loop())
    yield


async def _cloud_sync_loop():
    while True:
        await asyncio.sleep(300)
        pull_config_from_supabase()


app = FastAPI(title="Drunks POS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_static_dir = FRONTEND_DIR / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# ── Auth HTTP Basic para instancia cloud ──────────────────────────────────────
_security  = HTTPBasic(auto_error=False)
_CLOUD_PASS = os.getenv("CLOUD_PASS", "")

def _cloud_auth(credentials: HTTPBasicCredentials = Depends(_security)):
    if not IS_CLOUD or not _CLOUD_PASS:
        return
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            headers={"WWW-Authenticate": "Basic"})
    ok = secrets.compare_digest(
        (credentials.password or "").encode(),
        _CLOUD_PASS.encode(),
    )
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            headers={"WWW-Authenticate": "Basic"})

app.include_router(pedidos.router,   prefix="/api")
app.include_router(productos.router, prefix="/api")
app.include_router(bases.router,     prefix="/api")
app.include_router(notas.router,     prefix="/api")
app.include_router(settings.router,  prefix="/api")
app.include_router(updates.router,   prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(sync.router,      prefix="/api")


@app.get("/vendedor")
def page_vendedor(_=Depends(_cloud_auth)):
    if IS_CLOUD:
        return RedirectResponse("/admin", status_code=302)
    return FileResponse(str(FRONTEND_DIR / "vendedor" / "index.html"))


@app.get("/cocina")
def page_cocina(_=Depends(_cloud_auth)):
    if IS_CLOUD:
        return RedirectResponse("/admin", status_code=302)
    return FileResponse(str(FRONTEND_DIR / "cocina" / "index.html"))


@app.get("/admin")
def page_admin(_=Depends(_cloud_auth)):
    return FileResponse(str(FRONTEND_DIR / "admin" / "index.html"))


@app.get("/dashboard")
def page_dashboard(_=Depends(_cloud_auth)):
    return FileResponse(str(FRONTEND_DIR / "admin" / "index.html"))


@app.get("/app")
def page_app(_=Depends(_cloud_auth)):
    if IS_CLOUD:
        return RedirectResponse("/admin", status_code=302)
    return FileResponse(str(FRONTEND_DIR / "shell" / "index.html"))


@app.get("/")
def root(_=Depends(_cloud_auth)):
    if IS_CLOUD:
        return RedirectResponse("/admin", status_code=302)
    return FileResponse(str(FRONTEND_DIR / "shell" / "index.html"))
