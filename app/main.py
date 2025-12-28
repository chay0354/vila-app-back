from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import os
import requests
import bcrypt
import base64
import json
from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .supabase_client import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
import pywebpush
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="bolavila-backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REST_URL = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"
SERVICE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Prefer": "return=representation",  # Return inserted row
}
STORAGE_HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
}

# Push notification configuration
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_EMAIL = os.getenv("VAPID_EMAIL", "mailto:admin@bolavilla.com")
FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY", "")

# Initialize VAPID if keys are provided
# Note: pywebpush handles VAPID internally, no separate package needed
vapid_claims = None
if VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY:
    try:
        vapid_claims = {
            "sub": VAPID_EMAIL
        }
        logger.info("VAPID keys configured for Web Push")
    except Exception as e:
        logger.warning(f"Failed to initialize VAPID: {e}")

def send_web_push_notification(subscription: Dict[str, Any], title: str, body: str, icon: str = "/app-icon.jpg"):
    """Send a Web Push notification to a PWA subscription"""
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        logger.warning("VAPID keys not configured, skipping Web Push")
        return False
    
    try:
        pywebpush.webpush(
            subscription_info=subscription,
            data=json.dumps({
                "title": title,
                "body": body,
                "icon": icon,
                "badge": icon,
                "tag": "notification",
                "requireInteraction": False
            }),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=vapid_claims
        )
        logger.info(f"Web Push notification sent: {title}")
        return True
    except Exception as e:
        logger.error(f"Error sending Web Push notification: {e}")
        return False

def send_fcm_notification(fcm_token: str, title: str, body: str):
    """Send an FCM notification to a native Android device"""
    if not FCM_SERVER_KEY:
        logger.warning("FCM server key not configured, skipping FCM notification")
        return False
    
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            "Authorization": f"key={FCM_SERVER_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "to": fcm_token,
            "notification": {
                "title": title,
                "body": body,
                "icon": "app-icon",
                "sound": "default"
            },
            "data": {
                "title": title,
                "body": body
            },
            "priority": "high"
        }
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        logger.info(f"FCM notification sent: {title}")
        return True
    except Exception as e:
        logger.error(f"Error sending FCM notification: {e}")
        return False

def send_push_notification_to_user(username: str, title: str, body: str):
    """Send push notification to all devices registered for a user"""
    try:
        # Get all push subscriptions for this user
        resp = requests.get(
            f"{REST_URL}/push_subscriptions",
            headers=SERVICE_HEADERS,
            params={"username": f"eq.{username}", "select": "*"}
        )
        if resp.status_code == 200:
            subscriptions = resp.json() or []
            for sub in subscriptions:
                if sub.get("type") == "web":
                    # Web Push subscription
                    subscription_info = {
                        "endpoint": sub.get("endpoint"),
                        "keys": {
                            "p256dh": sub.get("p256dh"),
                            "auth": sub.get("auth")
                        }
                    }
                    send_web_push_notification(subscription_info, title, body)
                elif sub.get("type") == "fcm" and sub.get("fcm_token"):
                    # FCM token for native app
                    send_fcm_notification(sub.get("fcm_token"), title, body)
        return True
    except Exception as e:
        logger.error(f"Error sending push notification to user {username}: {e}")
        return False

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
    role: Optional[str] = "עובד תחזוקה"
    image_url: Optional[str] = None

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
            "password_hash": password_hash,
            "role": payload.role or "עובד תחזוקה",
            "image_url": payload.image_url
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
            "role": user.get("role", "עובד תחזוקה"),
            "image_url": user.get("image_url"),
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
            "role": user.get("role", "עובד תחזוקה"),
            "image_url": user.get("image_url"),
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

@app.get("/api/users/with-details")
def api_list_users_with_details():
    """
    Return all users with their details including image_url, hourly_wage, and role.
    For employee management page.
    """
    try:
        resp = requests.get(
            f"{REST_URL}/users",
            headers=SERVICE_HEADERS,
            params={"select": "id,username,image_url,hourly_wage,role", "order": "username.asc"},
        )
        resp.raise_for_status()
        return resp.json() or []
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")

@app.patch("/api/users/{user_id}/wage")
def api_update_user_wage(user_id: str, payload: dict):
    """
    Update hourly wage for a user.
    """
    try:
        hourly_wage = payload.get("hourly_wage")
        if hourly_wage is None:
            raise HTTPException(status_code=400, detail="hourly_wage is required")
        
        # Update the user's hourly_wage
        update_data = {"hourly_wage": float(hourly_wage)}
        resp = requests.patch(
            f"{REST_URL}/users?id=eq.{user_id}",
            headers=SERVICE_HEADERS,
            json=update_data
        )
        resp.raise_for_status()
        result = resp.json()
        return result[0] if isinstance(result, list) and result else result
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user wage: {str(e)}")

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
def api_update_order(order_id: str, payload: dict):
    """Update order with frontend camelCase format and sync inspections"""
    # Get the current order to check if departure_date changed
    try:
        current_order_resp = requests.get(
            f"{REST_URL}/orders",
            headers=SERVICE_HEADERS,
            params={"id": f"eq.{order_id}", "select": "id,departure_date,unit_number,guest_name,status"}
        )
        current_order = None
        if current_order_resp.status_code == 200:
            orders_list = current_order_resp.json() or []
            if orders_list:
                current_order = orders_list[0]
    except Exception as e:
        print(f"Warning: Could not fetch current order: {str(e)}")
        current_order = None
    
    old_departure_date = current_order.get("departure_date") if current_order else None
    
    # Map frontend camelCase or snake_case to backend snake_case
    # Only include fields that are actually provided and not empty
    update_data = {}
    if "guestName" in payload or "guest_name" in payload:
        val = payload.get("guestName") or payload.get("guest_name")
        if val and val.strip():
            update_data["guest_name"] = val.strip()
    if "unitNumber" in payload or "unit_number" in payload:
        val = payload.get("unitNumber") or payload.get("unit_number")
        if val and val.strip():
            update_data["unit_number"] = val.strip()
    if "arrivalDate" in payload or "arrival_date" in payload:
        val = payload.get("arrivalDate") or payload.get("arrival_date")
        if val and val.strip():
            update_data["arrival_date"] = val.strip()
    if "departureDate" in payload or "departure_date" in payload:
        val = payload.get("departureDate") or payload.get("departure_date")
        if val and val.strip():
            update_data["departure_date"] = val.strip()
    if "status" in payload and payload["status"]:
        update_data["status"] = payload["status"]
    if "guestsCount" in payload or "guests_count" in payload:
        val = payload.get("guestsCount") or payload.get("guests_count")
        if val is not None:
            update_data["guests_count"] = val
    if "specialRequests" in payload or "special_requests" in payload:
        val = payload.get("specialRequests") or payload.get("special_requests")
        if val is not None:
            update_data["special_requests"] = val
    if "internalNotes" in payload or "internal_notes" in payload:
        val = payload.get("internalNotes") or payload.get("internal_notes")
        if val is not None:
            update_data["internal_notes"] = val
    if "paidAmount" in payload or "paid_amount" in payload:
        val = payload.get("paidAmount") or payload.get("paid_amount")
        if val is not None:
            update_data["paid_amount"] = val
    if "totalAmount" in payload or "total_amount" in payload:
        val = payload.get("totalAmount") or payload.get("total_amount")
        if val is not None:
            update_data["total_amount"] = val
    if "paymentMethod" in payload or "payment_method" in payload:
        val = payload.get("paymentMethod") or payload.get("payment_method")
        if val is not None:
            update_data["payment_method"] = val
    
    # Create OrderUpdate model from mapped data
    order_update = OrderUpdate(**update_data)
    result = update_order(order_id, order_update)
    
    # Get the updated order
    updated_order = result
    if isinstance(result, list):
        updated_order = result[0] if result else {}
    
    # Sync inspections if departure_date changed or order was updated
    new_departure_date = updated_order.get("departure_date") or update_data.get("departure_date")
    order_status = updated_order.get("status") or update_data.get("status", current_order.get("status") if current_order else "חדש")
    
    if new_departure_date and order_status != "בוטל":
        unit_number = updated_order.get("unit_number") or update_data.get("unit_number") or (current_order.get("unit_number") if current_order else "")
        guest_name = updated_order.get("guest_name") or update_data.get("guest_name") or (current_order.get("guest_name") if current_order else "")
        
        if old_departure_date != new_departure_date:
            # Departure date changed - update inspection
            update_inspection_for_departure_date(
                old_departure_date,
                new_departure_date,
                order_id,
                unit_number,
                guest_name
            )
            # Also update cleaning inspection
            update_cleaning_inspection_for_departure_date(
                old_departure_date,
                new_departure_date,
                order_id,
                unit_number,
                guest_name
            )
        else:
            # Just ensure inspection exists for this date
            create_inspection_for_departure_date(
                new_departure_date,
                order_id,
                unit_number,
                guest_name
            )
            # Also ensure cleaning inspection exists
            create_cleaning_inspection_for_departure_date(
                new_departure_date,
                order_id,
                unit_number,
                guest_name
            )
    
    # Return as single object, not array
    if isinstance(result, list):
        return result[0] if result else {}
    return result


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

# Default inspection tasks (24 tasks) - for exit inspections
DEFAULT_INSPECTION_TASKS = [
    {"id": "1", "name": "לשים כלור בבריכה", "completed": False},
    {"id": "2", "name": "להוסיף מים בבריכה", "completed": False},
    {"id": "3", "name": "לנקות רובוט ולהפעיל", "completed": False},
    {"id": "4", "name": "לנקות רשת פנים המנוע", "completed": False},
    {"id": "5", "name": "לעשות בקווש שטיפה לפילטר", "completed": False},
    {"id": "6", "name": "לטאטא הבק מהמדרגות ומשטחי רביצה", "completed": False},
    {"id": "7", "name": "לשים כלור בגקוזי", "completed": False},
    {"id": "8", "name": "להוסיף מים בגקוזי", "completed": False},
    {"id": "9", "name": "לנקות רובוט גקוזי ולהפעיל", "completed": False},
    {"id": "10", "name": "לנקות רשת פנים המנוע גקוזי", "completed": False},
    {"id": "11", "name": "לעשות בקווש שטיפה לפילטר גקוזי", "completed": False},
    {"id": "12", "name": "לטאטא הבק מהמדרגות ומשטחי רביצה גקוזי", "completed": False},
    {"id": "13", "name": "ניקיון חדרים", "completed": False},
    {"id": "14", "name": "ניקיון מטבח", "completed": False},
    {"id": "15", "name": "ניקיון שירותים", "completed": False},
    {"id": "16", "name": "פינוי זבל לפח אשפה פנים וחוץ הוילה", "completed": False},
    {"id": "17", "name": "בדיקת מכשירים", "completed": False},
    {"id": "18", "name": "בדיקת מצב ריהוט", "completed": False},
    {"id": "19", "name": "החלפת מצעים", "completed": False},
    {"id": "20", "name": "החלפת מגבות", "completed": False},
    {"id": "21", "name": "בדיקת מלאי", "completed": False},
    {"id": "22", "name": "לבדוק תקינות חדרים", "completed": False},
    {"id": "23", "name": "כיבוי אורות פנים וחוץ הוילה", "completed": False},
    {"id": "24", "name": "לנעול דלת ראשית", "completed": False},
]

