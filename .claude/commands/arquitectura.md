# /arquitectura — Mapa de la estructura del proyecto Drunks POS

Este slash command te da el mapa completo de la arquitectura del proyecto.

## Estructura de carpetas

```
Sistema_Drunks/
├── app_launcher.py          # Entry point: arranca uvicorn + abre pywebview
├── updater.py               # Auto-updater desde GitHub Releases (APP_VERSION aquí)
├── installer_gui.py         # Instalador independiente (ttk, estilo Windows)
├── drunks_app.spec          # PyInstaller onefile — incluye frontend/ en datas
├── requirements.txt
│
├── backend/                 # FastAPI — toda la lógica del servidor
│   ├── __init__.py
│   ├── main.py              # App factory + lifespan + mounts estáticos + rutas de páginas
│   ├── database.py          # get_conn(), init_db(), migraciones, seeds, to_dict()
│   ├── config.py            # DB_PATH, SUPABASE_URL/KEY, PORT, FRONTEND_DIR (PyInstaller-aware)
│   ├── supabase.py          # sync_to_supabase, push_config, pull_config_from_supabase, etc.
│   │
│   └── routers/
│       ├── pedidos.py       # POST/GET /api/pedidos, /api/pedidos/{id}/entregar, /ws
│       ├── productos.py     # CRUD /api/productos + /api/categorias
│       ├── bases.py         # CRUD /api/bases, /api/tipos-base, /api/productos/{id}/bases
│       ├── notas.py         # CRUD /api/notas_rapidas
│       ├── settings.py      # GET/PUT /api/settings
│       ├── updates.py       # GET /api/update/check, POST /api/update/apply
│       ├── dashboard.py     # GET /api/dashboard, GET /api/export/excel
│       └── sync.py          # GET /api/sync/status
│
└── frontend/                # Archivos estáticos servidos por FastAPI vía FileResponse
    ├── static/
    │   ├── css/             # (para estilos compartidos futuros)
    │   └── js/              # (para JS compartido futuro)
    │
    ├── vendedor/
    │   └── index.html       # Vista operativa: tomar pedidos y cobrar
    │
    ├── cocina/
    │   └── index.html       # Vista operativa: ver y marcar pedidos + modal config (legacy)
    │
    ├── admin/
    │   └── index.html       # Panel admin: reportes + configuración con PIN
    │                        # PIN protección via settings.admin_pin
    │                        # Tabs: 📊 Reportes | ⚙️ Configuración
    │
    └── shell/
        └── index.html       # Shell pywebview: topbar + iframe
                             # Nav: 🛒 Vendedor | 👨‍🍳 Cocina | 🔐 Admin
```

## Rutas HTTP

| Ruta | Archivo servido | Descripción |
|------|-----------------|-------------|
| `/` | `frontend/shell/index.html` | Shell con topbar |
| `/app` | `frontend/shell/index.html` | Shell (entrada de pywebview) |
| `/vendedor` | `frontend/vendedor/index.html` | Vista operativa caja |
| `/cocina` | `frontend/cocina/index.html` | Vista operativa cocina |
| `/admin` | `frontend/admin/index.html` | Panel admin (PIN) |
| `/dashboard` | `frontend/admin/index.html` | Alias de admin |
| `/api/*` | FastAPI routers | Toda la API REST |
| `/ws` | FastAPI (pedidos.py) | WebSocket cocina |
| `/static/*` | `frontend/static/` | Assets estáticos |

## Versión

Hardcodeada en `updater.py` → `APP_VERSION`. NUNCA leer de archivo.

## PyInstaller

`drunks_app.spec` onefile. El `frontend/` se incluye via:
```python
datas=[('frontend', 'frontend')]
```

En PyInstaller frozen: `FRONTEND_DIR = Path(sys._MEIPASS) / "frontend"`  
En dev: `FRONTEND_DIR = Path(__file__).parent.parent / "frontend"`

## Supabase config sync

- **Proyecto**: `crqfohuwvbebyugxodqe`
- `push_config(tabla)` → sube en hilo daemon tras cada write
- `pull_config_from_supabase()` → al arrancar, reemplaza SQLite local
- Tablas sincronizadas: `categorias, tipos_base, productos, bases, notas_rapidas, producto_bases, settings`

## Admin PIN

- Setting `admin_pin` en tabla `settings`
- Si está vacío → acceso libre al admin
- Si tiene valor → se muestra overlay PIN al entrar a `/admin`
- PIN desbloqueado se guarda en `sessionStorage` (solo la sesión actual)
