from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import requests
import bcrypt
import base64
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

@app.get("/")
def root():
    return {"message": "bolavila-backend API", "status": "running", "docs": "/docs"}

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

# Add /api/ prefix endpoints for frontend compatibility
@app.post("/api/auth/login")
def api_login(payload: SignInRequest):
    """Alias for /auth/signin to match frontend expectations"""
    return signin(payload)

@app.post("/api/auth/signup")
def api_signup(payload: SignUpRequest):
    """Alias for /auth/signup to match frontend expectations"""
    return signup(payload)


@app.get("/users")
def list_users():
    """
    Return system users for UI dropdowns (id + username only).
    """
    try:
        resp = requests.get(
            f"{REST_URL}/users",
            headers=SERVICE_HEADERS,
            params={"select": "id,username", "order": "username.asc"},
        )
        resp.raise_for_status()
        return resp.json() or []
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@app.get("/api/users")
def api_list_users():
    """Alias for /users to match frontend expectations"""
    return list_users()

@app.get("/orders")
def orders():
    try:
        resp = requests.get(f"{REST_URL}/orders", headers=SERVICE_HEADERS, params={"select": "*"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orders")
def api_orders():
    """Alias for /orders to match frontend expectations"""
    return orders()


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

@app.patch("/api/orders/{order_id}")
def api_update_order(order_id: str, payload: OrderUpdate):
    """Alias for /orders/{order_id} to match frontend expectations"""
    return update_order(order_id, payload)


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

@app.post("/api/orders")
def api_create_order(payload: dict):
    """Create order with frontend camelCase format"""
    # Map frontend camelCase to backend snake_case
    order_data = {
        "guest_name": payload.get("guestName", ""),
        "unit_number": payload.get("unitNumber", ""),
        "arrival_date": payload.get("arrivalDate", ""),
        "departure_date": payload.get("departureDate", ""),
        "status": payload.get("status", "חדש"),
        "guests_count": payload.get("guestsCount", 0),
        "special_requests": payload.get("specialRequests") or "",
        "internal_notes": payload.get("internalNotes") or "",
        "paid_amount": payload.get("paidAmount", 0),
        "total_amount": payload.get("totalAmount", 0),
        "payment_method": payload.get("paymentMethod", "טרם נקבע"),
    }
    
    # Create OrderCreate model from mapped data
    order_create = OrderCreate(**order_data)
    result = create_order(order_create)
    
    # Return as single object, not array
    if isinstance(result, list):
        return result[0] if result else {}
    return result


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

@app.get("/api/inventory/items")
def api_inventory_items():
    """Alias for /inventory/items to match frontend expectations"""
    return inventory_items()

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

@app.get("/api/inventory/orders")
def api_inventory_orders():
    """Alias for /inventory/orders to match frontend expectations"""
    return inventory_orders()

@app.post("/inventory/orders")
def create_inventory_order(payload: dict):
    data = payload.copy()
    if not data.get("id"):
        import time
        data["id"] = f"ORD-INV-{int(time.time() * 1000)}"
    try:
        resp = requests.post(f"{REST_URL}/inventory_orders", headers=SERVICE_HEADERS, json=data)
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return data
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:400]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating inventory order: {str(e)}")

@app.post("/api/inventory/orders")
def api_create_inventory_order(payload: dict):
    """Create inventory order with frontend camelCase format"""
    import time
    # Map frontend camelCase to backend snake_case
    order_data = {
        "id": payload.get("id") or f"ORD-INV-{int(time.time() * 1000)}",
        "item_id": payload.get("itemId") or payload.get("item_id") or "",
        "item_name": payload.get("itemName") or payload.get("item_name", ""),
        "quantity": int(payload.get("quantity", 0)),
        "unit": payload.get("unit", ""),
        "order_date": payload.get("orderDate") or payload.get("order_date", ""),
        "status": payload.get("status", "ממתין לאישור"),
        "order_type": payload.get("orderType") or payload.get("order_type", "הזמנה כללית"),
    }
    
    # Optional fields - only add if provided
    if payload.get("deliveryDate") or payload.get("delivery_date"):
        order_data["delivery_date"] = payload.get("deliveryDate") or payload.get("delivery_date")
    if payload.get("orderedBy") or payload.get("ordered_by"):
        order_data["ordered_by"] = payload.get("orderedBy") or payload.get("ordered_by")
    if payload.get("unitNumber") or payload.get("unit_number"):
        order_data["unit_number"] = payload.get("unitNumber") or payload.get("unit_number")
    
    return create_inventory_order(order_data)

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

@app.get("/api/maintenance/tasks")
def api_maintenance_tasks():
    """Alias for /maintenance/tasks to match frontend expectations"""
    return maintenance_tasks()

@app.post("/api/maintenance/tasks")
async def api_create_maintenance_task(request: Request):
    """Alias for /maintenance/tasks to match frontend expectations"""
    return await create_maintenance_task(request)

@app.post("/maintenance/tasks")
async def create_maintenance_task(request: Request):
    """
    Create a maintenance task.

    Supports both:
    - application/json (legacy)
    - multipart/form-data with optional file field `media`

    Notes:
    - Category/Priority are deprecated in the UI. If the DB still requires `priority`,
      we set a default server-side to keep inserts working.
    - Media is stored in DB in `image_uri` as a data-URI: data:<mime>;base64,<...>
      (works for both images and videos).
    """
    content_type = (request.headers.get("content-type") or "").lower()

    data: dict = {}
    media_data_uri: Optional[str] = None

    try:
        if content_type.startswith("application/json"):
            payload = await request.json()
            if isinstance(payload, dict):
                data = payload
                # If imageUri is provided in JSON payload, use it directly
                if "imageUri" in data:
                    data["image_uri"] = data.pop("imageUri")
        else:
            form = await request.form()
            data = {k: v for k, v in form.items() if k != "media"}
            media = form.get("media")
            if media is not None and hasattr(media, "filename"):
                # Starlette UploadFile-like
                filename = getattr(media, "filename", None) or "upload.bin"
                content_type = getattr(media, "content_type", None) or "application/octet-stream"
                raw = await media.read()
                b64 = base64.b64encode(raw).decode("ascii")
                media_data_uri = f"data:{content_type};base64,{b64}"
                data["image_uri"] = media_data_uri

        if not data.get("id"):
            data["id"] = str(uuid.uuid4())

        # Normalize keys for Supabase schema - map camelCase to snake_case
        if "unitId" in data:
            data["unit_id"] = data.pop("unitId")
        if "createdDate" in data:
            data["created_date"] = data.pop("createdDate")
        if "assignedTo" in data:
            assigned_value = data.pop("assignedTo")
            if assigned_value:  # Only add if not empty
                data["assigned_to"] = assigned_value

        # Remove deprecated fields from client payload (UI no longer sends these)
        data.pop("category", None)
        data.pop("priority", None)

        # Keep DB compatibility if priority is NOT NULL (default it)
        if "priority" not in data:
            data["priority"] = "בינוני"
        
        # Ensure required fields have defaults
        if "unit_id" not in data or not data["unit_id"]:
            raise HTTPException(status_code=400, detail="unit_id is required")
        if "title" not in data or not data["title"]:
            raise HTTPException(status_code=400, detail="title is required")
        if "status" not in data:
            data["status"] = "פתוח"
        if "created_date" not in data:
            from datetime import datetime
            data["created_date"] = datetime.now().strftime("%Y-%m-%d")

        resp = requests.post(f"{REST_URL}/maintenance_tasks", headers=SERVICE_HEADERS, json=data)
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return data
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:400]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating maintenance task: {str(e)}")


