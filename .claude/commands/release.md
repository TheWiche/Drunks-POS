# /release — Publicar nueva versión de Drunks POS

Argumentos esperados: `$ARGUMENTS` (ej: `1.0.6 "Fix en sincronización de bases"`)

Pasos a ejecutar en orden:

1. Parsear argumentos: primer token = nueva versión (ej `1.0.6`), resto = descripción del cambio.
2. Actualizar `APP_VERSION` en `updater.py` a la nueva versión.
3. Actualizar `version.txt` con la nueva versión.
4. Compilar: `pyinstaller drunks_app.spec --noconfirm`
5. Verificar que `dist\Drunks\Drunks.exe` existe y tiene tamaño razonable (>10 MB).
5b. Compilar instalador (siempre): `pyinstaller installer_gui.py --onefile --noconsole --uac-admin --name Instalar_Drunks --noconfirm`
6. Crear ZIP del contenido de la carpeta (no la carpeta en sí): `Compress-Archive -Path dist\Drunks\* -DestinationPath "drunks_v{VERSION}.zip" -Force`
7. Publicar release en GitHub con gh CLI incluyendo AMBOS assets: el ZIP y `dist\Instalar_Drunks.exe`.
8. Hacer commit de los cambios y push.
9. Reportar la URL del release creado.

Si no se pasan argumentos, preguntar la versión y descripción antes de continuar.
