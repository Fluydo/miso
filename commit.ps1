# Commit and push changes

Write-Host "🔄 Staging changes..." -ForegroundColor Cyan
git add .

Write-Host "📝 Committing..." -ForegroundColor Cyan
git commit -m "feat: exponential crash curve, transparent UI, real-time updates

- Add TRUE exponential curve (1.08^t formula)
- Transparent background like log embeds  
- Light gray grid + Poppins font
- Fix text overlap issues
- Add bet results table PNG
- Fix website real-time subscription
- Better error handling on bet/cashout
- Force refresh after actions"

Write-Host "🚀 Force pushing to origin main..." -ForegroundColor Cyan
git push origin main --force

Write-Host "✅ Done!" -ForegroundColor Green
