# PowerShell script to run the backend locally

Write-Host "`n=== Running Backend Locally ===" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "requirements.txt")) {
    Write-Host "ERROR: requirements.txt not found!" -ForegroundColor Red
    Write-Host "Please run this script from the 'back' directory" -ForegroundColor Yellow
    exit 1
}

# Check if Python is available
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.8 or higher" -ForegroundColor Yellow
    exit 1
}

Write-Host "Python found: $($python.Version)" -ForegroundColor Green

# Check if virtual environment exists
if (Test-Path ".venv") {
    Write-Host "Virtual environment found" -ForegroundColor Green
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
} elseif (Test-Path "venv") {
    Write-Host "Virtual environment found (venv)" -ForegroundColor Green
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "No virtual environment found. Creating one..." -ForegroundColor Yellow
    python -m venv .venv
    & .\.venv\Scripts\Activate.ps1
    Write-Host "Installing requirements..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
}

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "`n⚠️  WARNING: .env file not found!" -ForegroundColor Yellow
    Write-Host "Creating .env template..." -ForegroundColor Yellow
    @"
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
PORT=4000
# Optional:
# FIREBASE_CREDENTIALS={"type":"service_account",...}
# OPENAI_API_KEY=your-openai-key
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "Please edit .env file with your credentials!" -ForegroundColor Red
    Write-Host "Press Enter to continue anyway, or Ctrl+C to cancel..." -ForegroundColor Yellow
    Read-Host
}

Write-Host "`nStarting server on http://localhost:4000" -ForegroundColor Green
Write-Host "API docs: http://localhost:4000/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

# Run the server
python run_server.py









