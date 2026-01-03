# PowerShell script to guide restart and test push notifications

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  RESTART AND TEST PUSH NOTIFICATIONS" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "STEP 1: Start Backend Server" -ForegroundColor Yellow
Write-Host "  Make sure backend is running on http://127.0.0.1:4000" -ForegroundColor White
Write-Host "  If not running, open a terminal and run:" -ForegroundColor Gray
Write-Host "    cd C:\projects\vila-app\back" -ForegroundColor Gray
Write-Host "    python run_server.py" -ForegroundColor Gray
Write-Host ""

$backendRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:4000/api/users" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $backendRunning = $true
        Write-Host "  ✅ Backend is running!" -ForegroundColor Green
    }
} catch {
    Write-Host "  ❌ Backend is NOT running" -ForegroundColor Red
    Write-Host "  Please start it first!" -ForegroundColor Yellow
}

Write-Host "`nSTEP 2: Start Metro Bundler" -ForegroundColor Yellow
Write-Host "  Open a NEW terminal and run:" -ForegroundColor White
Write-Host "    cd C:\projects\vila-app\front" -ForegroundColor Gray
Write-Host "    npm start" -ForegroundColor Gray
Write-Host "  Keep this terminal open!" -ForegroundColor White
Write-Host ""

Write-Host "STEP 3: Start Android Emulator" -ForegroundColor Yellow
Write-Host "  - Open Android Studio" -ForegroundColor White
Write-Host "  - Start an emulator (or use physical device)" -ForegroundColor White
Write-Host "  - Wait until it's fully booted" -ForegroundColor White
Write-Host ""

Write-Host "STEP 4: Launch the App" -ForegroundColor Yellow
Write-Host "  In a NEW terminal, run:" -ForegroundColor White
Write-Host "    cd C:\projects\vila-app\front" -ForegroundColor Gray
Write-Host "    npm run android:win" -ForegroundColor Gray
Write-Host "  OR if app is already installed, just open it on emulator" -ForegroundColor White
Write-Host ""

Write-Host "STEP 5: Sign In" -ForegroundColor Yellow
Write-Host "  - Open the app on emulator" -ForegroundColor White
Write-Host "  - Sign in as: test21 / 123456" -ForegroundColor White
Write-Host "  - Allow notification permissions when prompted" -ForegroundColor White
Write-Host "  - Wait 10 seconds for token registration" -ForegroundColor White
Write-Host ""

Write-Host "STEP 6: Check Token Registration" -ForegroundColor Yellow
Write-Host "  Watch for in Metro bundler console:" -ForegroundColor White
Write-Host "    'FCM token obtained: ...'" -ForegroundColor Gray
Write-Host "    'Push token registered successfully'" -ForegroundColor Gray
Write-Host ""
Write-Host "  Watch for in backend console:" -ForegroundColor White
Write-Host "    'POST /push/register HTTP/1.1'" -ForegroundColor Gray
Write-Host ""

Write-Host "STEP 7: Test Push Notifications" -ForegroundColor Yellow
Write-Host "  After signing in, wait 10 seconds, then run:" -ForegroundColor White
Write-Host "    cd C:\projects\vila-app\back" -ForegroundColor Gray
Write-Host "    python check_recent_registrations.py" -ForegroundColor Gray
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ready to start? Press Enter to check tokens..." -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host "`nChecking for registered tokens...`n" -ForegroundColor Yellow

try {
    $body = @{
        title = "Test"
        body = "Checking tokens"
    } | ConvertTo-Json
    
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:4000/push/send" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10
    $result = $response.Content | ConvertFrom-Json
    
    $total = $result.total_tokens
    $sent = $result.sent
    
    Write-Host "Results:" -ForegroundColor Cyan
    Write-Host "  Total tokens: $total" -ForegroundColor White
    Write-Host "  Successfully sent: $sent" -ForegroundColor White
    Write-Host ""
    
    if ($total -eq 0) {
        Write-Host "❌ No tokens registered yet" -ForegroundColor Red
        Write-Host "  Make sure you:" -ForegroundColor Yellow
        Write-Host "  1. Signed in successfully" -ForegroundColor White
        Write-Host "  2. Allowed notification permissions" -ForegroundColor White
        Write-Host "  3. Waited 10 seconds after sign-in" -ForegroundColor White
    } elseif ($sent -eq 0) {
        Write-Host "⚠️  Tokens exist but are invalid" -ForegroundColor Yellow
        Write-Host "  Try signing in again to refresh tokens" -ForegroundColor White
    } else {
        Write-Host "✅ SUCCESS! $sent token(s) are working!" -ForegroundColor Green
        Write-Host "  Push notifications should work correctly!" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Error checking tokens: $_" -ForegroundColor Red
}

Write-Host "`n"






