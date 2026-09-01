@echo off
title Miso Bot — Restart
cd /d "%~dp0"

echo.
echo  ==============================================
echo    Miso Bot — Restart
echo  ==============================================
echo.

echo  [~] Stopping bot...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo  [~] Cleaning up Python cache files...
del /S /Q __pycache__\*.pyc >nul 2>&1
rmdir /S /Q __pycache__ >nul 2>&1
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /S /Q "%%d" >nul 2>&1

echo  [~] Starting bot...
python main.py

pause
