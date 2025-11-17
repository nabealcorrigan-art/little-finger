#!/usr/bin/env python3
"""
Demo script to generate sample matches for testing the heat map
This populates the system with realistic data for visualization
"""
import json
import random
import time
from datetime import datetime, timedelta
from ring_monitor import RingMonitor


def generate_demo_locations():
    """Generate realistic locations in San Francisco Bay Area"""
    # Base coordinates for SF Bay Area neighborhoods
    locations = [
        {"name": "Mission District", "lat": 37.7599, "lng": -122.4148},
        {"name": "Castro", "lat": 37.7609, "lng": -122.4350},
        {"name": "Nob Hill", "lat": 37.7919, "lng": -122.4158},
        {"name": "Haight-Ashbury", "lat": 37.7692, "lng": -122.4481},
        {"name": "Marina", "lat": 37.8021, "lng": -122.4378},
        {"name": "Sunset District", "lat": 37.7575, "lng": -122.4948},
        {"name": "Richmond", "lat": 37.7805, "lng": -122.4716},
        {"name": "SOMA", "lat": 37.7749, "lng": -122.4194},
        {"name": "North Beach", "lat": 37.8006, "lng": -122.4100},
        {"name": "Potrero Hill", "lat": 37.7574, "lng": -122.3991},
    ]
    return locations


def generate_demo_posts(count=20):
    """Generate sample posts with various keywords and emojis"""
    locations = generate_demo_locations()
    keywords = ["suspicious", "theft", "break-in", "burglar", "police", "safety", "alert"]
    emojis = ["🚨", "🚔", "⚠️", "🔴", "👮", "🏃"]
    
    post_templates = [
        "Saw {keyword} activity near {location}",
        "Be aware: {keyword} reported in the area {emoji}",
        "{emoji} {keyword} alert! Stay vigilant",
        "Police responded to {keyword} incident",
        "Neighborhood watch: {keyword} behavior observed",
        "Security concern - {keyword} {emoji}",
        "Alert: {keyword} in progress",
        "Community safety: {keyword} reported {emoji}",
    ]
    
    posts = []
    start_time = datetime.now() - timedelta(hours=24)
    
    for i in range(count):
        loc = random.choice(locations)
        keyword = random.choice(keywords)
        emoji = random.choice(emojis) if random.random() > 0.5 else ""
        template = random.choice(post_templates)
        
        # Add some random offset to coordinates for variety
        lat_offset = random.uniform(-0.01, 0.01)
        lng_offset = random.uniform(-0.01, 0.01)
        
        # Randomize timestamp
        time_offset = random.randint(0, 24 * 60)  # within last 24 hours
        post_time = start_time + timedelta(minutes=time_offset)
        
        text = template.format(keyword=keyword, location=loc["name"], emoji=emoji)
        
        post = {
            "id": f"demo_post_{i}",
            "title": f"Alert #{i+1}",
            "text": text,
            "created_at": post_time.isoformat(),
            "latitude": loc["lat"] + lat_offset,
            "longitude": loc["lng"] + lng_offset,
            "address": f"{random.randint(100, 999)} Street, {loc['name']}, San Francisco, CA"
        }
        posts.append(post)
    
    return posts


def inject_demo_data(monitor, count=20):
    """Inject demo posts into the monitor"""
    print(f"Generating {count} demo posts...")
    posts = generate_demo_posts(count)
    
    print("Processing posts for matches...")
    matches = monitor.check_for_matches(posts)
    
    print(f"\n✓ Generated {len(matches)} matches out of {len(posts)} posts")
    print(f"✓ Matches distributed across San Francisco Bay Area")
    print(f"✓ Time range: Last 24 hours")
    
    return matches


def main():
    """Generate demo data and start the server"""
    print("╔════════════════════════════════════════════════╗")
    print("║   Little Finger - Demo Data Generator        ║")
    print("╚════════════════════════════════════════════════╝\n")
    
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found")
        return
    
    # Create monitor
    monitor = RingMonitor(config)
    
    # Generate demo data
    matches = inject_demo_data(monitor, count=30)
    
    # Display summary
    print("\n" + "="*50)
    print("DEMO DATA SUMMARY")
    print("="*50)
    
    keyword_counts = {}
    emoji_counts = {}
    
    for match in matches:
        for kw in match['matched_keywords']:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        for emoji in match['matched_emojis']:
            emoji_counts[emoji] = emoji_counts.get(emoji, 0) + 1
    
    print("\nKeyword Matches:")
    for kw, count in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {kw}: {count}")
    
    print("\nEmoji Matches:")
    for emoji, count in sorted(emoji_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {emoji}: {count}")
    
    print("\n" + "="*50)
    print("\n✓ Demo data ready!")
    print("  Run 'python server.py' to view the heat map")
    print("  Or import this module to use the demo data in your tests\n")


if __name__ == "__main__":
    main()
