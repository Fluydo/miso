@echo off
echo ================================================
echo    STOPPING OLD PC BOT
echo ================================================
echo.
echo This will stop the bot running on the old PC.
echo.
echo Steps:
echo 1. Creating STOP signal
echo 2. Committing to git
echo 3. Pushing to GitHub
echo.
pause

REM Update the timestamp in STOP_SIGNAL.txt
echo STOP > STOP_SIGNAL.txt
echo This file signals the old PC bot to shut down. >> STOP_SIGNAL.txt
echo When the bot sees this file during its check, it will stop immediately. >> STOP_SIGNAL.txt
echo. >> STOP_SIGNAL.txt
echo Timestamp: %date% %time% >> STOP_SIGNAL.txt

REM Git operations
git add STOP_SIGNAL.txt
git commit -m "STOP: Signal old PC bot to shut down"
git push origin main

echo.
echo ================================================
echo    STOP SIGNAL SENT!
echo ================================================
echo.
echo The old PC bot will shut down within 10 seconds
echo after it detects this change.
echo.
pause
