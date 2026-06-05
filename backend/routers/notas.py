from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from ..database import get_conn, to_dict
from ..supabase import push_config

router = APIRouter()


class NotaBody(BaseModel):
    texto:        str
    categoria_id: Optional[int] = None


@router.get("/notas_rapidas")
def get_notas():
    with get_conn() as conn:
        return [to_dict(r) for r in conn.execute(
            "SELECT * FROM notas_rapidas ORDER BY categoria_id NULLS LAST, id").fetchall()]


@router.post("/notas_rapidas", status_code=201)
def create_nota(data: NotaBody):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO notas_rapidas (texto, categoria_id) VALUES (?,?)",
            (data.texto, data.categoria_id))
        conn.commit()
        result = to_dict(conn.execute(
            "SELECT * FROM notas_rapidas WHERE id=?", (cur.lastrowid,)).fetchone())
    push_config("notas_rapidas")
    return result


@router.delete("/notas_rapidas/{id}")
def delete_nota(id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM notas_rapidas WHERE id=?", (id,))
        conn.commit()
    push_config("notas_rapidas")
    return {"ok": True}
