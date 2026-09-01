@echo off
title Miso Bot — Auto Update & Restart
cd /d "%~dp0"

REM This script runs continuously and checks for updates every 5 minutes

:LOOP

echo.
echo [%date% %time%] Checking for updates...

REM Clean up cache files first
del /S /Q __pycache__\*.pyc >nul 2>&1
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /S /Q "%%d" >nul 2>&1

REM Stash local changes
git stash push -u -- data/*.json cogs/__pycache__/*.pyc >nul 2>&1

REM Fetch latest changes
git fetch origin main >nul 2>&1

REM Check if there are updates
git diff --quiet HEAD origin/main
if %errorlevel% equ 0 (
    echo [%date% %time%] No updates available. Waiting...
    git stash pop >nul 2>&1
    goto WAIT
)

echo [%date% %time%] Updates found! Pulling...

REM Stop bot
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

REM Pull updates
git reset --hard origin/main >nul 2>&1
git pull origin main >nul 2>&1

REM Restore local data
git stash pop >nul 2>&1

REM Install any new dependencies
pip install -r requirements.txt --quiet >nul 2>&1

echo [%date% %time%] Starting bot with updates...
start "" python main.py

:WAIT
REM Wait 5 minutes before checking again
timeout /t 300 /nobreak >nul
goto LOOP
