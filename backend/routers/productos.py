from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_conn, to_dict
from ..supabase import push_config

router = APIRouter()

PROD_Q = """
    SELECT p.*, COALESCE(c.nombre,'Sin Categoria') AS categoria_nombre
    FROM productos p LEFT JOIN categorias c ON p.categoria_id=c.id
"""


class CategoriaBody(BaseModel):
    nombre: str
    icono:  Optional[str] = None
    color:  Optional[str] = None


class ProductoCreate(BaseModel):
    categoria_id: Optional[int] = None
    nombre:       str
    precio:       float = 0.0
    disponible:   bool  = True
    tiene_base:   bool  = False


class ProductoUpdate(BaseModel):
    categoria_id: Optional[int]   = None
    nombre:       Optional[str]   = None
    precio:       Optional[float] = None
    disponible:   Optional[bool]  = None
    tiene_base:   Optional[bool]  = None


# ── Categorías ──

@router.get("/categorias")
def get_categorias():
    with get_conn() as conn:
        return [to_dict(r) for r in conn.execute(
            "SELECT * FROM categorias ORDER BY nombre").fetchall()]


@router.post("/categorias", status_code=201)
def create_categoria(data: CategoriaBody):
    icono = data.icono or "🏷️"
    color = data.color or "#8b5cf6"
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO categorias (nombre, icono, color) VALUES (?,?,?)",
            (data.nombre, icono, color))
        conn.commit()
        result = to_dict(conn.execute("SELECT * FROM categorias WHERE id=?", (cur.lastrowid,)).fetchone())
    push_config("categorias")
    return result


@router.put("/categorias/{id}")
def update_categoria(id: int, data: CategoriaBody):
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM categorias WHERE id=?", (id,)).fetchone():
            raise HTTPException(404, "No encontrada")
        conn.execute(
            "UPDATE categorias SET nombre=?, icono=?, color=? WHERE id=?",
            (data.nombre, data.icono or "🏷️", data.color or "#8b5cf6", id))
        conn.commit()
        result = to_dict(conn.execute("SELECT * FROM categorias WHERE id=?", (id,)).fetchone())
    push_config("categorias")
    return result


@router.delete("/categorias/{id}")
def delete_categoria(id: int):
    with get_conn() as conn:
        conn.execute("UPDATE productos SET categoria_id=NULL WHERE categoria_id=?", (id,))
        conn.execute("UPDATE notas_rapidas SET categoria_id=NULL WHERE categoria_id=?", (id,))
        conn.execute("DELETE FROM categorias WHERE id=?", (id,))
        conn.commit()
    push_config("categorias")
    push_config("productos")
    push_config("notas_rapidas")
    return {"ok": True}


# ── Productos ──

@router.get("/productos")
def get_productos():
    with get_conn() as conn:
        productos = [to_dict(r) for r in conn.execute(
            PROD_Q + " ORDER BY c.nombre, p.nombre").fetchall()]
        ids_con_bases = {r[0] for r in conn.execute(
            "SELECT DISTINCT producto_id FROM producto_bases").fetchall()}
        for p in productos:
            if p.get("tiene_base") and p["id"] not in ids_con_bases:
                p["tiene_base"] = False
                conn.execute("UPDATE productos SET tiene_base=0 WHERE id=?", (p["id"],))
        conn.commit()
        return productos


@router.post("/productos", status_code=201)
def create_producto(data: ProductoCreate):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO productos (categoria_id, nombre, precio, disponible, tiene_base) VALUES (?,?,?,?,?)",
            (data.categoria_id, data.nombre, data.precio,
             1 if data.disponible else 0, 1 if data.tiene_base else 0))
        conn.commit()
        result = to_dict(conn.execute(PROD_Q + " WHERE p.id=?", (cur.lastrowid,)).fetchone())
    push_config("productos")
    return result


@router.put("/productos/{id}")
def update_producto(id: int, data: ProductoUpdate):
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM productos WHERE id=?", (id,)).fetchone():
            raise HTTPException(404, "No encontrado")
        u: dict = {}
        if data.categoria_id is not None: u["categoria_id"] = data.categoria_id
        if data.nombre       is not None: u["nombre"]       = data.nombre
        if data.precio       is not None: u["precio"]       = data.precio
        if data.disponible   is not None: u["disponible"]   = 1 if data.disponible else 0
        if data.tiene_base   is not None: u["tiene_base"]   = 1 if data.tiene_base else 0
        if u:
            conn.execute(
                f"UPDATE productos SET {', '.join(k+'=?' for k in u)} WHERE id=?",
                [*u.values(), id])
            conn.commit()
        result = to_dict(conn.execute(PROD_Q + " WHERE p.id=?", (id,)).fetchone())
    push_config("productos")
    return result


@router.delete("/productos/{id}")
def delete_producto(id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM productos WHERE id=?", (id,))
        conn.commit()
    push_config("productos")
    return {"ok": True}


@router.patch("/productos/{id}/toggle")
def toggle_producto(id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT disponible FROM productos WHERE id=?", (id,)).fetchone()
        if not row:
            raise HTTPException(404, "No encontrado")
        conn.execute("UPDATE productos SET disponible=? WHERE id=?",
                     (0 if row["disponible"] else 1, id))
        conn.commit()
        result = to_dict(conn.execute(PROD_Q + " WHERE p.id=?", (id,)).fetchone())
    push_config("productos")
    return result


@router.patch("/productos/{id}/toggle-base")
def toggle_base_producto(id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT tiene_base FROM productos WHERE id=?", (id,)).fetchone()
        if not row:
            raise HTTPException(404, "No encontrado")
        conn.execute("UPDATE productos SET tiene_base=? WHERE id=?",
                     (0 if row["tiene_base"] else 1, id))
        conn.commit()
        result = to_dict(conn.execute(PROD_Q + " WHERE p.id=?", (id,)).fetchone())
    push_config("productos")
    return result
