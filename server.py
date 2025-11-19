"""
Web Server for Ring Neighborhood Heat Map
Serves real-time heat map of detected Ring neighborhood posts
"""
import json
import logging
import secrets
import os
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from threading import Thread, Lock
from ring_monitor import RingMonitor

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
    
    This endpoint implements the Ring authentication flow using the ring-doorbell
    Python library for reliable API access.
    
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
    
    Authentication Failure Handling:
    --------------------------------
    If authentication fails, the response includes:
    - error_type: Category of error (validation, 2fa_required, invalid_credentials, 
      invalid_otp, network, timeout, server)
    - message: Detailed error message explaining what went wrong and how to fix it
    - success: false flag
    - requires_otp: true if 2FA is needed (for 2fa_required error type)
    
    Possible failure scenarios:
    1. Missing credentials (400): Email or password not provided
    2. 2FA required (200): SMS code needed but not yet provided
    3. Invalid credentials (401): Wrong email or password
    4. Invalid OTP (401): Wrong or expired 2FA code
    5. Network error (500): Cannot reach Ring's servers
    6. Timeout error (500): Request to Ring's servers timed out
    7. Server error (500): Internal server or config error
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
            logger.warning("Login attempt with missing credentials")
            return jsonify({
                'success': False,
                'error_type': 'validation',
                'message': 'Ring email address and password are required. Please fill in both fields.'
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
            logger.error("Failed to load configuration file")
            return jsonify({
                'success': False,
                'error_type': 'server',
                'message': 'Server configuration error. The config.json file is missing or invalid. Please contact the administrator.'
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
        logger.info(f"Attempting authentication for user: {username}")
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
                'message': 'Two-factor authentication is enabled on your Ring account. Ring has sent a 6-digit verification code to your phone via SMS. Please enter the code in the OTP field and submit again.'
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
            
            logger.info(f"✓ User {username} authenticated successfully with Ring via ring-doorbell library")
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
                error_message += 'Please verify:\n'
                error_message += '• Your Ring email address is correct\n'
                error_message += '• Your Ring password is correct\n'
                error_message += '• The 6-digit SMS verification code is correct and not expired\n'
                error_message += '• The code is from the most recent SMS (not an old one)\n\n'
                error_message += 'If the code expired, request a new one by attempting login again without the OTP field filled.'
                error_type = 'invalid_otp'
                logger.warning(f"❌ Authentication failed for {username} with OTP code - likely invalid or expired OTP")
            else:
                # No OTP provided, likely credential error
                error_message += 'Please verify:\n'
                error_message += '• You are using your Ring account EMAIL address (not a username)\n'
                error_message += '• Your password is correct (passwords are case-sensitive)\n'
                error_message += '• Your Ring account is active and not suspended\n\n'
                error_message += 'You can verify your credentials by logging in at https://account.ring.com'
                error_type = 'invalid_credentials'
                logger.warning(f"❌ Authentication failed for {username} - likely invalid email or password")
            
            return jsonify({
                'success': False,
                'error_type': error_type,
                'message': error_message
            }), 401
            
    except Exception as e:
        # Catch unexpected errors (network issues, Ring API changes, library bugs, etc.)
        error_str = str(e)
        username_for_log = username if 'username' in locals() else 'unknown'
        logger.error(f"❌ Unexpected login error for {username_for_log}: {error_str}")
        
        # Try to provide helpful error message based on exception
        error_type = 'server'
        error_message = 'An unexpected error occurred during authentication.\n\n'
        
        if 'network' in error_str.lower() or 'connection' in error_str.lower():
            error_message += 'Network Error:\n'
            error_message += '• Cannot connect to Ring\'s servers\n'
            error_message += '• Check your internet connection\n'
            error_message += '• Verify firewall is not blocking outbound HTTPS (port 443)\n'
            error_message += '• Ring API domains must be accessible: api.ring.com, oauth.ring.com'
            error_type = 'network'
        elif 'timeout' in error_str.lower():
            error_message += 'Connection Timeout:\n'
            error_message += '• Ring\'s servers are taking too long to respond\n'
            error_message += '• Try again in a few moments\n'
            error_message += '• Check your network connection speed and stability'
            error_type = 'timeout'
        else:
            error_message += f'Error details: {error_str}\n\n'
            error_message += 'Troubleshooting steps:\n'
            error_message += '• Try again in a few moments\n'
            error_message += '• Check server logs for more details\n'
            error_message += '• Verify ring-doorbell library is installed: pip install ring-doorbell==0.8.8\n'
            error_message += '• Report issue if problem persists at: https://github.com/nabealcorrigan-art/little-finger/issues'
        
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