# Default cleaning inspection tasks - for cleaning inspections
DEFAULT_CLEANING_INSPECTION_TASKS = [
    # מטבח (Kitchen)
    {"id": "1", "name": "מכונת קפה, לנקות ולהחליף פילטר קפה", "completed": False},
    {"id": "2", "name": "קפה תה סוכר וכו׳", "completed": False},
    {"id": "3", "name": "להעביר סמרטוט במתקן מים", "completed": False},
    {"id": "4", "name": "מקרר – בפנים ובחוץ", "completed": False},
    {"id": "5", "name": "תנור – בפנים ובחוץ", "completed": False},
    {"id": "6", "name": "כיריים וגריל", "completed": False},
    {"id": "7", "name": "מיקרו", "completed": False},
    {"id": "8", "name": "כיור", "completed": False},
    {"id": "9", "name": "כלים – לשטוף ליבש ולהחזיר לארון", "completed": False},
    {"id": "10", "name": "לבדוק שכל הכלים נקיים", "completed": False},
    {"id": "11", "name": "לבדוק שיש לפחות 20 כוסות אוכל מכל דבר", "completed": False},
    {"id": "12", "name": "ארונות מטבח – לפתוח ולראות שאין דברים להוציא דברים לא קשורים", "completed": False},
    {"id": "13", "name": "להעביר סמרטוט על הדלתות מטבח בחוץ", "completed": False},
    {"id": "14", "name": "להעביר סמרטוט על הפח ולראות שנקי", "completed": False},
    {"id": "15", "name": "פלטת שבת ומיחם מים חמים – לראות שאין אבן", "completed": False},
    {"id": "16", "name": "סכו״ם, כלים, סמרטוט, סקוֹץ׳ חדשים לאורחים", "completed": False},
    {"id": "17", "name": "סבון", "completed": False},
    # סלון (Living Room)
    {"id": "18", "name": "סלון שטיפה יסודית גם מתחת לספות ולשולחן, להזיז כורסאות ולבדוק שאין פירורים של אוכל", "completed": False},
    {"id": "19", "name": "שולחן אוכל וספסלים (לנקות בשפריצר ולהעביר סמרטוט)", "completed": False},
    {"id": "20", "name": "סלון – לנגב אבק ולהעביר סמרטוט גם על הספה. כיריות לנקות לסדר יפה", "completed": False},
    {"id": "21", "name": "שולחן אוכל וספסלים – להעביר סמרטוט נקי עם תריס", "completed": False},
    {"id": "22", "name": "חלונות ותריסים – עם ספריי חלונות וסמרטוט נקי. שלא יהיו סימנים. מסילות לנקות", "completed": False},
    # מסדרון (Hallway)
    {"id": "23", "name": "מסדרון – לנגב בחוץ שטיחים. לנקות מסילות בחלונות. לנקות חלונות", "completed": False},
    # חצר (Yard)
    {"id": "24", "name": "טיפול ברזים וניקוי", "completed": False},
    {"id": "25", "name": "להשקות עציצים בכל המתחם", "completed": False},
    {"id": "26", "name": "פינת מנגל – לרוקן פחים ולנקות רשת, וכל אזור המנגל", "completed": False},
    {"id": "27", "name": "לנקות דשא ולסדר פינות ישיבה", "completed": False},
    {"id": "28", "name": "שולחן חוץ – להעביר סמרטוט עם חומר. כיסאות נקיים", "completed": False},
    {"id": "29", "name": "שטיפה לרצפה בחוץ", "completed": False},
    {"id": "30", "name": "לרוקן את הפחים, לשים שקית חדשה", "completed": False},
    {"id": "31", "name": "להעביר סמרטוט על הפחים ולשים שקיות", "completed": False},
]

# Default monthly inspection tasks - for monthly inspections
DEFAULT_MONTHLY_INSPECTION_TASKS = [
    {"id": "1", "name": "בדיקת תקינות מערכות חשמל", "completed": False},
    {"id": "2", "name": "בדיקת תקינות מערכות מים", "completed": False},
    {"id": "3", "name": "בדיקת תקינות מערכות גז", "completed": False},
    {"id": "4", "name": "בדיקת תקינות מזגנים", "completed": False},
    {"id": "5", "name": "בדיקת תקינות דודי שמש", "completed": False},
    {"id": "6", "name": "בדיקת תקינות מערכות אבטחה", "completed": False},
    {"id": "7", "name": "בדיקת תקינות מערכות תאורה", "completed": False},
    {"id": "8", "name": "בדיקת תקינות דלתות וחלונות", "completed": False},
    {"id": "9", "name": "בדיקת תקינות ריהוט וציוד", "completed": False},
    {"id": "10", "name": "בדיקת תקינות מערכות ניקוז", "completed": False},
    {"id": "11", "name": "בדיקת תקינות מערכות אוורור", "completed": False},
    {"id": "12", "name": "בדיקת תקינות מערכות כיבוי אש", "completed": False},
    {"id": "13", "name": "בדיקת תקינות מערכות אינטרנט", "completed": False},
    {"id": "14", "name": "בדיקת תקינות מערכות טלוויזיה", "completed": False},
    {"id": "15", "name": "בדיקת תקינות מערכות מיזוג", "completed": False},
    {"id": "16", "name": "בדיקת תקינות מערכות מים חמים", "completed": False},
    {"id": "17", "name": "בדיקת תקינות מערכות תאורה חוץ", "completed": False},
    {"id": "18", "name": "בדיקת תקינות מערכות השקיה", "completed": False},
    {"id": "19", "name": "בדיקת תקינות מערכות בריכה", "completed": False},
    {"id": "20", "name": "בדיקת תקינות מערכות גקוזי", "completed": False},
]

def sync_inspections_with_orders():
    """Sync inspections table with all orders - ensure every departure date has an inspection"""
    try:
        # Get all non-cancelled orders
        orders_resp = requests.get(
            f"{REST_URL}/orders",
            headers=SERVICE_HEADERS,
            params={"status": "neq.בוטל", "select": "id,departure_date,unit_number,guest_name,status"}
        )
        
        if orders_resp.status_code != 200:
            print(f"Warning: Could not fetch orders for sync: {orders_resp.status_code}")
            return
        
        orders = orders_resp.json() or []
        
        # Get all existing inspections
        inspections_resp = requests.get(
            f"{REST_URL}/inspections",
            headers=SERVICE_HEADERS,
            params={"select": "id,departure_date"}
        )
        
        existing_inspections = []
        if inspections_resp.status_code == 200:
            existing_inspections = inspections_resp.json() or []
        elif inspections_resp.status_code == 404:
            existing_inspections = []
        
        # Group orders by departure date, filtering out orders with empty unit_number or guest_name
        orders_by_date = {}
        for order in orders:
            departure_date = order.get("departure_date")
            unit_number = order.get("unit_number", "").strip() if order.get("unit_number") else ""
            guest_name = order.get("guest_name", "").strip() if order.get("guest_name") else ""
            
            if departure_date and order.get("status") != "בוטל" and unit_number and guest_name:
                if departure_date not in orders_by_date:
                    orders_by_date[departure_date] = []
                orders_by_date[departure_date].append(order)
        
        # Get existing inspection dates and their IDs
        existing_dates = {insp.get("departure_date") for insp in existing_inspections if insp.get("departure_date")}
        existing_inspections_by_date = {insp.get("departure_date"): insp.get("id") for insp in existing_inspections if insp.get("departure_date")}
        
        # Create inspections for missing departure dates
        for departure_date, orders_for_date in orders_by_date.items():
            if departure_date not in existing_dates:
                # Create inspection for this departure date
                first_order = orders_for_date[0]
                guest_names = [o.get("guest_name", "").strip() for o in orders_for_date if o.get("guest_name", "").strip()]
                create_inspection_for_departure_date(
                    departure_date,
                    first_order.get("id"),
                    first_order.get("unit_number", "").strip(),
                    ", ".join(guest_names)
                )
        
        # Remove inspections for departure dates that no longer have orders
        orders_dates = set(orders_by_date.keys())
        for inspection in existing_inspections:
            inspection_date = inspection.get("departure_date")
            if inspection_date and inspection_date not in orders_dates:
                # This departure date no longer has any orders, delete the inspection
                inspection_id = inspection.get("id")
                try:
                    delete_resp = requests.delete(
                        f"{REST_URL}/inspections?id=eq.{inspection_id}",
                        headers=SERVICE_HEADERS
                    )
                    if delete_resp.status_code in [200, 204]:
                        print(f"Deleted orphaned inspection {inspection_id} for departure date {inspection_date}")
                except Exception as e:
                    print(f"Warning: Error deleting orphaned inspection {inspection_id}: {str(e)}")
        
        print(f"Synced inspections with orders: {len(orders_by_date)} unique departure dates, removed {len(existing_dates) - len(orders_dates)} orphaned inspections")
        
    except Exception as e:
        print(f"Warning: Error syncing inspections with orders: {str(e)}")

def update_inspection_for_departure_date(old_date: str, new_date: str, order_id: str, unit_number: str, guest_name: str):
    """Update inspection when order departure date changes"""
    if not new_date:
        return None
    
    try:
        # If old date exists, check if we need to move/update the inspection
        if old_date and old_date != new_date:
            # Check if old date inspection has other orders
            old_orders_resp = requests.get(
                f"{REST_URL}/orders",
                headers=SERVICE_HEADERS,
                params={"departure_date": f"eq.{old_date}", "status": "neq.בוטל", "select": "id"}
            )
            old_orders = []
            if old_orders_resp.status_code == 200:
                old_orders = old_orders_resp.json() or []
            
            # If old date has no other orders, we can delete or update that inspection
            # For now, we'll leave it and create a new one for the new date
            # (The sync function will clean up orphaned inspections)
        
        # Create/update inspection for new departure date
        return create_inspection_for_departure_date(new_date, order_id, unit_number, guest_name)
        
    except Exception as e:
        print(f"Warning: Error updating inspection for departure date change: {str(e)}")
        return None

def create_inspection_for_departure_date(departure_date: str, order_id: str, unit_number: str, guest_name: str):
    """Create an inspection for a departure date if one doesn't already exist"""
    if not departure_date:
        return None
    
    # Don't create inspection if unit_number or guest_name are empty
    if not unit_number or not unit_number.strip() or not guest_name or not guest_name.strip():
        print(f"Skipping inspection creation for {departure_date}: unit_number or guest_name is empty")
        return None
    
    try:
        # Check if inspection already exists for this departure date
        check_resp = requests.get(
            f"{REST_URL}/inspections",
            headers=SERVICE_HEADERS,
            params={"departure_date": f"eq.{departure_date}", "select": "id,departure_date,unit_number"}
        )
        
        existing_inspections = []
        if check_resp.status_code == 200:
            existing_inspections = check_resp.json() or []
        elif check_resp.status_code == 404:
            # Table doesn't exist yet, that's OK
            existing_inspections = []
        
        # If inspection already exists for this departure date, update it if needed
        if existing_inspections and len(existing_inspections) > 0:
            existing = existing_inspections[0]
            # Update unit_number and guest_name if they changed
            if existing.get("unit_number") != unit_number or existing.get("guest_name") != guest_name:
                update_data = {}
                if existing.get("unit_number") != unit_number:
                    update_data["unit_number"] = unit_number
                if existing.get("guest_name") != guest_name:
                    # Combine guest names if multiple orders share the date
                    existing_guests = existing.get("guest_name", "")
                    if guest_name not in existing_guests:
                        update_data["guest_name"] = f"{existing_guests}, {guest_name}".strip(", ")
                    else:
                        update_data["guest_name"] = existing_guests
                
                if update_data:
                    try:
                        update_resp = requests.patch(
                            f"{REST_URL}/inspections?id=eq.{existing['id']}",
                            headers=SERVICE_HEADERS,
                            json=update_data
                        )
                        if update_resp.status_code in [200, 201, 204]:
                            print(f"Updated inspection {existing['id']} with new unit/guest info")
                    except Exception as e:
                        print(f"Warning: Error updating inspection: {str(e)}")
            
            return existing
        
        # Create new inspection for this departure date
        inspection_id = f"INSP-{departure_date}"
        inspection_data = {
            "id": inspection_id,
            "order_id": order_id,  # Keep first order ID for reference
            "unit_number": unit_number,
            "guest_name": guest_name,
            "departure_date": departure_date,
            "status": "זמן הביקורות טרם הגיע",
        }
        
        # Create inspection
        create_resp = requests.post(
            f"{REST_URL}/inspections",
            headers=SERVICE_HEADERS,
            json=inspection_data
        )
        
        if create_resp.status_code not in [200, 201, 404, 409]:
            # If not 404 (table doesn't exist) or 409 (conflict), log error but don't fail
            if create_resp.status_code != 404 and create_resp.status_code != 409:
                print(f"Warning: Failed to create inspection for departure date {departure_date}: {create_resp.status_code}")
        
        # Create all default tasks for this inspection
        for task in DEFAULT_INSPECTION_TASKS:
            task_data = {
                "id": task["id"],
                "inspection_id": inspection_id,
                "name": task["name"],
                "completed": task["completed"],
            }
            
            try:
                task_resp = requests.post(
                    f"{REST_URL}/inspection_tasks",
                    headers=SERVICE_HEADERS,
                    json=task_data
                )
                # Ignore 404 (table doesn't exist) and 409 (task already exists)
                if task_resp.status_code not in [200, 201, 404, 409]:
                    print(f"Warning: Failed to create task {task['id']} for inspection {inspection_id}: {task_resp.status_code}")
            except Exception as e:
                print(f"Warning: Error creating task {task['id']}: {str(e)}")
        
        print(f"Created inspection {inspection_id} for departure date {departure_date}")
        return inspection_data
        
    except Exception as e:
        # Don't fail order creation if inspection creation fails
        print(f"Warning: Failed to create inspection for departure date {departure_date}: {str(e)}")
        return None

