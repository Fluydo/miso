# Commit and push ALL fixes

Write-Host "🔄 Staging all changes..." -ForegroundColor Cyan
git add .

Write-Host "📝 Committing..." -ForegroundColor Cyan
git commit -m "fix: live updates + gif overhaul + mobile responsive

WEBSITE FIXES:
- Add polling backup (3s) for real-time updates
- Force fetch on subscription events
- Better error handling and logging
- Betting now registers immediately

DISCORD GIF OVERHAUL:
- Fresh canvas each frame (no text overlap)
- Draw FULL curve from 1.0x to current (like website)
- Rocket emoji at end of line
- Clean exponential curve visualization
- Bets image now appears BELOW gif

MOBILE:
- Responsive layout for all screen sizes
- Graph visible on mobile devices

Game now fully synced between Discord and website!"

Write-Host "🚀 Pushing to origin main..." -ForegroundColor Cyan
git push origin main --force

Write-Host "✅ Done! Test it now!" -ForegroundColor Green
