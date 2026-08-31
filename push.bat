@echo off
title Miso Bot — Git Push
cd /d "%~dp0"

echo.
echo  ==============================================
echo    Miso Bot — Push to GitHub
echo  ==============================================
echo.

git status --short
echo.

set /p MSG=  Commit message: 
if "%MSG%"=="" (
    echo  [!] Commit message cannot be empty.
    pause
    exit /b 1
)

echo.
echo  [~] Staging all changes...
git add -A

echo  [~] Committing...
git commit -m "%MSG%"
if %errorlevel% neq 0 (
    echo  [!] Nothing to commit or commit failed.
    pause
    exit /b 1
)

echo  [~] Pushing to origin/main...
git push origin main
if %errorlevel% neq 0 (
    echo.
    echo  [X] Push failed. Check the error above.
    pause
    exit /b 1
)

echo.
echo  [OK] Pushed successfully!
echo.
pause
