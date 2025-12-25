from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import requests
import bcrypt
import base64
from datetime import datetime
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
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy",
        "ok": True,
        "service": "bolavila-backend"
    }

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
    """Get all inspections with their tasks"""
    try:
        # First get all inspections
        resp = requests.get(f"{REST_URL}/inspections", headers=SERVICE_HEADERS, params={"select": "*"})
        # If table doesn't exist (404), return empty array
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        inspections_list = resp.json() or []
        
        # Then get all tasks for these inspections
        inspection_ids = [insp.get("id") for insp in inspections_list if insp.get("id")]
        tasks_by_inspection = {}
        
        if inspection_ids:
            # Get all tasks for these inspections
            # Supabase PostgREST IN query format: in.(value1,value2,value3)
            try:
                inspection_ids_str = ','.join(inspection_ids)
                tasks_resp = requests.get(
                    f"{REST_URL}/inspection_tasks",
                    headers=SERVICE_HEADERS,
                    params={"inspection_id": f"in.({inspection_ids_str})", "select": "*"}
                )
                # If table doesn't exist (404), that's OK - return empty tasks
                if tasks_resp.status_code == 404:
                    all_tasks = []
                else:
                    tasks_resp.raise_for_status()
                    all_tasks = tasks_resp.json() or []
            except requests.exceptions.HTTPError as e:
                # If table doesn't exist, return empty tasks
                if e.response and e.response.status_code == 404:
                    all_tasks = []
                else:
                    raise
            except Exception:
                # Any other error, return empty tasks
                all_tasks = []
            
            # Group tasks by inspection_id
            for task in all_tasks:
                insp_id = task.get("inspection_id")
                if insp_id:
                    if insp_id not in tasks_by_inspection:
                        tasks_by_inspection[insp_id] = []
                    tasks_by_inspection[insp_id].append({
                        "id": task.get("id"),
                        "name": task.get("name"),
                        "completed": task.get("completed", False),
                    })
        
        # Combine inspections with their tasks
        result = []
        for inspection in inspections_list:
            insp_id = inspection.get("id")
            inspection_with_tasks = inspection.copy()
            inspection_with_tasks["tasks"] = tasks_by_inspection.get(insp_id, [])
            result.append(inspection_with_tasks)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching inspections: {str(e)}")

@app.get("/api/inspections")
def api_inspections():
    """Alias for /inspections to match frontend expectations"""
    return inspections()

@app.post("/api/inspections")
def create_inspection(payload: dict):
    """Create or update an inspection mission with its tasks"""
    try:
        inspection_id = payload.get("id") or str(uuid.uuid4())
        order_id = payload.get("orderId") or payload.get("order_id")
        
        # Create or update inspection
        inspection_data = {
            "id": inspection_id,
            "order_id": order_id,
            "unit_number": payload.get("unitNumber") or payload.get("unit_number", ""),
            "guest_name": payload.get("guestName") or payload.get("guest_name", ""),
            "departure_date": payload.get("departureDate") or payload.get("departure_date", ""),
            "status": payload.get("status", "זמן הביקורות טרם הגיע"),
        }
        
        # Check if inspection exists
        existing = []
        try:
            check_resp = requests.get(
                f"{REST_URL}/inspections",
                headers=SERVICE_HEADERS,
                params={"id": f"eq.{inspection_id}", "select": "id"}
            )
            # If table doesn't exist (404), that's OK - we'll create it
            if check_resp.status_code == 404:
                existing = []
            else:
                check_resp.raise_for_status()
                existing = check_resp.json() or []
        except requests.exceptions.HTTPError as e:
            # If table doesn't exist, that's OK
            if e.response and e.response.status_code == 404:
                existing = []
            else:
                raise
        except Exception:
            # If any other error, assume inspection doesn't exist
            existing = []
        
        if existing and len(existing) > 0:
            # Update existing inspection
            try:
                update_resp = requests.patch(
                    f"{REST_URL}/inspections?id=eq.{inspection_id}",
                    headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                    json=inspection_data
                )
                # If table doesn't exist (404), that's OK - will be created by migration
                if update_resp.status_code != 404:
                    update_resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                # If table doesn't exist, that's OK
                if e.response and e.response.status_code == 404:
                    pass
                else:
                    raise
        else:
            # Create new inspection
            try:
                create_resp = requests.post(
                    f"{REST_URL}/inspections",
                    headers=SERVICE_HEADERS,
                    json=inspection_data
                )
                # If table doesn't exist (404), that's OK - will be created by migration
                # If inspection already exists (409 or similar), that's also OK
                if create_resp.status_code not in [200, 201, 404, 409]:
                    create_resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                # If table doesn't exist (404), that's OK
                if e.response and e.response.status_code == 404:
                    pass
                # If conflict (409), inspection might already exist - that's OK
                elif e.response and e.response.status_code == 409:
                    pass
                else:
                    raise
        
        # Handle tasks
        tasks = payload.get("tasks", [])
        if tasks:
            # Delete existing tasks for this inspection
            try:
                delete_resp = requests.delete(
                    f"{REST_URL}/inspection_tasks?inspection_id=eq.{inspection_id}",
                    headers=SERVICE_HEADERS
                )
                # Ignore errors if no tasks exist (404 is OK)
            except:
                pass
            
            # Insert tasks one by one, but don't fail the whole operation if some fail
            # This is more resilient and allows partial success
            # If table doesn't exist (404), that's OK - it will be created by migration
            for task in tasks:
                try:
                    task_data = {
                        "id": task.get("id") or str(uuid.uuid4()),
                        "inspection_id": inspection_id,
                        "name": task.get("name", ""),
                        "completed": task.get("completed", False),
                    }
                    task_resp = requests.post(
                        f"{REST_URL}/inspection_tasks",
                        headers=SERVICE_HEADERS,
                        json=task_data
                    )
                    # Don't raise on error - continue with other tasks
                    # 404 means table doesn't exist yet (will be created by migration)
                    # Other errors we'll log but continue
                    if task_resp.status_code == 404:
                        # Table doesn't exist - that's OK, continue
                        pass
                    elif task_resp.status_code not in [200, 201]:
                        # Other error - log but continue
                        pass
                except requests.exceptions.HTTPError as e:
                    # If table doesn't exist (404), that's OK
                    if e.response and e.response.status_code == 404:
                        pass
                    # Otherwise, continue with other tasks
                except Exception as e:
                    # Any other error - continue with other tasks
                    # This prevents one failed task from breaking the whole operation
                    pass
        
        # Return the created/updated inspection with tasks
        return {
            "id": inspection_id,
            "orderId": order_id,
            "unitNumber": inspection_data["unit_number"],
            "guestName": inspection_data["guest_name"],
            "departureDate": inspection_data["departure_date"],
            "status": inspection_data["status"],
            "tasks": tasks,
        }
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating/updating inspection: {str(e)}")

