# PowerShell script to run the diagnostic
# Make sure you have Python installed and virtual environment set up

Write-Host "Running Inventory Orders Diagnostic..." -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "Using virtual environment..." -ForegroundColor Green
    .venv\Scripts\python.exe diagnose_inventory_orders.py
} elseif (Test-Path "venv\Scripts\python.exe") {
    Write-Host "Using venv..." -ForegroundColor Green
    venv\Scripts\python.exe diagnose_inventory_orders.py
} else {
    Write-Host "Virtual environment not found. Attempting to use system Python..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "If this fails, please:" -ForegroundColor Yellow
    Write-Host "1. Create virtual environment: python -m venv .venv" -ForegroundColor Yellow
    Write-Host "2. Activate it: .venv\Scripts\activate" -ForegroundColor Yellow
    Write-Host "3. Install dependencies: pip install -r requirements.txt" -ForegroundColor Yellow
    Write-Host "4. Run this script again" -ForegroundColor Yellow
    Write-Host ""
    
    # Try to find Python
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        python diagnose_inventory_orders.py
    } else {
        Write-Host "ERROR: Python not found in PATH" -ForegroundColor Red
        Write-Host "Please install Python or set up the virtual environment" -ForegroundColor Red
    }
}