@app.get("/maintenance/tasks/{task_id}")
def get_maintenance_task(task_id: str):
    try:
        resp = requests.get(
            f"{REST_URL}/maintenance_tasks",
            headers=SERVICE_HEADERS,
            params={"id": f"eq.{task_id}", "select": "*"},
        )
        resp.raise_for_status()
        rows = resp.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Task not found")
        return rows[0]
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching maintenance task: {str(e)}")

@app.patch("/maintenance/tasks/{task_id}")
def update_maintenance_task(task_id: str, payload: dict):
    data = {k: v for k, v in payload.items() if v is not None}
    # Deprecated fields - ignore if sent
    data.pop("category", None)
    data.pop("priority", None)
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

@app.patch("/api/maintenance/tasks/{task_id}")
def api_update_maintenance_task(task_id: str, payload: dict):
    """Alias for /maintenance/tasks/{task_id} to match frontend expectations"""
    return update_maintenance_task(task_id, payload)

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

@app.get("/api/reports/summary")
def api_reports_summary():
    """Alias for /reports/summary to match frontend expectations"""
    return reports_summary()

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

@app.get("/api/chat/messages")
def api_chat_messages():
    """Alias for /chat/messages to match frontend expectations"""
    return chat_messages()

@app.post("/api/chat/messages")
def api_send_chat_message(payload: dict):
    """Send a chat message"""
    try:
        # Don't send id - let Supabase auto-generate it (bigint identity)
        # Don't send created_at - let Supabase use default now()
        data = {
            "sender": payload.get("sender", ""),
            "content": payload.get("content", ""),
        }
        
        if not data["sender"] or not data["content"]:
            raise HTTPException(status_code=400, detail="sender and content are required")
        
        resp = requests.post(f"{REST_URL}/chat_messages", headers=SERVICE_HEADERS, json=data)
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            result = body[0] if isinstance(body, list) and body else body
            
            # TODO: Send push notifications to all users except sender
            # This would require:
            # 1. User device tokens stored in database
            # 2. FCM/APNS setup
            # 3. Notification service integration
            # For now, frontend will handle local notifications
            
            return result
        return data
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:400]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending chat message: {str(e)}")

