import sqlite3
import uuid
from .config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def to_dict(row) -> dict:
    d = dict(row)
    for k in ("disponible", "sincronizado", "tiene_base"):
        if k in d:
            d[k] = bool(d[k])
    return d


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL,
                nombre       TEXT    NOT NULL,
                precio       REAL    NOT NULL DEFAULT 0.0,
                disponible   INTEGER NOT NULL DEFAULT 1,
                tiene_base   INTEGER NOT NULL DEFAULT 0
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notas_rapidas (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                texto        TEXT    NOT NULL,
                categoria_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL
            )""")

        for migration in [
            "ALTER TABLE notas_rapidas ADD COLUMN categoria_id INTEGER REFERENCES categorias(id) ON DELETE SET NULL",
            "ALTER TABLE productos ADD COLUMN tiene_base INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE categorias ADD COLUMN icono TEXT NOT NULL DEFAULT '🏷️'",
        ]:
            try:
                conn.execute(migration)
                conn.commit()
            except Exception:
                pass

        try:
            conn.execute("ALTER TABLE pedidos ADD COLUMN numero_factura TEXT NOT NULL DEFAULT ''")
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE pedidos ADD COLUMN sync_id TEXT NOT NULL DEFAULT ''")
            conn.commit()
        except Exception:
            pass
        try:
            rows = conn.execute("SELECT id FROM pedidos WHERE sync_id='' OR sync_id IS NULL").fetchall()
            for row in rows:
                conn.execute("UPDATE pedidos SET sync_id=? WHERE id=?", (str(uuid.uuid4()), row["id"]))
            if rows:
                conn.commit()
        except Exception:
            pass
        try:
            rows = conn.execute("SELECT id FROM pedidos WHERE numero_factura='' OR numero_factura IS NULL").fetchall()
            for row in rows:
                conn.execute("UPDATE pedidos SET numero_factura=? WHERE id=?",
                             (f"DRK-{row['id']:05d}", row["id"]))
            if rows:
                conn.commit()
        except Exception:
            pass

        try:
            mich_row = conn.execute("SELECT id FROM categorias WHERE nombre='Micheladas'").fetchone()
            if mich_row:
                conn.execute("UPDATE productos SET tiene_base=1 WHERE categoria_id=? AND tiene_base=0", (mich_row["id"],))
                conn.commit()
        except Exception:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente        TEXT    NOT NULL,
                metodo_pago    TEXT    NOT NULL,
                total          REAL    NOT NULL,
                estado         TEXT    NOT NULL DEFAULT 'pendiente',
                fecha          TEXT    NOT NULL,
                sincronizado   INTEGER NOT NULL DEFAULT 0,
                numero_factura TEXT    NOT NULL DEFAULT '',
                sync_id        TEXT    NOT NULL DEFAULT ''
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS detalle_pedidos (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id     INTEGER NOT NULL REFERENCES pedidos(id),
                producto_id   INTEGER NOT NULL REFERENCES productos(id),
                cantidad      INTEGER NOT NULL,
                observaciones TEXT    DEFAULT ''
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tipos_base (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT    NOT NULL UNIQUE,
                icono  TEXT    NOT NULL DEFAULT '🍹'
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bases (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre     TEXT    NOT NULL,
                tipo       TEXT    NOT NULL DEFAULT 'Gaseosa',
                tipo_id    INTEGER REFERENCES tipos_base(id) ON DELETE SET NULL,
                disponible INTEGER NOT NULL DEFAULT 1
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS producto_bases (
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                base_id     INTEGER NOT NULL REFERENCES bases(id)     ON DELETE CASCADE,
                PRIMARY KEY (producto_id, base_id)
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""")
        conn.commit()

        if conn.execute("SELECT COUNT(*) FROM tipos_base").fetchone()[0] == 0:
            conn.executemany("INSERT INTO tipos_base (nombre, icono) VALUES (?,?)", [
                ("Cerveza", "🍺"), ("Gaseosa", "🧃"), ("Soda", "🫧"),
            ])
            conn.commit()
        else:
            if not conn.execute("SELECT id FROM tipos_base WHERE nombre='Soda'").fetchone():
                conn.execute("INSERT INTO tipos_base (nombre, icono) VALUES ('Soda','🫧')")
                conn.commit()

        if conn.execute("SELECT COUNT(*) FROM bases").fetchone()[0] == 0:
            cer_id = conn.execute("SELECT id FROM tipos_base WHERE nombre='Cerveza'").fetchone()["id"]
            gas_id = conn.execute("SELECT id FROM tipos_base WHERE nombre='Gaseosa'").fetchone()["id"]
            sod_id = conn.execute("SELECT id FROM tipos_base WHERE nombre='Soda'").fetchone()["id"]
            conn.executemany("INSERT INTO bases (nombre, tipo, tipo_id) VALUES (?,?,?)", [
                ("Aguila",  "Cerveza", cer_id), ("Corona",  "Cerveza", cer_id),
                ("Costena", "Cerveza", cer_id),
                ("Quatro",  "Gaseosa", gas_id), ("Sprite",  "Gaseosa", gas_id),
                ("Bretana", "Soda",    sod_id),  ("Ginger",  "Soda",    sod_id),
            ])
            conn.commit()
        else:
            try:
                sod_id = conn.execute("SELECT id FROM tipos_base WHERE nombre='Soda'").fetchone()["id"]
                conn.execute(
                    "UPDATE bases SET tipo='Soda', tipo_id=? WHERE LOWER(nombre) IN ('bretana','ginger') AND (tipo='Gaseosa' OR tipo_id IS NULL OR tipo_id!=(?))",
                    (sod_id, sod_id)
                )
                conn.commit()
            except Exception:
                pass

        try:
            conn.execute("ALTER TABLE bases ADD COLUMN tipo_id INTEGER REFERENCES tipos_base(id) ON DELETE SET NULL")
            conn.commit()
        except Exception:
            pass

        try:
            rows = conn.execute("SELECT id, tipo FROM bases WHERE tipo_id IS NULL").fetchall()
            if rows:
                tipos = {r["nombre"]: r["id"] for r in conn.execute("SELECT id, nombre FROM tipos_base").fetchall()}
                for row in rows:
                    tid = tipos.get(row["tipo"])
                    if tid:
                        conn.execute("UPDATE bases SET tipo_id=? WHERE id=?", (tid, row["id"]))
                conn.commit()
        except Exception:
            pass

        if conn.execute("SELECT COUNT(*) FROM categorias").fetchone()[0] == 0:
            conn.executemany("INSERT INTO categorias (nombre) VALUES (?)", [
                ("Micheladas",), ("Mojitos",), ("Especiales",)
            ])
            conn.commit()

        if conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0:
            ids = [r["id"] for r in conn.execute("SELECT id FROM categorias ORDER BY id").fetchall()]
            c_mich, c_moji, c_esp = ids[0], ids[1], ids[2]
            conn.executemany(
                "INSERT INTO productos (categoria_id, nombre, precio, disponible, tiene_base) VALUES (?,?,?,1,?)",
                [
                    (c_mich, "Michelada Maracuya",      14000, 1),
                    (c_mich, "Michelada Tamarindo",     14000, 1),
                    (c_mich, "Michelada Frutos Rojos",  14000, 1),
                    (c_mich, "Michelada Clasica",       10000, 1),
                    (c_moji, "Mojito Maracuya",         16000, 0),
                    (c_moji, "Mojito Tamarindo",        16000, 0),
                    (c_moji, "Mojito Frutos Rojos",     16000, 0),
                    (c_esp,  "Pati Chamoy",             12000, 0),
                    (c_esp,  "Chamoy",                   5000, 0),
                ]
            )
            conn.commit()

        if conn.execute("SELECT COUNT(*) FROM notas_rapidas").fetchone()[0] == 0:
            ids = {r["nombre"]: r["id"] for r in conn.execute("SELECT id, nombre FROM categorias").fetchall()}
            mich = ids.get("Micheladas")
            moji = ids.get("Mojitos")
            conn.executemany("INSERT INTO notas_rapidas (texto, categoria_id) VALUES (?,?)", [
                ("Sin Hielo",       None),
                ("Para Llevar",     None),
                ("Poco Chamoy",     mich),
                ("Poca Sal",        mich),
                ("Extra Limon",     mich),
                ("Sin Chamoy",      mich),
                ("Extra Chamoy",    mich),
                ("Poca Crema",      mich),
                ("Sin Sal",         mich),
                ("Extra Crema",     mich),
                ("Extra Limon",     moji),
                ("Poco Azucar",     moji),
                ("Con Gas",         moji),
                ("Sin Hierbabuena", moji),
            ])
            conn.commit()
