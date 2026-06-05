@echo off
title Drunks POS - Instalador
color 0A
echo.
echo  ==========================================
echo    DRUNKS POS - INSTALADOR
echo  ==========================================
echo.
echo  Descargando la ultima version desde GitHub...
echo.

:: Escribir script PowerShell a archivo temporal y ejecutarlo
set "PS_SCRIPT=%TEMP%\instalar_drunks.ps1"
set "DEST=%~dp0"

(
echo $ErrorActionPreference = 'Stop'
echo try {
echo     $rel = Invoke-RestMethod 'https://api.github.com/repos/TheWiche/Drunks-POS/releases/latest'
echo     $asset = $rel.assets ^| Where-Object { $_.name -like '*.zip' } ^| Select-Object -First 1
echo     if (-not $asset) { Write-Host 'ERROR: No se encontro archivo de instalacion en GitHub.' -ForegroundColor Red; exit 1 }
echo     $dest = '%DEST%'
echo     $zip = Join-Path $dest 'drunks_update.zip'
echo     Write-Host ('Descargando ' + $asset.name + '...')
echo     Invoke-WebRequest $asset.browser_download_url -OutFile $zip
echo     Write-Host 'Extrayendo archivos...'
echo     Expand-Archive $zip -DestinationPath $dest -Force
echo     Remove-Item $zip -Force
echo     $lnkPath = [System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Drunks POS.lnk')
echo     $batPath = Join-Path $dest 'INICIAR_SISTEMA.bat'
echo     $shell = New-Object -ComObject WScript.Shell
echo     $link = $shell.CreateShortcut($lnkPath)
echo     $link.TargetPath = $batPath
echo     $link.WorkingDirectory = $dest
echo     $link.Description = 'Drunks POS - Sistema de Ventas'
echo     $link.Save()
echo     Write-Host ''
echo     Write-Host '  Instalacion completa!' -ForegroundColor Green
echo     $v = Get-Content (Join-Path $dest 'version.txt') -ErrorAction SilentlyContinue
echo     Write-Host ('  Version instalada: ' + $v)
echo     Write-Host '  Acceso directo creado en el Escritorio.'
echo } catch {
echo     Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
echo     exit 1
echo }
) > "%PS_SCRIPT%"

powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
set "EXIT_CODE=%ERRORLEVEL%"
del "%PS_SCRIPT%" >nul 2>&1

echo.
if %EXIT_CODE% neq 0 (
    echo  Hubo un error en la instalacion. Revisa tu conexion a internet.
) else (
    echo  Listo! Usa el acceso directo "Drunks POS" en tu Escritorio.
)
echo.
echo  Presiona cualquier tecla para salir...
pause >nul