@app.get("/attendance/logs")
def attendance_logs():
    try:
        resp = requests.get(f"{REST_URL}/attendance_logs", headers=SERVICE_HEADERS, params={"select": "*", "order": "clock_in.desc", "limit": "50"})
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching attendance logs: {str(e)}")

@app.get("/api/attendance/logs")
def api_attendance_logs():
    """Alias for /attendance/logs to match frontend expectations"""
    return attendance_logs()

# Warehouse endpoints
@app.get("/api/warehouses")
def api_get_warehouses():
    """Get all warehouses"""
    try:
        resp = requests.get(f"{REST_URL}/warehouses", headers=SERVICE_HEADERS, params={"select": "*"})
        resp.raise_for_status()
        return resp.json() or []
    except requests.exceptions.HTTPError as e:
        # If table doesn't exist, return empty array
        if e.response and e.response.status_code == 404:
            return []
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching warehouses: {str(e)}")

@app.post("/api/warehouses")
def api_create_warehouse(payload: dict):
    """Create a warehouse"""
    try:
        data = payload
        if not data.get("id"):
            data["id"] = str(uuid.uuid4())
        resp = requests.post(f"{REST_URL}/warehouses", headers=SERVICE_HEADERS, json=data)
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating warehouse: {str(e)}")

@app.get("/api/warehouses/{warehouse_id}/items")
def api_get_warehouse_items(warehouse_id: str):
    """Get items for a warehouse"""
    try:
        resp = requests.get(
            f"{REST_URL}/warehouse_items",
            headers=SERVICE_HEADERS,
            params={"warehouse_id": f"eq.{warehouse_id}", "select": "*"}
        )
        resp.raise_for_status()
        return resp.json() or []
    except requests.exceptions.HTTPError as e:
        # If table doesn't exist, return empty array
        if e.response and e.response.status_code == 404:
            return []
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching warehouse items: {str(e)}")

@app.post("/api/warehouses/{warehouse_id}/items")
def api_create_warehouse_item(warehouse_id: str, payload: dict):
    """Create a warehouse item"""
    try:
        data = payload
        data["warehouse_id"] = warehouse_id
        if not data.get("id"):
            data["id"] = str(uuid.uuid4())
        resp = requests.post(f"{REST_URL}/warehouse_items", headers=SERVICE_HEADERS, json=data)
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating warehouse item: {str(e)}")

@app.patch("/api/warehouses/{warehouse_id}/items/{item_id}")
def api_update_warehouse_item(warehouse_id: str, item_id: str, payload: dict):
    """Update a warehouse item"""
    try:
        data = {k: v for k, v in payload.items() if v is not None}
        if not data:
            return {"message": "No changes provided"}
        headers = {**SERVICE_HEADERS, "Prefer": "return=representation"}
        resp = requests.patch(
            f"{REST_URL}/warehouse_items?id=eq.{item_id}",
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
        raise HTTPException(status_code=500, detail=f"Error updating warehouse item: {str(e)}")

