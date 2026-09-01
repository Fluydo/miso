@echo off
echo ========================================
echo   FIRST TIME SETUP - RUN THIS ONCE
echo ========================================
echo.
echo This script will:
echo 1. Pull latest code from GitHub
echo 2. Install Python dependencies
echo 3. Start the auto-update handler
echo.
echo After this runs, you NEVER need to manually update again!
echo Just push from your main PC and the bot auto-updates.
echo.
pause
echo.
echo ========================================
echo STEP 1: Pulling latest code...
echo ========================================
git stash
git fetch origin main
git reset --hard origin/main
echo.
echo ========================================
echo STEP 2: Installing dependencies...
echo ========================================
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
echo.
echo ========================================
echo STEP 3: Starting handler...
echo ========================================
echo.
echo The bot will now run forever with auto-updates!
echo DO NOT CLOSE THIS WINDOW - minimize it instead.
echo.
pause
echo.
py handler.py
