# PowerShell script to check and setup the backend

Write-Host "Checking backend setup..." -ForegroundColor Green
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
if (Test-Path "venv") {
    Write-Host "Virtual environment found" -ForegroundColor Green
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "No virtual environment found. Creating one..." -ForegroundColor Yellow
    python -m venv venv
    & .\venv\Scripts\Activate.ps1
}

# Install/upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing requirements..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

# Run test script
Write-Host ""
Write-Host "Running setup test..." -ForegroundColor Yellow
python test_setup.py

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To run the server:" -ForegroundColor Cyan
Write-Host "  python run_server.py" -ForegroundColor White
Write-Host "  OR" -ForegroundColor White
Write-Host "  python -m uvicorn app.main:app --reload" -ForegroundColor White












