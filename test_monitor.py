#!/usr/bin/env python3
"""
Demo/Test script for Little Finger Ring Monitor
Demonstrates the monitoring system with mock data
"""
import json
import time
from datetime import datetime
from ring_monitor import RingMonitor


def create_mock_config():
    """Create a test configuration"""
    return {
        "ring": {
            "username": "test@example.com",
            "password": "test",
            "refresh_token": ""
        },
        "monitoring": {
            "poll_interval_seconds": 5,
            "keywords": ["suspicious", "theft", "police"],
            "emojis": ["🚨", "🚔"]
        },
        "server": {
            "host": "127.0.0.1",
            "port": 5777
        }
    }


def create_mock_posts():
    """Create sample Ring neighborhood posts for testing"""
    return [
        {
            "id": "post_1",
            "title": "Suspicious Activity",
            "text": "Someone was lurking around the neighborhood looking suspicious",
            "created_at": datetime.now().isoformat(),
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "123 Main St, San Francisco, CA"
        },
        {
            "id": "post_2",
            "title": "Police Response",
            "text": "Police were called to the area 🚔 for a reported theft",
            "created_at": datetime.now().isoformat(),
            "latitude": 37.7849,
            "longitude": -122.4094,
            "address": "456 Oak Ave, San Francisco, CA"
        },
        {
            "id": "post_3",
            "title": "Neighborhood Watch",
            "text": "Everyone stay safe! 🚨",
            "created_at": datetime.now().isoformat(),
            "latitude": 37.7649,
            "longitude": -122.4294,
            "address": "789 Pine St, San Francisco, CA"
        },
        {
            "id": "post_4",
            "title": "Lost Dog",
            "text": "Has anyone seen a golden retriever?",
            "created_at": datetime.now().isoformat(),
            "latitude": 37.7749,
            "longitude": -122.4394,
            "address": "321 Elm St, San Francisco, CA"
        }
    ]


def test_keyword_detection():
    """Test keyword and emoji detection"""
    print("=== Testing Keyword and Emoji Detection ===\n")
    
    config = create_mock_config()
    monitor = RingMonitor(config)
    mock_posts = create_mock_posts()
    
    print(f"Monitoring keywords: {monitor.keywords}")
    print(f"Monitoring emojis: {monitor.emojis}")
    print(f"\nProcessing {len(mock_posts)} posts...\n")
    
    matches = monitor.check_for_matches(mock_posts)
    
    print(f"Found {len(matches)} matches:\n")
    for match in matches:
        print(f"Match ID: {match['id']}")
        print(f"  Title: {match['title']}")
        print(f"  Location: {match['location']['address']}")
        print(f"  Coordinates: ({match['location']['latitude']}, {match['location']['longitude']})")
        print(f"  Matched Keywords: {match['matched_keywords']}")
        print(f"  Matched Emojis: {match['matched_emojis']}")
        print(f"  Timestamp: {match['timestamp']}")
        print()
    
    return len(matches) == 3  # Should match posts 1, 2, and 3


def test_filtering():
    """Test filtering by term"""
    print("=== Testing Filtering ===\n")
    
    config = create_mock_config()
    monitor = RingMonitor(config)
    mock_posts = create_mock_posts()
    
    # Generate matches and add them to monitor's match list
    matches = monitor.check_for_matches(mock_posts)
    monitor.matches.extend(matches)
    
    # Test filtering by keyword
    police_matches = monitor.get_matches_by_term("police")
    print(f"Matches for 'police': {len(police_matches)}")
    for match in police_matches:
        print(f"  - {match['title']}")
    
    # Test filtering by emoji
    emoji_matches = monitor.get_matches_by_term("🚨")
    print(f"\nMatches for '🚨': {len(emoji_matches)}")
    for match in emoji_matches:
        print(f"  - {match['title']}")
    
    print()
    return len(police_matches) == 1 and len(emoji_matches) == 1


def test_deduplication():
    """Test that duplicate posts aren't reported twice"""
    print("=== Testing Deduplication ===\n")
    
    config = create_mock_config()
    monitor = RingMonitor(config)
    mock_posts = create_mock_posts()
    
    # First check
    matches1 = monitor.check_for_matches(mock_posts)
    print(f"First check: {len(matches1)} matches")
    
    # Second check with same posts (should find 0 new matches)
    matches2 = monitor.check_for_matches(mock_posts)
    print(f"Second check (duplicates): {len(matches2)} matches")
    
    # Add a new post
    new_post = {
        "id": "post_5",
        "title": "Theft Report",
        "text": "My package was stolen, be careful with theft in the area",
        "created_at": datetime.now().isoformat(),
        "latitude": 37.7549,
        "longitude": -122.4494,
        "address": "555 Maple Dr, San Francisco, CA"
    }
    
    matches3 = monitor.check_for_matches([new_post])
    print(f"Third check (new post): {len(matches3)} matches")
    
    print()
    return len(matches1) == 3 and len(matches2) == 0 and len(matches3) == 1


def main():
    """Run all tests"""
    print("╔════════════════════════════════════════════════╗")
    print("║   Little Finger Ring Monitor - Test Suite    ║")
    print("╚════════════════════════════════════════════════╝\n")
    
    tests = [
        ("Keyword Detection", test_keyword_detection),
        ("Filtering", test_filtering),
        ("Deduplication", test_deduplication)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"{status}: {test_name}\n")
        except Exception as e:
            results.append((test_name, False))
            print(f"✗ FAILED: {test_name}")
            print(f"  Error: {e}\n")
    
    # Print summary
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    for test_name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {test_name}")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
