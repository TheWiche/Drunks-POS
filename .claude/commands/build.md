# /build — Compilar Drunks.exe

Compila el ejecutable onefile sin publicar release.

Pasos:
1. Ejecutar: `pyinstaller drunks_app.spec --noconfirm`
2. Verificar que `dist\Drunks.exe` existe y tiene tamaño >10 MB.
3. Reportar versión actual (`APP_VERSION` en `updater.py`) y tamaño del exe generado.

Si `$ARGUMENTS` contiene "instalador", también compilar:
`pyinstaller installer_gui.py --onefile --noconsole --uac-admin --name Instalar_Drunks --noconfirm`
