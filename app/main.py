from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import requests
import bcrypt
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .supabase_client import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

app = FastAPI(title="bolavila-backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REST_URL = f"{SUPABASE_URL}/rest/v1"
SERVICE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Prefer": "return=representation",  # Return inserted row
}

@app.get("/health")
def health():
    return {"ok": True}

# Authentication endpoints
class SignUpRequest(BaseModel):
    username: str
    password: str

class SignInRequest(BaseModel):
    username: str
    password: str

@app.post("/auth/signup")
def signup(payload: SignUpRequest):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    try:
        # Check if user already exists
        resp = requests.get(
            f"{REST_URL}/users",
            headers=SERVICE_HEADERS,
            params={"username": f"eq.{payload.username}", "select": "id"}
        )
        resp.raise_for_status()
        existing = resp.json()
        if existing and len(existing) > 0:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Hash password
        password_hash = bcrypt.hashpw(payload.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        user_data = {
            "id": str(uuid.uuid4()),
            "username": payload.username,
            "password_hash": password_hash
        }
        
        resp = requests.post(
            f"{REST_URL}/users",
            headers=SERVICE_HEADERS,
            json=user_data
        )
        resp.raise_for_status()
        
        if resp.text:
            body = resp.json()
            user = body[0] if isinstance(body, list) and body else body
        else:
            user = user_data
        
        # Return user without password hash
        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "message": "User created successfully"
        }
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.post("/auth/signin")
def signin(payload: SignInRequest):
    if not payload.username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    try:
        # Get user by username
        resp = requests.get(
            f"{REST_URL}/users",
            headers=SERVICE_HEADERS,
            params={"username": f"eq.{payload.username}", "select": "*"}
        )
        resp.raise_for_status()
        users = resp.json()
        
        if not users or len(users) == 0:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        user = users[0]
        password_hash = user.get("password_hash")
        
        if not password_hash:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Verify password
        if not bcrypt.checkpw(payload.password.encode('utf-8'), password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Return user without password hash
        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "message": "Sign in successful"
        }
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error signing in: {str(e)}")

