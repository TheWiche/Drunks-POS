@echo off
title Drunks POS - Iniciando...
color 0A

echo.
echo  ==========================================
echo    DRUNKS POS - SISTEMA DE VENTAS
echo  ==========================================
echo.

:: ── Credenciales Supabase (sync a la nube) ──
set SUPABASE_URL=https://crqfohuwvbebyugxodqe.supabase.co
set SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNycWZvaHV3dmJlYnl1Z3hvZHFlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA1ODgyMTgsImV4cCI6MjA5NjE2NDIxOH0.F5RAHHnBt722dm9-yfe8bZw6J0wAJWh01fJfh3pf4lM

echo  [1/2] Iniciando servidor...
echo.

start "" /B "dist\drunks_backend\drunks_backend.exe"

echo  [2/2] Abriendo sistema en el navegador...
timeout /t 3 /nobreak >nul

start "" "http://localhost:8000/cocina"

echo.
echo  ==========================================
echo    Sistema iniciado correctamente.
echo    Cocina   : http://localhost:8000/cocina
echo    Vendedor : http://localhost:8000/vendedor
echo    Dashboard: http://localhost:8000/dashboard
echo  ==========================================
echo.
echo  Presiona cualquier tecla para cerrar esta ventana...
pause >nul
