import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIR
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
    yield


app = FastAPI(title="Drunks POS", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")

app.include_router(pedidos.router,   prefix="/api")
app.include_router(productos.router, prefix="/api")
app.include_router(bases.router,     prefix="/api")
app.include_router(notas.router,     prefix="/api")
app.include_router(settings.router,  prefix="/api")
app.include_router(updates.router,   prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(sync.router,      prefix="/api")


@app.get("/vendedor")
def page_vendedor():
    return FileResponse(str(FRONTEND_DIR / "vendedor" / "index.html"))


@app.get("/cocina")
def page_cocina():
    return FileResponse(str(FRONTEND_DIR / "cocina" / "index.html"))


@app.get("/admin")
def page_admin():
    return FileResponse(str(FRONTEND_DIR / "admin" / "index.html"))


@app.get("/dashboard")
def page_dashboard():
    return FileResponse(str(FRONTEND_DIR / "admin" / "index.html"))


@app.get("/app")
def page_app():
    return FileResponse(str(FRONTEND_DIR / "shell" / "index.html"))


@app.get("/")
def root():
    return FileResponse(str(FRONTEND_DIR / "shell" / "index.html"))