def create_cleaning_inspection_for_departure_date(departure_date: str, order_id: str, unit_number: str, guest_name: str):
    """Create a cleaning inspection for a departure date if one doesn't already exist"""
    if not departure_date:
        return None
    
    # Don't create inspection if unit_number or guest_name are empty
    if not unit_number or not unit_number.strip() or not guest_name or not guest_name.strip():
        print(f"Skipping cleaning inspection creation for {departure_date}: unit_number or guest_name is empty")
        return None
    
    try:
        # Check if cleaning inspection already exists for this departure date
        check_resp = requests.get(
            f"{REST_URL}/cleaning_inspections",
            headers=SERVICE_HEADERS,
            params={"departure_date": f"eq.{departure_date}", "select": "id,departure_date,unit_number"}
        )
        
        existing_inspections = []
        if check_resp.status_code == 200:
            existing_inspections = check_resp.json() or []
        elif check_resp.status_code == 404:
            # Table doesn't exist yet, that's OK
            existing_inspections = []
        
        # If inspection already exists for this departure date, update it if needed
        if existing_inspections and len(existing_inspections) > 0:
            existing = existing_inspections[0]
            # Update unit_number and guest_name if they changed
            if existing.get("unit_number") != unit_number or existing.get("guest_name") != guest_name:
                update_data = {}
                if existing.get("unit_number") != unit_number:
                    update_data["unit_number"] = unit_number
                if existing.get("guest_name") != guest_name:
                    # Combine guest names if multiple orders share the date
                    existing_guests = existing.get("guest_name", "")
                    if guest_name not in existing_guests:
                        update_data["guest_name"] = f"{existing_guests}, {guest_name}".strip(", ")
                    else:
                        update_data["guest_name"] = existing_guests
                
                if update_data:
                    try:
                        update_resp = requests.patch(
                            f"{REST_URL}/cleaning_inspections?id=eq.{existing['id']}",
                            headers=SERVICE_HEADERS,
                            json=update_data
                        )
                        if update_resp.status_code in [200, 201, 204]:
                            print(f"Updated cleaning inspection {existing['id']} with new unit/guest info")
                    except Exception as e:
                        print(f"Warning: Error updating cleaning inspection: {str(e)}")
            
            return existing
        
        # Create new cleaning inspection for this departure date
        inspection_id = f"CLEAN-{departure_date}"
        inspection_data = {
            "id": inspection_id,
            "order_id": order_id,  # Keep first order ID for reference
            "unit_number": unit_number,
            "guest_name": guest_name,
            "departure_date": departure_date,
            "status": "זמן הביקורות טרם הגיע",
        }
        
        # Create cleaning inspection
        create_resp = requests.post(
            f"{REST_URL}/cleaning_inspections",
            headers=SERVICE_HEADERS,
            json=inspection_data
        )
        
        if create_resp.status_code not in [200, 201, 404, 409]:
            # If not 404 (table doesn't exist) or 409 (conflict), log error but don't fail
            if create_resp.status_code != 404 and create_resp.status_code != 409:
                print(f"Warning: Failed to create cleaning inspection for departure date {departure_date}: {create_resp.status_code}")
        
        # Create all default tasks for this cleaning inspection
        for task in DEFAULT_CLEANING_INSPECTION_TASKS:
            task_data = {
                "id": task["id"],
                "inspection_id": inspection_id,
                "name": task["name"],
                "completed": task["completed"],
            }
            
            try:
                task_resp = requests.post(
                    f"{REST_URL}/cleaning_inspection_tasks",
                    headers=SERVICE_HEADERS,
                    json=task_data
                )
                # Ignore 404 (table doesn't exist) and 409 (task already exists)
                if task_resp.status_code not in [200, 201, 404, 409]:
                    print(f"Warning: Failed to create cleaning task {task['id']} for inspection {inspection_id}: {task_resp.status_code}")
            except Exception as e:
                print(f"Warning: Exception creating cleaning task {task['id']}: {str(e)}")
        
        print(f"Created cleaning inspection {inspection_id} for departure date {departure_date}")
        return inspection_data
        
    except Exception as e:
        # Don't fail order creation if cleaning inspection creation fails
        print(f"Warning: Failed to create cleaning inspection for departure date {departure_date}: {str(e)}")
        return None

def update_cleaning_inspection_for_departure_date(old_departure_date: str, new_departure_date: str, order_id: str, unit_number: str, guest_name: str):
    """Update cleaning inspection when departure date changes"""
    if not new_departure_date:
        return None
    
    try:
        # Delete old cleaning inspection if departure date changed
        if old_departure_date and old_departure_date != new_departure_date:
            old_inspection_id = f"CLEAN-{old_departure_date}"
            try:
                delete_resp = requests.delete(
                    f"{REST_URL}/cleaning_inspections?id=eq.{old_inspection_id}",
                    headers=SERVICE_HEADERS
                )
                if delete_resp.status_code in [200, 204]:
                    print(f"Deleted old cleaning inspection {old_inspection_id} due to departure date change")
            except Exception as e:
                print(f"Warning: Error deleting old cleaning inspection: {str(e)}")
        
        # Create new cleaning inspection for new departure date
        return create_cleaning_inspection_for_departure_date(new_departure_date, order_id, unit_number, guest_name)
    except Exception as e:
        print(f"Warning: Error updating cleaning inspection for departure date change: {str(e)}")
        return None

def sync_cleaning_inspections_with_orders():
    """Sync cleaning inspections table with all orders - ensure every departure date has a cleaning inspection"""
    try:
        # Get all orders
        orders_resp = requests.get(
            f"{REST_URL}/orders",
            headers=SERVICE_HEADERS,
            params={"select": "id,departure_date,unit_number,guest_name,status"}
        )
        
        if orders_resp.status_code != 200:
            print(f"Warning: Failed to fetch orders for cleaning inspection sync: {orders_resp.status_code}")
            return
        
        orders = orders_resp.json() or []
        
        # Group orders by departure date
        orders_by_date = {}
        for order in orders:
            departure_date = order.get("departure_date")
            status = order.get("status", "")
            
            # Skip cancelled orders
            if not departure_date or status == "בוטל":
                continue
            
            # Skip orders with empty unit_number or guest_name
            unit_number = order.get("unit_number", "").strip()
            guest_name = order.get("guest_name", "").strip()
            if not unit_number or not guest_name:
                continue
            
            if departure_date not in orders_by_date:
                orders_by_date[departure_date] = []
            orders_by_date[departure_date].append(order)
        
        # Get all existing cleaning inspections
        cleaning_inspections_resp = requests.get(
            f"{REST_URL}/cleaning_inspections",
            headers=SERVICE_HEADERS,
            params={"select": "id,departure_date"}
        )
        
        existing_cleaning_inspections = []
        if cleaning_inspections_resp.status_code == 200:
            existing_cleaning_inspections = cleaning_inspections_resp.json() or []
        elif cleaning_inspections_resp.status_code == 404:
            existing_cleaning_inspections = []
        
        # Get existing cleaning inspection dates
        existing_cleaning_dates = {insp.get("departure_date") for insp in existing_cleaning_inspections if insp.get("departure_date")}
        
        # Create or update cleaning inspections for each departure date
        for departure_date, date_orders in orders_by_date.items():
            if not date_orders:
                continue
            
            # Only create if it doesn't exist
            if departure_date not in existing_cleaning_dates:
                # Use first order's details
                first_order = date_orders[0]
                order_id = first_order.get("id")
                unit_number = first_order.get("unit_number", "").strip()
                guest_name = first_order.get("guest_name", "").strip()
                
                # Combine guest names if multiple orders
                if len(date_orders) > 1:
                    guest_names = [o.get("guest_name", "").strip() for o in date_orders if o.get("guest_name", "").strip()]
                    guest_name = ", ".join(set(guest_names))  # Remove duplicates
                
                create_cleaning_inspection_for_departure_date(departure_date, order_id, unit_number, guest_name)
        
        # Remove cleaning inspections for departure dates that no longer have orders
        orders_dates = set(orders_by_date.keys())
        for inspection in existing_cleaning_inspections:
            inspection_date = inspection.get("departure_date")
            if inspection_date and inspection_date not in orders_dates:
                # This departure date no longer has any orders, delete the cleaning inspection
                inspection_id = inspection.get("id")
                try:
                    delete_resp = requests.delete(
                        f"{REST_URL}/cleaning_inspections?id=eq.{inspection_id}",
                        headers=SERVICE_HEADERS
                    )
                    if delete_resp.status_code in [200, 204]:
                        print(f"Deleted orphaned cleaning inspection {inspection_id} for departure date {inspection_date}")
                except Exception as e:
                    print(f"Warning: Error deleting orphaned cleaning inspection {inspection_id}: {str(e)}")
        
        print(f"Synced cleaning inspections with {len(orders)} orders: {len(orders_by_date)} unique departure dates, removed {len(existing_cleaning_dates) - len(orders_dates)} orphaned cleaning inspections")
    except Exception as e:
        print(f"Error syncing cleaning inspections with orders: {str(e)}")

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
    
    # Get the created order (handle both single object and list responses)
    created_order = result
    if isinstance(result, list):
        created_order = result[0] if result else {}
    
    # Automatically create inspection for the departure date if order was created successfully
    if created_order and created_order.get("departure_date"):
        departure_date = created_order.get("departure_date")
        order_id = created_order.get("id") or order_data.get("id")
        unit_number = created_order.get("unit_number") or order_data.get("unit_number", "")
        guest_name = created_order.get("guest_name") or order_data.get("guest_name", "")
        
        # Only create inspection if order status is not cancelled
        if created_order.get("status") != "בוטל":
            create_inspection_for_departure_date(departure_date, order_id, unit_number, guest_name)
            # Also create cleaning inspection
            create_cleaning_inspection_for_departure_date(departure_date, order_id, unit_number, guest_name)
    
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

@app.delete("/api/orders/{order_id}")
def api_delete_order(order_id: str):
    """Delete an order - API endpoint for frontend"""
    try:
        resp = requests.delete(
            f"{REST_URL}/orders",
            headers=SERVICE_HEADERS,
            params={"id": f"eq.{order_id}"},
        )
        resp.raise_for_status()
        return JSONResponse(content={"message": "Deleted successfully"}, status_code=200)
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting order: {str(e)}")

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
                # Format: in.(id1,id2,id3) - no spaces after commas
                inspection_ids_str = ','.join(inspection_ids)
                tasks_resp = requests.get(
                    f"{REST_URL}/inspection_tasks",
                    headers=SERVICE_HEADERS,
                    params={"inspection_id": f"in.({inspection_ids_str})", "select": "*"}
                )
                print(f"Loading tasks for inspections: {inspection_ids_str}")
                print(f"Tasks query status: {tasks_resp.status_code}")
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
            print(f"Loaded {len(all_tasks)} tasks from database")
            print(f"Tasks for inspections: {inspection_ids}")
            for task in all_tasks:
                insp_id = task.get("inspection_id")
                if insp_id:
                    if insp_id not in tasks_by_inspection:
                        tasks_by_inspection[insp_id] = []
                    # Ensure completed is a boolean (not string "true"/"false")
                    completed = task.get("completed", False)
                    if isinstance(completed, str):
                        completed = completed.lower() in ('true', '1', 'yes', 'on')
                    elif completed is None:
                        completed = False
                    else:
                        completed = bool(completed)
                    
                    task_data = {
                        "id": task.get("id"),
                        "name": task.get("name"),
                        "completed": completed,
                    }
                    print(f"Task {task_data['id']} for inspection {insp_id} ({task_data['name']}): completed={completed}")
                    tasks_by_inspection[insp_id].append(task_data)
            
            # Log summary per inspection
            for insp_id in inspection_ids:
                task_count = len(tasks_by_inspection.get(insp_id, []))
                completed_count = sum(1 for t in tasks_by_inspection.get(insp_id, []) if t.get("completed", False))
                print(f"Inspection {insp_id}: {completed_count}/{task_count} tasks completed")
        
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

