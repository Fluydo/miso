@echo off
echo ==============================================
echo Testing Crash GIF Generation (Pure JS)
echo ==============================================
echo.

cd /d "%~dp0"

echo Step 1: Installing dependencies (omggif - pure JS, no native deps)...
call npm install omggif
echo.

echo Step 2: Testing betting phase...
node generate_crash_pure.js betting 1.0 test_betting.gif
echo.

echo Step 3: Testing running phase...
node generate_crash_pure.js running 2.5 test_running.gif
echo.

echo Step 4: Testing supersonic phase...
node generate_crash_pure.js supersonic 8.0 test_supersonic.gif
echo.

echo Step 5: Testing crashed phase...
node generate_crash_pure.js crashed 3.7 test_crashed.gif
echo.

echo ==============================================
echo Done! Check for test_*.gif files in this folder
echo ==============================================
pause
