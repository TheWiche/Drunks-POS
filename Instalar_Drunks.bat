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

powershell -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference = 'Stop'; ^
   try { ^
     $rel = Invoke-RestMethod 'https://api.github.com/repos/TheWiche/Drunks-POS/releases/latest'; ^
     $asset = $rel.assets | Where-Object { $_.name -like '*.zip' } | Select-Object -First 1; ^
     if (-not $asset) { Write-Host 'ERROR: No se encontro el archivo de instalacion en GitHub.' -ForegroundColor Red; exit 1 } ^
     $dest = Split-Path -Parent $MyInvocation.MyCommand.Path; ^
     $zip  = Join-Path $dest 'drunks_update.zip'; ^
     Write-Host ('Descargando ' + $asset.name + '...'); ^
     Invoke-WebRequest $asset.browser_download_url -OutFile $zip; ^
     Write-Host 'Extrayendo archivos...'; ^
     Expand-Archive $zip -DestinationPath $dest -Force; ^
     Remove-Item $zip -Force; ^
     $lnkPath = [System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Drunks POS.lnk'); ^
     $batPath = Join-Path $dest 'INICIAR_SISTEMA.bat'; ^
     $shell = New-Object -ComObject WScript.Shell; ^
     $link  = $shell.CreateShortcut($lnkPath); ^
     $link.TargetPath     = $batPath; ^
     $link.WorkingDirectory = $dest; ^
     $link.Description    = 'Drunks POS - Sistema de Ventas'; ^
     $link.Save(); ^
     Write-Host '' ; ^
     Write-Host '  Instalacion completa!' -ForegroundColor Green; ^
     Write-Host ('  Version: ' + (Get-Content (Join-Path $dest 'version.txt') -ErrorAction SilentlyContinue)); ^
     Write-Host '  Acceso directo creado en el Escritorio.' ^
   } catch { ^
     Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red; ^
     exit 1 ^
   }"

echo.
echo  Presiona cualquier tecla para salir...
pause >nul
