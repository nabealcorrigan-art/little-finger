"""
Test suite for web-based authentication UI
Tests the login flow and session management
"""
import json
from server import app


def test_login_page_redirect():
    """Test that unauthenticated users are redirected to login"""
    print("\n=== Testing Login Page Redirect ===")
    
    with app.test_client() as client:
        # Try to access dashboard without authentication
        response = client.get('/')
        
        # Should redirect to login page
        assert response.status_code == 302, f"Expected redirect (302), got {response.status_code}"
        assert '/login' in response.location, f"Expected redirect to /login, got {response.location}"
        
        print("✓ Unauthenticated users are redirected to login")


def test_login_page_loads():
    """Test that login page loads correctly"""
    print("\n=== Testing Login Page Loading ===")
    
    with app.test_client() as client:
        response = client.get('/login')
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Check that login page contains required fields
        html = response.data.decode('utf-8')
        assert 'Ring Email Address' in html, "Email field not found"
        assert 'Ring Password' in html, "Password field not found"
        assert 'Login to Ring' in html, "Login button not found"
        
        print("✓ Login page loads with all required fields")


def test_login_validation():
    """Test that login endpoint validates required fields"""
    print("\n=== Testing Login Validation ===")
    
    with app.test_client() as client:
        # Test with missing credentials
        response = client.post('/login',
                              data=json.dumps({}),
                              content_type='application/json')
        
        assert response.status_code == 400, f"Expected 400 for missing fields, got {response.status_code}"
        
        data = json.loads(response.data)
        assert data['success'] == False, "Expected success=False"
        assert 'required' in data['message'].lower(), "Expected 'required' in error message"
        
        print("✓ Login endpoint validates required fields")


def test_session_management():
    """Test that sessions are managed correctly"""
    print("\n=== Testing Session Management ===")
    
    with app.test_client() as client:
        # Initially should not be authenticated
        response = client.get('/')
        assert response.status_code == 302, "Should redirect when not authenticated"
        
        # After logout, should redirect to login
        response = client.get('/logout')
        assert response.status_code == 302, "Logout should redirect"
        assert '/login' in response.location, "Logout should redirect to login"
        
        print("✓ Session management works correctly")


def test_api_endpoints_work():
    """Test that API endpoints are still accessible"""
    print("\n=== Testing API Endpoints ===")
    
    with app.test_client() as client:
        # API endpoints should work (they return empty data if no monitor)
        endpoints = ['/api/matches', '/api/stats', '/api/config']
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # These might redirect or return data depending on auth state
            # Just verify they don't error
            assert response.status_code in [200, 302], f"{endpoint} returned {response.status_code}"
        
        print("✓ API endpoints are accessible")


def main():
    """Run all tests"""
    print("╔════════════════════════════════════════════════╗")
    print("║   Little Finger Auth UI - Test Suite         ║")
    print("╚════════════════════════════════════════════════╝")
    
    tests = [
        test_login_page_redirect,
        test_login_page_loads,
        test_login_validation,
        test_session_management,
        test_api_endpoints_work
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Passed: {passed}/{len(tests)}")
    
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
