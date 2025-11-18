"""
Test browser authentication integration
"""
import sys
import asyncio

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing module imports...")
    
    try:
        from ring_browser_auth import RingBrowserAuth, authenticate_with_browser
        print("✓ ring_browser_auth imports successfully")
    except Exception as e:
        print(f"✗ Error importing ring_browser_auth: {e}")
        return False
    
    try:
        from server import app, socketio
        print("✓ server.py imports successfully")
    except Exception as e:
        print(f"✗ Error importing server: {e}")
        return False
    
    try:
        from ring_monitor import RingMonitor
        print("✓ ring_monitor imports successfully")
    except Exception as e:
        print(f"✗ Error importing ring_monitor: {e}")
        return False
    
    return True


def test_browser_auth_class():
    """Test RingBrowserAuth class instantiation"""
    print("\nTesting RingBrowserAuth class...")
    
    try:
        from ring_browser_auth import RingBrowserAuth
        
        # Test instantiation
        auth = RingBrowserAuth(headless=True)
        print("✓ RingBrowserAuth instantiated successfully")
        
        # Test URL constants
        assert auth.RING_LOGIN_URL == "https://account.ring.com/account/login"
        print("✓ RING_LOGIN_URL is correct")
        
        assert auth.RING_OAUTH_URL == "https://oauth.ring.com/oauth/token"
        print("✓ RING_OAUTH_URL is correct")
        
        assert auth.RING_DASHBOARD_URL == "https://account.ring.com/dashboard"
        print("✓ RING_DASHBOARD_URL is correct")
        
        return True
    except Exception as e:
        print(f"✗ Error testing RingBrowserAuth: {e}")
        return False


def test_server_routes():
    """Test that new server routes exist"""
    print("\nTesting server routes...")
    
    try:
        from server import app
        
        with app.test_client() as client:
            # Test login page
            response = client.get('/login')
            if response.status_code == 200:
                print("✓ GET /login returns 200")
            else:
                print(f"✗ GET /login returned {response.status_code}")
                return False
            
            # Check for browser auth UI
            if b'Login via Ring Website' in response.data:
                print("✓ Browser auth button present in login page")
            else:
                print("✗ Browser auth button not found")
                return False
            
            # Test browser auth status endpoint
            response = client.get('/auth/browser/status')
            if response.status_code == 200:
                print("✓ GET /auth/browser/status returns 200")
            else:
                print(f"✗ GET /auth/browser/status returned {response.status_code}")
                return False
            
            # Check response is JSON
            data = response.get_json()
            if 'authenticated' in data:
                print("✓ /auth/browser/status returns valid JSON")
            else:
                print("✗ /auth/browser/status JSON missing 'authenticated' field")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Error testing server routes: {e}")
        return False


def test_url_validation():
    """Test URL validation logic"""
    print("\nTesting URL validation...")
    
    try:
        from urllib.parse import urlparse
        
        # Test valid dashboard URL
        test_url = "https://account.ring.com/dashboard"
        parsed = urlparse(test_url)
        
        if (parsed.hostname == "account.ring.com" and 
            "dashboard" in parsed.path and 
            "login" not in parsed.path):
            print("✓ Valid dashboard URL recognized correctly")
        else:
            print("✗ Valid dashboard URL not recognized")
            return False
        
        # Test login URL should not pass
        test_url = "https://account.ring.com/account/login"
        parsed = urlparse(test_url)
        
        if not (parsed.hostname == "account.ring.com" and 
                "dashboard" in parsed.path and 
                "login" not in parsed.path):
            print("✓ Login URL correctly rejected")
        else:
            print("✗ Login URL incorrectly accepted")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error testing URL validation: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Browser Authentication Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Module Imports", test_imports),
        ("RingBrowserAuth Class", test_browser_auth_class),
        ("Server Routes", test_server_routes),
        ("URL Validation", test_url_validation),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
