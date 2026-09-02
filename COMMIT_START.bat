@echo off
echo ================================================
echo    COMMIT START SIGNAL (Without Touching Your Files)
echo ================================================
echo.
echo This commits the full main.py to restart old PC bot
echo without touching your local files!
echo.
pause

REM Create temp directory
set TEMP_DIR=%TEMP%\miso_bot_temp_%RANDOM%
echo Creating temp directory: %TEMP_DIR%
mkdir "%TEMP_DIR%"

REM Copy entire repo to temp
echo Copying files to temp...
xcopy /E /I /Q . "%TEMP_DIR%"

REM Copy .git folder
xcopy /E /I /Q /H .git "%TEMP_DIR%\.git"

REM Go to temp and make changes there
cd /d "%TEMP_DIR%"

REM Copy the full main.py (main_WITH_STOP_CHECK.py)
copy /Y main_WITH_STOP_CHECK.py main.py

REM Commit and push
git add main.py
git commit -m "START: old PC bot with stop monitoring"
git push origin main

echo.
echo ================================================
echo    DONE! Old PC bot will start with stop monitoring.
echo ================================================
echo.
echo Your local files were NOT touched!
echo Temp folder: %TEMP_DIR%
echo.
pause

REM Clean up
cd /d "%~dp0"
rmdir /S /Q "%TEMP_DIR%"
