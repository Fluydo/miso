@echo off
echo Installing GIF generation dependencies...
cd /d "%~dp0"
call npm install gifencoder canvas --save
echo.
echo Done! Press any key to exit...
pause >nul
