from fastapi import APIRouter, Request
from ..database import get_conn
from ..supabase import push_config

router = APIRouter()


@router.get("/settings")
def get_settings():
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


@router.put("/settings/{key}")
async def set_setting(key: str, req: Request):
    data = await req.json()
    value = str(data.get("value", ""))
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
        conn.commit()
    push_config("settings")
    return {"ok": True}
