"""
Test 2FA/OTP authentication configuration
"""
import json
import sys
from ring_monitor import RingMonitor

def test_otp_config_loading():
    """Test that OTP code is properly loaded from config"""
    print("Testing OTP code configuration loading...")
    
    # Test config with OTP code
    test_config = {
        "ring": {
            "username": "test@example.com",
            "password": "testpass",
            "refresh_token": "",
            "otp_code": "123456"
        },
        "monitoring": {
            "poll_interval_seconds": 60,
            "keywords": ["test"],
            "emojis": ["🚨"]
        }
    }
    
    monitor = RingMonitor(test_config)
    
    # Verify OTP code is accessible
    otp_code = monitor.config['ring'].get('otp_code', '').strip()
    assert otp_code == "123456", f"Expected '123456', got '{otp_code}'"
    
    print("✓ PASSED: OTP code loaded correctly from config")
    return True

def test_config_file_format():
    """Test that config.json has the otp_code field"""
    print("\nTesting config.json format...")
    
    try:
        with open('config.json', 'r', encoding='utf-8-sig') as f:
            config = json.load(f)
        
        # Check if otp_code field exists
        assert 'ring' in config, "Missing 'ring' section in config.json"
        assert 'otp_code' in config['ring'], "Missing 'otp_code' field in ring section"
        
        print("✓ PASSED: config.json has otp_code field")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def test_example_config_format():
    """Test that config.example.json has the otp_code field with documentation"""
    print("\nTesting config.example.json format...")
    
    try:
        with open('config.example.json', 'r', encoding='utf-8-sig') as f:
            config = json.load(f)
        
        # Check if otp_code field exists
        assert 'ring' in config, "Missing 'ring' section in config.example.json"
        assert 'otp_code' in config['ring'], "Missing 'otp_code' field in ring section"
        
        # Check for documentation comment
        has_comment = '_comment_otp' in config['ring']
        if has_comment:
            print("  ✓ Documentation comment found")
        
        print("✓ PASSED: config.example.json has otp_code field")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def main():
    print("╔════════════════════════════════════════════╗")
    print("║  2FA/OTP Authentication Test Suite        ║")
    print("╚════════════════════════════════════════════╝\n")
    
    tests = [
        ("OTP Config Loading", test_otp_config_loading),
        ("Config File Format", test_config_file_format),
        ("Example Config Format", test_example_config_format)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ FAILED: {test_name} - {e}")
            failed += 1
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Passed: {passed}/{len(tests)}")
    
    if failed == 0:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {failed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
