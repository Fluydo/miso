@echo off
title Miso Bot — Persistent Mode
cd /d "%~dp0"

echo.
echo  ==============================================
echo    Miso Bot — Persistent Mode
echo  ==============================================
echo.
echo  This will keep the bot running and auto-update.
echo  Press Ctrl+C to stop both monitoring and bot.
echo.

REM Start the auto-updater in a new window
start "Miso Bot Auto-Updater" /MIN cmd /c auto-update.bat

REM Start the bot
echo  [~] Starting bot...
python main.py

REM If bot crashes, restart after 10 seconds
echo.
echo  [!] Bot stopped. Restarting in 10 seconds...
timeout /t 10 /nobreak
goto START