@app.get("/orders")
def orders():
    try:
        resp = requests.get(f"{REST_URL}/orders", headers=SERVICE_HEADERS, params={"select": "*"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    paid_amount: Optional[float] = None
    payment_method: Optional[str] = None
    total_amount: Optional[float] = None
    guest_name: Optional[str] = None
    unit_number: Optional[str] = None
    arrival_date: Optional[str] = None
    departure_date: Optional[str] = None
    guests_count: Optional[int] = None
    special_requests: Optional[str] = None
    internal_notes: Optional[str] = None


@app.patch("/orders/{order_id}")
def update_order(order_id: str, payload: OrderUpdate):
    data = {k: v for k, v in payload.dict().items() if v is not None}
    if not data:
        return []
    try:
        resp = requests.patch(
            f"{REST_URL}/orders",
            headers=SERVICE_HEADERS,
            params={"id": f"eq.{order_id}"},
            json=data,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class OrderCreate(BaseModel):
    id: Optional[str] = None
    guest_name: str
    unit_number: str
    arrival_date: str
    departure_date: str
    status: str
    guests_count: int = 0
    special_requests: Optional[str] = None
    internal_notes: Optional[str] = None
    paid_amount: float = 0
    total_amount: float = 0
    payment_method: Optional[str] = None


@app.post("/orders")
def create_order(payload: OrderCreate):
    data = payload.dict()
    if not data.get("id"):
        data["id"] = str(uuid.uuid4())
    try:
        resp = requests.post(
            f"{REST_URL}/orders",
            headers=SERVICE_HEADERS,
            json=data,
        )
        resp.raise_for_status()
        # Supabase returns the inserted row(s) as a list
        if resp.text:
            body = resp.json()
            if isinstance(body, list) and body:
                return body[0]
            return body
        # If empty response, return the data we sent (insert was successful)
        return data
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating order: {str(e)}")


@app.delete("/orders/{order_id}")
def delete_order(order_id: str):
    try:
        resp = requests.delete(
            f"{REST_URL}/orders",
            headers=SERVICE_HEADERS,
            params={"id": f"eq.{order_id}"},
        )
        resp.raise_for_status()
        return JSONResponse(content=resp.json() or [], status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/inspections")
def inspections():
    try:
        resp = requests.get(f"{REST_URL}/inspections", headers=SERVICE_HEADERS, params={"select": "*"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching inspections: {str(e)}")

@app.get("/inventory/items")
def inventory_items():
    try:
        resp = requests.get(f"{REST_URL}/inventory_items", headers=SERVICE_HEADERS, params={"select": "*"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching inventory items: {str(e)}")

@app.post("/inventory/items")
def create_inventory_item(payload: dict):
    data = payload
    if not data.get("id"):
        data["id"] = str(uuid.uuid4())
    try:
        resp = requests.post(f"{REST_URL}/inventory_items", headers=SERVICE_HEADERS, json=data)
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating inventory item: {str(e)}")

@app.patch("/inventory/items/{item_id}")
def update_inventory_item(item_id: str, payload: dict):
    data = {k: v for k, v in payload.items() if v is not None}
    if not data:
        return {"message": "No changes provided"}
    try:
        # Use Prefer header to return updated row
        headers = {**SERVICE_HEADERS, "Prefer": "return=representation"}
        resp = requests.patch(
            f"{REST_URL}/inventory_items?id=eq.{item_id}",
            headers=headers,
            json=data
        )
        resp.raise_for_status()
        if resp.text:
            result = resp.json()
            return result[0] if isinstance(result, list) and result else result
        return {"id": item_id, "message": "Updated successfully"}
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating inventory item: {str(e)}")

@app.delete("/inventory/items/{item_id}")
def delete_inventory_item(item_id: str):
    try:
        resp = requests.delete(
            f"{REST_URL}/inventory_items?id=eq.{item_id}",
            headers=SERVICE_HEADERS
        )
        resp.raise_for_status()
        return JSONResponse(content=[], status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting inventory item: {str(e)}")

@app.get("/inventory/orders")
def inventory_orders():
    try:
        resp = requests.get(f"{REST_URL}/inventory_orders", headers=SERVICE_HEADERS, params={"select": "*"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching inventory orders: {str(e)}")

@app.post("/inventory/orders")
def create_inventory_order(payload: dict):
    data = payload
    if not data.get("id"):
        data["id"] = str(uuid.uuid4())
    try:
        resp = requests.post(f"{REST_URL}/inventory_orders", headers=SERVICE_HEADERS, json=data)
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating inventory order: {str(e)}")

@app.patch("/inventory/orders/{order_id}")
def update_inventory_order(order_id: str, payload: dict):
    data = {k: v for k, v in payload.items() if v is not None}
    if not data:
        return []
    try:
        resp = requests.patch(
            f"{REST_URL}/inventory_orders?id=eq.{order_id}",
            headers=SERVICE_HEADERS,
            json=data
        )
        resp.raise_for_status()
        return resp.json() if resp.text else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating inventory order: {str(e)}")

@app.delete("/inventory/orders/{order_id}")
def delete_inventory_order(order_id: str):
    try:
        resp = requests.delete(
            f"{REST_URL}/inventory_orders?id=eq.{order_id}",
            headers=SERVICE_HEADERS
        )
        resp.raise_for_status()
        return JSONResponse(content=[], status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting inventory order: {str(e)}")

@app.get("/maintenance/tasks")
def maintenance_tasks():
    try:
        resp = requests.get(f"{REST_URL}/maintenance_tasks", headers=SERVICE_HEADERS, params={"select": "*", "order": "created_date.desc"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching maintenance tasks: {str(e)}")

@app.post("/maintenance/tasks")
def create_maintenance_task(payload: dict):
    data = payload
    if not data.get("id"):
        data["id"] = str(uuid.uuid4())
    try:
        resp = requests.post(f"{REST_URL}/maintenance_tasks", headers=SERVICE_HEADERS, json=data)
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating maintenance task: {str(e)}")

@app.patch("/maintenance/tasks/{task_id}")
def update_maintenance_task(task_id: str, payload: dict):
    data = {k: v for k, v in payload.items() if v is not None}
    if not data:
        return {"message": "No changes provided"}
    try:
        headers = {**SERVICE_HEADERS, "Prefer": "return=representation"}
        resp = requests.patch(
            f"{REST_URL}/maintenance_tasks?id=eq.{task_id}",
            headers=headers,
            json=data
        )
        resp.raise_for_status()
        if resp.text:
            result = resp.json()
            return result[0] if isinstance(result, list) and result else result
        return {"id": task_id, "message": "Updated successfully"}
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating maintenance task: {str(e)}")

@app.delete("/maintenance/tasks/{task_id}")
def delete_maintenance_task(task_id: str):
    try:
        resp = requests.delete(
            f"{REST_URL}/maintenance_tasks?id=eq.{task_id}",
            headers=SERVICE_HEADERS
        )
        resp.raise_for_status()
        return JSONResponse(content=[], status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting maintenance task: {str(e)}")

@app.get("/reports/summary")
def reports_summary():
    try:
        orders_resp = requests.get(f"{REST_URL}/orders", headers=SERVICE_HEADERS, params={"select": "total_amount,paid_amount"})
        orders_resp.raise_for_status()
        orders = orders_resp.json() or []
        
        expenses_resp = requests.get(f"{REST_URL}/expenses", headers=SERVICE_HEADERS, params={"select": "amount"})
        expenses_resp.raise_for_status()
        expenses = expenses_resp.json() or []
        
        total_revenue = sum((o.get("total_amount") or 0) for o in orders)
        total_paid = sum((o.get("paid_amount") or 0) for o in orders)
        total_expenses = sum((e.get("amount") or 0) for e in expenses)
        return {"totalRevenue": total_revenue, "totalPaid": total_paid, "totalExpenses": total_expenses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reports summary: {str(e)}")

@app.get("/invoices")
def invoices():
    try:
        resp = requests.get(f"{REST_URL}/invoices", headers=SERVICE_HEADERS, params={"select": "*"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching invoices: {str(e)}")

@app.get("/chat/messages")
def chat_messages():
    try:
        resp = requests.get(f"{REST_URL}/chat_messages", headers=SERVICE_HEADERS, params={"select": "*", "order": "created_at.desc", "limit": "50"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chat messages: {str(e)}")

@app.get("/attendance/logs")
def attendance_logs():
    try:
        resp = requests.get(f"{REST_URL}/attendance_logs", headers=SERVICE_HEADERS, params={"select": "*", "order": "clock_in.desc", "limit": "50"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching attendance logs: {str(e)}")