@app.post("/api/inspections/sync")
def sync_all_inspections():
    """Sync all inspections with orders - ensure every departure date has an inspection"""
    try:
        sync_inspections_with_orders()
        return {"status": "success", "message": "Inspections synced with orders"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing inspections: {str(e)}")

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
        
        # Handle tasks - use upsert (update or insert) instead of delete + insert
        # This prevents losing tasks if insertion fails
        tasks = payload.get("tasks", [])
        return_tasks = tasks  # Default to original tasks if nothing is saved
        saved_tasks = []
        failed_tasks = []
        
        if tasks:
            # First, get existing tasks for this inspection to see what needs updating vs inserting
            existing_task_ids = set()
            try:
                existing_resp = requests.get(
                    f"{REST_URL}/inspection_tasks",
                    headers=SERVICE_HEADERS,
                    params={"inspection_id": f"eq.{inspection_id}", "select": "id,name"}
                )
                if existing_resp.status_code == 200:
                    existing_tasks = existing_resp.json() or []
                    existing_task_ids = {t.get("id") for t in existing_tasks if t.get("id")}
                    print(f"Found {len(existing_task_ids)} existing tasks for inspection {inspection_id}: {existing_task_ids}")
                else:
                    print(f"No existing tasks found for inspection {inspection_id} (status: {existing_resp.status_code})")
            except Exception as e:
                print(f"Error getting existing tasks for inspection {inspection_id}: {str(e)}")
                # If we can't get existing tasks, we'll try to insert/update all
            
            # Upsert tasks one by one (update if exists, insert if not)
            for task in tasks:
                try:
                    # Ensure completed is a boolean
                    completed = task.get("completed", False)
                    if isinstance(completed, str):
                        completed = completed.lower() in ('true', '1', 'yes', 'on')
                    elif completed is None:
                        completed = False
                    else:
                        completed = bool(completed)
                    
                    task_data = {
                        "id": task.get("id") or str(uuid.uuid4()),
                        "inspection_id": inspection_id,
                        "name": task.get("name", ""),
                        "completed": completed,  # Ensure boolean
                    }
                    task_id = task_data["id"]
                    print(f"Saving task {task_id} ({task_data['name']}): completed={completed} (type: {type(completed).__name__})")
                    
                    # Try to update if task exists for THIS inspection, otherwise insert
                    # IMPORTANT: Check if task exists for this specific inspection_id
                    task_exists_for_this_inspection = task_id in existing_task_ids
                    
                    if task_exists_for_this_inspection:
                        # Task exists for this inspection, update it
                        print(f"  → Updating existing task {task_id} for inspection {inspection_id}")
                        update_resp = requests.patch(
                            f"{REST_URL}/inspection_tasks?id=eq.{task_id}&inspection_id=eq.{inspection_id}",
                            headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                            json={"completed": task_data["completed"], "name": task_data["name"]}
                        )
                        if update_resp.status_code in [200, 201, 204]:
                            saved_tasks.append(task_data)
                            print(f"  ✓ Task {task_id} updated successfully")
                        else:
                            # Update failed, try insert (maybe task was deleted?)
                            print(f"  ⚠ Update failed (status {update_resp.status_code}), trying insert...")
                            task_resp = requests.post(
                                f"{REST_URL}/inspection_tasks",
                                headers=SERVICE_HEADERS,
                                json=task_data
                            )
                            if task_resp.status_code in [200, 201]:
                                saved_tasks.append(task_data)
                                print(f"  ✓ Task {task_id} inserted successfully (after update failed)")
                            elif task_resp.status_code == 404:
                                # Table doesn't exist - this is a real error, don't treat as success
                                error_text = task_resp.text[:200] if task_resp.text else ""
                                print(f"  ✗ ERROR: Table doesn't exist (404) - task {task_id} NOT saved: {error_text}")
                                failed_tasks.append(task_data)
                            else:
                                error_text = task_resp.text[:200] if task_resp.text else ""
                                print(f"  ✗ ERROR: Failed to insert task {task_id} after update failed: {task_resp.status_code} {error_text}")
                                failed_tasks.append(task_data)
                    else:
                        # Task doesn't exist for this inspection, insert it
                        print(f"  → Inserting new task {task_id} for inspection {inspection_id}")
                        task_resp = requests.post(
                            f"{REST_URL}/inspection_tasks",
                            headers=SERVICE_HEADERS,
                            json=task_data
                        )
                        if task_resp.status_code in [200, 201]:
                            saved_tasks.append(task_data)
                            print(f"  ✓ Task {task_id} inserted successfully")
                        elif task_resp.status_code == 404:
                            # Table doesn't exist - this is a real error, don't treat as success
                            error_text = task_resp.text[:200] if task_resp.text else ""
                            print(f"  ✗ ERROR: Table doesn't exist (404) - task {task_id} NOT saved: {error_text}")
                            failed_tasks.append(task_data)
                        elif task_resp.status_code == 409:
                            # Conflict - task ID already exists (maybe for another inspection?)
                            # Try to update it for this inspection_id
                            print(f"  ⚠ Conflict (409) - task {task_id} may exist for another inspection, trying update...")
                            try:
                                update_resp = requests.patch(
                                    f"{REST_URL}/inspection_tasks?id=eq.{task_id}&inspection_id=eq.{inspection_id}",
                                    headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                                    json={"completed": task_data["completed"], "name": task_data["name"]}
                                )
                                if update_resp.status_code in [200, 201, 204]:
                                    saved_tasks.append(task_data)
                                    print(f"  ✓ Task {task_id} updated after conflict")
                                else:
                                    error_text = update_resp.text[:200] if update_resp.text else ""
                                    print(f"  ✗ ERROR: Failed to update task {task_id} after conflict: {update_resp.status_code} {error_text}")
                                    failed_tasks.append(task_data)
                            except Exception as e:
                                print(f"  ✗ ERROR: Exception updating task {task_id} after conflict: {str(e)}")
                                failed_tasks.append(task_data)
                        else:
                            error_text = task_resp.text[:200] if task_resp.text else ""
                            print(f"  ✗ ERROR: Failed to insert task {task_id}: {task_resp.status_code} {error_text}")
                            print(f"  Task data: {task_data}")
                            failed_tasks.append(task_data)
                except requests.exceptions.HTTPError as e:
                    # If table doesn't exist (404), that's OK
                    if e.response and e.response.status_code == 404:
                        saved_tasks.append({
                            "id": task.get("id") or str(uuid.uuid4()),
                            "inspection_id": inspection_id,
                            "name": task.get("name", ""),
                            "completed": bool(task.get("completed", False)),
                        })
                    else:
                        error_text = e.response.text[:200] if e.response and e.response.text else str(e)
                        print(f"Warning: Failed to save task: {error_text}")
                        failed_tasks.append({
                            "id": task.get("id") or str(uuid.uuid4()),
                            "inspection_id": inspection_id,
                            "name": task.get("name", ""),
                            "completed": bool(task.get("completed", False)),
                        })
                except Exception as e:
                    # Any other error - continue with other tasks
                    print(f"Warning: Exception saving task: {str(e)}")
                    failed_tasks.append({
                        "id": task.get("id") or str(uuid.uuid4()),
                        "inspection_id": inspection_id,
                        "name": task.get("name", ""),
                        "completed": bool(task.get("completed", False)),
                    })
            
            # Only delete tasks that are no longer in the list (cleanup)
            # But only if we successfully saved the new tasks
            # IMPORTANT: Only delete if we saved ALL tasks successfully
            # Also, only delete tasks for THIS specific inspection_id
            if saved_tasks and len(saved_tasks) == len(tasks) and len(failed_tasks) == 0:
                try:
                    saved_task_ids = {t["id"] for t in saved_tasks}
                    # Delete tasks that exist in DB for THIS inspection but are not in the new list
                    if existing_task_ids:
                        tasks_to_delete = existing_task_ids - saved_task_ids
                        if tasks_to_delete:
                            print(f"Cleaning up {len(tasks_to_delete)} orphaned tasks for inspection {inspection_id}: {tasks_to_delete}")
                            for task_id_to_delete in tasks_to_delete:
                                try:
                                    # CRITICAL: Filter by BOTH id AND inspection_id to ensure we only delete tasks for this inspection
                                    delete_resp = requests.delete(
                                        f"{REST_URL}/inspection_tasks?id=eq.{task_id_to_delete}&inspection_id=eq.{inspection_id}",
                                        headers=SERVICE_HEADERS
                                    )
                                    if delete_resp.status_code in [200, 204]:
                                        print(f"  ✓ Deleted orphaned task {task_id_to_delete} for inspection {inspection_id}")
                                    else:
                                        print(f"  ⚠ Failed to delete task {task_id_to_delete} for inspection {inspection_id}: {delete_resp.status_code}")
                                except Exception as e:
                                    print(f"  ✗ Error deleting task {task_id_to_delete} for inspection {inspection_id}: {str(e)}")
                        else:
                            print(f"No orphaned tasks to clean up for inspection {inspection_id}")
                    else:
                        print(f"No existing tasks found for inspection {inspection_id}, skipping cleanup")
                except Exception as e:
                    print(f"Error during cleanup for inspection {inspection_id}: {str(e)}")
            else:
                if len(failed_tasks) > 0:
                    print(f"Skipping cleanup for inspection {inspection_id} - {len(failed_tasks)} tasks failed to save")
                elif len(saved_tasks) < len(tasks):
                    print(f"Skipping cleanup for inspection {inspection_id} - only {len(saved_tasks)}/{len(tasks)} tasks saved")
            
            # Log summary
            print(f"Inspection {inspection_id}: Saved {len(saved_tasks)}/{len(tasks)} tasks. Failed: {len(failed_tasks)}")
            if failed_tasks:
                print(f"WARNING: {len(failed_tasks)} tasks failed to save:")
                for failed_task in failed_tasks[:5]:  # Show first 5 failed tasks
                    print(f"  - Task {failed_task.get('id')} ({failed_task.get('name')})")
            
            if saved_tasks:
                return_tasks = saved_tasks
            else:
                # If all tasks failed, log error but still return original tasks
                print(f"ERROR: All {len(tasks)} tasks failed to save for inspection {inspection_id}!")
                return_tasks = tasks  # Return original tasks so frontend doesn't lose them
        
        # Return the created/updated inspection with tasks
        # Include metadata about save success
        completed_count = sum(1 for t in return_tasks if t.get("completed", False))
        result = {
            "id": inspection_id,
            "orderId": order_id,
            "unitNumber": inspection_data["unit_number"],
            "guestName": inspection_data["guest_name"],
            "departureDate": inspection_data["departure_date"],
            "status": inspection_data["status"],
            "tasks": return_tasks,
            "savedTasksCount": len(saved_tasks),  # Only count actually saved tasks
            "totalTasksCount": len(tasks),
            "completedTasksCount": completed_count,
            "failedTasksCount": len(failed_tasks),  # Add failed count so frontend knows
        }
        print(f"Returning inspection result: {len(return_tasks)} tasks ({len(saved_tasks)} saved, {len(failed_tasks)} failed), {completed_count} completed")
        if return_tasks:
            print(f"Sample task from result: id={return_tasks[0].get('id')}, completed={return_tasks[0].get('completed')}")
        return result
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

# ========== CLEANING INSPECTIONS ENDPOINTS ==========
# These are completely separate from regular inspections

@app.get("/cleaning-inspections")
def cleaning_inspections():
    """Get all cleaning inspections with their tasks"""
    try:
        # Get all cleaning inspections
        inspections_resp = requests.get(
            f"{REST_URL}/cleaning_inspections",
            headers=SERVICE_HEADERS,
            params={"select": "*", "order": "departure_date.desc"}
        )
        
        if inspections_resp.status_code == 404:
            # Table doesn't exist yet, return empty list
            return []
        
        inspections_resp.raise_for_status()
        inspections = inspections_resp.json() or []
        
        # Get all cleaning inspection tasks
        tasks_resp = requests.get(
            f"{REST_URL}/cleaning_inspection_tasks",
            headers=SERVICE_HEADERS,
            params={"select": "*"}
        )
        
        tasks = []
        if tasks_resp.status_code == 200:
            tasks = tasks_resp.json() or []
        elif tasks_resp.status_code == 404:
            # Table doesn't exist yet, that's OK
            tasks = []
        
        # Group tasks by inspection_id
        tasks_by_inspection = {}
        for task in tasks:
            insp_id = task.get("inspection_id")
            if insp_id:
                if insp_id not in tasks_by_inspection:
                    tasks_by_inspection[insp_id] = []
                tasks_by_inspection[insp_id].append(task)
        
        # Combine inspections with their tasks
        result = []
        for inspection in inspections:
            insp_id = inspection.get("id")
            inspection_with_tasks = inspection.copy()
            inspection_with_tasks["tasks"] = tasks_by_inspection.get(insp_id, [])
            result.append(inspection_with_tasks)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching cleaning inspections: {str(e)}")

@app.get("/api/cleaning-inspections")
def api_cleaning_inspections():
    """Alias for /cleaning-inspections to match frontend expectations"""
    return cleaning_inspections()

@app.post("/api/cleaning-inspections/sync")
def sync_all_cleaning_inspections():
    """Sync all cleaning inspections with orders - ensure every departure date has a cleaning inspection"""
    try:
        sync_cleaning_inspections_with_orders()
        return {"status": "success", "message": "Cleaning inspections synced with orders"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing cleaning inspections: {str(e)}")

@app.post("/api/cleaning-inspections")
def create_cleaning_inspection(payload: dict):
    """Create or update a cleaning inspection mission with its tasks"""
    try:
        inspection_id = payload.get("id") or str(uuid.uuid4())
        order_id = payload.get("orderId") or payload.get("order_id")
        
        # Create or update cleaning inspection
        inspection_data = {
            "id": inspection_id,
            "order_id": order_id,
            "unit_number": payload.get("unitNumber") or payload.get("unit_number", ""),
            "guest_name": payload.get("guestName") or payload.get("guest_name", ""),
            "departure_date": payload.get("departureDate") or payload.get("departure_date", ""),
            "status": payload.get("status", "זמן הביקורות טרם הגיע"),
        }
        
        # Check if cleaning inspection exists
        existing = []
        try:
            check_resp = requests.get(
                f"{REST_URL}/cleaning_inspections",
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
            # Update existing cleaning inspection
            try:
                update_resp = requests.patch(
                    f"{REST_URL}/cleaning_inspections?id=eq.{inspection_id}",
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
            # Create new cleaning inspection
            try:
                create_resp = requests.post(
                    f"{REST_URL}/cleaning_inspections",
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
        
        # Handle tasks - use upsert (update or insert) instead of delete + insert
        tasks = payload.get("tasks", [])
        return_tasks = tasks  # Default to original tasks if nothing is saved
        saved_tasks = []
        failed_tasks = []
        
        if tasks:
            # First, get existing tasks for this cleaning inspection
            existing_task_ids = set()
            try:
                existing_resp = requests.get(
                    f"{REST_URL}/cleaning_inspection_tasks",
                    headers=SERVICE_HEADERS,
                    params={"inspection_id": f"eq.{inspection_id}", "select": "id,name"}
                )
                if existing_resp.status_code == 200:
                    existing_tasks = existing_resp.json() or []
                    existing_task_ids = {t.get("id") for t in existing_tasks if t.get("id")}
                    print(f"Found {len(existing_task_ids)} existing cleaning tasks for inspection {inspection_id}: {existing_task_ids}")
                else:
                    print(f"No existing cleaning tasks found for inspection {inspection_id} (status: {existing_resp.status_code})")
            except Exception as e:
                print(f"Error getting existing cleaning tasks for inspection {inspection_id}: {str(e)}")
            
            # Upsert tasks one by one
            for task in tasks:
                try:
                    # Ensure completed is a boolean
                    completed = task.get("completed", False)
                    if isinstance(completed, str):
                        completed = completed.lower() in ('true', '1', 'yes', 'on')
                    elif completed is None:
                        completed = False
                    else:
                        completed = bool(completed)
                    
                    task_data = {
                        "id": task.get("id") or str(uuid.uuid4()),
                        "inspection_id": inspection_id,
                        "name": task.get("name", ""),
                        "completed": completed,
                    }
                    task_id = task_data["id"]
                    print(f"Saving cleaning task {task_id} ({task_data['name']}): completed={completed}")
                    
                    # Try to update if task exists for THIS inspection, otherwise insert
                    task_exists_for_this_inspection = task_id in existing_task_ids
                    
                    if task_exists_for_this_inspection:
                        # Task exists for this inspection, update it
                        print(f"  → Updating existing cleaning task {task_id} for inspection {inspection_id}")
                        update_resp = requests.patch(
                            f"{REST_URL}/cleaning_inspection_tasks?id=eq.{task_id}&inspection_id=eq.{inspection_id}",
                            headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                            json={"completed": task_data["completed"], "name": task_data["name"]}
                        )
                        if update_resp.status_code in [200, 201, 204]:
                            saved_tasks.append(task_data)
                            print(f"  ✓ Cleaning task {task_id} updated successfully")
                        else:
                            # Update failed, try insert
                            print(f"  ⚠ Update failed (status {update_resp.status_code}), trying insert...")
                            task_resp = requests.post(
                                f"{REST_URL}/cleaning_inspection_tasks",
                                headers=SERVICE_HEADERS,
                                json=task_data
                            )
                            if task_resp.status_code in [200, 201]:
                                saved_tasks.append(task_data)
                                print(f"  ✓ Cleaning task {task_id} inserted successfully (after update failed)")
                            elif task_resp.status_code == 404:
                                error_text = task_resp.text[:200] if task_resp.text else ""
                                print(f"  ✗ ERROR: Table doesn't exist (404) - cleaning task {task_id} NOT saved: {error_text}")
                                failed_tasks.append(task_data)
                            else:
                                error_text = task_resp.text[:200] if task_resp.text else ""
                                print(f"  ✗ ERROR: Failed to insert cleaning task {task_id} after update failed: {task_resp.status_code} {error_text}")
                                failed_tasks.append(task_data)
                    else:
                        # Task doesn't exist for this inspection, insert it
                        print(f"  → Inserting new cleaning task {task_id} for inspection {inspection_id}")
                        task_resp = requests.post(
                            f"{REST_URL}/cleaning_inspection_tasks",
                            headers=SERVICE_HEADERS,
                            json=task_data
                        )
                        if task_resp.status_code in [200, 201]:
                            saved_tasks.append(task_data)
                            print(f"  ✓ Cleaning task {task_id} inserted successfully")
                        elif task_resp.status_code == 404:
                            error_text = task_resp.text[:200] if task_resp.text else ""
                            print(f"  ✗ ERROR: Table doesn't exist (404) - cleaning task {task_id} NOT saved: {error_text}")
                            failed_tasks.append(task_data)
                        elif task_resp.status_code == 409:
                            # Conflict - try to update it for this inspection_id
                            print(f"  ⚠ Conflict (409) - cleaning task {task_id} may exist for another inspection, trying update...")
                            try:
                                update_resp = requests.patch(
                                    f"{REST_URL}/cleaning_inspection_tasks?id=eq.{task_id}&inspection_id=eq.{inspection_id}",
                                    headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                                    json={"completed": task_data["completed"], "name": task_data["name"]}
                                )
                                if update_resp.status_code in [200, 201, 204]:
                                    saved_tasks.append(task_data)
                                    print(f"  ✓ Cleaning task {task_id} updated after conflict")
                                else:
                                    error_text = update_resp.text[:200] if update_resp.text else ""
                                    print(f"  ✗ ERROR: Failed to update cleaning task {task_id} after conflict: {update_resp.status_code} {error_text}")
                                    failed_tasks.append(task_data)
                            except Exception as e:
                                print(f"  ✗ ERROR: Exception updating cleaning task {task_id} after conflict: {str(e)}")
                                failed_tasks.append(task_data)
                        else:
                            error_text = task_resp.text[:200] if task_resp.text else ""
                            print(f"  ✗ ERROR: Failed to insert cleaning task {task_id}: {task_resp.status_code} {error_text}")
                            failed_tasks.append(task_data)
                except requests.exceptions.HTTPError as e:
                    if e.response and e.response.status_code == 404:
                        saved_tasks.append({
                            "id": task.get("id") or str(uuid.uuid4()),
                            "inspection_id": inspection_id,
                            "name": task.get("name", ""),
                            "completed": bool(task.get("completed", False)),
                        })
                    else:
                        error_text = e.response.text[:200] if e.response and e.response.text else str(e)
                        print(f"Warning: Failed to save cleaning task: {error_text}")
                        failed_tasks.append({
                            "id": task.get("id") or str(uuid.uuid4()),
                            "inspection_id": inspection_id,
                            "name": task.get("name", ""),
                            "completed": bool(task.get("completed", False)),
                        })
                except Exception as e:
                    print(f"Warning: Exception saving cleaning task: {str(e)}")
                    failed_tasks.append({
                        "id": task.get("id") or str(uuid.uuid4()),
                        "inspection_id": inspection_id,
                        "name": task.get("name", ""),
                        "completed": bool(task.get("completed", False)),
                    })
            
            # Only delete tasks that are no longer in the list (cleanup)
            if saved_tasks and len(saved_tasks) == len(tasks) and len(failed_tasks) == 0:
                try:
                    saved_task_ids = {t["id"] for t in saved_tasks}
                    if existing_task_ids:
                        tasks_to_delete = existing_task_ids - saved_task_ids
                        if tasks_to_delete:
                            print(f"Cleaning up {len(tasks_to_delete)} orphaned cleaning tasks for inspection {inspection_id}: {tasks_to_delete}")
                            for task_id_to_delete in tasks_to_delete:
                                try:
                                    delete_resp = requests.delete(
                                        f"{REST_URL}/cleaning_inspection_tasks?id=eq.{task_id_to_delete}&inspection_id=eq.{inspection_id}",
                                        headers=SERVICE_HEADERS
                                    )
                                    if delete_resp.status_code in [200, 204]:
                                        print(f"  ✓ Deleted orphaned cleaning task {task_id_to_delete} for inspection {inspection_id}")
                                    else:
                                        print(f"  ⚠ Failed to delete cleaning task {task_id_to_delete} for inspection {inspection_id}: {delete_resp.status_code}")
                                except Exception as e:
                                    print(f"  ✗ Error deleting cleaning task {task_id_to_delete} for inspection {inspection_id}: {str(e)}")
                except Exception as e:
                    print(f"Error during cleanup for cleaning inspection {inspection_id}: {str(e)}")
            
            # Log summary
            print(f"Cleaning inspection {inspection_id}: Saved {len(saved_tasks)}/{len(tasks)} tasks. Failed: {len(failed_tasks)}")
            if failed_tasks:
                print(f"WARNING: {len(failed_tasks)} cleaning tasks failed to save:")
                for failed_task in failed_tasks[:5]:
                    print(f"  - Cleaning task {failed_task.get('id')} ({failed_task.get('name')})")
            
            if saved_tasks:
                return_tasks = saved_tasks
            else:
                print(f"ERROR: All {len(tasks)} cleaning tasks failed to save for inspection {inspection_id}!")
                return_tasks = tasks
        
        # Return the created/updated cleaning inspection with tasks
        completed_count = sum(1 for t in return_tasks if t.get("completed", False))
        result = {
            "id": inspection_id,
            "orderId": order_id,
            "unitNumber": inspection_data["unit_number"],
            "guestName": inspection_data["guest_name"],
            "departureDate": inspection_data["departure_date"],
            "status": inspection_data["status"],
            "tasks": return_tasks,
            "savedTasksCount": len(saved_tasks),
            "totalTasksCount": len(tasks),
            "completedTasksCount": completed_count,
            "failedTasksCount": len(failed_tasks),
        }
        print(f"Returning cleaning inspection result: {len(return_tasks)} tasks ({len(saved_tasks)} saved, {len(failed_tasks)} failed), {completed_count} completed")
        return result
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating/updating cleaning inspection: {str(e)}")

@app.patch("/api/cleaning-inspections/{inspection_id}/tasks/{task_id}")
def update_cleaning_inspection_task(inspection_id: str, task_id: str, payload: dict):
    """Update a single cleaning inspection task (e.g., toggle completion). Creates task if it doesn't exist."""
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
                f"{REST_URL}/cleaning_inspection_tasks",
                headers=SERVICE_HEADERS,
                params={"id": f"eq.{task_id}", "inspection_id": f"eq.{inspection_id}", "select": "*"}
            )
            if check_resp.status_code == 200:
                existing_tasks = check_resp.json() or []
                if existing_tasks and len(existing_tasks) > 0:
                    existing_task = existing_tasks[0]
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 404:
                existing_task = None
            else:
                existing_task = None
        
        if existing_task:
            # Update existing task
            update_resp = requests.patch(
                f"{REST_URL}/cleaning_inspection_tasks?id=eq.{task_id}&inspection_id=eq.{inspection_id}",
                headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                json=task_data
            )
            if update_resp.status_code in [200, 201, 204]:
                try:
                    result = update_resp.json()
                    updated_task = result[0] if isinstance(result, list) and result else result
                    return {
                        "id": updated_task.get("id") if isinstance(updated_task, dict) else task_id,
                        "name": updated_task.get("name") if isinstance(updated_task, dict) else existing_task.get("name", ""),
                        "completed": updated_task.get("completed", False) if isinstance(updated_task, dict) else task_data.get("completed", False),
                    }
                except:
                    return {
                        "id": task_id,
                        "name": existing_task.get("name", ""),
                        "completed": task_data.get("completed", False),
                    }
        
        # Task doesn't exist, create it
        task_name = task_data.get("name") or payload.get("name", "")
        create_data = {
            "id": task_id,
            "inspection_id": inspection_id,
            "name": task_name,
            "completed": task_data.get("completed", False),
        }
        
        try:
            create_resp = requests.post(
                f"{REST_URL}/cleaning_inspection_tasks",
                headers=SERVICE_HEADERS,
                json=create_data
            )
            if create_resp.status_code == 404:
                return create_data
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
            if e.response and e.response.status_code == 404:
                return create_data
            return create_data
        except Exception:
            return create_data
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 404:
            return {
                "id": task_id,
                "name": payload.get("name", ""),
                "completed": payload.get("completed", False),
            }
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
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
        "status": payload.get("status", "מחכה להשלמת תשלום"),
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

@app.post("/api/storage/upload")
async def upload_to_storage(request: Request):
    """
    Upload a file to Supabase Storage.
    Returns the public URL of the uploaded file.
    """
    try:
        form = await request.form()
        media = form.get("file")
        if not media or not hasattr(media, "filename"):
            raise HTTPException(status_code=400, detail="File is required")
        
        filename = getattr(media, "filename", None) or f"upload-{uuid.uuid4()}"
        content_type = getattr(media, "content_type", None) or "application/octet-stream"
        raw = await media.read()
        
        # Determine bucket based on content type (using "vidoes" bucket as shown in Supabase)
        bucket = "vidoes" if content_type.startswith("video/") else "images"
        
        # Generate unique filename
        file_ext = filename.split(".")[-1] if "." in filename else ("mp4" if content_type.startswith("video/") else "jpg")
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # Upload to Supabase Storage
        upload_url = f"{STORAGE_URL}/object/{bucket}/{unique_filename}"
        upload_headers = {
            **STORAGE_HEADERS,
            "Content-Type": content_type,
        }
        
        resp = requests.put(upload_url, headers=upload_headers, data=raw)
        if resp.status_code not in [200, 201]:
            error_text = resp.text[:200] if resp.text else "Unknown error"
            raise HTTPException(status_code=500, detail=f"Storage upload failed: {error_text}")
        
        # Get public URL
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{unique_filename}"
        
        return {"url": public_url, "filename": unique_filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

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
                # If imageUri is provided in JSON payload, check if it's a data URI and upload to storage
                if "imageUri" in data:
                    image_uri = data.pop("imageUri")
                    # If it's a data URI (especially for videos), upload to storage
                    if image_uri and image_uri.startswith("data:"):
                        try:
                            # Extract mime type and base64 data
                            parts = image_uri.split(",", 1)
                            if len(parts) == 2:
                                mime_part = parts[0].split(";")[0]
                                mime_type = mime_part.replace("data:", "") if mime_part.startswith("data:") else "application/octet-stream"
                                base64_data = parts[1]
                                
                                # Decode base64
                                raw = base64.b64decode(base64_data)
                                
                                # Determine bucket (using "vidoes" as shown in Supabase)
                                bucket = "vidoes" if mime_type.startswith("video/") else "images"
                                
                                # Generate unique filename
                                file_ext = "mp4" if mime_type.startswith("video/") else ("jpg" if "jpeg" in mime_type else "png")
                                unique_filename = f"{uuid.uuid4()}.{file_ext}"
                                
                                # Upload to Supabase Storage
                                upload_url = f"{STORAGE_URL}/object/{bucket}/{unique_filename}"
                                upload_headers = {
                                    **STORAGE_HEADERS,
                                    "Content-Type": mime_type,
                                }
                                
                                resp = requests.put(upload_url, headers=upload_headers, data=raw)
                                if resp.status_code in [200, 201]:
                                    # Use public URL from storage
                                    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{unique_filename}"
                                    data["image_uri"] = public_url
                                else:
                                    # Fallback to data URI if storage upload fails
                                    data["image_uri"] = image_uri
                            else:
                                data["image_uri"] = image_uri
                        except Exception as e:
                            # Fallback to data URI if conversion fails
                            print(f"Error uploading data URI to storage: {e}")
                            data["image_uri"] = image_uri
                    else:
                        data["image_uri"] = image_uri
        else:
            form = await request.form()
            data = {k: v for k, v in form.items() if k != "media"}
            media = form.get("media")
            if media is not None and hasattr(media, "filename"):
                # Upload to Supabase Storage instead of storing as data URI
                filename = getattr(media, "filename", None) or "upload.bin"
                content_type = getattr(media, "content_type", None) or "application/octet-stream"
                raw = await media.read()
                
                # Determine bucket based on content type (using "vidoes" as shown in Supabase)
                bucket = "vidoes" if content_type.startswith("video/") else "images"
                
                # Generate unique filename
                file_ext = filename.split(".")[-1] if "." in filename else ("mp4" if content_type.startswith("video/") else "jpg")
                unique_filename = f"{uuid.uuid4()}.{file_ext}"
                
                # Upload to Supabase Storage
                upload_url = f"{STORAGE_URL}/object/{bucket}/{unique_filename}"
                upload_headers = {
                    **STORAGE_HEADERS,
                    "Content-Type": content_type,
                }
                
                resp = requests.put(upload_url, headers=upload_headers, data=raw)
                if resp.status_code not in [200, 201]:
                    # Fallback to data URI if storage upload fails
                    b64 = base64.b64encode(raw).decode("ascii")
                    media_data_uri = f"data:{content_type};base64,{b64}"
                    data["image_uri"] = media_data_uri
                else:
                    # Use public URL from storage
                    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{unique_filename}"
                    data["image_uri"] = public_url

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
            result = body[0] if isinstance(body, list) and body else body
            
            # Send push notification if task was assigned
            if "assigned_to" in data and data["assigned_to"]:
                assigned_to = data["assigned_to"]
                # Get username from user ID if needed
                user_resp = requests.get(
                    f"{REST_URL}/users",
                    headers=SERVICE_HEADERS,
                    params={"id": f"eq.{assigned_to}", "select": "username"}
                )
                username = assigned_to  # Default to ID
                if user_resp.status_code == 200:
                    users = user_resp.json() or []
                    if users:
                        username = users[0].get("username", assigned_to)
                
                task_title = result.get("title", "ללא כותרת")
                send_push_notification_to_user(
                    username,
                    "משימה חדשה הוקצתה לך",
                    f"משימת תחזוקה חדשה: {task_title}"
                )
            
            return result
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
        # Get previous task to check if assigned_to changed
        prev_resp = requests.get(
            f"{REST_URL}/maintenance_tasks?id=eq.{task_id}",
            headers=SERVICE_HEADERS
        )
        prev_task = None
        if prev_resp.status_code == 200:
            prev_tasks = prev_resp.json() or []
            if prev_tasks:
                prev_task = prev_tasks[0]
        
        headers = {**SERVICE_HEADERS, "Prefer": "return=representation"}
        resp = requests.patch(
            f"{REST_URL}/maintenance_tasks?id=eq.{task_id}",
            headers=headers,
            json=data
        )
        resp.raise_for_status()
        if resp.text:
            result = resp.json()
            updated_task = result[0] if isinstance(result, list) and result else result
            
            # Send push notification if task was assigned to someone
            if "assigned_to" in data and data["assigned_to"]:
                assigned_to = data["assigned_to"]
                prev_assigned = prev_task.get("assigned_to") if prev_task else None
                
                # Only send if assignment changed
                if assigned_to != prev_assigned:
                    # Get username from user ID if needed
                    user_resp = requests.get(
                        f"{REST_URL}/users",
                        headers=SERVICE_HEADERS,
                        params={"id": f"eq.{assigned_to}", "select": "username"}
                    )
                    username = assigned_to  # Default to ID
                    if user_resp.status_code == 200:
                        users = user_resp.json() or []
                        if users:
                            username = users[0].get("username", assigned_to)
                    
                    task_title = updated_task.get("title", "ללא כותרת")
                    send_push_notification_to_user(
                        username,
                        "משימה חדשה הוקצתה לך",
                        f"משימת תחזוקה חדשה: {task_title}"
                    )
            
            return updated_task
        return {"id": task_id, "message": "Updated successfully"}
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating maintenance task: {str(e)}")

@app.patch("/api/maintenance/tasks/{task_id}")
async def api_update_maintenance_task(request: Request, task_id: str):
    """
    Update maintenance task.
    
    Supports both:
    - application/json (legacy)
    - multipart/form-data with optional file field `media`
    """
    content_type = (request.headers.get("content-type") or "").lower()
    
    data: dict = {}
    media_data_uri: Optional[str] = None
    
    try:
        if content_type.startswith("application/json"):
            payload = await request.json()
            if isinstance(payload, dict):
                data = payload
                # If imageUri is provided in JSON payload, check if it's a data URI and upload to storage
                if "imageUri" in data or "image_uri" in data:
                    image_uri = data.pop("imageUri", None) or data.pop("image_uri", None)
                    if image_uri:
                        # If it's a data URI (especially for videos), upload to storage
                        if image_uri.startswith("data:"):
                            try:
                                # Extract mime type and base64 data
                                parts = image_uri.split(",", 1)
                                if len(parts) == 2:
                                    mime_part = parts[0].split(";")[0]
                                    mime_type = mime_part.replace("data:", "") if mime_part.startswith("data:") else "application/octet-stream"
                                    base64_data = parts[1]
                                    
                                    # Decode base64
                                    raw = base64.b64decode(base64_data)
                                    
                                    # Determine bucket (using "vidoes" as shown in Supabase)
                                    bucket = "vidoes" if mime_type.startswith("video/") else "images"
                                    
                                    # Generate unique filename
                                    file_ext = "mp4" if mime_type.startswith("video/") else ("jpg" if "jpeg" in mime_type else "png")
                                    unique_filename = f"{uuid.uuid4()}.{file_ext}"
                                    
                                    # Upload to Supabase Storage
                                    upload_url = f"{STORAGE_URL}/object/{bucket}/{unique_filename}"
                                    upload_headers = {
                                        **STORAGE_HEADERS,
                                        "Content-Type": mime_type,
                                    }
                                    
                                    resp = requests.put(upload_url, headers=upload_headers, data=raw)
                                    if resp.status_code in [200, 201]:
                                        # Use public URL from storage
                                        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{unique_filename}"
                                        data["image_uri"] = public_url
                                    else:
                                        # Fallback to data URI if storage upload fails
                                        data["image_uri"] = image_uri
                                else:
                                    data["image_uri"] = image_uri
                            except Exception as e:
                                # Fallback to data URI if conversion fails
                                print(f"Error uploading data URI to storage: {e}")
                                data["image_uri"] = image_uri
                        else:
                            data["image_uri"] = image_uri
        else:
            # multipart/form-data
            form = await request.form()
            data = {k: v for k, v in form.items() if k != "media"}
            media = form.get("media")
            if media is not None and hasattr(media, "filename"):
                # Upload to Supabase Storage instead of storing as data URI
                filename = getattr(media, "filename", None) or "upload.bin"
                content_type_media = getattr(media, "content_type", None) or "application/octet-stream"
                raw = await media.read()
                
                # Determine bucket based on content type (using "vidoes" as shown in Supabase)
                bucket = "vidoes" if content_type_media.startswith("video/") else "images"
                
                # Generate unique filename
                file_ext = filename.split(".")[-1] if "." in filename else ("mp4" if content_type_media.startswith("video/") else "jpg")
                unique_filename = f"{uuid.uuid4()}.{file_ext}"
                
                # Upload to Supabase Storage
                upload_url = f"{STORAGE_URL}/object/{bucket}/{unique_filename}"
                upload_headers = {
                    **STORAGE_HEADERS,
                    "Content-Type": content_type_media,
                }
                
                resp = requests.put(upload_url, headers=upload_headers, data=raw)
                if resp.status_code not in [200, 201]:
                    # Fallback to data URI if storage upload fails
                    b64 = base64.b64encode(raw).decode("ascii")
                    media_data_uri = f"data:{content_type_media};base64,{b64}"
                    data["image_uri"] = media_data_uri
                else:
                    # Use public URL from storage
                    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{unique_filename}"
                    data["image_uri"] = public_url
        
        # Normalize keys for Supabase schema
        if "unitId" in data:
            data["unit_id"] = data.pop("unitId")
        if "createdDate" in data:
            data["created_date"] = data.pop("createdDate")
        if "assignedTo" in data:
            assigned_value = data.pop("assignedTo")
            if assigned_value:
                data["assigned_to"] = assigned_value
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        if not data:
            return {"message": "No changes provided"}
        
        # Get previous task to check if assigned_to changed
        prev_resp = requests.get(
            f"{REST_URL}/maintenance_tasks?id=eq.{task_id}",
            headers=SERVICE_HEADERS
        )
        prev_task = None
        if prev_resp.status_code == 200:
            prev_tasks = prev_resp.json() or []
            if prev_tasks:
                prev_task = prev_tasks[0]
        
        # Update in Supabase
        headers = {**SERVICE_HEADERS, "Prefer": "return=representation"}
        resp = requests.patch(
            f"{REST_URL}/maintenance_tasks?id=eq.{task_id}",
            headers=headers,
            json=data
        )
        resp.raise_for_status()
        if resp.text:
            result = resp.json()
            updated_task = result[0] if isinstance(result, list) and result else result
            
            # Send push notification if task was assigned to someone
            if "assigned_to" in data and data["assigned_to"]:
                assigned_to = data["assigned_to"]
                prev_assigned = prev_task.get("assigned_to") if prev_task else None
                
                # Only send if assignment changed
                if assigned_to != prev_assigned:
                    # Get username from user ID if needed
                    user_resp = requests.get(
                        f"{REST_URL}/users",
                        headers=SERVICE_HEADERS,
                        params={"id": f"eq.{assigned_to}", "select": "username"}
                    )
                    username = assigned_to  # Default to ID
                    if user_resp.status_code == 200:
                        users = user_resp.json() or []
                        if users:
                            username = users[0].get("username", assigned_to)
                    
                    task_title = updated_task.get("title", "ללא כותרת")
                    send_push_notification_to_user(
                        username,
                        "משימה חדשה הוקצתה לך",
                        f"משימת תחזוקה חדשה: {task_title}"
                    )
            
            return updated_task
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
        
        # Calculate expenses from invoices instead of expenses table
        total_expenses = 0
        try:
            invoices_resp = requests.get(f"{REST_URL}/invoices", headers=SERVICE_HEADERS, params={"select": "total_price,extracted_data"})
            invoices_resp.raise_for_status()
            invoices = invoices_resp.json() or []
            
            for invoice in invoices:
                amount = 0
                # Try to get amount from extracted_data first (simplified schema)
                extracted_data = invoice.get("extracted_data")
                if extracted_data:
                    if isinstance(extracted_data, str):
                        try:
                            extracted_data = json.loads(extracted_data)
                        except:
                            extracted_data = None
                    if isinstance(extracted_data, dict):
                        amount = extracted_data.get("total_price") or 0
                
                # Fallback to invoice-level total_price
                if not amount:
                    amount = invoice.get("total_price") or 0
                
                if amount:
                    try:
                        total_expenses += float(amount) if amount else 0
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            print(f"Warning: Could not fetch invoices for expenses calculation: {e}")
        
        total_revenue = sum((o.get("total_amount") or 0) for o in orders)
        total_paid = sum((o.get("paid_amount") or 0) for o in orders)
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
            result = body[0] if isinstance(body, list) and body else result
            
            # Send push notifications to all users except sender
            sender = data.get("sender", "")
            if sender:
                # Get all users
                users_resp = requests.get(
                    f"{REST_URL}/users",
                    headers=SERVICE_HEADERS,
                    params={"select": "username"}
                )
                if users_resp.status_code == 200:
                    users = users_resp.json() or []
                    for user in users:
                        user_username = user.get("username", "")
                        if user_username and user_username != sender:
                            message_content = data.get("content", "")
                            message_preview = message_content[:50] + "..." if len(message_content) > 50 else message_content
                            send_push_notification_to_user(
                                user_username,
                                f"הודעה חדשה מ-{sender}",
                                message_preview
                            )
            
            return result
        return data
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:400]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending chat message: {str(e)}")

# Push notification endpoints
@app.post("/api/push/subscribe")
def subscribe_push(payload: PushSubscriptionRequest):
    """Register a push subscription for a user"""
    try:
        if not payload.username:
            raise HTTPException(status_code=400, detail="username is required")
        if payload.type not in ["web", "fcm"]:
            raise HTTPException(status_code=400, detail="type must be 'web' or 'fcm'")
        
        subscription_data = {
            "username": payload.username,
            "type": payload.type,
            "created_at": datetime.now().isoformat()
        }
        
        if payload.type == "web":
            if not payload.subscription:
                raise HTTPException(status_code=400, detail="subscription is required for web push")
            subscription_data["endpoint"] = payload.subscription.endpoint
            subscription_data["p256dh"] = payload.subscription.keys.get("p256dh", "")
            subscription_data["auth"] = payload.subscription.keys.get("auth", "")
        elif payload.type == "fcm":
            if not payload.fcm_token:
                raise HTTPException(status_code=400, detail="fcm_token is required for FCM")
            subscription_data["fcm_token"] = payload.fcm_token
        
        # Check if subscription already exists (by endpoint for web, fcm_token for FCM)
        check_field = "endpoint" if payload.type == "web" else "fcm_token"
        check_value = subscription_data.get(check_field)
        if check_value:
            check_resp = requests.get(
                f"{REST_URL}/push_subscriptions",
                headers=SERVICE_HEADERS,
                params={check_field: f"eq.{check_value}", "select": "id"}
            )
            if check_resp.status_code == 200:
                existing = check_resp.json() or []
                if existing:
                    # Update existing subscription
                    sub_id = existing[0]["id"]
                    update_resp = requests.patch(
                        f"{REST_URL}/push_subscriptions?id=eq.{sub_id}",
                        headers=SERVICE_HEADERS,
                        json=subscription_data
                    )
                    update_resp.raise_for_status()
                    return {"message": "Subscription updated", "id": sub_id}
        
        # Create new subscription
        subscription_data["id"] = str(uuid.uuid4())
        resp = requests.post(
            f"{REST_URL}/push_subscriptions",
            headers=SERVICE_HEADERS,
            json=subscription_data
        )
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return subscription_data
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:400]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error subscribing to push: {str(e)}")

@app.post("/api/push/unsubscribe")
def unsubscribe_push(payload: dict):
    """Unregister a push subscription"""
    try:
        username = payload.get("username")
        subscription_id = payload.get("subscription_id")
        endpoint = payload.get("endpoint")
        fcm_token = payload.get("fcm_token")
        
        if not username:
            raise HTTPException(status_code=400, detail="username is required")
        
        # Build delete query
        params = {"username": f"eq.{username}"}
        if subscription_id:
            params["id"] = f"eq.{subscription_id}"
        elif endpoint:
            params["endpoint"] = f"eq.{endpoint}"
        elif fcm_token:
            params["fcm_token"] = f"eq.{fcm_token}"
        else:
            raise HTTPException(status_code=400, detail="subscription_id, endpoint, or fcm_token is required")
        
        resp = requests.delete(
            f"{REST_URL}/push_subscriptions",
            headers=SERVICE_HEADERS,
            params=params
        )
        resp.raise_for_status()
        return {"message": "Unsubscribed successfully"}
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:400]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error unsubscribing from push: {str(e)}")

@app.get("/api/push/vapid-public-key")
def get_vapid_public_key():
    """Get VAPID public key for Web Push registration"""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="VAPID keys not configured")
    return {"publicKey": VAPID_PUBLIC_KEY}

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

@app.get("/api/attendance/logs/all")
def api_attendance_logs_all():
    """
    Get all attendance logs (no limit) for employee management.
    """
    try:
        resp = requests.get(f"{REST_URL}/attendance_logs", headers=SERVICE_HEADERS, params={"select": "*", "order": "clock_in.desc"})
        resp.raise_for_status()
        return resp.json() or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching attendance logs: {str(e)}")

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
        
        # Ensure data types are correct - Supabase expects date and time as strings in ISO format
        # Remove any extra fields that might cause issues
        clean_data = {
            "id": data.get("id"),
            "date": str(data.get("date")),  # Ensure it's a string
            "start_time": str(data.get("start_time")),  # Ensure it's a string
            "end_time": str(data.get("end_time")),  # Ensure it's a string
            "cleaner_name": str(data.get("cleaner_name")).strip(),  # Ensure it's a string and trimmed
        }
        
        resp = requests.post(
            f"{REST_URL}/cleaning_schedule",
            headers=SERVICE_HEADERS,
            json=clean_data
        )
        
        # Handle 400 errors specifically to provide better error messages
        if resp.status_code == 400:
            error_text = resp.text[:500] if resp.text else "Bad Request"
            try:
                error_json = resp.json()
                if isinstance(error_json, dict) and "message" in error_json:
                    error_text = error_json["message"]
                elif isinstance(error_json, dict) and "detail" in error_json:
                    error_text = error_json["detail"]
            except:
                pass
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request data: {error_text}. Please check that date, start_time, end_time, and cleaner_name are provided correctly."
            )
        
        resp.raise_for_status()
        if resp.text:
            body = resp.json()
            return body[0] if isinstance(body, list) and body else body
        return clean_data
    except HTTPException:
        raise
    except requests.exceptions.HTTPError as e:
        # If table doesn't exist (404), provide a helpful error message
        if e.response and e.response.status_code == 404:
            raise HTTPException(
                status_code=404, 
                detail="Cleaning schedule table does not exist. Please create the table in Supabase first."
            )
        # Re-raise 400 errors that we already handled
        if e.response and e.response.status_code == 400:
            raise
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

