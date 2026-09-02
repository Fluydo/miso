# Commit and push changes

Write-Host "🔄 Staging changes..." -ForegroundColor Cyan
git add .

Write-Host "📝 Committing..." -ForegroundColor Cyan
git commit -m "fix: crash game auto-restart and mobile responsiveness

- Fix game loop to handle 'ended' status and restart automatically
- Game now properly cycles: betting → running → ended → new game
- Add mobile responsiveness to crash page
- Graph now visible on mobile devices
- Responsive text sizes and padding
- Better error logging with traceback"

Write-Host "🚀 Pushing to origin main..." -ForegroundColor Cyan
git push origin main --force

Write-Host "✅ Done!" -ForegroundColor Green
