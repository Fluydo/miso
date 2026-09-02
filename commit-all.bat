@echo off
echo Staging all changes...
git add .
echo.
echo Enter commit message:
set /p commit_msg="Commit message: "
echo.
echo Committing with message: %commit_msg%
git commit -m "%commit_msg%"
echo.
echo Pushing to remote...
git push --force
echo.
echo Done!
pause
