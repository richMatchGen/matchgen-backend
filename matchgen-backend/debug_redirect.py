#!/usr/bin/env python3
"""
Debug script to test redirect issues and API endpoints
"""
import requests
import json

# Test URLs
BASE_URL = "https://matchgen-backend-production.up.railway.app"

def test_redirect_chain(url, max_redirects=5):
    """Test redirect chain to identify loops"""
    print(f"\nTesting redirect chain for: {url}")
    
    try:
        response = requests.get(url, allow_redirects=False, timeout=10)
        print(f"Initial response: {response.status_code}")
        
        if response.status_code in [301, 302, 307, 308]:
            print(f"Redirect location: {response.headers.get('Location', 'None')}")
            
            # Follow redirects manually
            redirect_count = 0
            current_url = response.headers.get('Location')
            
            while current_url and redirect_count < max_redirects:
                redirect_count += 1
                print(f"Following redirect {redirect_count}: {current_url}")
                
                response = requests.get(current_url, allow_redirects=False, timeout=10)
                print(f"Response: {response.status_code}")
                
                if response.status_code in [301, 302, 307, 308]:
                    current_url = response.headers.get('Location')
                else:
                    break
            
            if redirect_count >= max_redirects:
                print("⚠️  Too many redirects - possible redirect loop!")
                return False
            else:
                print(f"✅ Final response: {response.status_code}")
                return True
        else:
            print(f"✅ No redirect: {response.status_code}")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_endpoint_with_curl_style(url, method="GET", data=None):
    """Test endpoint with detailed request/response info"""
    print(f"\n{'='*60}")
    print(f"Testing: {method} {url}")
    print(f"{'='*60}")
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Debug-Script/1.0'
        }
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print(f"\nResponse Body:")
        try:
            json_response = response.json()
            print(json.dumps(json_response, indent=2))
        except:
            print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
        
        return response.status_code < 400
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔍 Debugging MatchGen Backend Redirect Issues")
    print("=" * 60)
    
    # Test basic endpoints
    endpoints = [
        ("/", "GET"),
        ("/api/users/health/", "GET"),
        ("/api/users/test-token/", "GET"),
        ("/api/users/test-token/", "POST", {"test": "data"}),
        ("/api/users/token/", "GET"),
        ("/api/users/token/", "POST", {"email": "test@example.com", "password": "test123"}),
    ]
    
    results = []
    
    for endpoint_info in endpoints:
        if len(endpoint_info) == 2:
            url = BASE_URL + endpoint_info[0]
            method = endpoint_info[1]
            data = None
        else:
            url = BASE_URL + endpoint_info[0]
            method = endpoint_info[1]
            data = endpoint_info[2]
        
        success = test_endpoint_with_curl_style(url, method, data)
        results.append((endpoint_info[0], success))
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for endpoint, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{endpoint}: {status}")
    
    # Test redirect chains specifically
    print(f"\n{'='*60}")
    print("REDIRECT CHAIN TESTS")
    print(f"{'='*60}")
    
    redirect_tests = [
        "/api/users/token/",
        "/api/users/health/",
        "/api/users/test-token/",
    ]
    
    for endpoint in redirect_tests:
        test_redirect_chain(BASE_URL + endpoint)

if __name__ == "__main__":
    main()
