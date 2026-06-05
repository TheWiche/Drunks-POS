from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_conn, to_dict
from ..supabase import push_config

router = APIRouter()

BASE_JOIN = """
    SELECT b.id, b.nombre, b.disponible, b.tipo_id,
           t.nombre AS tipo_nombre, t.icono AS tipo_icono
    FROM bases b
    LEFT JOIN tipos_base t ON b.tipo_id = t.id
"""


class TipoBaseCreate(BaseModel):
    nombre: str
    icono:  str = "🍹"


class TipoBaseUpdate(BaseModel):
    nombre: str
    icono:  str = "🍹"


class BaseCreate(BaseModel):
    nombre:  str
    tipo_id: int


class BaseUpdate(BaseModel):
    nombre:  str
    tipo_id: int


class ProductoBasesUpdate(BaseModel):
    base_ids: List[int]


# ── Tipos de Base ──

@router.get("/tipos-base")
def get_tipos_base():
    with get_conn() as conn:
        return [to_dict(r) for r in conn.execute(
            "SELECT * FROM tipos_base ORDER BY nombre").fetchall()]


@router.post("/tipos-base", status_code=201)
def create_tipo_base(data: TipoBaseCreate):
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(400, "Nombre requerido")
    with get_conn() as conn:
        if conn.execute("SELECT id FROM tipos_base WHERE LOWER(nombre)=LOWER(?)", (nombre,)).fetchone():
            raise HTTPException(409, "Ya existe un tipo con ese nombre")
        cur = conn.execute("INSERT INTO tipos_base (nombre, icono) VALUES (?,?)",
                           (nombre, data.icono.strip() or "🍹"))
        conn.commit()
        result = to_dict(conn.execute("SELECT * FROM tipos_base WHERE id=?", (cur.lastrowid,)).fetchone())
    push_config("tipos_base")
    return result


@router.put("/tipos-base/{id}")
def update_tipo_base(id: int, data: TipoBaseUpdate):
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(400, "Nombre requerido")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM tipos_base WHERE id=?", (id,)).fetchone():
            raise HTTPException(404, "Tipo no encontrado")
        if conn.execute("SELECT id FROM tipos_base WHERE LOWER(nombre)=LOWER(?) AND id!=?",
                        (nombre, id)).fetchone():
            raise HTTPException(409, "Ya existe un tipo con ese nombre")
        conn.execute("UPDATE tipos_base SET nombre=?, icono=? WHERE id=?",
                     (nombre, data.icono.strip() or "🍹", id))
        conn.commit()
        result = to_dict(conn.execute("SELECT * FROM tipos_base WHERE id=?", (id,)).fetchone())
    push_config("tipos_base")
    return result


@router.delete("/tipos-base/{id}")
def delete_tipo_base(id: int):
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM bases WHERE tipo_id=?", (id,)).fetchone()[0]
        if count:
            raise HTTPException(409, f"Este tipo tiene {count} base(s). Elimínalas primero.")
        conn.execute("DELETE FROM tipos_base WHERE id=?", (id,))
        conn.commit()
    push_config("tipos_base")
    return {"ok": True}


# ── Bases ──

@router.get("/bases")
def get_bases():
    with get_conn() as conn:
        return [to_dict(r) for r in conn.execute(
            BASE_JOIN + " ORDER BY t.nombre, b.nombre").fetchall()]


@router.post("/bases", status_code=201)
def create_base(data: BaseCreate):
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(400, "Nombre requerido")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM tipos_base WHERE id=?", (data.tipo_id,)).fetchone():
            raise HTTPException(400, "Tipo de base no válido")
        tipo_text = conn.execute("SELECT nombre FROM tipos_base WHERE id=?",
                                 (data.tipo_id,)).fetchone()["nombre"]
        cur = conn.execute("INSERT INTO bases (nombre, tipo, tipo_id) VALUES (?,?,?)",
                           (nombre, tipo_text, data.tipo_id))
        conn.commit()
        result = to_dict(conn.execute(BASE_JOIN + " WHERE b.id=?", (cur.lastrowid,)).fetchone())
    push_config("bases")
    return result


@router.put("/bases/{id}")
def update_base(id: int, data: BaseUpdate):
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(400, "Nombre requerido")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM bases WHERE id=?", (id,)).fetchone():
            raise HTTPException(404, "Base no encontrada")
        if not conn.execute("SELECT id FROM tipos_base WHERE id=?", (data.tipo_id,)).fetchone():
            raise HTTPException(400, "Tipo de base no válido")
        tipo_text = conn.execute("SELECT nombre FROM tipos_base WHERE id=?",
                                 (data.tipo_id,)).fetchone()["nombre"]
        conn.execute("UPDATE bases SET nombre=?, tipo=?, tipo_id=? WHERE id=?",
                     (nombre, tipo_text, data.tipo_id, id))
        conn.commit()
        result = to_dict(conn.execute(BASE_JOIN + " WHERE b.id=?", (id,)).fetchone())
    push_config("bases")
    return result


@router.delete("/bases/{id}")
def delete_base(id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM bases WHERE id=?", (id,))
        conn.commit()
    push_config("bases")
    return {"ok": True}


@router.patch("/bases/{id}/toggle")
def toggle_base_disponible(id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT disponible FROM bases WHERE id=?", (id,)).fetchone()
        if not row:
            raise HTTPException(404, "Base no encontrada")
        conn.execute("UPDATE bases SET disponible=? WHERE id=?",
                     (0 if row["disponible"] else 1, id))
        conn.commit()
        result = to_dict(conn.execute(BASE_JOIN + " WHERE b.id=?", (id,)).fetchone())
    push_config("bases")
    return result


# ── Producto ↔ Bases ──

@router.get("/productos/{id}/bases")
def get_producto_bases(id: int):
    with get_conn() as conn:
        assigned_ids = {r["base_id"] for r in conn.execute(
            "SELECT base_id FROM producto_bases WHERE producto_id=?", (id,)).fetchall()}
        all_bases = [to_dict(r) for r in conn.execute(
            BASE_JOIN + " ORDER BY t.nombre, b.nombre").fetchall()]
        if assigned_ids:
            for b in all_bases:
                b["assigned"] = b["id"] in assigned_ids
        else:
            all_bases = [dict(**b, assigned=False) for b in all_bases if b["disponible"]]
        return all_bases


@router.put("/productos/{id}/bases")
def set_producto_bases(id: int, data: ProductoBasesUpdate):
    with get_conn() as conn:
        conn.execute("DELETE FROM producto_bases WHERE producto_id=?", (id,))
        if data.base_ids:
            conn.executemany(
                "INSERT INTO producto_bases (producto_id, base_id) VALUES (?,?)",
                [(id, bid) for bid in data.base_ids])
        conn.commit()
    push_config("producto_bases")
    return {"ok": True, "count": len(data.base_ids)}


@router.get("/productos/bases-bulk")
def get_all_producto_bases():
    with get_conn() as conn:
        rows = conn.execute("SELECT producto_id, base_id FROM producto_bases").fetchall()
    result: dict = {}
    for r in rows:
        result.setdefault(r["producto_id"], []).append(r["base_id"])
    return result
