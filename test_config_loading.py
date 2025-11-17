#!/usr/bin/env python3
"""
Test suite for configuration loading and error handling
"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch
import server


class TestConfigLoading(unittest.TestCase):
    """Test configuration file loading and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.original_dir = os.getcwd()
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up after tests"""
        os.chdir(self.original_dir)
        # Clean up test files
        if os.path.exists(os.path.join(self.test_dir, 'config.json')):
            os.remove(os.path.join(self.test_dir, 'config.json'))
        os.rmdir(self.test_dir)
    
    def test_valid_config_loading(self):
        """Test that valid config loads successfully"""
        valid_config = {
            "ring": {
                "username": "test@example.com",
                "password": "test",
                "refresh_token": ""
            },
            "monitoring": {
                "poll_interval_seconds": 60,
                "keywords": ["test"],
                "emojis": ["🚨"]
            },
            "server": {
                "host": "127.0.0.1",
                "port": 5777
            }
        }
        
        with open('config.json', 'w') as f:
            json.dump(valid_config, f)
        
        config = server.load_config()
        self.assertIsNotNone(config)
        self.assertEqual(config['ring']['username'], 'test@example.com')
        self.assertEqual(config['monitoring']['poll_interval_seconds'], 60)
    
    def test_missing_config_file(self):
        """Test that missing config file is handled gracefully"""
        # Ensure no config.json exists
        if os.path.exists('config.json'):
            os.remove('config.json')
        
        with patch('server.logger') as mock_logger:
            config = server.load_config()
            self.assertIsNone(config)
            mock_logger.error.assert_called_with("config.json not found")
    
    def test_invalid_json_trailing_comma(self):
        """Test that invalid JSON with trailing comma is handled"""
        invalid_json = """{
  "ring": {
    "username": "test@example.com",
    "password": "test",
  },
  "monitoring": {
    "keywords": ["test"]
  }
}"""
        
        with open('config.json', 'w') as f:
            f.write(invalid_json)
        
        with patch('server.logger') as mock_logger:
            config = server.load_config()
            self.assertIsNone(config)
            # Check that error message was logged
            calls = [str(call) for call in mock_logger.error.call_args_list]
            error_logged = any('Invalid JSON' in str(call) for call in calls)
            self.assertTrue(error_logged, "Expected error message about invalid JSON")
    
    def test_invalid_json_missing_bracket(self):
        """Test that invalid JSON with missing bracket is handled"""
        invalid_json = """{
  "ring": {
    "username": "test@example.com",
    "password": "test"
  },
  "monitoring": {
    "keywords": ["test"
  }
}"""
        
        with open('config.json', 'w') as f:
            f.write(invalid_json)
        
        with patch('server.logger') as mock_logger:
            config = server.load_config()
            self.assertIsNone(config)
            # Check that error message was logged with line/column info
            calls = [str(call) for call in mock_logger.error.call_args_list]
            error_logged = any('Invalid JSON' in str(call) and 'line' in str(call) for call in calls)
            self.assertTrue(error_logged, "Expected detailed error message with line/column info")
    
    def test_invalid_json_malformed_structure(self):
        """Test that malformed JSON structure is handled"""
        invalid_json = """not valid json at all"""
        
        with open('config.json', 'w') as f:
            f.write(invalid_json)
        
        with patch('server.logger') as mock_logger:
            config = server.load_config()
            self.assertIsNone(config)
            # Check that helpful error messages were logged
            calls = [str(call) for call in mock_logger.error.call_args_list]
            # Should have multiple error messages including suggestions
            self.assertGreaterEqual(len(calls), 2, "Expected multiple error messages")


if __name__ == '__main__':
    unittest.main()