# Monthly Inspections Endpoints
def sync_monthly_inspections():
    """Sync monthly inspections - ensure each hotel has an inspection for current month and next month"""
    try:
        from datetime import date
        from calendar import monthrange
        
        # Get current month and next month (first day of each month)
        today = date.today()
        current_month = date(today.year, today.month, 1)
        
        # Calculate next month
        if today.month == 12:
            next_month = date(today.year + 1, 1, 1)
        else:
            next_month = date(today.year, today.month + 1, 1)
        
        months_to_sync = [current_month, next_month]
        
        # List of all hotels/units (from UNIT_CATEGORIES)
        UNIT_NAMES = [
            'צימרים כלנית ריזורט',
            'וילה ויקטוריה',
            'וילה כלנית',
            'וילה ממלכת אהרון',
            'וילה בוטיק אהרון',
            'וילה אירופה',
            'וילאה 1',
            'וילאה 2',
            'לה כינרה',
            'הודולה 1',
            'הודולה 2',
            'הודולה 3',
            'הודולה 4',
            'הודולה 5',
            'בית קונפיטה',
        ]
        
        # Get all existing monthly inspections
        existing_resp = requests.get(
            f"{REST_URL}/monthly_inspections",
            headers=SERVICE_HEADERS,
            params={"select": "id,unit_number,inspection_month"}
        )
        
        existing_inspections = []
        if existing_resp.status_code == 200:
            existing_inspections = existing_resp.json() or []
            print(f"Found {len(existing_inspections)} existing monthly inspections")
        elif existing_resp.status_code == 404:
            print("WARNING: monthly_inspections table returned 404 - table may not exist")
            existing_inspections = []
        else:
            print(f"WARNING: Failed to get existing monthly inspections: {existing_resp.status_code} {existing_resp.text[:200]}")
            existing_inspections = []
        
        # Create a set of (unit_number, inspection_month) tuples for existing inspections
        existing_keys = set()
        for insp in existing_inspections:
            unit = insp.get("unit_number", "").strip()
            month = insp.get("inspection_month")
            if unit and month:
                existing_keys.add((unit, month))
        
        # Create inspections for each hotel and month combination
        created_count = 0
        for unit_number in UNIT_NAMES:
            for inspection_month in months_to_sync:
                month_str = inspection_month.isoformat()
                key = (unit_number, month_str)
                
                if key not in existing_keys:
                    # Create new monthly inspection
                    inspection_id = f"MONTHLY-{unit_number.replace(' ', '-')}-{month_str}"
                    
                    inspection_data = {
                        "id": inspection_id,
                        "unit_number": unit_number,
                        "inspection_month": month_str,
                        "status": "זמן הביקורות טרם הגיע",
                    }
                    
                    try:
                        create_resp = requests.post(
                            f"{REST_URL}/monthly_inspections",
                            headers=SERVICE_HEADERS,
                            json=inspection_data
                        )
                        if create_resp.status_code in [200, 201]:
                            created_count += 1
                            print(f"Created monthly inspection {inspection_id} for {unit_number} on {month_str}")
                            
                            # Create default tasks for this inspection
                            for task in DEFAULT_MONTHLY_INSPECTION_TASKS:
                                task_data = {
                                    "id": task["id"],
                                    "inspection_id": inspection_id,
                                    "name": task["name"],
                                    "completed": False,
                                }
                                try:
                                    task_resp = requests.post(
                                        f"{REST_URL}/monthly_inspection_tasks",
                                        headers=SERVICE_HEADERS,
                                        json=task_data
                                    )
                                    if task_resp.status_code not in [200, 201, 409]:
                                        print(f"Warning: Failed to create task {task['id']} for inspection {inspection_id}: {task_resp.status_code} {task_resp.text[:200]}")
                                except Exception as e:
                                    print(f"Warning: Error creating task {task['id']} for inspection {inspection_id}: {str(e)}")
                        elif create_resp.status_code == 409:
                            # Already exists, that's OK
                            print(f"Monthly inspection {inspection_id} already exists for {unit_number} on {month_str}")
                        elif create_resp.status_code == 404:
                            # Table doesn't exist yet - this is an error, not OK
                            error_text = create_resp.text[:500] if create_resp.text else "No error text"
                            print(f"ERROR: monthly_inspections table does not exist! Please run create_monthly_inspections_tables.sql")
                            print(f"  Response: {error_text}")
                            # Don't raise - continue with other hotels, but log clearly
                        else:
                            error_text = create_resp.text[:500] if create_resp.text else "No error text"
                            print(f"Warning: Failed to create monthly inspection {inspection_id} for {unit_number} on {month_str}: {create_resp.status_code}")
                            print(f"  Error: {error_text}")
                    except Exception as e:
                        print(f"Exception creating monthly inspection for {unit_number} on {month_str}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        # Don't raise - continue with other hotels
        
        # Remove inspections for months that are not current or next
        months_to_keep = {m.isoformat() for m in months_to_sync}
        removed_count = 0
        for insp in existing_inspections:
            month = insp.get("inspection_month")
            if month and month not in months_to_keep:
                inspection_id = insp.get("id")
                try:
                    delete_resp = requests.delete(
                        f"{REST_URL}/monthly_inspections?id=eq.{inspection_id}",
                        headers=SERVICE_HEADERS
                    )
                    if delete_resp.status_code in [200, 204]:
                        removed_count += 1
                        print(f"Removed old monthly inspection {inspection_id} for month {month}")
                except Exception as e:
                    print(f"Warning: Error removing old monthly inspection {inspection_id}: {str(e)}")
        
        print(f"Synced monthly inspections: created {created_count}, removed {removed_count} for {len(UNIT_NAMES)} hotels across {len(months_to_sync)} months")
        print(f"Expected: {len(UNIT_NAMES) * len(months_to_sync)} total inspections ({len(UNIT_NAMES)} hotels × {len(months_to_sync)} months)")
        if created_count == 0 and len(existing_inspections) == 0:
            print("WARNING: No inspections were created and none exist. Check if table exists and sync logic.")
    except Exception as e:
        print(f"ERROR syncing monthly inspections: {str(e)}")
        import traceback
        traceback.print_exc()

@app.get("/api/monthly-inspections")
def get_monthly_inspections():
    """Get all monthly inspections"""
    try:
        print("GET /api/monthly-inspections - Starting sync...")
        sync_monthly_inspections()  # Sync before returning
        print("GET /api/monthly-inspections - Sync completed, fetching inspections...")
        resp = requests.get(
            f"{REST_URL}/monthly_inspections",
            headers=SERVICE_HEADERS,
            params={"select": "*,monthly_inspection_tasks(*)", "order": "inspection_month.asc,unit_number.asc"}
        )
        if resp.status_code == 404:
            print("WARNING: monthly_inspections table returned 404 - table may not exist")
            return []
        resp.raise_for_status()
        inspections = resp.json() or []
        print(f"GET /api/monthly-inspections - Found {len(inspections)} inspections in database")
        
        # Format response similar to regular inspections
        result = []
        for insp in inspections:
            tasks = insp.get("monthly_inspection_tasks", [])
            result.append({
                "id": insp.get("id"),
                "unitNumber": insp.get("unit_number"),
                "inspectionMonth": insp.get("inspection_month"),
                "status": insp.get("status", "זמן הביקורות טרם הגיע"),
                "tasks": [{"id": t.get("id"), "name": t.get("name"), "completed": t.get("completed", False)} for t in tasks],
            })
        print(f"GET /api/monthly-inspections - Returning {len(result)} formatted inspections")
        return result
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 404:
            print("ERROR: monthly_inspections table not found (404)")
            return []
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        print(f"ERROR fetching monthly inspections: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        print(f"ERROR in get_monthly_inspections: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching monthly inspections: {str(e)}")

@app.post("/api/monthly-inspections/sync")
def sync_monthly_inspections_endpoint():
    """Sync monthly inspections with hotels"""
    try:
        sync_monthly_inspections()
        return {"message": "Monthly inspections synced successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing monthly inspections: {str(e)}")

@app.post("/api/monthly-inspections")
def create_monthly_inspection(payload: dict):
    """Create or update a monthly inspection mission with its tasks"""
    try:
        inspection_id = payload.get("id") or str(uuid.uuid4())
        
        # Create or update monthly inspection
        inspection_data = {
            "id": inspection_id,
            "unit_number": payload.get("unitNumber") or payload.get("unit_number", ""),
            "inspection_month": payload.get("inspectionMonth") or payload.get("inspection_month", ""),
            "status": payload.get("status", "זמן הביקורות טרם הגיע"),
        }
        
        # Check if monthly inspection exists
        existing = []
        try:
            check_resp = requests.get(
                f"{REST_URL}/monthly_inspections",
                headers=SERVICE_HEADERS,
                params={"id": f"eq.{inspection_id}", "select": "id"}
            )
            if check_resp.status_code == 404:
                existing = []
            else:
                check_resp.raise_for_status()
                existing = check_resp.json() or []
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 404:
                existing = []
            else:
                raise
        except Exception:
            existing = []
        
        if existing and len(existing) > 0:
            # Update existing monthly inspection
            try:
                update_resp = requests.patch(
                    f"{REST_URL}/monthly_inspections?id=eq.{inspection_id}",
                    headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                    json=inspection_data
                )
                if update_resp.status_code != 404:
                    update_resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 404:
                    pass
                else:
                    raise
        else:
            # Create new monthly inspection
            try:
                create_resp = requests.post(
                    f"{REST_URL}/monthly_inspections",
                    headers=SERVICE_HEADERS,
                    json=inspection_data
                )
                if create_resp.status_code not in [200, 201, 404, 409]:
                    create_resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code in [404, 409]:
                    pass
                else:
                    raise
        
        # Handle tasks - upsert
        tasks = payload.get("tasks", [])
        saved_tasks = []
        failed_tasks = []
        
        if tasks:
            # Get existing tasks for this monthly inspection
            existing_task_ids = set()
            try:
                existing_resp = requests.get(
                    f"{REST_URL}/monthly_inspection_tasks",
                    headers=SERVICE_HEADERS,
                    params={"inspection_id": f"eq.{inspection_id}", "select": "id,name"}
                )
                if existing_resp.status_code == 200:
                    existing_tasks = existing_resp.json() or []
                    existing_task_ids = {t.get("id") for t in existing_tasks if t.get("id")}
            except Exception:
                pass
            
            # Upsert tasks
            for task in tasks:
                try:
                    completed = task.get("completed", False)
                    if isinstance(completed, str):
                        completed = completed.lower() in ('true', '1', 'yes', 'on')
                    elif completed is None:
                        completed = False
                    else:
                        completed = bool(completed)
                    
                    task_data = {
                        "id": task.get("id") or str(uuid.uuid4()),
                        "inspection_id": inspection_id,
                        "name": task.get("name", ""),
                        "completed": completed,
                    }
                    task_id = task_data["id"]
                    task_exists = task_id in existing_task_ids
                    
                    if task_exists:
                        update_resp = requests.patch(
                            f"{REST_URL}/monthly_inspection_tasks?id=eq.{task_id}&inspection_id=eq.{inspection_id}",
                            headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                            json={"completed": task_data["completed"], "name": task_data["name"]}
                        )
                        if update_resp.status_code in [200, 201, 204]:
                            saved_tasks.append(task_data)
                        else:
                            task_resp = requests.post(
                                f"{REST_URL}/monthly_inspection_tasks",
                                headers=SERVICE_HEADERS,
                                json=task_data
                            )
                            if task_resp.status_code in [200, 201]:
                                saved_tasks.append(task_data)
                            else:
                                failed_tasks.append(task_data)
                    else:
                        task_resp = requests.post(
                            f"{REST_URL}/monthly_inspection_tasks",
                            headers=SERVICE_HEADERS,
                            json=task_data
                        )
                        if task_resp.status_code in [200, 201]:
                            saved_tasks.append(task_data)
                        elif task_resp.status_code == 409:
                            # Conflict - try update
                            try:
                                update_resp = requests.patch(
                                    f"{REST_URL}/monthly_inspection_tasks?id=eq.{task_id}&inspection_id=eq.{inspection_id}",
                                    headers={**SERVICE_HEADERS, "Prefer": "return=representation"},
                                    json={"completed": task_data["completed"], "name": task_data["name"]}
                                )
                                if update_resp.status_code in [200, 201, 204]:
                                    saved_tasks.append(task_data)
                                else:
                                    failed_tasks.append(task_data)
                            except Exception:
                                failed_tasks.append(task_data)
                        else:
                            failed_tasks.append(task_data)
                except Exception as e:
                    print(f"Error saving monthly inspection task: {str(e)}")
                    failed_tasks.append(task_data)
        
        # Get updated inspection with tasks
        get_resp = requests.get(
            f"{REST_URL}/monthly_inspections",
            headers=SERVICE_HEADERS,
            params={"id": f"eq.{inspection_id}", "select": "*,monthly_inspection_tasks(*)"}
        )
        
        if get_resp.status_code == 200:
            inspections = get_resp.json() or []
            if inspections:
                insp = inspections[0]
                tasks = insp.get("monthly_inspection_tasks", [])
                return {
                    "id": insp.get("id"),
                    "unitNumber": insp.get("unit_number"),
                    "inspectionMonth": insp.get("inspection_month"),
                    "status": insp.get("status"),
                    "tasks": [{"id": t.get("id"), "name": t.get("name"), "completed": t.get("completed", False)} for t in tasks],
                    "savedTasksCount": len(saved_tasks),
                    "failedTasksCount": len(failed_tasks),
                    "totalTasksCount": len(tasks),
                    "completedTasksCount": sum(1 for t in tasks if t.get("completed", False)),
                }
        
        return {
            "id": inspection_id,
            "tasks": saved_tasks,
            "savedTasksCount": len(saved_tasks),
            "failedTasksCount": len(failed_tasks),
        }
    except requests.exceptions.HTTPError as e:
        error_detail = f"HTTP {e.response.status_code}: {e.response.text[:200]}" if e.response else str(e)
        raise HTTPException(status_code=500, detail=f"Supabase error: {error_detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving monthly inspection: {str(e)}")

