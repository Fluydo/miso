# Check if crash.py exists and is loaded
Write-Host "=== CRASH GAME DIAGNOSTIC ===" -ForegroundColor Cyan
Write-Host ""

# Check if crash.py file exists
$crashFile = "C:\Users\lucas\Downloads\miso\cogs\crash.py"
if (Test-Path $crashFile) {
    Write-Host "[OK] crash.py exists" -ForegroundColor Green
    Write-Host "     Path: $crashFile" -ForegroundColor Gray
} else {
    Write-Host "[FAIL] crash.py NOT FOUND!" -ForegroundColor Red
    Write-Host "       Expected: $crashFile" -ForegroundColor Gray
    Write-Host "       ACTION: Run 'git pull origin main' in C:\Users\lucas\Downloads\miso" -ForegroundColor Yellow
}

Write-Host ""

# Check git status
Write-Host "Checking git status..." -ForegroundColor Cyan
Set-Location "C:\Users\lucas\Downloads\miso"
$gitLog = git log --oneline -5
Write-Host "Recent commits:" -ForegroundColor Gray
$gitLog | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

Write-Host ""

# Check if crash commands are in recent commits
$hasCrash = git log --all --oneline | Select-String "crash"
if ($hasCrash) {
    Write-Host "[OK] Crash commits found in git history" -ForegroundColor Green
    $hasCrash | ForEach-Object { Write-Host "     $_" -ForegroundColor Gray }
} else {
    Write-Host "[FAIL] No crash commits in git history" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== NEXT STEPS ===" -ForegroundColor Cyan
Write-Host "1. If crash.py is missing, run:" -ForegroundColor Yellow
Write-Host "   cd C:\Users\lucas\Downloads\miso" -ForegroundColor White
Write-Host "   git pull origin main" -ForegroundColor White
Write-Host ""
Write-Host "2. Then restart handler.py:" -ForegroundColor Yellow
Write-Host "   py handler.py" -ForegroundColor White
Write-Host ""
Write-Host "3. Look for this line in the output:" -ForegroundColor Yellow
Write-Host "   [INFO] Loaded extension: cogs.crash" -ForegroundColor White
