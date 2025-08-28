#!/usr/bin/env python3
"""
NY Pizza Woodstock Backend API Test Suite
Tests all critical API endpoints for the pizza ordering system
"""

import requests
import sys
import json
from datetime import datetime

class NYPizzaAPITester:
    def __init__(self, base_url="https://doughcode-review.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_token = None

    def log_test(self, name, success, message=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {message}")
        return success

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.token and 'Authorization' not in test_headers:
            test_headers['Authorization'] = f'Bearer {self.token}'

        try:
            print(f"\n🔍 Testing {name}...")
            print(f"   URL: {url}")
            print(f"   Method: {method}")
            
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    return self.log_test(name, True), response_data
                except:
                    return self.log_test(name, True), {}
            else:
                try:
                    error_data = response.json()
                    return self.log_test(name, False, f"Status {response.status_code}: {error_data}"), {}
                except:
                    return self.log_test(name, False, f"Status {response.status_code}: {response.text[:200]}"), {}

        except requests.exceptions.Timeout:
            return self.log_test(name, False, "Request timeout"), {}
        except requests.exceptions.ConnectionError:
            return self.log_test(name, False, "Connection error"), {}
        except Exception as e:
            return self.log_test(name, False, f"Error: {str(e)}"), {}

    def test_api_root(self):
        """Test API root endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET",
            "",
            200
        )
        return success

    def test_menu_pizzas(self):
        """Test GET /api/menu/pizzas - Should return 18 pizzas"""
        success, response = self.run_test(
            "Get Pizzas Menu",
            "GET",
            "menu/pizzas",
            200
        )
        
        if success and isinstance(response, list):
            pizza_count = len(response)
            print(f"   Found {pizza_count} pizzas")
            
            if pizza_count >= 18:
                print(f"   ✅ Pizza count OK (expected ≥18, got {pizza_count})")
                
                # Check pizza structure
                if pizza_count > 0:
                    sample_pizza = response[0]
                    required_fields = ['id', 'name', 'description', 'category', 'sizes', 'image_url']
                    missing_fields = [field for field in required_fields if field not in sample_pizza]
                    
                    if not missing_fields:
                        print(f"   ✅ Pizza structure OK")
                        
                        # Check categories
                        categories = set(pizza.get('category', '') for pizza in response)
                        print(f"   Pizza categories: {categories}")
                        
                        return True
                    else:
                        print(f"   ❌ Missing fields in pizza: {missing_fields}")
                        return False
            else:
                print(f"   ❌ Expected ≥18 pizzas, got {pizza_count}")
                return False
        
        return success

    def test_menu_items(self):
        """Test GET /api/menu/items - Should return 100+ items"""
        success, response = self.run_test(
            "Get Menu Items",
            "GET",
            "menu/items",
            200
        )
        
        if success and isinstance(response, list):
            item_count = len(response)
            print(f"   Found {item_count} menu items")
            
            if item_count >= 100:
                print(f"   ✅ Menu item count OK (expected ≥100, got {item_count})")
                
                # Check item structure
                if item_count > 0:
                    sample_item = response[0]
                    required_fields = ['id', 'name', 'description', 'category', 'price', 'image_url']
                    missing_fields = [field for field in required_fields if field not in sample_item]
                    
                    if not missing_fields:
                        print(f"   ✅ Menu item structure OK")
                        
                        # Check categories
                        categories = set(item.get('category', '') for item in response)
                        print(f"   Menu categories: {sorted(categories)}")
                        
                        # Count items per category
                        category_counts = {}
                        for item in response:
                            cat = item.get('category', 'unknown')
                            category_counts[cat] = category_counts.get(cat, 0) + 1
                        
                        print(f"   Category breakdown:")
                        for cat, count in sorted(category_counts.items()):
                            print(f"     {cat}: {count} items")
                        
                        return True
                    else:
                        print(f"   ❌ Missing fields in menu item: {missing_fields}")
                        return False
            else:
                print(f"   ❌ Expected ≥100 menu items, got {item_count}")
                return False
        
        return success

    def test_user_registration(self):
        """Test POST /api/auth/register"""
        timestamp = datetime.now().strftime("%H%M%S")
        test_user_data = {
            "email": f"test_user_{timestamp}@test.com",
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "User",
            "phone": "(555) 123-4567"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            if 'user' in response:
                self.user_id = response['user'].get('id')
                print(f"   ✅ User registered with ID: {self.user_id}")
            print(f"   ✅ Access token received")
            return True
        
        return success

    def test_user_login(self):
        """Test POST /api/auth/login with the registered user"""
        if not self.token:
            print("   ⚠️  Skipping login test - no user registered")
            return False
            
        # Test with admin credentials
        admin_data = {
            "email": "admin@nypizzawoodstock.com",
            "password": "admin123"
        }
        
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data=admin_data
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            if 'user' in response:
                user_data = response['user']
                is_admin = user_data.get('is_admin', False)
                print(f"   ✅ Admin login successful, is_admin: {is_admin}")
            return True
        
        return success

    def test_get_current_user(self):
        """Test GET /api/auth/me"""
        if not self.token:
            print("   ⚠️  Skipping current user test - no token available")
            return False
            
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        
        if success and 'email' in response:
            print(f"   ✅ Current user: {response.get('email')}")
            return True
        
        return success

    def test_create_order(self):
        """Test POST /api/orders"""
        if not self.token:
            print("   ⚠️  Skipping order test - no token available")
            return False
            
        # Create a sample order - user_id will be set by backend from token
        order_data = {
            "user_id": "placeholder",  # This will be overridden by backend
            "items": [
                {
                    "item_id": "test-pizza-id",
                    "item_type": "pizza",
                    "name": "NY Cheese Pizza",
                    "size": "Medium",
                    "quantity": 1,
                    "price": 13.95,
                    "toppings": []
                }
            ],
            "order_type": "pickup",
            "payment_method": "cash",
            "subtotal": 13.95,
            "delivery_fee": 0.0,
            "tax": 1.19,
            "total": 15.14,
            "special_instructions": "Test order"
        }
        
        success, response = self.run_test(
            "Create Order",
            "POST",
            "orders",
            200,
            data=order_data
        )
        
        if success and 'id' in response:
            order_id = response['id']
            print(f"   ✅ Order created with ID: {order_id}")
            return True
        
        return success

    def test_get_user_orders(self):
        """Test GET /api/orders/my-orders"""
        if not self.token:
            print("   ⚠️  Skipping user orders test - no token available")
            return False
            
        success, response = self.run_test(
            "Get User Orders",
            "GET",
            "orders/my-orders",
            200
        )
        
        if success and isinstance(response, list):
            print(f"   ✅ Found {len(response)} user orders")
            return True
        
        return success

    def test_admin_endpoints(self):
        """Test admin-only endpoints"""
        if not self.admin_token:
            print("   ⚠️  Skipping admin tests - no admin token available")
            return False
            
        # Temporarily use admin token
        original_token = self.token
        self.token = self.admin_token
        
        success, response = self.run_test(
            "Get All Orders (Admin)",
            "GET",
            "admin/orders",
            200
        )
        
        admin_success = success
        if success and isinstance(response, list):
            print(f"   ✅ Admin can access {len(response)} orders")
        
        # Restore original token
        self.token = original_token
        return admin_success

    def run_all_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("🍕 NY PIZZA WOODSTOCK API TEST SUITE")
        print("=" * 60)
        print(f"Testing API at: {self.api_url}")
        print()

        # Test sequence
        tests = [
            ("API Root", self.test_api_root),
            ("Menu Pizzas", self.test_menu_pizzas),
            ("Menu Items", self.test_menu_items),
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("Current User", self.test_get_current_user),
            ("Create Order", self.test_create_order),
            ("User Orders", self.test_get_user_orders),
            ("Admin Endpoints", self.test_admin_endpoints),
        ]

        print("\n" + "=" * 60)
        print("RUNNING TESTS...")
        print("=" * 60)

        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log_test(test_name, False, f"Exception: {str(e)}")
            print()

        # Final results
        print("=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL TESTS PASSED! Backend API is working correctly.")
            return 0
        else:
            print(f"\n⚠️  {self.tests_run - self.tests_passed} TESTS FAILED. Please check the issues above.")
            return 1

def main():
    """Main test runner"""
    tester = NYPizzaAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())