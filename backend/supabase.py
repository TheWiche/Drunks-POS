import asyncio
import json
import threading

from .config import SUPABASE_URL, SUPABASE_KEY
from .database import get_conn

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

_CFG_COLS = {
    "categorias":    ("id", "nombre"),
    "tipos_base":    ("id", "nombre", "icono"),
    "productos":     ("id", "categoria_id", "nombre", "precio", "disponible", "tiene_base"),
    "bases":         ("id", "nombre", "tipo", "tipo_id", "disponible"),
    "notas_rapidas": ("id", "texto", "categoria_id"),
    "producto_bases":("producto_id", "base_id"),
    "settings":      ("key", "value"),
}
_CFG_INSERT_ORDER = ["categorias", "tipos_base", "productos",
                     "bases", "notas_rapidas", "producto_bases", "settings"]


async def sync_to_supabase(pedido_id: int, payload: dict):
    if not SUPABASE_URL or not SUPABASE_KEY or not HTTPX_AVAILABLE:
        return
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        campos = {"sync_id", "numero_factura", "cliente", "metodo_pago",
                  "total", "estado", "fecha", "items_json"}
        data = {k: v for k, v in payload.items() if k in campos}
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{SUPABASE_URL}/rest/v1/pedidos", headers=headers, json=data
            )
            if r.status_code not in (200, 201):
                fallback = {k: v for k, v in data.items()
                            if k not in ("sync_id", "items_json")}
                r2 = await client.post(
                    f"{SUPABASE_URL}/rest/v1/pedidos", headers=headers, json=fallback
                )
                if r2.status_code not in (200, 201):
                    return
        with get_conn() as conn:
            conn.execute("UPDATE pedidos SET sincronizado=1 WHERE id=?", (pedido_id,))
            conn.commit()
    except Exception:
        pass


async def _sync_estado_to_supabase(pedido_id: int, estado: str):
    if not SUPABASE_URL or not SUPABASE_KEY or not HTTPX_AVAILABLE:
        return
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT sync_id FROM pedidos WHERE id=?", (pedido_id,)).fetchone()
        if not row or not row["sync_id"]:
            return
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/pedidos?sync_id=eq.{row['sync_id']}",
                headers=headers,
                json={"estado": estado},
            )
    except Exception:
        pass


async def sync_prepare_to_supabase(pedido_id: int):
    await _sync_estado_to_supabase(pedido_id, "preparado")


async def sync_deliver_to_supabase(pedido_id: int):
    await _sync_estado_to_supabase(pedido_id, "entregado")


def _push_config_bg(tabla: str) -> None:
    if not SUPABASE_URL or not SUPABASE_KEY or not HTTPX_AVAILABLE:
        return
    try:
        import httpx as _hx
        cols = _CFG_COLS.get(tabla)
        if not cols:
            return
        with get_conn() as conn:
            rows = [dict(zip(cols, row)) for row in
                    conn.execute(f"SELECT {','.join(cols)} FROM {tabla}").fetchall()]
        _hx.post(
            f"{SUPABASE_URL}/rest/v1/config",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            json={"clave": tabla, "valor": rows},
            timeout=10.0,
        )
    except Exception:
        pass


def push_config(tabla: str) -> None:
    threading.Thread(target=_push_config_bg, args=(tabla,), daemon=True).start()


async def pull_config_from_supabase() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY or not HTTPX_AVAILABLE:
        return
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/config",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Accept": "application/json",
                },
            )
        if r.status_code != 200 or not r.json():
            return

        cloud = {row["clave"]: row["valor"] for row in r.json()
                 if row.get("clave") in _CFG_COLS}
        if not cloud:
            return

        with get_conn() as conn:
            for tabla in reversed(_CFG_INSERT_ORDER):
                if tabla in cloud and tabla != "settings":
                    conn.execute(f"DELETE FROM {tabla}")
            for tabla in _CFG_INSERT_ORDER:
                if tabla not in cloud or not cloud[tabla]:
                    continue
                cols = _CFG_COLS[tabla]
                # settings usa upsert para no pisar valores locales como admin_pin
                on_conflict = "REPLACE" if tabla == "settings" else "IGNORE"
                conn.executemany(
                    f"INSERT OR {on_conflict} INTO {tabla} ({','.join(cols)}) "
                    f"VALUES ({','.join('?' * len(cols))})",
                    [[row.get(c) for c in cols] for row in cloud[tabla]],
                )
            conn.commit()
    except Exception:
        pass


