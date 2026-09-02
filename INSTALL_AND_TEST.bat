@echo off
echo Installing HTML to GIF dependencies (NO ffmpeg needed!)...
cd /d "%~dp0"
npm install gif-encoder get-pixels && echo. && echo Success! Now testing... && echo. && node generate_html_gif.js betting 1.0 test.gif && echo. && echo ✅ GIF created! Check test.gif
pause
