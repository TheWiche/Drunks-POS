@echo off
title Drunks POS - Iniciando...
color 0A

echo.
echo  ==========================================
echo    DRUNKS POS - SISTEMA DE VENTAS
echo  ==========================================
echo.
echo  [1/2] Iniciando servidor en segundo plano...
echo.

start "" /B "dist\drunks_backend\drunks_backend.exe"

echo  [2/2] Esperando que el servidor arranque...
timeout /t 3 /nobreak >nul

echo.
echo  Abriendo interfaz de cocina en el navegador predeterminado...
echo.

start "" "http://192.168.137.1:8000/cocina"

echo  ==========================================
echo    Sistema iniciado correctamente.
echo    Cocina   : http://192.168.137.1:8000/cocina
echo    Vendedor : http://192.168.137.1:8000/vendedor
echo  ==========================================
echo.
echo  Presiona cualquier tecla para cerrar esta ventana...
pause >nul
