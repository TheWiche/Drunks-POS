@echo off
title Drunks POS - Publicar Release
color 0B
echo.
echo  ==========================================
echo    DRUNKS POS - PUBLICAR NUEVA VERSION
echo  ==========================================
echo.

:: Leer version actual
set /p CURRENT_VER=<version.txt
echo  Version actual: %CURRENT_VER%
echo.
set /p NEW_VER=  Nueva version (Enter para mantener %CURRENT_VER%):

if "%NEW_VER%"=="" (
    set NEW_VER=%CURRENT_VER%
) else (
    echo %NEW_VER%>version.txt
    echo  Version actualizada a: %NEW_VER%
)

echo.
echo  [1/4] Compilando .exe...
pyinstaller drunks_backend.spec -y
if errorlevel 1 (
    echo  ERROR en la compilacion. Abortando.
    pause
    exit /b 1
)

echo.
echo  [2/4] Empaquetando...
powershell -Command "Compress-Archive -Path 'dist\drunks_backend','INICIAR_SISTEMA.bat','version.txt' -DestinationPath 'drunks_v%NEW_VER%.zip' -Force"
if errorlevel 1 (
    echo  ERROR al empaquetar. Abortando.
    pause
    exit /b 1
)

echo.
echo  [3/4] Subiendo a GitHub...
git add version.txt
git commit -m "release: v%NEW_VER%"
git push

echo.
echo  [4/4] Creando GitHub Release v%NEW_VER%...
gh release create "v%NEW_VER%" "drunks_v%NEW_VER%.zip" --title "Drunks POS v%NEW_VER%" --generate-notes
if errorlevel 1 (
    echo.
    echo  AVISO: No se pudo crear el release automaticamente.
    echo  Puedes subirlo manualmente en: https://github.com/TheWiche/Drunks-POS/releases/new
    echo  Archivo a subir: drunks_v%NEW_VER%.zip
) else (
    del "drunks_v%NEW_VER%.zip" >nul 2>&1
    echo.
    echo  ==========================================
    echo    Release v%NEW_VER% publicado exitosamente!
    echo    Las PCs con el sistema se actualizaran
    echo    automaticamente al reiniciar la app.
    echo  ==========================================
)

echo.
pause
