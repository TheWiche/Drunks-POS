# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Recolectar todo lo de pywebview y pythonnet automáticamente
wv_datas, wv_bins, wv_hiddenimports = collect_all('webview')
pn_datas, pn_bins, pn_hiddenimports = collect_all('pythonnet')
cl_datas, cl_bins, cl_hiddenimports = collect_all('clr_loader')

a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=wv_bins + pn_bins + cl_bins,
    datas=[
        ('version.txt', '.'),
        ('updater.py', '.'),
    ] + wv_datas + pn_datas + cl_datas,
    hiddenimports=wv_hiddenimports + pn_hiddenimports + cl_hiddenimports + [
        'webview',
        'webview.platforms',
        'webview.platforms.winforms',
        'clr',
        'proxy_tools',
        # uvicorn
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        # anyio
        'anyio._backends._asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Drunks',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    uac_admin=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Drunks',
)
