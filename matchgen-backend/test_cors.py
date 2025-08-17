#!/usr/bin/env python3
"""
Simple test script to verify CORS and API endpoints
"""
import requests
import json

# Test URLs
BASE_URL = "https://matchgen-backend-production.up.railway.app"
HEALTH_URL = f"{BASE_URL}/api/users/health/"
TOKEN_URL = f"{BASE_URL}/api/users/token/"
SIMPLE_TOKEN_URL = f"{BASE_URL}/api/users/simple-token/"
TEST_TOKEN_URL = f"{BASE_URL}/api/users/test-token/"

def test_health_endpoint():
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(HEALTH_URL)
        print(f"Health endpoint status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health endpoint error: {e}")
        return False

def test_cors_preflight():
    """Test CORS preflight request"""
    print("\nTesting CORS preflight...")
    try:
        headers = {
            'Origin': 'https://matchgen-frontend.vercel.app',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type,authorization',
        }
        response = requests.options(TOKEN_URL, headers=headers)
        print(f"CORS preflight status: {response.status_code}")
        print(f"CORS headers: {dict(response.headers)}")
        return response.status_code == 200
    except Exception as e:
        print(f"CORS preflight error: {e}")
        return False

def test_simple_token_endpoint():
    """Test the simple token endpoint"""
    print("\nTesting simple token endpoint...")
    try:
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://matchgen-frontend.vercel.app',
        }
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        response = requests.post(SIMPLE_TOKEN_URL, headers=headers, json=data)
        print(f"Simple token endpoint status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200  # Should always return 200
    except Exception as e:
        print(f"Simple token endpoint error: {e}")
        return False


def test_token_endpoint():
    """Test the token endpoint with sample data"""
    print("\nTesting token endpoint...")
    try:
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://matchgen-frontend.vercel.app',
        }
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        response = requests.post(TOKEN_URL, headers=headers, json=data)
        print(f"Token endpoint status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code in [200, 401]  # 401 is expected for invalid credentials
    except Exception as e:
        print(f"Token endpoint error: {e}")
        return False


def test_test_token_endpoint():
    """Test the test token endpoint with sample data"""
    print("\nTesting test-token endpoint...")
    try:
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'https://matchgen-frontend.vercel.app',
        }
        data = {
            'email': 'test@example.com',
            'password': 'testpassword123'
        }
        response = requests.post(TEST_TOKEN_URL, headers=headers, json=data)
        print(f"Test token endpoint status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code in [200, 401]  # 401 is expected for invalid credentials
    except Exception as e:
        print(f"Test token endpoint error: {e}")
        return False

if __name__ == "__main__":
    print("Testing MatchGen Backend API...")
    print("=" * 50)
    
    health_ok = test_health_endpoint()
    cors_ok = test_cors_preflight()
    simple_token_ok = test_simple_token_endpoint()
    token_ok = test_token_endpoint()
    test_token_ok = test_test_token_endpoint()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Health endpoint: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"CORS preflight: {'✅ PASS' if cors_ok else '❌ FAIL'}")
    print(f"Simple token endpoint: {'✅ PASS' if simple_token_ok else '❌ FAIL'}")
    print(f"Token endpoint: {'✅ PASS' if token_ok else '❌ FAIL'}")
    print(f"Test token endpoint: {'✅ PASS' if test_token_ok else '❌ FAIL'}")
    
    if all([health_ok, cors_ok, simple_token_ok, token_ok, test_token_ok]):
        print("\n🎉 All tests passed! The API should be working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