async def clear_supabase_pedidos() -> None:
    """Elimina todos los pedidos de la tabla pedidos en Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY or not HTTPX_AVAILABLE:
        return
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Prefer": "return=minimal",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.delete(
                f"{SUPABASE_URL}/rest/v1/pedidos?fecha=not.is.null",
                headers=headers,
            )
    except Exception:
        pass


async def sync_pending_loop():
    while True:
        await asyncio.sleep(300)
        if not SUPABASE_URL or not SUPABASE_KEY or not HTTPX_AVAILABLE:
            continue
        try:
            with get_conn() as conn:
                rows = conn.execute("SELECT * FROM pedidos WHERE sincronizado=0").fetchall()
            for row in rows:
                await sync_to_supabase(row["id"], dict(row))
        except Exception:
            pass


async def download_from_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY or not HTTPX_AVAILABLE:
        return
    try:
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/pedidos?select=*&order=fecha.asc&limit=5000",
                headers=headers,
            )
            if r.status_code != 200:
                return
            cloud_pedidos = r.json()

        cloud_sync_ids = {p.get("sync_id") for p in cloud_pedidos if p.get("sync_id")}

        with get_conn() as conn:
            local_synced = conn.execute(
                "SELECT id, sync_id FROM pedidos WHERE sincronizado=1 AND sync_id != '' AND sync_id IS NOT NULL"
            ).fetchall()
            for row in local_synced:
                if row["sync_id"] not in cloud_sync_ids:
                    conn.execute("UPDATE pedidos SET sincronizado=0 WHERE id=?", (row["id"],))

            for p in cloud_pedidos:
                sid = p.get("sync_id") or ""
                nf  = p.get("numero_factura") or ""

                existing = None
                if sid:
                    existing = conn.execute(
                        "SELECT id, estado FROM pedidos WHERE sync_id=?", (sid,)
                    ).fetchone()
                if not existing and nf:
                    existing = conn.execute(
                        "SELECT id, estado FROM pedidos WHERE numero_factura=?", (nf,)
                    ).fetchone()

                if existing:
                    if p.get("estado") == "entregado" and existing["estado"] != "entregado":
                        conn.execute(
                            "UPDATE pedidos SET estado='entregado', sincronizado=1 WHERE id=?",
                            (existing["id"],)
                        )
                    elif sid and not conn.execute(
                        "SELECT id FROM pedidos WHERE sync_id=?", (sid,)
                    ).fetchone():
                        conn.execute("UPDATE pedidos SET sync_id=? WHERE id=?", (sid, existing["id"]))
                    continue

                cur = conn.execute(
                    "INSERT INTO pedidos "
                    "(cliente,metodo_pago,total,estado,fecha,sincronizado,numero_factura,sync_id) "
                    "VALUES (?,?,?,?,?,1,?,?)",
                    (p["cliente"], p["metodo_pago"], float(p.get("total") or 0),
                     p.get("estado", "pendiente"), p["fecha"], nf, sid),
                )
                pedido_id = cur.lastrowid
                items = []
                try:
                    items = json.loads(p.get("items_json") or "[]")
                except Exception:
                    pass
                for it in items:
                    prod = conn.execute(
                        "SELECT id FROM productos WHERE nombre=?", (it.get("nombre", ""),)
                    ).fetchone()
                    if prod:
                        conn.execute(
                            "INSERT INTO detalle_pedidos "
                            "(pedido_id,producto_id,cantidad,observaciones) VALUES (?,?,?,?)",
                            (pedido_id, prod["id"],
                             it.get("cantidad", 1), it.get("observaciones", "")),
                        )
            conn.commit()
    except Exception:
        pass
