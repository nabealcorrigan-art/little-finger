"""
Web Server for Ring Neighborhood Heat Map
Serves real-time heat map of detected Ring neighborhood posts
"""
import json
import logging
import secrets
import asyncio
import os
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from threading import Thread, Lock
from ring_monitor import RingMonitor
from ring_browser_auth import RingBrowserAuth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global monitor instance
monitor = None
monitor_thread = None
auth_lock = Lock()
pending_credentials = None
browser_auth = None
auth_state_file = 'ring_auth_state.json'


def load_config():
    """Load configuration from JSON file"""
    try:
        # Use utf-8-sig encoding to handle UTF-8 BOM if present
        with open('config.json', 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found")
        return None
    except json.JSONDecodeError as e:
        # Defensive attribute access in case exception object is malformed
        try:
            msg = getattr(e, 'msg', 'Unknown JSON error')
            lineno = getattr(e, 'lineno', '?')
            colno = getattr(e, 'colno', '?')
            logger.error(f"Invalid JSON in config.json: {msg} at line {lineno}, column {colno}")
        except Exception:
            # Fallback if accessing attributes fails
            logger.error(f"Invalid JSON in config.json: {str(e)}")
        logger.error("Please check your config.json file for syntax errors (trailing commas, missing brackets, etc.)")
        logger.error("You can validate your JSON at https://jsonlint.com/")
        return None
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error loading config.json: {type(e).__name__}: {e}")
        return None


def on_new_match(match):
    """Callback for new matches - emit via SocketIO"""
    logger.info(f"Broadcasting new match: {match['id']}")
    socketio.emit('new_match', match, namespace='/')


def start_monitoring_thread():
    """Start the Ring monitoring in a background thread"""
    global monitor
    if monitor:
        monitor.start_monitoring(callback=on_new_match)


def is_authenticated():
    """Check if user is authenticated"""
    return session.get('authenticated', False)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login page and Ring authentication via ring-doorbell library.
    
    This endpoint implements the complete Ring authentication flow:
    
    GET /login:
        - Displays the login form with fields for email, password, and OTP
        - If user is already authenticated, redirects to dashboard
    
    POST /login:
        - Accepts JSON payload with username, password, and optional otp_code
        - Uses ring-doorbell library to authenticate with Ring's API
        - Handles the 2FA flow if the Ring account has SMS verification enabled
        
    Ring Authentication Flow via ring-doorbell:
    -------------------------------------------
    1. User submits email + password
    2. ring-doorbell attempts authentication via Ring's OAuth API
    3. Three possible outcomes:
       a) Success: Account has no 2FA, authentication complete
       b) 2FA Required: Ring requires SMS verification code
       c) Failure: Invalid credentials or Ring API error
    
    2FA Flow:
    ---------
    If 2FA is enabled on the Ring account:
    1. Initial auth attempt (email+password only) fails with 2FA error
    2. Server returns requires_otp=True response
    3. Client prompts user to enter 6-digit SMS code
    4. User submits email + password + OTP code
    5. ring-doorbell re-authenticates with OTP included
    6. Success: OAuth tokens obtained, user is authenticated
    
    Error Handling:
    ---------------
    The implementation provides specific feedback for different failure types:
    - Missing credentials: 400 error with validation message
    - 2FA required: 200 response with requires_otp flag and instructions
    - Invalid credentials/OTP: 401 error with credential check message
    - Ring API errors: 500 error with specific error details
    - Network/server errors: 500 error with error message
    """
    if request.method == 'GET':
        # Serve the login page
        # If already authenticated, redirect to dashboard to prevent re-login
        if is_authenticated():
            return redirect(url_for('index'))
        return render_template('login.html')
    
    # Handle POST request (authentication attempt with ring-doorbell library)
    try:
        # Parse credentials from JSON request body
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        otp_code = data.get('otp_code', '').strip()
        
        # Validate required fields
        if not username or not password:
            return jsonify({
                'success': False,
                'error_type': 'validation',
                'message': 'Ring email address and password are required'
            }), 400
        
        global monitor, monitor_thread, pending_credentials
        
        # Store credentials temporarily for potential retry with OTP
        with auth_lock:
            pending_credentials = {
                'username': username,
                'password': password,
                'otp_code': otp_code
            }
        
        # Load monitoring configuration (keywords, poll interval, etc.)
        config = load_config()
        if not config:
            return jsonify({
                'success': False,
                'error_type': 'server',
                'message': 'Server configuration error. Please contact administrator.'
            }), 500
        
        # Set Ring authentication credentials in config
        # ring-doorbell library will use these to authenticate with Ring's API
        config['ring']['username'] = username
        config['ring']['password'] = password
        config['ring']['otp_code'] = otp_code
        config['ring']['refresh_token'] = ''  # Clear any existing token to force fresh auth
        
        # Initialize Ring monitor with credentials
        # This creates an instance but doesn't authenticate yet
        temp_monitor = RingMonitor(config)
        
        # Attempt authentication via ring-doorbell library
        # This calls Ring's OAuth API to exchange credentials for tokens
        auth_result = temp_monitor.authenticate()
        
        # Handle authentication result
        if auth_result == 'requires_otp' and not otp_code:
            # CASE 1: 2FA is enabled but user hasn't provided OTP code yet
            # Ring has sent an SMS with 6-digit code to the user's phone
            # Return special response to trigger OTP input in UI
            logger.info(f"2FA required for user {username}, waiting for OTP code")
            return jsonify({
                'success': False,
                'requires_otp': True,
                'error_type': '2fa_required',
                'message': 'Two-factor authentication is enabled on your Ring account. Please enter the 6-digit verification code sent to your phone via SMS.'
            }), 200
            
        elif auth_result == True:
            # CASE 2: Authentication successful!
            # ring-doorbell has obtained OAuth tokens from Ring's API
            # User is now authenticated and can access Ring data
            
            # Create authenticated session
            session['authenticated'] = True
            session['username'] = username
            session.permanent = True  # Keep session across browser restarts
            
            # Store refresh token in session for persistent authentication
            # This allows re-authentication without credentials on next login
            if temp_monitor.config['ring'].get('refresh_token'):
                session['refresh_token'] = temp_monitor.config['ring']['refresh_token']
            
            # Update global monitor instance with authenticated session
            with auth_lock:
                monitor = temp_monitor
                pending_credentials = None  # Clear stored credentials
            
            # Start background monitoring thread if not already running
            # This begins polling Ring API for neighborhood posts
            if not monitor_thread or not monitor_thread.is_alive():
                monitor_thread = Thread(target=start_monitoring_thread, daemon=True)
                monitor_thread.start()
            
            logger.info(f"User {username} authenticated successfully with Ring")
            return jsonify({
                'success': True,
                'message': 'Successfully authenticated with Ring. Redirecting to dashboard...'
            }), 200
            
        else:
            # CASE 3: Authentication failed
            # Could be: wrong password, invalid OTP, expired OTP, Ring API error, etc.
            # Provide detailed feedback to help user troubleshoot
            
            error_message = 'Authentication with Ring failed. '
            
            if otp_code:
                # User provided OTP but auth still failed
                # Most likely: wrong OTP, expired OTP, or credential issue
                error_message += 'Please check your email, password, and verification code. The SMS code may have expired - request a new one by logging in again.'
                error_type = 'invalid_otp'
                logger.warning(f"Authentication failed for {username} with OTP code")
            else:
                # No OTP provided, likely credential error
                error_message += 'Please verify your Ring email address and password are correct.'
                error_type = 'invalid_credentials'
                logger.warning(f"Authentication failed for {username}: invalid credentials")
            
            return jsonify({
                'success': False,
                'error_type': error_type,
                'message': error_message
            }), 401
            
    except Exception as e:
        # Catch unexpected errors (network issues, Ring API changes, etc.)
        error_str = str(e)
        logger.error(f"Login error for {username if 'username' in locals() else 'unknown'}: {error_str}")
        
        # Try to provide helpful error message based on exception
        error_type = 'server'
        if 'network' in error_str.lower() or 'connection' in error_str.lower():
            error_message = 'Network error connecting to Ring. Please check your internet connection and try again.'
            error_type = 'network'
        elif 'timeout' in error_str.lower():
            error_message = 'Connection to Ring timed out. Please try again.'
            error_type = 'timeout'
        else:
            error_message = f'An error occurred during authentication: {error_str}'
        
        return jsonify({
            'success': False,
            'error_type': error_type,
            'message': error_message
        }), 500


@app.route('/logout')
def logout():
    """Handle logout"""
    global monitor, monitor_thread
    
    username = session.get('username', 'Unknown')
    session.clear()
    
    # Note: We don't stop the monitor thread as it's daemon and will stop with the app
    # This allows other users to still see data if in a multi-user scenario
    
    logger.info(f"User {username} logged out")
    return redirect(url_for('login'))


@app.route('/auth/browser/start', methods=['POST'])
def start_browser_auth():
    """Start browser-based authentication with Ring"""
    global browser_auth
    
    try:
        # Check if already authenticated
        if is_authenticated():
            return jsonify({
                'success': False,
                'message': 'Already authenticated'
            }), 400
        
        # Check if browser auth is already in progress
        if browser_auth is not None:
            return jsonify({
                'success': False,
                'message': 'Browser authentication already in progress'
            }), 400
        
        # Initialize browser_auth before starting thread so status endpoint can see it
        browser_auth = RingBrowserAuth(headless=False)
        
        # Run async auth in a separate thread
        def run_auth():
            global browser_auth
            
            async def do_auth():
                global browser_auth, monitor, monitor_thread
                
                try:
                    await browser_auth.start_browser()
                    await browser_auth.navigate_to_login()
                    
                    # Wait for authentication (5 minutes timeout)
                    auth_data = await browser_auth.wait_for_authentication(timeout_seconds=300)
                    
                    # Save the auth state
                    await browser_auth.save_auth_state(auth_state_file)
                    
                    logger.info("Browser authentication successful")
                    
                    # Initialize monitor with the captured session
                    await initialize_monitor_from_browser_auth(auth_data)
                    
                    # Mark as authenticated (using Flask's session requires app context)
                    with app.app_context():
                        from flask import session as flask_session
                        # Note: Session modifications in thread won't persist
                        # The client-side polling will detect successful auth via monitor state
                    
                except Exception as e:
                    logger.error(f"Browser authentication failed: {e}")
                finally:
                    await browser_auth.close()
                    browser_auth = None
            
            # Run the async function
            asyncio.run(do_auth())
        
        # Start auth in background thread
        auth_thread = Thread(target=run_auth, daemon=True)
        auth_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Browser authentication started. Please complete login in the browser window.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting browser auth: {e}")
        browser_auth = None  # Reset on error
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/auth/browser/status', methods=['GET'])
def check_browser_auth_status():
    """Check status of browser authentication"""
    # Check if monitor is authenticated (indicates successful browser auth)
    if monitor and monitor.is_authenticated:
        # Mark session as authenticated
        session['authenticated'] = True
        session['auth_method'] = 'browser'
        return jsonify({
            'authenticated': True,
            'method': 'browser'
        }), 200
    
    # Fall back to session check
    if is_authenticated():
        return jsonify({
            'authenticated': True,
            'method': session.get('auth_method', 'unknown')
        }), 200
    
    return jsonify({
        'authenticated': False,
        'browser_active': browser_auth is not None
    }), 200


async def initialize_monitor_from_browser_auth(auth_data):
    """Initialize Ring monitor using browser-captured authentication
    
    ⚠️ KNOWN ISSUE: This function is part of an experimental feature that does not
    currently work with Ring's API. Ring does not expose OAuth tokens in a way that
    can be captured from browser storage or easily intercepted.
    
    This function will typically fail with "Could not extract authentication tokens"
    because the required refresh_token is not available.
    """
    global monitor, monitor_thread
    
    logger.warning("=" * 70)
    logger.warning("⚠️ EXPERIMENTAL: Attempting to initialize monitor from browser auth")
    logger.warning("⚠️ THIS IS KNOWN TO NOT WORK - Ring API tokens cannot be extracted")
    logger.warning("=" * 70)
    
    config = load_config()
    if not config:
        raise RuntimeError("Failed to load configuration")
    
    # Try to extract refresh token from auth data
    refresh_token = None
    
    logger.info("Checking for refresh token in intercepted API calls...")
    if auth_data.get('intercepted_tokens'):
        logger.info(f"Found {len(auth_data['intercepted_tokens'])} intercepted token responses")
        for i, token_data in enumerate(auth_data['intercepted_tokens']):
            if isinstance(token_data, dict) and 'refresh_token' in token_data:
                refresh_token = token_data['refresh_token']
                logger.info(f"✓ Found refresh token in intercepted API call #{i}")
                break
        if not refresh_token:
            logger.warning("❌ No refresh_token found in any intercepted API calls")
    else:
        logger.warning("❌ No intercepted_tokens in auth data")
    
    if not refresh_token:
        logger.info("Checking for refresh token in browser storage...")
        if auth_data.get('tokens'):
            logger.info(f"Found {len(auth_data['tokens'])} token-related storage keys")
            for key, value in auth_data['tokens'].items():
                logger.info(f"  - Checking key: {key}")
                if isinstance(value, dict) and 'refresh_token' in value:
                    refresh_token = value['refresh_token']
                    logger.info(f"✓ Found refresh token in browser storage key: {key}")
                    break
            if not refresh_token:
                logger.warning("❌ No refresh_token found in any browser storage keys")
        else:
            logger.warning("❌ No tokens dictionary in auth data")
    
    if refresh_token:
        logger.info("=" * 70)
        logger.info("✓ UNEXPECTED SUCCESS: Found a refresh token!")
        logger.info("  Attempting to initialize Ring monitor...")
        logger.info("=" * 70)
        
        # Use the captured refresh token
        config['ring']['refresh_token'] = refresh_token
        config['ring']['username'] = ''
        config['ring']['password'] = ''
        config['ring']['otp_code'] = ''
        
        # Initialize monitor with refresh token
        with auth_lock:
            monitor = RingMonitor(config)
            auth_result = monitor.authenticate()
            
            if auth_result:
                logger.info("✓✓✓ SUCCESS! Monitor initialized with browser-captured tokens!")
                logger.info("✓✓✓ Browser authentication is now working!")
                
                # Start monitoring if not already running
                if not monitor_thread or not monitor_thread.is_alive():
                    monitor_thread = Thread(target=start_monitoring_thread, daemon=True)
                    monitor_thread.start()
            else:
                logger.error("❌ Failed to authenticate monitor with captured tokens")
                raise RuntimeError("Failed to authenticate monitor with captured tokens")
    else:
        logger.error("=" * 70)
        logger.error("❌ EXPECTED FAILURE: No refresh token found in browser auth data")
        logger.error("❌ This is the known limitation of the browser auth feature")
        logger.error("=" * 70)
        logger.error("Ring does not expose OAuth tokens in browser storage or easily")
        logger.error("interceptable API calls. To authenticate with Ring:")
        logger.error("")
        logger.error("1. Use the FORM-BASED LOGIN on the login page")
        logger.error("2. Enter your Ring email and password directly")
        logger.error("3. Include 2FA code if required")
        logger.error("")
        logger.error("Browser authentication is experimental and NOT FUNCTIONAL.")
        logger.error("=" * 70)
        raise RuntimeError("Could not extract authentication tokens from browser session. Use form-based login instead.")


@app.route('/')
def index():
    """Serve the heat map dashboard"""
    if not is_authenticated():
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/api/matches')
def get_matches():
    """Get all matches"""
    if not monitor:
        return jsonify([])
    return jsonify(monitor.get_all_matches())


@app.route('/api/matches/filter')
def filter_matches():
    """Filter matches by term"""
    term = request.args.get('term', '')
    if not monitor or not term:
        return jsonify([])
    return jsonify(monitor.get_matches_by_term(term))


@app.route('/api/stats')
def get_stats():
    """Get statistics about matches"""
    if not monitor:
        return jsonify({
            'total_matches': 0,
            'keywords': [],
            'emojis': []
        })
    
    matches = monitor.get_all_matches()
    
    # Count keyword occurrences
    keyword_counts = {}
    emoji_counts = {}
    
    for match in matches:
        for kw in match.get('matched_keywords', []):
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        for emoji in match.get('matched_emojis', []):
            emoji_counts[emoji] = emoji_counts.get(emoji, 0) + 1
    
    return jsonify({
        'total_matches': len(matches),
        'keyword_counts': keyword_counts,
        'emoji_counts': emoji_counts,
        'configured_keywords': monitor.keywords,
        'configured_emojis': monitor.emojis
    })


@app.route('/api/config')
def get_config():
    """Get monitoring configuration (without credentials)"""
    if not monitor:
        return jsonify({})
    
    return jsonify({
        'keywords': monitor.keywords,
        'emojis': monitor.emojis,
        'poll_interval': monitor.poll_interval
    })


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('connected', {'data': 'Connected to Little Finger Monitor'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')


def main():
    """Main entry point"""
    global monitor, monitor_thread
    
    # Load configuration (monitoring settings only, not credentials)
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return
    
    # Clear any credentials from config file (we'll use web-based login)
    config['ring']['username'] = ''
    config['ring']['password'] = ''
    config['ring']['otp_code'] = ''
    config['ring']['refresh_token'] = ''
    
    # Initialize monitor without credentials (will be set via web login)
    monitor = RingMonitor(config)
    
    # Note: monitoring thread will start after successful login
    
    # Start web server
    host = config['server']['host']
    port = config['server']['port']
    
    logger.info(f"Starting Little Finger Monitor on http://{host}:{port}")
    logger.info("Please open your browser and login to start monitoring")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
