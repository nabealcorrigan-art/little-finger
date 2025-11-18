"""
Test the browser authentication button functionality
"""
import sys
import json
import time
from threading import Thread

def test_browser_auth_button():
    """Test that browser auth button initializes correctly and status endpoint reports it"""
    print("\nTesting browser auth button initialization...")
    
    try:
        from server import app, browser_auth
        from ring_browser_auth import RingBrowserAuth
        
        with app.test_client() as client:
            # First check that status shows not authenticated and no browser active
            response = client.get('/auth/browser/status')
            assert response.status_code == 200
            data = response.get_json()
            assert data['authenticated'] == False
            assert data['browser_active'] == False
            print("✓ Initial status: not authenticated, no browser active")
            
            # Note: We cannot test the actual POST to /auth/browser/start because:
            # 1. It would open a real browser window (headless=False)
            # 2. It requires actual Ring credentials
            # 3. The background thread would continue running
            # Instead we verify the logic is correct by checking the code flow
            
            # Verify the browser_auth global is None initially
            from server import browser_auth as initial_browser_auth
            assert initial_browser_auth is None
            print("✓ browser_auth global is initially None")
            
            # Verify RingBrowserAuth class can be instantiated
            test_auth = RingBrowserAuth(headless=True)
            assert test_auth.headless == True
            print("✓ RingBrowserAuth can be instantiated")
            
        return True
    except Exception as e:
        print(f"✗ Error testing browser auth button: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_monitor_is_authenticated():
    """Test the is_authenticated property on RingMonitor"""
    print("\nTesting RingMonitor.is_authenticated property...")
    
    try:
        from ring_monitor import RingMonitor
        
        # Create a minimal config
        config = {
            'ring': {
                'username': '',
                'password': '',
                'refresh_token': '',
                'otp_code': ''
            },
            'monitoring': {
                'poll_interval_seconds': 60,
                'keywords': ['test'],
                'emojis': []
            }
        }
        
        monitor = RingMonitor(config)
        
        # Initially should not be authenticated (ring is None)
        assert hasattr(monitor, 'is_authenticated')
        assert monitor.is_authenticated == False
        print("✓ is_authenticated property exists and returns False when not authenticated")
        
        # If we set monitor.ring to something, it should return True
        monitor.ring = object()  # Mock object
        assert monitor.is_authenticated == True
        print("✓ is_authenticated returns True when monitor.ring is set")
        
        return True
    except Exception as e:
        print(f"✗ Error testing is_authenticated: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_status_endpoint_with_authenticated_monitor():
    """Test that status endpoint detects authenticated monitor"""
    print("\nTesting status endpoint with authenticated monitor...")
    
    try:
        from server import app
        from ring_monitor import RingMonitor
        
        # Create a minimal config
        config = {
            'ring': {
                'username': '',
                'password': '',
                'refresh_token': '',
                'otp_code': ''
            },
            'monitoring': {
                'poll_interval_seconds': 60,
                'keywords': ['test'],
                'emojis': []
            }
        }
        
        # Create monitor and mock it as authenticated
        test_monitor = RingMonitor(config)
        test_monitor.ring = object()  # Mock authentication
        
        # Temporarily replace the global monitor
        import server
        original_monitor = server.monitor
        server.monitor = test_monitor
        
        try:
            with app.test_client() as client:
                # Check status - should now show authenticated
                response = client.get('/auth/browser/status')
                assert response.status_code == 200
                data = response.get_json()
                assert data['authenticated'] == True
                assert data['method'] == 'browser'
                print("✓ Status endpoint correctly detects authenticated monitor")
        finally:
            # Restore original monitor
            server.monitor = original_monitor
        
        return True
    except Exception as e:
        print(f"✗ Error testing status endpoint: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Browser Auth Button Functionality Tests")
    print("=" * 60)
    
    tests = [
        ("Browser Auth Button Initialization", test_browser_auth_button),
        ("RingMonitor.is_authenticated Property", test_monitor_is_authenticated),
        ("Status Endpoint with Authenticated Monitor", test_status_endpoint_with_authenticated_monitor),
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
