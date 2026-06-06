import json
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..database import get_conn
from ..supabase import sync_to_supabase, sync_deliver_to_supabase

router = APIRouter()


class OrderItem(BaseModel):
    producto_id:   int
    cantidad:      int
    observaciones: str = ""


class PedidoCreate(BaseModel):
    cliente:     str
    metodo_pago: str
    total:       float
    items:       List[OrderItem]


class ConnectionManager:
    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self._clients:
            self._clients.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self._clients:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.remove(ws)


manager = ConnectionManager()


@router.post("/pedidos", status_code=201)
async def create_pedido(data: PedidoCreate, background_tasks: BackgroundTasks):
    fecha   = datetime.now().isoformat()
    sync_id = str(uuid.uuid4())
    items_detail: list[dict] = []

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO pedidos (cliente,metodo_pago,total,estado,fecha,sincronizado,numero_factura,sync_id) VALUES (?,?,?,?,?,?,'',?)",
            (data.cliente, data.metodo_pago, data.total, "pendiente", fecha, 0, sync_id))
        pedido_id = cur.lastrowid
        numero_factura = f"DRK-{pedido_id:05d}"
        conn.execute("UPDATE pedidos SET numero_factura=? WHERE id=?", (numero_factura, pedido_id))
        for item in data.items:
            conn.execute(
                "INSERT INTO detalle_pedidos (pedido_id,producto_id,cantidad,observaciones) VALUES (?,?,?,?)",
                (pedido_id, item.producto_id, item.cantidad, item.observaciones))
            prod = conn.execute("""
                SELECT p.nombre, p.precio, p.categoria_id,
                       COALESCE(c.nombre,'Sin Categoria') AS categoria
                FROM productos p LEFT JOIN categorias c ON p.categoria_id=c.id
                WHERE p.id=?
            """, (item.producto_id,)).fetchone()
            items_detail.append({
                "producto_id":   item.producto_id,
                "nombre":        prod["nombre"]       if prod else "Desconocido",
                "cantidad":      item.cantidad,
                "precio":        prod["precio"]       if prod else 0,
                "categoria_id":  prod["categoria_id"] if prod else None,
                "categoria":     prod["categoria"]    if prod else "Sin Categoria",
                "observaciones": item.observaciones,
            })
        conn.commit()

    payload = {
        "id": pedido_id, "numero_factura": numero_factura,
        "cliente": data.cliente, "metodo_pago": data.metodo_pago,
        "total": data.total, "estado": "pendiente", "fecha": fecha, "items": items_detail,
    }
    await manager.broadcast({"type": "new_order", "order": payload})
    background_tasks.add_task(sync_to_supabase, pedido_id, {
        "sync_id": sync_id, "numero_factura": numero_factura,
        "cliente": data.cliente, "metodo_pago": data.metodo_pago,
        "total": data.total, "estado": "pendiente", "fecha": fecha,
        "items_json": json.dumps(items_detail),
    })
    return payload


@router.get("/pedidos/pendientes")
def get_pendientes():
    with get_conn() as conn:
        pedidos = conn.execute(
            "SELECT * FROM pedidos WHERE estado='pendiente' ORDER BY fecha DESC").fetchall()
        result = []
        for p in pedidos:
            pd = dict(p)
            pd["items"] = [dict(d) for d in conn.execute("""
                SELECT dp.producto_id, dp.cantidad, dp.observaciones,
                       COALESCE(pr.nombre,'Producto eliminado') AS nombre,
                       pr.categoria_id
                FROM detalle_pedidos dp LEFT JOIN productos pr ON dp.producto_id=pr.id
                WHERE dp.pedido_id=?""", (p["id"],)).fetchall()]
            result.append(pd)
    return result


@router.get("/pedidos/{id}")
def get_pedido(id: int):
    with get_conn() as conn:
        p = conn.execute("SELECT * FROM pedidos WHERE id=?", (id,)).fetchone()
        if not p:
            raise HTTPException(404, "Pedido no encontrado")
        pd = dict(p)
        pd["items"] = [dict(d) for d in conn.execute("""
            SELECT dp.cantidad, dp.observaciones,
                   pr.nombre, pr.precio, dp.cantidad * pr.precio AS subtotal,
                   COALESCE(c.nombre,'Sin Categoria') AS categoria
            FROM detalle_pedidos dp
            JOIN  productos   pr ON dp.producto_id  = pr.id
            LEFT JOIN categorias c  ON pr.categoria_id = c.id
            WHERE dp.pedido_id = ?
        """, (id,)).fetchall()]
    return pd


@router.put("/pedidos/{id}/entregar")
async def entregar_pedido(id: int, background_tasks: BackgroundTasks):
    with get_conn() as conn:
        conn.execute("UPDATE pedidos SET estado='entregado' WHERE id=?", (id,))
        conn.commit()
    background_tasks.add_task(sync_deliver_to_supabase, id)
    return {"ok": True}


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
