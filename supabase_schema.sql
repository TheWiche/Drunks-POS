-- ============================================================
-- DRUNKS POS — Schema para Supabase (PostgreSQL)
-- Ejecuta este script en el SQL Editor de tu proyecto Supabase
-- ============================================================

-- Categorías de bebidas
CREATE TABLE IF NOT EXISTS categorias (
  id          BIGSERIAL PRIMARY KEY,
  nombre      TEXT NOT NULL
);

-- Productos / bebidas
CREATE TABLE IF NOT EXISTS productos (
  id           BIGSERIAL PRIMARY KEY,
  categoria_id BIGINT REFERENCES categorias(id) ON DELETE SET NULL,
  nombre       TEXT NOT NULL,
  precio       NUMERIC(12,2) NOT NULL DEFAULT 0,
  disponible   BOOLEAN NOT NULL DEFAULT TRUE,
  tiene_base   BOOLEAN NOT NULL DEFAULT FALSE
);

-- Notas rápidas (por categoría o globales)
CREATE TABLE IF NOT EXISTS notas_rapidas (
  id           BIGSERIAL PRIMARY KEY,
  texto        TEXT NOT NULL,
  categoria_id BIGINT REFERENCES categorias(id) ON DELETE SET NULL
);

-- Pedidos
CREATE TABLE IF NOT EXISTS pedidos (
  id              BIGSERIAL PRIMARY KEY,
  numero_factura  TEXT NOT NULL DEFAULT '',
  cliente         TEXT NOT NULL,
  metodo_pago     TEXT NOT NULL CHECK (metodo_pago IN ('Efectivo','Transferencia')),
  total           NUMERIC(12,2) NOT NULL,
  estado          TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','entregado')),
  fecha           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sincronizado    BOOLEAN NOT NULL DEFAULT FALSE,
  items_json      TEXT NOT NULL DEFAULT '[]'
);

-- Si la tabla ya existe, agrega la columna items_json (seguro si ya existe)
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS items_json TEXT NOT NULL DEFAULT '[]';

-- Detalle de cada pedido
CREATE TABLE IF NOT EXISTS detalle_pedidos (
  id            BIGSERIAL PRIMARY KEY,
  pedido_id     BIGINT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
  producto_id   BIGINT NOT NULL REFERENCES productos(id),
  cantidad      INTEGER NOT NULL CHECK (cantidad > 0),
  observaciones TEXT DEFAULT ''
);

-- ── Índices para acelerar consultas del dashboard ──
CREATE INDEX IF NOT EXISTS idx_pedidos_fecha   ON pedidos(fecha DESC);
CREATE INDEX IF NOT EXISTS idx_pedidos_estado  ON pedidos(estado);
CREATE INDEX IF NOT EXISTS idx_detalle_pedido  ON detalle_pedidos(pedido_id);

-- ── Row Level Security (RLS) — acceso solo con tu API key ──
ALTER TABLE categorias      ENABLE ROW LEVEL SECURITY;
ALTER TABLE productos        ENABLE ROW LEVEL SECURITY;
ALTER TABLE notas_rapidas    ENABLE ROW LEVEL SECURITY;
ALTER TABLE pedidos          ENABLE ROW LEVEL SECURITY;
ALTER TABLE detalle_pedidos  ENABLE ROW LEVEL SECURITY;

-- Política: cualquier petición autenticada con la service_role key puede leer y escribir
CREATE POLICY "service_role_all" ON categorias     FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON productos       FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON notas_rapidas   FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON pedidos         FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_all" ON detalle_pedidos FOR ALL USING (true) WITH CHECK (true);
