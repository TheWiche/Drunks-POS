from fastapi import APIRouter
from ..database import get_conn
from ..config import SUPABASE_URL, SUPABASE_KEY
from ..supabase import HTTPX_AVAILABLE

router = APIRouter()

try:
    import httpx
except ImportError:
    httpx = None


@router.get("/sync/status")
async def sync_status():
    with get_conn() as conn:
        pending = conn.execute("SELECT COUNT(*) FROM pedidos WHERE sincronizado=0").fetchone()[0]
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"configured": False, "reachable": False, "pending": pending}
    reachable = False
    if HTTPX_AVAILABLE and httpx:
        try:
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(
                    f"{SUPABASE_URL}/rest/v1/pedidos?select=id&limit=1", headers=headers
                )
                reachable = r.status_code == 200
        except Exception:
            reachable = False
    return {"configured": True, "reachable": reachable, "pending": pending}
