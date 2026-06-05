@echo off
title Drunks POS - Instalador
color 0A
echo.
echo  ==========================================
echo    DRUNKS POS - INSTALADOR
echo  ==========================================
echo.
echo  Descargando ultima version de GitHub...
echo  (Puede tardar unos segundos)
echo.

powershell -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; $rel = Invoke-RestMethod 'https://api.github.com/repos/TheWiche/Drunks-POS/releases/latest'; $url = ($rel.assets | Where-Object { $_.name -like '*.zip' } | Select-Object -First 1).browser_download_url; Invoke-WebRequest $url -OutFile '%TEMP%\drunks.zip'; Expand-Archive '%TEMP%\drunks.zip' -DestinationPath '%~dp0' -Force; Remove-Item '%TEMP%\drunks.zip' -Force; $s = New-Object -ComObject WScript.Shell; $l = $s.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Drunks POS.lnk')); $l.TargetPath = '%~dp0INICIAR_SISTEMA.bat'; $l.WorkingDirectory = '%~dp0'; $l.Save()"

if %ERRORLEVEL% neq 0 (
    echo.
    echo  ERROR: No se pudo instalar.
    echo  Revisa tu conexion a internet e intentalo de nuevo.
    echo.
    pause
    exit /b 1
)

echo.
echo  ==========================================
echo    Instalacion completa!
echo    Acceso directo creado en el Escritorio.
echo  ==========================================
echo.
pause