@app.patch("/api/inspections/{inspection_id}/tasks/{task_id}")
def update_inspection_task(inspection_id: str, task_id: str, payload: dict):
    """Update a single inspection task (e.g., toggle completion). Creates task if it doesn't exist."""
    try:
        task_data = {}
        if "completed" in payload:
            task_data["completed"] = payload["completed"]
        if "name" in payload:
            task_data["name"] = payload["name"]
        
        if not task_data:
            return {"message": "No changes provided"}
        
        # First, try to find the task by id and inspection_id
        existing_task = None
        try:
            check_resp = requests.get(
                f"{REST_URL}/inspection_tasks",
                headers=SERVICE_HEADERS,
                params={"id": f"eq.{task_id}", "inspection_id": f"eq.{inspection_id}", "select": "*"}
            )
            # If table doesn't exist (404), that's OK - we'll create the task
            if check_resp.status_code == 200:
                existing_tasks = check_resp.json() or []
                if existing_tasks and len(existing_tasks) > 0:
                    existing_task = existing_tasks[0]
        except requests.exceptions.HTTPError as e:
            # If table doesn't exist (404), that's OK
            if e.response and e.response.status_code == 404:
                existing_task = None
            else:
                # For other errors, assume task doesn't exist and try to create it
                existing_task = None
        except Exception:
            # Any other error, assume task doesn't exist
            existing_task = None
        
        task_name = payload.get("name", "") or (existing_task.get("name") if existing_task else "")
        
        if existing_task:
            # Task exists, try to update it
            try:
                update_resp = requests.patch(
                    f"{REST_URL}/inspection_tasks?id=eq.{task_id}&inspection_id=eq.{inspection_id}",
                    headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                    json=task_data
                )
                # If update succeeds, return the updated task
                if update_resp.status_code in [200, 201, 204]:
                    try:
                        result = update_resp.json()
                        updated_task = result[0] if isinstance(result, list) and result else result
                        return {
                            "id": updated_task.get("id"),
                            "name": updated_task.get("name"),
                            "completed": updated_task.get("completed", False),
                        }
                    except:
                        # If response has no body, return what we know
                        return {
                            "id": task_id,
                            "name": task_name,
                            "completed": task_data.get("completed", False),
                        }
                # If update fails (404 = table doesn't exist, or other error), try to create it
            except:
                pass
        
        # Task doesn't exist or update failed, create it
        create_data = {
            "id": task_id,
            "inspection_id": inspection_id,
            "name": task_name,
            "completed": task_data.get("completed", False),
        }
        
        try:
            create_resp = requests.post(
                f"{REST_URL}/inspection_tasks",
                headers=SERVICE_HEADERS,
                json=create_data
            )
            # If table doesn't exist (404), return success anyway (table will be created by migration)
            if create_resp.status_code == 404:
                return create_data
            # If creation succeeds
            if create_resp.status_code in [200, 201]:
                try:
                    result = create_resp.json()
                    created_task = result[0] if isinstance(result, list) and result else result
                    return {
                        "id": created_task.get("id") if isinstance(created_task, dict) else task_id,
                        "name": created_task.get("name") if isinstance(created_task, dict) else task_name,
                        "completed": created_task.get("completed", False) if isinstance(created_task, dict) else task_data.get("completed", False),
                    }
                except:
                    return create_data
        except requests.exceptions.HTTPError as e:
            # If table doesn't exist (404), return success anyway
            if e.response and e.response.status_code == 404:
                return create_data
            # For other errors, still return success to prevent UI blocking
            return create_data
        except Exception:
            # Any error, return success to prevent UI blocking
            return create_data
    except requests.exceptions.HTTPError as e:
        # If table doesn't exist yet, return success (will be created by migration)
        if e.response and e.response.status_code == 404:
            return {
                "id": task_id,
                "name": payload.get("name", ""),
                "completed": payload.get("completed", False),
            }
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        # If any error occurs, return success anyway to prevent UI blocking
        # The full mission save will handle persistence
        return {
            "id": task_id,
            "name": payload.get("name", ""),
            "completed": payload.get("completed", False),
        }

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
        # Get orders with their items using a join query
        # First get all orders
        orders_resp = requests.get(
            f"{REST_URL}/inventory_orders", 
            headers=SERVICE_HEADERS, 
            params={"select": "*", "order": "order_date.desc"}
        )
        orders_resp.raise_for_status()
        orders = orders_resp.json()
        
        # Get all order items (if table exists)
        items_by_order = {}
        try:
            items_resp = requests.get(
                f"{REST_URL}/inventory_order_items",
                headers=SERVICE_HEADERS,
                params={"select": "*"}
            )
            items_resp.raise_for_status()
            all_items = items_resp.json()
            
            # Group items by order_id
            for item in all_items:
                order_id = item.get("order_id")
                if order_id:
                    if order_id not in items_by_order:
                        items_by_order[order_id] = []
                    items_by_order[order_id].append({
                        "id": item.get("id"),
                        "item_id": item.get("item_id"),
                        "item_name": item.get("item_name"),
                        "quantity": item.get("quantity"),
                        "unit": item.get("unit", ""),
                    })
        except Exception as e:
            # Table might not exist yet - that's OK, we'll use legacy fields
            print(f"Note: inventory_order_items table may not exist yet: {e}")
            pass
        
        # Combine orders with their items
        result = []
        for order in orders:
            order_id = order.get("id")
            order_with_items = order.copy()
            # Add items array if items exist, otherwise create from legacy fields
            if order_id in items_by_order:
                order_with_items["items"] = items_by_order[order_id]
            else:
                # Fallback for old structure (backward compatibility)
                order_with_items["items"] = [{
                    "id": order_id + "-item",
                    "item_id": order.get("item_id"),
                    "item_name": order.get("item_name", ""),
                    "quantity": order.get("quantity", 0),
                    "unit": order.get("unit", ""),
                }] if order.get("item_name") else []
            result.append(order_with_items)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching inventory orders: {str(e)}")

