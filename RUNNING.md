# Running the Backend Server

## Quick Start

### Option 1: Using the run script (Recommended)
```powershell
cd back
python run_server.py
```

### Option 2: Using uvicorn directly
```powershell
cd back
python -m uvicorn app.main:app --reload
```

## Setup Check

Before running, you can check if everything is set up correctly:

```powershell
cd back
python test_setup.py
```

Or use the PowerShell setup script:

```powershell
cd back
.\check_setup.ps1
```

## Common Issues

### Issue: `ModuleNotFoundError: No module named 'bcrypt'`

**Solution:**
```powershell
cd back
python -m pip install -r requirements.txt
```

### Issue: `ImportError: attempted relative import with no known parent package`

**Solution:** Don't run `main.py` directly. Use one of these methods:
- `python run_server.py` (from the `back` directory)
- `python -m uvicorn app.main:app --reload` (from the `back` directory)

### Issue: `ERROR: Could not open requirements file`

**Solution:** Make sure you're in the `back` directory, not `back/app`:
```powershell
cd C:\projects\vila-app\back
python -m pip install -r requirements.txt
```

## Environment Variables

Make sure you have a `.env` file in the `back` directory with:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- (Optional) `FIREBASE_CREDENTIALS`
- (Optional) `OPENAI_API_KEY`

## Server Access

Once running, the server will be available at:
- http://localhost:8000
- API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc












