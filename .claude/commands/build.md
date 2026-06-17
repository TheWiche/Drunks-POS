# /build — Compilar Drunks.exe

Compila la app sin publicar release.

Pasos:
1. Ejecutar: `pyinstaller drunks_app.spec --noconfirm`
2. Verificar que `dist\Drunks\Drunks.exe` existe y tiene tamaño >10 MB.
3. Reportar versión actual (`APP_VERSION` en `updater.py`) y tamaño del exe generado.
4. Hacer commit de cualquier archivo modificado y push: `git add -A && git commit -m "build: compilar vX.X.X" && git push`

Si `$ARGUMENTS` contiene "instalador", también compilar antes del commit:
`pyinstaller installer_gui.py --onefile --noconsole --uac-admin --name Instalar_Drunks --noconfirm`