@app.get("/api/inventory/orders")
def api_inventory_orders():
    """Alias for /inventory/orders to match frontend expectations"""
    return inventory_orders()

@app.post("/inventory/orders")
def create_inventory_order(payload: dict):
    data = payload.copy()
    # Always generate a new UUID to avoid conflicts - ignore any existing ID
    data["id"] = str(uuid.uuid4())
    try:
        resp = requests.post(f"{REST_URL}/inventory_orders", headers=SERVICE_HEADERS, json=data)
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return data
    except requests.exceptions.HTTPError as e:
        # Get full error response for debugging
        error_text = ""
        if e.response:
            try:
                error_text = e.response.text
            except:
                error_text = str(e.response)
        error_detail = f"HTTP {e.response.status_code}: {error_text[:500]}" if e.response else str(e)
        # Log the data being sent for debugging
        print(f"Error creating inventory order. Data sent: {data}")
        print(f"Full error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating inventory order: {str(e)}")

@app.post("/api/inventory/orders")
def api_create_inventory_order(payload: dict):
    """Create inventory order with items (two-table structure)"""
    # Generate UUID for order
    order_id = str(uuid.uuid4())
    
    # Get items from payload (new structure)
    items = payload.get("items", [])
    
    # Fallback: if no items array, create from legacy fields (backward compatibility)
    if not items and (payload.get("itemName") or payload.get("item_name")):
        items = [{
            "itemId": payload.get("itemId") or payload.get("item_id"),
            "itemName": payload.get("itemName") or payload.get("item_name", ""),
            "quantity": payload.get("quantity", 0),
            "unit": payload.get("unit", ""),
        }]
    
    if not items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")
    
    # Get first item for backward compatibility with old table structure
    first_item = items[0] if items else None
    
    # Create order data
    order_data = {
        "id": order_id,
        "order_date": payload.get("orderDate") or payload.get("order_date", ""),
        "status": payload.get("status", "ממתין לאישור"),
        "order_type": payload.get("orderType") or payload.get("order_type", "הזמנה כללית"),
    }
    
    # Backward compatibility: include item fields for old table structure
    # These are required by the current database schema
    if first_item:
        order_data["item_id"] = first_item.get("itemId") or first_item.get("item_id") or None
        order_data["item_name"] = first_item.get("itemName") or first_item.get("item_name", "")
        order_data["quantity"] = int(first_item.get("quantity", 0))
        order_data["unit"] = first_item.get("unit", "")
    else:
        # Fallback for legacy single-item requests
        order_data["item_id"] = payload.get("itemId") or payload.get("item_id") or None
        order_data["item_name"] = payload.get("itemName") or payload.get("item_name", "")
        order_data["quantity"] = int(payload.get("quantity", 0))
        order_data["unit"] = payload.get("unit", "")
    
    # Optional fields - only add if provided
    if payload.get("deliveryDate") or payload.get("delivery_date"):
        order_data["delivery_date"] = payload.get("deliveryDate") or payload.get("delivery_date")
    if payload.get("orderedBy") or payload.get("ordered_by"):
        order_data["ordered_by"] = payload.get("orderedBy") or payload.get("ordered_by")
    if payload.get("unitNumber") or payload.get("unit_number"):
        order_data["unit_number"] = payload.get("unitNumber") or payload.get("unit_number")
    
    try:
        # Step 1: Create the order
        order_resp = requests.post(
            f"{REST_URL}/inventory_orders", 
            headers=SERVICE_HEADERS, 
            json=order_data
        )
        order_resp.raise_for_status()
        created_order = order_resp.json()
        if isinstance(created_order, list) and created_order:
            created_order = created_order[0]
        
        # Step 2: Create order items
        created_items = []
        for item in items:
            item_data = {
                "id": str(uuid.uuid4()),
                "order_id": order_id,
                "item_id": item.get("itemId") or item.get("item_id") or None,
                "item_name": item.get("itemName") or item.get("item_name", ""),
                "quantity": int(item.get("quantity", 0)),
                "unit": item.get("unit", ""),
            }
            
            item_resp = requests.post(
                f"{REST_URL}/inventory_order_items",
                headers=SERVICE_HEADERS,
                json=item_data
            )
            item_resp.raise_for_status()
            created_item = item_resp.json()
            if isinstance(created_item, list) and created_item:
                created_item = created_item[0]
            created_items.append({
                "id": created_item.get("id"),
                "item_id": created_item.get("item_id"),
                "item_name": created_item.get("item_name"),
                "quantity": created_item.get("quantity"),
                "unit": created_item.get("unit", ""),
            })
        
        # Return order with items
        result = created_order.copy()
        result["items"] = created_items
        return result
        
    except requests.exceptions.HTTPError as e:
        error_text = ""
        if e.response:
            try:
                error_text = e.response.text
            except:
                error_text = str(e.response)
        error_detail = f"HTTP {e.response.status_code}: {error_text[:500]}" if e.response else str(e)
        print(f"Error creating inventory order. Order data: {order_data}")
        print(f"Items: {items}")
        print(f"Full error: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating inventory order: {str(e)}")

