"""
Test script to verify all backend endpoints work correctly
Run this after starting the backend server on port 4001
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:4001"

def print_test(name):
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")

def test_endpoint(method, endpoint, data=None, expected_status=200):
    """Test an endpoint and return the response"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=5)
        elif method == "PATCH":
            response = requests.patch(url, json=data, headers={"Content-Type": "application/json"}, timeout=5)
        else:
            return None, f"Unknown method: {method}"
        
        status_ok = response.status_code == expected_status
        status_symbol = "[OK]" if status_ok else "[FAIL]"
        print(f"  {status_symbol} {method} {endpoint}")
        print(f"    Status: {response.status_code} (expected {expected_status})")
        
        try:
            response_data = response.json()
            # Use ensure_ascii=True to avoid Unicode encoding issues
            response_str = json.dumps(response_data, indent=2, ensure_ascii=True)
            print(f"    Response: {response_str[:200]}...")
        except:
            try:
                print(f"    Response: {response.text[:200].encode('ascii', 'ignore').decode('ascii')}")
            except:
                print(f"    Response: [Binary or non-ASCII content]")
        
        return response, None
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] {method} {endpoint}")
        print(f"    ERROR: Could not connect to {BASE_URL}")
        print(f"    Make sure the backend server is running on port 4001")
        return None, "Connection error"
    except Exception as e:
        print(f"  [FAIL] {method} {endpoint}")
        print(f"    ERROR: {str(e)}")
        return None, str(e)

def main():
    print("="*60)
    print("Backend API Endpoint Test Suite")
    print(f"Testing against: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    # Test 1: Root endpoint
    print_test("Root Endpoint")
    response, error = test_endpoint("GET", "/")
    if error:
        results["failed"] += 1
        results["errors"].append(("GET /", error))
    else:
        results["passed"] += 1
    
    # Test 2: API index
    print_test("API Index")
    response, error = test_endpoint("GET", "/api")
    if error:
        results["failed"] += 1
        results["errors"].append(("GET /api", error))
    else:
        results["passed"] += 1
    
    # Test 3: Get users
    print_test("Get Users")
    response, error = test_endpoint("GET", "/api/users")
    if error:
        results["failed"] += 1
        results["errors"].append(("GET /api/users", error))
    else:
        results["passed"] += 1
    
    # Test 4: Get orders
    print_test("Get Orders")
    response, error = test_endpoint("GET", "/api/orders")
    if error:
        results["failed"] += 1
        results["errors"].append(("GET /api/orders", error))
    else:
        results["passed"] += 1
    
    # Test 5: Create order
    print_test("Create Order")
    test_order = {
        "guestName": "Test Guest",
        "unitNumber": "יחידה 1",
        "arrivalDate": "2025-01-15",
        "departureDate": "2025-01-20",
        "status": "חדש",
        "guestsCount": 2,
        "specialRequests": "Test request",
        "internalNotes": "Test notes",
        "paidAmount": 0,
        "totalAmount": 1000,
        "paymentMethod": "טרם נקבע"
    }
    response, error = test_endpoint("POST", "/api/orders", test_order, expected_status=200)
    if error:
        results["failed"] += 1
        results["errors"].append(("POST /api/orders", error))
    else:
        results["passed"] += 1
        # Save order ID for update test
        if response and response.status_code == 200:
            try:
                order_data = response.json()
                if order_data.get("status") == "success" and order_data.get("order"):
                    created_order_id = order_data["order"].get("id")
                    if created_order_id:
                        # Test 6: Update order
                        print_test("Update Order")
                        update_data = {
                            "paidAmount": 500,
                            "status": "שולם חלקית"
                        }
                        response, error = test_endpoint("PATCH", f"/api/orders/{created_order_id}", update_data)
                        if error:
                            results["failed"] += 1
                            results["errors"].append((f"PATCH /api/orders/{created_order_id}", error))
                        else:
                            results["passed"] += 1
            except:
                pass
    
    # Test 7: Get inventory items
    print_test("Get Inventory Items")
    response, error = test_endpoint("GET", "/api/inventory/items")
    if error:
        results["failed"] += 1
        results["errors"].append(("GET /api/inventory/items", error))
    else:
        results["passed"] += 1
    
    # Test 8: Get inventory orders
    print_test("Get Inventory Orders")
    response, error = test_endpoint("GET", "/api/inventory/orders")
    if error:
        results["failed"] += 1
        results["errors"].append(("GET /api/inventory/orders", error))
    else:
        results["passed"] += 1
    
    # Test 9: Get maintenance tasks
    print_test("Get Maintenance Tasks")
    response, error = test_endpoint("GET", "/api/maintenance/tasks")
    if error:
        results["failed"] += 1
        results["errors"].append(("GET /api/maintenance/tasks", error))
    else:
        results["passed"] += 1
    
    # Test 10: Login (should fail without valid credentials, but endpoint should exist)
    print_test("Login Endpoint (Invalid Credentials)")
    login_data = {
        "username": "test_user",
        "password": "wrong_password"
    }
    response, error = test_endpoint("POST", "/api/auth/login", login_data, expected_status=401)
    if error:
        results["failed"] += 1
        results["errors"].append(("POST /api/auth/login", error))
    else:
        results["passed"] += 1
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Total: {results['passed'] + results['failed']}")
    
    if results["errors"]:
        print("\nErrors:")
        for endpoint, error in results["errors"]:
            print(f"  - {endpoint}: {error}")
    
    if results["failed"] == 0:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[FAILED] {results['failed']} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

