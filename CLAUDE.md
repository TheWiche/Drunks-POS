# Drunks POS — Contexto para Claude

> Para ver el mapa completo de carpetas/archivos usa `/arquitectura`

## Qué es
POS offline-first para negocio de bebidas. Desktop app: pywebview → FastAPI/Uvicorn → SQLite. Distribuida como un solo `Drunks.exe` (PyInstaller onefile). Auto-actualización desde GitHub Releases.

## Arquitectura (desde v1.0.6)

El proyecto fue reestructurado — el monolítico `main.py` fue dividido en:

```
backend/          ← FastAPI: lógica, DB, Supabase, API
frontend/         ← HTML/CSS/JS servidos como archivos estáticos
```

### Archivos clave

| Archivo | Rol |
|---|---|
| `app_launcher.py` | Entry point: arranca uvicorn en hilo, abre pywebview, maneja updates con ventana tkinter. Import: `from backend.main import app` |
| `updater.py` | Chequea GitHub Releases, descarga ZIP, bat mínimo para reemplazar Drunks.exe. `APP_VERSION` hardcodeado aquí. |
| `installer_gui.py` | Instalador independiente (ttk tema `vista`, estilo Windows nativo). |
| `drunks_app.spec` | PyInstaller **onefile** spec. Incluye `('frontend','frontend')` en datas. |
| `version.txt` | Informativo solamente — la app NO lo lee. |

### Backend (`backend/`)

| Módulo | Contenido |
|---|---|
| `backend/main.py` | App factory FastAPI + lifespan + rutas de páginas (FileResponse) |
| `backend/config.py` | `DB_PATH`, `SUPABASE_URL/KEY`, `PORT`, `FRONTEND_DIR` (PyInstaller-aware) |
| `backend/database.py` | `get_conn()`, `init_db()`, migraciones, seeds, `to_dict()` |
| `backend/supabase.py` | `push_config()`, `pull_config_from_supabase()`, `sync_to_supabase()` |
| `backend/routers/pedidos.py` | `/api/pedidos`, `/api/pedidos/{id}/entregar`, `/ws` |
| `backend/routers/productos.py` | CRUD `/api/productos` + `/api/categorias` |
| `backend/routers/bases.py` | CRUD `/api/bases`, `/api/tipos-base`, `/api/productos/{id}/bases` |
| `backend/routers/notas.py` | CRUD `/api/notas_rapidas` |
| `backend/routers/settings.py` | GET/PUT `/api/settings` |
| `backend/routers/updates.py` | `/api/update/check`, `/api/update/apply` |
| `backend/routers/dashboard.py` | `/api/dashboard`, `/api/export/excel` |
| `backend/routers/sync.py` | `/api/sync/status` |

### Frontend (`frontend/`)

| Carpeta | Vista | Ruta |
|---|---|---|
| `frontend/shell/` | Shell pywebview: topbar + iframe con nav Vendedor/Cocina/Admin | `/` y `/app` |
| `frontend/vendedor/` | Vista operativa: tomar pedidos y cobrar | `/vendedor` |
| `frontend/cocina/` | Vista operativa: ver y marcar pedidos + modal config (legacy) | `/cocina` |
| `frontend/admin/` | Panel admin con PIN: 📊 Reportes + ⚙️ Configuración | `/admin` y `/dashboard` |

**Admin PIN**: el setting `admin_pin` en SQLite. Si está vacío → acceso libre. Si tiene valor → overlay PIN. Se guarda en `sessionStorage` al desbloquear.

## Versión actual
**1.0.5** — hardcodeada en `updater.py` línea `APP_VERSION = "1.0.5"`.  
GitHub repo: `TheWiche/Drunks-POS`  
Último release: `v1.0.5`

## Cómo hacer un release (paso a paso)

1. **Subir versión** en `updater.py`: cambiar `APP_VERSION = "1.0.X"`
2. **Actualizar** `version.txt` (informativo)
3. **Compilar**: `pyinstaller drunks_app.spec --noconfirm`  
   → produce `dist\Drunks.exe` (incluye `frontend/` dentro)
4. **Compilar instalador** (si hubo cambios): `pyinstaller installer_gui.py --onefile --noconsole --uac-admin --name Instalar_Drunks --noconfirm`
5. **Crear ZIP**: `Compress-Archive -Path dist\Drunks.exe -DestinationPath drunks_v1.0.X.zip -Force`
6. **Publicar release**:
   ```
   & "C:\Program Files\GitHub CLI\gh.exe" release create v1.0.X `
     drunks_v1.0.X.zip dist\Drunks.exe dist\Instalar_Drunks.exe `
     --repo TheWiche/Drunks-POS `
     --title "Drunks POS v1.0.X" `
     --notes "- descripción del cambio"
   ```
7. **Commit + push**: `git add -A && git commit -m "..." && git push`

## Supabase (cloud sync)
- **Proyecto**: `crqfohuwvbebyugxodqe`
- **URL**: `https://crqfohuwvbebyugxodqe.supabase.co`
- **Uso**: Sincronización de configuración (productos, bases, categorías, notas, settings)
- **Tabla requerida** en Supabase (el usuario debe crearla una vez):
  ```sql
  create table config (clave text primary key, valor jsonb not null, actualizado_en timestamptz default now());
  alter table config enable row level security;
  create policy "allow_all" on config for all using (true) with check (true);
  ```
- **Push**: después de cada write → `push_config("tabla")` en hilo daemon (en `backend/supabase.py`)
- **Pull**: al arrancar la app → `pull_config_from_supabase()` en lifespan

## Tablas SQLite sincronizadas
`categorias`, `tipos_base`, `productos`, `bases`, `notas_rapidas`, `producto_bases`, `settings`

## Reglas importantes
- La versión **NUNCA** se lee de archivo — solo de `APP_VERSION` en `updater.py`
- Build es **onefile** — no COLLECT, no carpeta `_internal`
- El bat de update usa `ping 127.0.0.1 -n 5 > nul` (no `timeout` — falla sin stdin)
- La ventana de progreso de update es **tkinter** (no segunda ventana pywebview)
- El `frontend/` se sirve via `FileResponse` — **no** como strings embebidos en Python
- `FRONTEND_DIR` en `backend/config.py` detecta automáticamente si está frozen (PyInstaller) o en dev
- La carpeta `frontend/static/` se monta en `/static` vía `StaticFiles`

## Error conocido en otro PC
`Failed to load Python DLL python312.dll` → error de antivirus o Windows Defender bloqueando la extracción del onefile en `%TEMP%\_MEI...`. Solución: agregar excepción en el antivirus, o usar build tipo COLLECT (carpeta) en vez de onefile.
