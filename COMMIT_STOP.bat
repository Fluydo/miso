@echo off
echo ================================================
echo    COMMIT STOP SIGNAL (Without Touching Your Files)
echo ================================================
echo.
echo This creates a temp folder, edits main.py there,
echo and commits from there - your files stay untouched!
echo.
pause

REM Create temp directory
set TEMP_DIR=%TEMP%\miso_bot_temp_%RANDOM%
echo Creating temp directory: %TEMP_DIR%
mkdir "%TEMP_DIR%"

REM Copy entire repo to temp (excluding .git)
echo Copying files to temp...
xcopy /E /I /Q /EXCLUDE:exclude.txt . "%TEMP_DIR%"

REM Copy .git folder
xcopy /E /I /Q /H .git "%TEMP_DIR%\.git"

REM Go to temp and make changes there
cd /d "%TEMP_DIR%"

REM Create dummy main.py
echo print("nothing") > main.py

REM Commit and push
git add main.py
git commit -m "STOP: old PC bot shutdown"
git push origin main

echo.
echo ================================================
echo    DONE! Old PC bot will stop.
echo ================================================
echo.
echo Your local files were NOT touched!
echo Temp folder: %TEMP_DIR%
echo.
pause

REM Clean up
cd /d "%~dp0"
rmdir /S /Q "%TEMP_DIR%"