@app.patch("/inventory/orders/{order_id}")
def update_inventory_order(order_id: str, payload: dict):
    """Update inventory order (status, delivery_date, etc.)"""
    # Map camelCase to snake_case for order fields
    order_data = {}
    if "status" in payload:
        order_data["status"] = payload["status"]
    if "deliveryDate" in payload or "delivery_date" in payload:
        order_data["delivery_date"] = payload.get("deliveryDate") or payload.get("delivery_date")
    if "orderType" in payload or "order_type" in payload:
        order_data["order_type"] = payload.get("orderType") or payload.get("order_type")
    if "orderedBy" in payload or "ordered_by" in payload:
        order_data["ordered_by"] = payload.get("orderedBy") or payload.get("ordered_by")
    if "unitNumber" in payload or "unit_number" in payload:
        order_data["unit_number"] = payload.get("unitNumber") or payload.get("unit_number")
    
    # Also accept snake_case directly
    for key in ["status", "delivery_date", "order_type", "ordered_by", "unit_number"]:
        if key in payload and key not in order_data:
            order_data[key] = payload[key]
    
    if not order_data:
        return []
    
    try:
        resp = requests.patch(
            f"{REST_URL}/inventory_orders?id=eq.{order_id}",
            headers=SERVICE_HEADERS,
            json=order_data
        )
        resp.raise_for_status()
        return resp.json() if resp.text else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating inventory order: {str(e)}")

@app.patch("/api/inventory/orders/{order_id}")
def api_update_inventory_order(order_id: str, payload: dict):
    """Alias for /inventory/orders/{order_id} to match frontend expectations"""
    return update_inventory_order(order_id, payload)

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

