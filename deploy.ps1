# SignalWatch - GitHub Push & Render Deployment Script
# Run this in PowerShell

Write-Host "🚀 SignalWatch Deployment Script" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Initialize Git
Write-Host "Step 1: Initializing Git Repository..." -ForegroundColor Yellow
git init

# Step 2: Add remote
Write-Host "Step 2: Adding GitHub Remote..." -ForegroundColor Yellow
git remote add origin https://github.com/Signal-Watch/SignalWatchUK-Private.git

# Step 3: Check what files will be committed
Write-Host "Step 3: Checking Files..." -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  IMPORTANT: Check that .env file is NOT in the list below!" -ForegroundColor Red
Write-Host ""
git status

Write-Host ""
Write-Host "Files above will be committed to GitHub." -ForegroundColor Green
Write-Host ""
$continue = Read-Host "Do you want to continue? (y/n)"

if ($continue -ne 'y') {
    Write-Host "❌ Deployment cancelled." -ForegroundColor Red
    exit
}

# Step 4: Add all files
Write-Host "Step 4: Adding Files..." -ForegroundColor Yellow
git add .

# Step 5: Commit
Write-Host "Step 5: Committing..." -ForegroundColor Yellow
git commit -m "Initial commit - SignalWatch backend ready for deployment"

# Step 6: Push to GitHub
Write-Host "Step 6: Pushing to GitHub..." -ForegroundColor Yellow
git branch -M main
git push -u origin main --force

Write-Host ""
Write-Host "✅ Successfully pushed to GitHub!" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Go to https://dashboard.render.com/" -ForegroundColor White
Write-Host "2. Click 'New +' → 'Web Service'" -ForegroundColor White
Write-Host "3. Connect GitHub repo: Signal-Watch/SignalWatchUK-Private" -ForegroundColor White
Write-Host "4. Use these settings:" -ForegroundColor White
Write-Host "   - Build Command: pip install -r requirements.txt" -ForegroundColor Gray
Write-Host "   - Start Command: gunicorn app:app --bind 0.0.0.0:`$PORT" -ForegroundColor Gray
Write-Host "5. Add Environment Variable:" -ForegroundColor White
Write-Host "   GITHUB_TOKEN = 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" -ForegroundColor Gray
Write-Host ""
Write-Host "See DEPLOYMENT.md for detailed instructions" -ForegroundColor Cyan
