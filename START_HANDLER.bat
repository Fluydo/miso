@echo off
echo ========================================
echo   MISO BOT - AUTO-UPDATE HANDLER
echo ========================================
echo.
echo This will start the bot with auto-updates enabled.
echo.
echo The bot will automatically:
echo - Check GitHub for updates every 30 seconds
echo - Pull new code when available
echo - Restart with updated code
echo - Keep running forever
echo.
echo DO NOT CLOSE THIS WINDOW!
echo Minimize it instead.
echo.
echo Press Ctrl+C to stop (only if needed)
echo.
echo ========================================
pause
echo.
echo Starting handler...
echo.
py handler.py
