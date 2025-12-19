"""
Authentication endpoints - login and signup
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os
import requests
import bcrypt
from dotenv import load_dotenv

load_dotenv()

def get_supabase_config():
    """Get Supabase configuration"""
    supabase_url = os.environ.get('SUPABASE_URL', '').rstrip('/')
    supabase_key = os.environ.get('SUPABASE_ANON_KEY', '')
    if not supabase_key:
        supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    return supabase_url, supabase_key

def query_users(url: str, key: str, username: str = None):
    """Query users from database"""
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }
    
    api_url = f"{url}/rest/v1/users"
    if username:
        api_url += f"?username=eq.{username}"
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error querying users: {e}")
        return []

def create_user(url: str, key: str, username: str, password: str):
    """Create a new user"""
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    data = {
        'username': username,
        'password_hash': password_hash
    }
    
    api_url = f"{url}/rest/v1/users"
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        if response.status_code == 201:
            return response.json()
        return None
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

# FastAPI routes
app = FastAPI()

@app.post("/api/auth/login")
async def login(request: dict):
    """Login endpoint"""
    username = request.get('username', '').strip()
    password = request.get('password', '').strip()
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    url, key = get_supabase_config()
    if not url or not key:
        raise HTTPException(status_code=500, detail="Database configuration error")
    
    # Find user
    users = query_users(url, key, username)
    if not users or len(users) == 0:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user = users[0]
    stored_hash = user.get('password_hash', '')
    
    # Verify password
    try:
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return {
                'status': 'success',
                'user': {
                    'id': user.get('id'),
                    'username': user.get('username')
                }
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid username or password")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid username or password")

@app.post("/api/auth/signup")
async def signup(request: dict):
    """Signup endpoint"""
    username = request.get('username', '').strip()
    password = request.get('password', '').strip()
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    url, key = get_supabase_config()
    if not url or not key:
        raise HTTPException(status_code=500, detail="Database configuration error")
    
    # Check if user exists
    existing = query_users(url, key, username)
    if existing and len(existing) > 0:
        raise HTTPException(status_code=409, detail="Username already exists")
    
    # Create user
    new_user = create_user(url, key, username, password)
    if new_user:
        return {
            'status': 'success',
            'user': {
                'id': new_user[0].get('id') if isinstance(new_user, list) else new_user.get('id'),
                'username': username
            }
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to create user")


