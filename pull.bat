@echo off
title Miso Bot — Git Pull & Restart
cd /d "%~dp0"

echo.
echo  ==============================================
echo    Miso Bot — Pull Latest Code
echo  ==============================================
echo.

echo  [~] Stopping bot...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

echo  [~] Cleaning up Python cache files...
del /S /Q __pycache__\*.pyc >nul 2>&1
rmdir /S /Q __pycache__ >nul 2>&1
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /S /Q "%%d" >nul 2>&1

echo  [~] Stashing local changes to data files...
git stash push -u -- data/*.json cogs/__pycache__/*.pyc >nul 2>&1

echo  [~] Pulling latest code...
git pull origin main
if %errorlevel% neq 0 (
    echo.
    echo  [X] Git pull failed. Trying to reset...
    git reset --hard origin/main
    if %errorlevel% neq 0 (
        echo  [X] Failed to pull. Please check your internet connection.
        pause
        exit /b 1
    )
)

echo  [~] Restoring local data files...
git stash pop >nul 2>&1

echo.
echo  [OK] Code updated successfully!
echo.
echo  [~] Starting bot...
start "" python main.py

echo.
echo  [OK] Bot restarted!
echo.
pause
