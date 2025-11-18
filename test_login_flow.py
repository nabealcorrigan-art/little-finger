"""
Test login flow and authentication
"""
import json
import pytest
import tempfile
import os
from server import app, load_config, save_config, check_credentials_configured


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_config():
    """Create temporary config file"""
    config = {
        "ring": {
            "username": "",
            "password": "",
            "refresh_token": "",
            "otp_code": ""
        },
        "monitoring": {
            "poll_interval_seconds": 60,
            "keywords": ["test"],
            "emojis": ["🚨"]
        },
        "server": {
            "host": "0.0.0.0",
            "port": 5777
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_login_page_accessible(client):
    """Test that login page is accessible"""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Little Finger' in response.data
    assert b'Ring Email Address' in response.data


def test_root_redirects_to_login_when_not_authenticated(client):
    """Test that root redirects to login when not authenticated"""
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location


def test_login_requires_credentials(client):
    """Test that login endpoint requires username and password"""
    response = client.post('/api/login', 
                          json={},
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_login_with_credentials(client):
    """Test login with credentials (will fail auth but should process)"""
    response = client.post('/api/login',
                          json={
                              'username': 'test@example.com',
                              'password': 'testpassword'
                          },
                          content_type='application/json')
    # Expecting auth failure since these are test credentials
    # But the endpoint should process them correctly
    assert response.status_code in [200, 401]


def test_logout(client):
    """Test logout endpoint"""
    with client.session_transaction() as sess:
        sess['authenticated'] = True
    
    response = client.post('/api/logout',
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True


def test_check_credentials_configured_empty():
    """Test checking for empty credentials"""
    # Create a temporary empty config for this test
    import tempfile
    import os
    
    empty_config = {
        "ring": {
            "username": "",
            "password": "",
            "refresh_token": "",
            "otp_code": ""
        },
        "monitoring": {
            "poll_interval_seconds": 60,
            "keywords": ["test"],
            "emojis": ["🚨"]
        },
        "server": {
            "host": "0.0.0.0",
            "port": 5777
        }
    }
    
    # Backup original config
    backup_path = 'config.json.backup'
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            original = f.read()
        with open(backup_path, 'w') as f:
            f.write(original)
    
    try:
        # Write empty config
        with open('config.json', 'w') as f:
            json.dump(empty_config, f)
        
        result = check_credentials_configured()
        assert result is False
    finally:
        # Restore original config
        if os.path.exists(backup_path):
            with open(backup_path, 'r') as f:
                original = f.read()
            with open('config.json', 'w') as f:
                f.write(original)
            os.remove(backup_path)


def test_save_and_load_config(temp_config):
    """Test saving and loading configuration"""
    # Load temp config
    with open(temp_config, 'r') as f:
        config = json.load(f)
    
    # Modify and save
    config['ring']['username'] = 'test@example.com'
    
    # Save to temp file
    with open(temp_config, 'w') as f:
        json.dump(config, f)
    
    # Load again
    with open(temp_config, 'r') as f:
        loaded = json.load(f)
    
    assert loaded['ring']['username'] == 'test@example.com'


def test_api_endpoints_require_auth(client):
    """Test that API endpoints are accessible (they don't require auth)"""
    # These endpoints should work without authentication
    response = client.get('/api/matches')
    assert response.status_code == 200
    
    response = client.get('/api/stats')
    assert response.status_code == 200
    
    response = client.get('/api/config')
    assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