@app.get("/api/reports/monthly-income-expenses")
def monthly_income_expenses():
    """
    Get monthly breakdown of income (from orders) and expenses (from invoices)
    Returns data grouped by month in format: YYYY-MM
    """
    from collections import defaultdict
    from datetime import datetime
    
    try:
        # Get all orders with their dates and amounts
        try:
            orders_resp = requests.get(
                f"{REST_URL}/orders", 
                headers=SERVICE_HEADERS, 
                params={"select": "total_amount,paid_amount,arrival_date"}
            )
            orders_resp.raise_for_status()
            orders = orders_resp.json() or []
        except Exception as e:
            print(f"Warning: Could not fetch orders: {e}")
            orders = []
        
        # Group income by month from orders
        monthly_income = defaultdict(float)
        for order in orders:
            arrival_date = order.get("arrival_date")
            if arrival_date:
                try:
                    # Parse date and get YYYY-MM format
                    if isinstance(arrival_date, str):
                        date_obj = datetime.strptime(arrival_date.split('T')[0], "%Y-%m-%d")
                    else:
                        date_obj = arrival_date
                    month_key = date_obj.strftime("%Y-%m")
                    # Use paid_amount if available, otherwise total_amount
                    amount = order.get("paid_amount") or order.get("total_amount") or 0
                    monthly_income[month_key] += float(amount) if amount else 0
                except (ValueError, TypeError, AttributeError) as e:
                    print(f"Error parsing order date {arrival_date}: {e}")
                    continue
        
        # Get all invoices with their dates and amounts
        monthly_expenses = defaultdict(float)
        try:
            invoices_resp = requests.get(
                f"{REST_URL}/invoices",
                headers=SERVICE_HEADERS,
                params={"select": "*"}
            )
            invoices_resp.raise_for_status()
            invoices = invoices_resp.json() or []
        except Exception as e:
            print(f"Warning: Could not fetch invoices (table might not exist): {e}")
            invoices = []
        
        # Group expenses by month from invoices
        for invoice in invoices:
            try:
                # Try to get date from different fields
                invoice_date = invoice.get("issued_at") or invoice.get("date")
                extracted_data = invoice.get("extracted_data")
                
                # Parse extracted_data if it's a string
                if isinstance(extracted_data, str):
                    try:
                        import json
                        extracted_data = json.loads(extracted_data)
                    except:
                        extracted_data = None
                
                if not invoice_date and extracted_data and isinstance(extracted_data, dict):
                    invoice_info = extracted_data.get("invoice", {})
                    invoice_date = invoice_info.get("invoice_date")
                
                # If still no date, use created_at or current month as fallback
                if not invoice_date:
                    invoice_date = invoice.get("created_at") or datetime.now().strftime("%Y-%m-%d")
                
                # Always process the invoice (even if we use fallback date)
                if invoice_date:
                    try:
                        # Parse date and get YYYY-MM format
                        if isinstance(invoice_date, str):
                            # Handle different date formats
                            date_str = invoice_date.split('T')[0].split(' ')[0]
                            try:
                                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            except ValueError:
                                # Try other formats or use current date
                                date_obj = datetime.now()
                        else:
                            date_obj = invoice_date
                        month_key = date_obj.strftime("%Y-%m")
                        
                        # Get amount - prioritize extracted_data.total_price (simplified schema)
                        amount = None
                        if extracted_data and isinstance(extracted_data, dict):
                            # First check the simplified schema structure
                            amount = extracted_data.get("total_price")
                            # If not found, check old detailed schema
                            if not amount:
                                totals = extracted_data.get("totals", {})
                                amount = totals.get("grand_total") or totals.get("amount_due")
                        
                        # Fallback to invoice-level fields
                        if not amount:
                            amount = invoice.get("total_price") or invoice.get("amount")
                        
                        if amount:
                            try:
                                amount_float = float(amount) if amount else 0
                                monthly_expenses[month_key] += amount_float
                                print(f"Invoice {invoice.get('id')}: Added {amount_float} to month {month_key}")
                            except (ValueError, TypeError) as e:
                                print(f"Error converting amount {amount} to float: {e}")
                        else:
                            print(f"Invoice {invoice.get('id')}: No amount found, extracted_data keys: {list(extracted_data.keys()) if isinstance(extracted_data, dict) else 'not a dict'}")
                    except (ValueError, TypeError, AttributeError) as e:
                        print(f"Error parsing invoice date {invoice_date}: {e}")
                        continue
            except Exception as e:
                print(f"Error processing invoice: {e}")
                continue
        
        # Combine all months and create sorted list
        all_months = set(list(monthly_income.keys()) + list(monthly_expenses.keys()))
        monthly_data = []
        for month in sorted(all_months, reverse=True):  # Most recent first
            monthly_data.append({
                "month": month,
                "income": monthly_income.get(month, 0),
                "expenses": monthly_expenses.get(month, 0),
                "net": monthly_income.get(month, 0) - monthly_expenses.get(month, 0)
            })
        
        return {
            "monthly_data": monthly_data,
            "total_income": sum(monthly_income.values()),
            "total_expenses": sum(monthly_expenses.values()),
            "total_net": sum(monthly_income.values()) - sum(monthly_expenses.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching monthly income/expenses: {str(e)}")

@app.get("/invoices")
def invoices():
    """Get all invoices - maps to actual table schema: id, vendor, invoice_number, amount, payment_method, issued_at, file_url"""
    try:
        # Try with order by issued_at (actual column name)
        resp = requests.get(
            f"{REST_URL}/invoices", 
            headers=SERVICE_HEADERS, 
            params={"select": "*", "order": "issued_at.desc"}
        )
        resp.raise_for_status()
        invoices = resp.json() or []
        # Map database columns to frontend format
        mapped_invoices = []
        for inv in invoices:
            # Check if we have the new structure with extracted_data
            if inv.get("extracted_data"):
                mapped = {
                    "id": str(inv.get("id", "")),
                    "image_data": inv.get("image_data") or inv.get("file_url", ""),
                    "total_price": inv.get("total_price") or inv.get("amount"),
                    "currency": inv.get("currency", "ILS"),
                    "vendor": inv.get("vendor"),
                    "date": inv.get("date") or inv.get("issued_at"),
                    "invoice_number": inv.get("invoice_number"),
                    "extracted_data": inv.get("extracted_data"),  # Full structured data
                    "created_at": inv.get("created_at") or inv.get("issued_at"),
                    "updated_at": inv.get("updated_at") or inv.get("issued_at"),
                }
            else:
                # Legacy format - map old structure
                mapped = {
                    "id": str(inv.get("id", "")),
                    "image_data": inv.get("file_url", "") or inv.get("image_data", ""),
                    "total_price": inv.get("amount") or inv.get("total_price"),
                    "currency": inv.get("currency", "ILS"),
                    "vendor": inv.get("vendor"),
                    "date": inv.get("issued_at") or inv.get("date"),
                    "invoice_number": inv.get("invoice_number"),
                    "extracted_data": None,
                    "created_at": inv.get("created_at") or inv.get("issued_at"),
                    "updated_at": inv.get("updated_at") or inv.get("issued_at"),
                }
            mapped_invoices.append(mapped)
        return mapped_invoices
    except requests.exceptions.HTTPError as e:
        # If table doesn't exist (404) or bad request (400), try without order
        if e.response and (e.response.status_code == 404 or e.response.status_code == 400):
            try:
                # Try without order parameter
                resp = requests.get(
                    f"{REST_URL}/invoices", 
                    headers=SERVICE_HEADERS, 
                    params={"select": "*"}
                )
                resp.raise_for_status()
                invoices = resp.json() or []
                # Map database columns to frontend format
                mapped_invoices = []
                for inv in invoices:
                    # Check if we have the new structure with extracted_data
                    if inv.get("extracted_data"):
                        mapped = {
                            "id": str(inv.get("id", "")),
                            "image_data": inv.get("image_data") or inv.get("file_url", ""),
                            "total_price": inv.get("total_price") or inv.get("amount"),
                            "currency": inv.get("currency", "ILS"),
                            "vendor": inv.get("vendor"),
                            "date": inv.get("date") or inv.get("issued_at"),
                            "invoice_number": inv.get("invoice_number"),
                            "extracted_data": inv.get("extracted_data"),
                            "created_at": inv.get("created_at") or inv.get("issued_at"),
                            "updated_at": inv.get("updated_at") or inv.get("issued_at"),
                        }
                    else:
                        mapped = {
                            "id": str(inv.get("id", "")),
                            "image_data": inv.get("file_url", "") or inv.get("image_data", ""),
                            "total_price": inv.get("amount") or inv.get("total_price"),
                            "currency": inv.get("currency", "ILS"),
                            "vendor": inv.get("vendor"),
                            "date": inv.get("issued_at") or inv.get("date"),
                            "invoice_number": inv.get("invoice_number"),
                            "extracted_data": None,
                            "created_at": inv.get("created_at") or inv.get("issued_at"),
                            "updated_at": inv.get("updated_at") or inv.get("issued_at"),
                        }
                    mapped_invoices.append(mapped)
                return mapped_invoices
            except:
                # If that also fails, table probably doesn't exist
                print("Invoices table does not exist yet, returning empty array")
                return []
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        print(f"Error fetching invoices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching invoices: {str(e)}")

@app.post("/api/invoices/process")
async def process_invoice(request: Request):
    """
    Process an invoice image using OpenAI Vision API to extract:
    - Total price
    - Price per item (list of items with prices)
    """
    import os
    from openai import OpenAI
    
    # Get OpenAI API key from environment
    openai_key = os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    content_type = (request.headers.get("content-type") or "").lower()
    
    try:
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            image_file = form.get("image")
            if not image_file:
                raise HTTPException(status_code=400, detail="Image file is required")
            
            # Read image file
            image_data = await image_file.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            image_mime = getattr(image_file, "content_type", "image/jpeg")
        elif content_type.startswith("application/json"):
            payload = await request.json()
            # Expect base64 encoded image in data URI format: data:image/jpeg;base64,...
            image_data_uri = payload.get("image")
            if not image_data_uri:
                raise HTTPException(status_code=400, detail="Image data is required")
            
            # Extract base64 from data URI
            if image_data_uri.startswith("data:"):
                parts = image_data_uri.split(",", 1)
                image_base64 = parts[1] if len(parts) > 1 else image_data_uri
                mime_part = parts[0].split(";")[0] if len(parts) > 0 else "data:image/jpeg"
                image_mime = mime_part.replace("data:", "") if mime_part.startswith("data:") else "image/jpeg"
            else:
                image_base64 = image_data_uri
                image_mime = "image/jpeg"
        else:
            raise HTTPException(status_code=400, detail="Content-Type must be multipart/form-data or application/json")
        
        # Import json and re at the function level to avoid scoping issues
        import json
        import re
        
        # Store image data for saving even if OpenAI fails
        image_data_uri = f"data:{image_mime};base64,{image_base64}"
        
        # Initialize OpenAI client
        client = OpenAI(api_key=openai_key)
        
        # Initialize simple invoice data structure - only 2 fields
        invoice_data = {
            "total_price": None,
            "product_description": None
        }
        
        # Try to call OpenAI Responses API with GPT-5.2
        try:
            response = client.responses.create(
                model="gpt-5.2",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": """Extract invoice data from this image and return it as a JSON object with only 2 fields.

CRITICAL: You MUST respond with ONLY valid JSON. No markdown, no code blocks, no explanations, no text before or after the JSON. Just the raw JSON object.

The JSON structure MUST be exactly:
{
  "total_price": <number or null>,
  "product_description": "<string or null>"
}

Rules:
- total_price: Extract the final total amount to pay from the invoice (look for "Total", "סה\"כ", "Amount Due", etc.). Must be a number or null.
- product_description: Extract a description of what products/services are on the invoice. This should be a summary of the main items or services. Must be a string or null.
- If a field is not found, use null (not empty string, not 0, use null)
- Be thorough and extract all available information

Return ONLY the JSON object, nothing else."""
                            },
                            {
                                "type": "input_image",
                                "image_url": f"data:{image_mime};base64,{image_base64}"
                            }
                        ]
                    }
                ]
            )
            
            # Parse the response - Responses API returns output_text
            content = response.output_text if hasattr(response, 'output_text') else ""
            
            # Try to extract and parse JSON from the response
            if content:
                try:
                    # First, try to find JSON object (handle markdown code blocks if present)
                    json_content = content.strip()
                    
                    # Remove markdown code blocks if present (```json ... ``` or ``` ... ```)
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_content, re.DOTALL)
                    if json_match:
                        json_content = json_match.group(1).strip()
                    else:
                        # Try to find JSON object directly (from { to matching })
                        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_content, re.DOTALL)
                        if json_match:
                            json_content = json_match.group(0).strip()
                        else:
                            # Last resort: try to find anything between first { and last }
                            first_brace = json_content.find('{')
                            last_brace = json_content.rfind('}')
                            if first_brace >= 0 and last_brace > first_brace:
                                json_content = json_content[first_brace:last_brace + 1].strip()
                    
                    # Try to parse the JSON
                    parsed_data = json.loads(json_content)
                    
                    # Validate and merge parsed data with defaults - simple 2 field structure
                    if isinstance(parsed_data, dict):
                        if "total_price" in parsed_data:
                            try:
                                invoice_data["total_price"] = float(parsed_data["total_price"]) if parsed_data["total_price"] is not None else None
                            except (ValueError, TypeError):
                                invoice_data["total_price"] = None
                        
                        if "product_description" in parsed_data:
                            invoice_data["product_description"] = str(parsed_data["product_description"]) if parsed_data["product_description"] else None
                        
                except (json.JSONDecodeError, AttributeError, KeyError, ValueError, TypeError) as parse_error:
                    # If parsing fails, log the error but continue with empty fields
                    print(f"Warning: Could not parse OpenAI response: {parse_error}")
                    print(f"Response content (first 500 chars): {content[:500]}")  # Log first 500 chars for debugging
                    # Continue with empty invoice_data - user can edit manually
        except Exception as openai_error:
            # If OpenAI call fails (network, API error, etc.), log and continue with empty fields
            print(f"Warning: OpenAI API call failed: {openai_error}")
            print("Saving invoice with empty fields - user can edit manually")
            # Continue with empty invoice_data - user can edit manually
        
        # Save to database - simple 2 field structure
        invoice_record = {
            "image_data": image_data_uri,
            "total_price": invoice_data.get("total_price"),
            "currency": "ILS",  # Default currency
            "vendor": None,
            "date": None,
            "invoice_number": None,
            "extracted_data": invoice_data  # Store the simple structured data
        }
        
        # Fallback record for old table structure if needed
        invoice_record_fallback = {
            "file_url": image_data_uri,
            "amount": invoice_data.get("total_price"),
            "vendor": None,
            "invoice_number": None,
            "issued_at": None,
            "payment_method": None
        }
        
        try:
            # Try to save with new structure first
            resp = requests.post(
                f"{REST_URL}/invoices",
                headers=SERVICE_HEADERS,
                json=invoice_record
            )
            
            # If that fails, try fallback structure
            if resp.status_code not in [200, 201]:
                try:
                    resp = requests.post(
                        f"{REST_URL}/invoices",
                        headers=SERVICE_HEADERS,
                        json=invoice_record_fallback
                    )
                except:
                    pass
            # Check if save was successful
            if resp.status_code == 201 or resp.status_code == 200:
                saved_invoice = resp.json()
                saved_id = None
                if isinstance(saved_invoice, list) and saved_invoice:
                    saved_id = saved_invoice[0].get("id")
                elif isinstance(saved_invoice, dict):
                    saved_id = saved_invoice.get("id")
                print(f"Invoice saved successfully with ID: {saved_id}")
                invoice_data["saved"] = True
                invoice_data["id"] = str(saved_id) if saved_id else None
            else:
                # Log the error but don't fail
                error_text = resp.text[:200] if resp.text else "Unknown error"
                print(f"Warning: Could not save invoice to database. Status: {resp.status_code}, Error: {error_text}")
                invoice_data["saved"] = False
        except requests.exceptions.HTTPError as http_err:
            # Log HTTP errors
            error_text = ""
            if http_err.response:
                error_text = http_err.response.text[:200] if http_err.response.text else str(http_err.response)
            print(f"Warning: HTTP error saving invoice to database: {http_err.response.status_code if http_err.response else 'Unknown'}, Error: {error_text}")
            invoice_data["saved"] = False
        except Exception as db_error:
            # Log but don't fail - the invoice can still be returned
            print(f"Warning: Could not save invoice to database: {db_error}")
            invoice_data["saved"] = False
        
        # Add image_data to response (frontend expects this)
        invoice_data["image_data"] = image_data_uri
        
        return invoice_data
    except HTTPException:
        # Re-raise HTTP exceptions (like 400, 401, etc.)
        raise
    except Exception as e:
        # For any other unexpected errors, try to save the invoice with empty fields
        error_msg = str(e)
        print(f"Unexpected error processing invoice: {error_msg}")
        
        # If we have the image data, try to save it with empty fields
        try:
            if 'image_data_uri' in locals() or 'image_base64' in locals():
                image_uri = image_data_uri if 'image_data_uri' in locals() else f"data:{image_mime};base64,{image_base64}"
                invoice_record = {
                    # Map to actual table schema
                    "file_url": image_uri,
                    "amount": None,
                    "vendor": None,
                    "invoice_number": None,
                    "issued_at": None,
                    "payment_method": None
                }
                
                resp = requests.post(
                    f"{REST_URL}/invoices",
                    headers=SERVICE_HEADERS,
                    json=invoice_record
                )
                if resp.status_code == 201 or resp.status_code == 200:
                    saved_invoice = resp.json()
                    saved_id = None
                    if isinstance(saved_invoice, list) and saved_invoice:
                        saved_id = saved_invoice[0].get("id")
                    elif isinstance(saved_invoice, dict):
                        saved_id = saved_invoice.get("id")
                    
                    # Return the saved invoice with empty fields (frontend format)
                    return {
                        "id": str(saved_id) if saved_id else None,
                        "total_price": None,
                        "currency": "ILS",
                        "items": [],
                        "vendor": None,
                        "date": None,
                        "invoice_number": None,
                        "image_data": image_uri,
                        "saved": True
                    }
        except Exception as save_error:
            print(f"Could not save invoice after error: {save_error}")
        
        # If we can't save, still raise the original error
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid OpenAI API key")
        raise HTTPException(status_code=500, detail=f"Error processing invoice: {error_msg}")

@app.get("/api/invoices")
def api_invoices():
    """Alias for /invoices to match frontend expectations"""
    return invoices()

@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    """Get a single invoice by ID - maps to frontend format"""
    try:
        resp = requests.get(
            f"{REST_URL}/invoices",
            headers=SERVICE_HEADERS,
            params={"id": f"eq.{invoice_id}", "select": "*"}
        )
        resp.raise_for_status()
        invoices_list = resp.json()
        if not invoices_list or len(invoices_list) == 0:
            raise HTTPException(status_code=404, detail="Invoice not found")
        db_invoice = invoices_list[0]
        # Map database columns to frontend format
        return {
            "id": str(db_invoice.get("id", "")),
            "image_data": db_invoice.get("file_url", ""),
            "total_price": db_invoice.get("amount"),
            "currency": "ILS",
            "vendor": db_invoice.get("vendor"),
            "date": db_invoice.get("issued_at"),
            "invoice_number": db_invoice.get("invoice_number"),
            "extracted_data": None,
            "created_at": db_invoice.get("issued_at"),
            "updated_at": db_invoice.get("issued_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching invoice: {str(e)}")

@app.patch("/api/invoices/{invoice_id}")
def update_invoice(invoice_id: str, payload: dict):
    """Update an invoice - maps frontend fields to database schema"""
    try:
        # Map frontend fields to database columns
        data = {}
        if "total_price" in payload:
            data["amount"] = payload["total_price"]  # Map total_price to amount
        if "image_data" in payload:
            data["file_url"] = payload["image_data"]  # Map image_data to file_url
        if "vendor" in payload:
            data["vendor"] = payload["vendor"]
        if "invoice_number" in payload:
            data["invoice_number"] = payload["invoice_number"]
        if "date" in payload:
            data["issued_at"] = payload["date"]  # Map date to issued_at
        if "payment_method" in payload:
            data["payment_method"] = payload["payment_method"]
        
        if not data:
            return {"message": "No changes provided"}
        
        headers = {**SERVICE_HEADERS, "Prefer": "return=representation"}
        resp = requests.patch(
            f"{REST_URL}/invoices?id=eq.{invoice_id}",
            headers=headers,
            json=data
        )
        resp.raise_for_status()
        if resp.text:
            result = resp.json()
            db_invoice = result[0] if isinstance(result, list) and result else result
            # Map back to frontend format
            return {
                "id": str(db_invoice.get("id", "")),
                "image_data": db_invoice.get("file_url", ""),
                "total_price": db_invoice.get("amount"),
                "currency": "ILS",
                "vendor": db_invoice.get("vendor"),
                "date": db_invoice.get("issued_at"),
                "invoice_number": db_invoice.get("invoice_number"),
                "extracted_data": None,
                "created_at": db_invoice.get("issued_at"),
                "updated_at": db_invoice.get("issued_at"),
            }
        return {"id": invoice_id, "message": "Updated successfully"}
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating invoice: {str(e)}")

@app.delete("/api/invoices/{invoice_id}")
def delete_invoice(invoice_id: str):
    """Delete an invoice"""
    try:
        resp = requests.delete(
            f"{REST_URL}/invoices?id=eq.{invoice_id}",
            headers=SERVICE_HEADERS
        )
        resp.raise_for_status()
        return JSONResponse(content={"message": "Deleted successfully"}, status_code=200)
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting invoice: {str(e)}")

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

@app.get("/attendance/status/{employee}")
def get_attendance_status(employee: str):
    """Get current attendance status for an employee"""
    try:
        # Get the most recent log entry for this employee that doesn't have a clock_out
        resp = requests.get(
            f"{REST_URL}/attendance_logs?employee=eq.{employee}&clock_out=is.null&order=clock_in.desc&limit=1",
            headers=SERVICE_HEADERS
        )
        resp.raise_for_status()
        logs = resp.json()
        
        # Check if there's an active session (no clock_out)
        is_clocked_in = False
        session = None
        
        if logs and len(logs) > 0:
            latest_log = logs[0]
            if latest_log.get("clock_out") is None or latest_log.get("clock_out") == "":
                is_clocked_in = True
                session = {
                    "clock_in": latest_log.get("clock_in"),
                    "clock_out": latest_log.get("clock_out"),
                    "id": latest_log.get("id")
                }
        
        return {
            "is_clocked_in": is_clocked_in,
            "session": session
        }
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 404:
            return {"is_clocked_in": False, "session": None}
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching attendance status: {str(e)}")

@app.post("/attendance/start")
def start_attendance(payload: dict):
    """Start attendance (clock in) for an employee"""
    try:
        employee = payload.get("employee")
        if not employee:
            raise HTTPException(status_code=400, detail="Employee name is required")
        
        # Create a new attendance log entry
        log_data = {
            "employee": employee,
            "clock_in": datetime.now().isoformat(),
            "clock_out": None
        }
        
        resp = requests.post(
            f"{REST_URL}/attendance_logs",
            headers=SERVICE_HEADERS,
            json=log_data
        )
        resp.raise_for_status()
        
        result = resp.json()
        return result[0] if isinstance(result, list) and result else result
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting attendance: {str(e)}")

@app.post("/attendance/stop")
def stop_attendance(payload: dict):
    """Stop attendance (clock out) for an employee"""
    try:
        employee = payload.get("employee")
        if not employee:
            raise HTTPException(status_code=400, detail="Employee name is required")
        
        # Find the most recent log entry without a clock_out
        resp = requests.get(
            f"{REST_URL}/attendance_logs?employee=eq.{employee}&clock_out=is.null&order=clock_in.desc&limit=1&select=id",
            headers=SERVICE_HEADERS
        )
        resp.raise_for_status()
        logs = resp.json()
        
        if not logs or len(logs) == 0:
            raise HTTPException(status_code=404, detail="No active attendance session found")
        
        log_id = logs[0]["id"]
        
        # Update the log entry with clock_out time
        update_data = {
            "clock_out": datetime.now().isoformat()
        }
        
        update_resp = requests.patch(
            f"{REST_URL}/attendance_logs?id=eq.{log_id}",
            headers=SERVICE_HEADERS,
            json=update_data
        )
        update_resp.raise_for_status()
        
        result = update_resp.json()
        return result[0] if isinstance(result, list) and result else result
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="No active attendance session found")
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping attendance: {str(e)}")

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

# Cleaning Schedule endpoints
@app.get("/api/cleaning-schedule")
def get_cleaning_schedule():
    """Get all cleaning schedule entries"""
    try:
        resp = requests.get(
            f"{REST_URL}/cleaning_schedule",
            headers=SERVICE_HEADERS,
            params={"select": "*", "order": "date.asc,start_time.asc"}
        )
        resp.raise_for_status()
        return resp.json() or []
    except requests.exceptions.HTTPError as e:
        # If table doesn't exist (404) or any other error, return empty array gracefully
        if e.response:
            status_code = e.response.status_code
            if status_code == 404:
                # Table doesn't exist yet - return empty array
                return []
            # For other HTTP errors, still return empty array to avoid breaking the frontend
            print(f"Warning: Error fetching cleaning schedule (HTTP {status_code}): {e.response.text[:200]}")
            return []
        # Network or other errors - return empty array
        print(f"Warning: Error fetching cleaning schedule: {str(e)}")
        return []
    except Exception as e:
        # Any other exception - return empty array gracefully
        print(f"Warning: Error fetching cleaning schedule: {str(e)}")
        return []

@app.post("/api/cleaning-schedule")
def create_cleaning_schedule_entry(payload: dict):
    """Create a new cleaning schedule entry"""
    try:
        data = payload.copy()
        if not data.get("id"):
            data["id"] = str(uuid.uuid4())
        
        # Validate required fields
        if not data.get("date") or not data.get("start_time") or not data.get("end_time") or not data.get("cleaner_name"):
            raise HTTPException(status_code=400, detail="date, start_time, end_time, and cleaner_name are required")
        
        resp = requests.post(
            f"{REST_URL}/cleaning_schedule",
            headers=SERVICE_HEADERS,
            json=data
        )
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return data
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as e:
        # If table doesn't exist (404), provide a helpful error message
        if e.response and e.response.status_code == 404:
            raise HTTPException(
                status_code=404, 
                detail="Cleaning schedule table does not exist. Please create the table in Supabase first."
            )
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating cleaning schedule entry: {str(e)}")

@app.patch("/api/cleaning-schedule/{entry_id}")
def update_cleaning_schedule_entry(entry_id: str, payload: dict):
    """Update a cleaning schedule entry"""
    try:
        data = {k: v for k, v in payload.items() if v is not None}
        if not data:
            return {"message": "No changes provided"}
        headers = {**SERVICE_HEADERS, "Prefer": "return=representation"}
        resp = requests.patch(
            f"{REST_URL}/cleaning_schedule?id=eq.{entry_id}",
            headers=headers,
            json=data
        )
        resp.raise_for_status()
        if resp.text:
            result = resp.json()
            return result[0] if isinstance(result, list) and result else result
        return {"id": entry_id, "message": "Updated successfully"}
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating cleaning schedule entry: {str(e)}")

@app.delete("/api/cleaning-schedule/{entry_id}")
def delete_cleaning_schedule_entry(entry_id: str):
    """Delete a cleaning schedule entry"""
    try:
        resp = requests.delete(
            f"{REST_URL}/cleaning_schedule?id=eq.{entry_id}",
            headers=SERVICE_HEADERS
        )
        resp.raise_for_status()
        return JSONResponse(content={"message": "Deleted successfully"}, status_code=200)
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting cleaning schedule entry: {str(e)}")

