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
    
    @property
    def is_authenticated(self):
        """Check if monitor is authenticated with Ring"""
        return self.ring is not None
        
    def authenticate(self):
        """Authenticate with Ring API using the ring-doorbell library.
        
        This method implements Ring's authentication flow which supports multiple
        authentication methods:
        
        1. **Refresh Token Authentication** (preferred):
           - If a refresh_token is available from a previous successful login,
             use it to authenticate without requiring credentials again
           - This is the most secure method as credentials don't need to be stored
           - The ring-doorbell library will automatically refresh expired tokens
        
        2. **Email/Password Authentication**:
           - Initial authentication requires Ring account email and password
           - The ring-doorbell library's fetch_token() method exchanges credentials
             for OAuth tokens from Ring's API
        
        3. **Two-Factor Authentication (2FA/OTP)**:
           - If 2FA is enabled on the Ring account, initial auth will fail
           - Ring sends a 6-digit SMS verification code to the account phone
           - The OTP code must be provided in a second authentication attempt
           - The ring-doorbell library's fetch_token() accepts an otp_code parameter
        
        Authentication Flow:
        --------------------
        Step 1: Check for refresh_token
                └─> If available, use it to authenticate (no credentials needed)
                └─> If not available, proceed to Step 2
        
        Step 2: Attempt email/password authentication
                └─> Call fetch_token(username, password)
                └─> Success: Authentication complete, get OAuth tokens
                └─> Failure with 2FA error: Proceed to Step 3
                └─> Failure with other error: Authentication failed
        
        Step 3: 2FA/OTP required (if Step 2 indicated 2FA is enabled)
                └─> Return 'requires_otp' to prompt user for SMS code
                └─> User provides OTP code received via SMS
                └─> Call fetch_token(username, password, otp_code)
                └─> Success: Authentication complete, get OAuth tokens
                └─> Failure: Invalid OTP or other error
        
        The ring-doorbell library handles:
        - OAuth token exchange with Ring's API
        - Token refresh when expired
        - Secure storage of session data
        - Automatic retry logic for transient failures
        
        Returns:
            True: Authentication successful - OAuth tokens obtained and Ring API ready
            'requires_otp': 2FA is enabled - OTP code required to complete authentication
            False: Authentication failed - invalid credentials, network error, or other issue
        """
        if not Auth:
            logger.warning("Ring API not available, running in mock mode")
            return False
            
        try:
            ring_config = self.config['ring']
            
            # AUTHENTICATION PATH 1: Refresh Token (preferred method)
            # --------------------------------------------------------
            # If we have a refresh token from a previous successful login,
            # use it to authenticate. This is more secure as we don't need
            # to store or handle the user's password again.
            if ring_config.get('refresh_token'):
                logger.info("Authenticating with refresh token...")
                self.auth = Auth(
                    "Little Finger Monitor",
                    ring_config['refresh_token'],
                    token_updated_callback=self._token_updated
                )
                # Initialize Ring API client with authenticated session
                self.ring = Ring(self.auth)
                logger.info("Successfully authenticated with Ring using refresh token")
                return True
            else:
                # AUTHENTICATION PATH 2: Email/Password + Optional 2FA
                # -----------------------------------------------------
                logger.info("Authenticating with username/password...")
                
                # Initialize Auth object without token (credential-based auth)
                self.auth = Auth(
                    "Little Finger Monitor"
                )
                
                # Get OTP code from config if provided by user
                # This will be empty on first attempt, set only after user enters it
                otp_code = ring_config.get('otp_code', '').strip()
                
                # STEP 1: Try authentication without OTP first
                # This will succeed if 2FA is not enabled on the account
                try:
                    self.auth.fetch_token(
                        ring_config['username'],
                        ring_config['password']
                    )
                    # Authentication successful without 2FA
                    self.ring = Ring(self.auth)
                    logger.info("Successfully authenticated with Ring (no 2FA required)")
                    return True
                    
                except Exception as e:
                    # STEP 2: Handle 2FA requirement
                    # Check if the error indicates 2FA/OTP is required
                    # Ring's API returns errors mentioning verification, 2FA, code, etc.
                    error_msg = str(e).lower()
                    if '2fa' in error_msg or 'verification' in error_msg or 'code' in error_msg or 'otp' in error_msg:
                        if not otp_code:
                            # 2FA is required but user hasn't provided OTP yet
                            # Return special status to trigger OTP prompt in UI
                            logger.info("2FA/SMS authentication required - OTP code needed")
                            return 'requires_otp'
                        else:
                            # STEP 3: Retry authentication with OTP code
                            # User has provided the 6-digit SMS code, include it in auth
                            logger.info("Authenticating with OTP code...")
                            self.auth.fetch_token(
                                ring_config['username'],
                                ring_config['password'],
                                otp_code=otp_code  # Include SMS verification code
                            )
                            # 2FA authentication successful
                            self.ring = Ring(self.auth)
                            logger.info("Successfully authenticated with Ring (2FA completed)")
                            return True
                    else:
                        # Not a 2FA error - could be wrong password, network issue, etc.
                        # Re-raise to be caught by outer exception handler
                        raise
            
        except Exception as e:
            # Handle any authentication errors
            # Could be: invalid credentials, wrong OTP, network errors, Ring API issues
            logger.error(f"Authentication failed: {e}")
            return False
    
    def _token_updated(self, token):
        """Callback invoked by ring-doorbell library when OAuth token is refreshed.
        
        The ring-doorbell library automatically refreshes OAuth tokens when they expire.
        This callback allows us to capture the new refresh token and update our config
        so that future authentication attempts can use the new token.
        
        Token Lifecycle:
        - Ring OAuth tokens expire after a period of inactivity
        - The ring-doorbell library detects expiration and refreshes automatically
        - New tokens are provided via this callback
        - Storing the new token allows persistent authentication across app restarts
        
        Args:
            token: New OAuth refresh token from Ring's API
        """
        logger.info("Ring OAuth token refreshed by ring-doorbell library")
        # Update config with new refresh token for persistent authentication
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
