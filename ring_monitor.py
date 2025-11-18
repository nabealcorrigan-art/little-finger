"""
Ring Neighborhood Monitor
Monitors Ring neighborhood posts for specified keywords and emojis
"""
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Set
import re

try:
    from ring_doorbell import Ring, Auth
except ImportError:
    # Mock for testing when ring_doorbell is not available
    Ring = None
    Auth = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RingMonitor:
    """Monitors Ring neighborhood posts for keywords and emojis"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.keywords = [kw.lower() for kw in config['monitoring']['keywords']]
        self.emojis = config['monitoring']['emojis']
        self.poll_interval = config['monitoring']['poll_interval_seconds']
        self.seen_posts: Set[str] = set()
        self.matches: List[Dict] = []
        self.ring = None
        self.auth = None
        
    def authenticate(self):
        """Authenticate with Ring API"""
        if not Auth:
            logger.warning("Ring API not available, running in mock mode")
            return False
            
        try:
            ring_config = self.config['ring']
            
            # Try refresh token first if available
            if ring_config.get('refresh_token'):
                logger.info("Authenticating with refresh token...")
                self.auth = Auth(
                    "Little Finger Monitor",
                    ring_config['refresh_token'],
                    token_updated_callback=self._token_updated
                )
            else:
                logger.info("Authenticating with username/password...")
                self.auth = Auth(
                    "Little Finger Monitor"
                )
                
                # Get OTP code from config or prompt user
                otp_code = ring_config.get('otp_code', '').strip()
                
                # If no OTP code in config, try initial authentication
                if not otp_code:
                    try:
                        self.auth.fetch_token(
                            ring_config['username'],
                            ring_config['password']
                        )
                    except Exception as e:
                        # Check if error is related to 2FA
                        error_msg = str(e).lower()
                        if '2fa' in error_msg or 'verification' in error_msg or 'code' in error_msg:
                            logger.info("2FA/SMS authentication required")
                            logger.info("Please enter the verification code you received via SMS:")
                            # Try to read OTP code interactively
                            try:
                                import sys
                                if sys.stdin.isatty():
                                    otp_code = input("Enter OTP code: ").strip()
                                else:
                                    logger.error("2FA code required but running in non-interactive mode")
                                    logger.error("Please add 'otp_code' to your config.json file")
                                    raise
                            except (EOFError, KeyboardInterrupt):
                                logger.error("OTP input cancelled")
                                raise
                        else:
                            raise
                
                # Authenticate with OTP code if provided
                if otp_code:
                    logger.info("Authenticating with OTP code...")
                    self.auth.fetch_token(
                        ring_config['username'],
                        ring_config['password'],
                        otp_code=otp_code
                    )
                
            self.ring = Ring(self.auth)
            logger.info("Successfully authenticated with Ring")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def _token_updated(self, token):
        """Callback when token is updated"""
        logger.info("Ring token updated")
        # Save new token to config
        self.config['ring']['refresh_token'] = token
        
    def get_neighborhood_posts(self):
        """Fetch neighborhood posts from Ring"""
        if not self.ring:
            # Return mock data for testing
            return self._get_mock_posts()
            
        try:
            posts = []
            for device in self.ring.devices():
                if hasattr(device, 'neighborhood'):
                    neighborhood_data = device.neighborhood()
                    if neighborhood_data:
                        posts.extend(neighborhood_data)
            return posts
        except Exception as e:
            logger.error(f"Error fetching neighborhood posts: {e}")
            return []
    
    def _get_mock_posts(self):
        """Generate mock posts for testing"""
        # Return empty list in production, or mock data for development
        return []
    
    def check_for_matches(self, posts: List[Dict]) -> List[Dict]:
        """Check posts for keyword and emoji matches"""
        new_matches = []
        
        for post in posts:
            post_id = post.get('id', str(hash(str(post))))
            
            # Skip if we've already seen this post
            if post_id in self.seen_posts:
                continue
                
            self.seen_posts.add(post_id)
            
            # Extract text content
            text = post.get('text', '').lower()
            title = post.get('title', '').lower()
            full_text = f"{title} {text}"
            
            # Check for keyword matches
            matched_keywords = [kw for kw in self.keywords if kw in full_text]
            
            # Check for emoji matches
            matched_emojis = [emoji for emoji in self.emojis if emoji in full_text]
            
            if matched_keywords or matched_emojis:
                match = {
                    'id': post_id,
                    'timestamp': post.get('created_at', datetime.now().isoformat()),
                    'title': post.get('title', ''),
                    'text': post.get('text', ''),
                    'location': {
                        'latitude': post.get('latitude', 0),
                        'longitude': post.get('longitude', 0),
                        'address': post.get('address', 'Unknown')
                    },
                    'matched_keywords': matched_keywords,
                    'matched_emojis': matched_emojis,
                    'detected_at': datetime.now().isoformat()
                }
                
                new_matches.append(match)
                logger.info(f"Match found: {matched_keywords + matched_emojis} in post {post_id}")
                
        return new_matches
    
    def start_monitoring(self, callback=None):
        """Start continuous monitoring loop"""
        logger.info("Starting Ring neighborhood monitoring...")
        
        if not self.authenticate():
            logger.warning("Running in mock mode without Ring authentication")
        
        while True:
            try:
                posts = self.get_neighborhood_posts()
                new_matches = self.check_for_matches(posts)
                
                if new_matches:
                    self.matches.extend(new_matches)
                    logger.info(f"Found {len(new_matches)} new matches")
                    
                    # Call callback if provided (for real-time updates)
                    if callback:
                        for match in new_matches:
                            callback(match)
                
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.poll_interval)
    
    def get_all_matches(self) -> List[Dict]:
        """Get all detected matches"""
        return self.matches
    
    def get_matches_by_term(self, term: str) -> List[Dict]:
        """Filter matches by keyword or emoji"""
        term_lower = term.lower()
        filtered = []
        
        for match in self.matches:
            if term_lower in [kw.lower() for kw in match['matched_keywords']]:
                filtered.append(match)
            elif term in match['matched_emojis']:
                filtered.append(match)
                
        return filtered
