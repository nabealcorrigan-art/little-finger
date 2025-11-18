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
    """Handle login page and authentication"""
    if request.method == 'GET':
        # If already authenticated, redirect to dashboard
        if is_authenticated():
            return redirect(url_for('index'))
        return render_template('login.html')
    
    # Handle POST request (authentication attempt)
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        otp_code = data.get('otp_code', '').strip()
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password are required'
            }), 400
        
        global monitor, monitor_thread, pending_credentials
        
        # Store credentials for authentication
        with auth_lock:
            pending_credentials = {
                'username': username,
                'password': password,
                'otp_code': otp_code
            }
        
        # Create a temporary config with credentials
        config = load_config()
        if not config:
            return jsonify({
                'success': False,
                'message': 'Server configuration error'
            }), 500
        
        # Override ring config with provided credentials
        config['ring']['username'] = username
        config['ring']['password'] = password
        config['ring']['otp_code'] = otp_code
        config['ring']['refresh_token'] = ''  # Clear any existing token
        
        # Try to authenticate
        temp_monitor = RingMonitor(config)
        auth_result = temp_monitor.authenticate()
        
        if auth_result == 'requires_otp' and not otp_code:
            # OTP is required but not provided
            return jsonify({
                'success': False,
                'requires_otp': True,
                'message': 'Two-factor authentication code required'
            }), 200
        elif auth_result == True:
            # Authentication successful
            session['authenticated'] = True
            session['username'] = username
            session.permanent = True
            
            # Store the refresh token in session if available
            if temp_monitor.config['ring'].get('refresh_token'):
                session['refresh_token'] = temp_monitor.config['ring']['refresh_token']
            
            # Update global monitor with authenticated instance
            with auth_lock:
                monitor = temp_monitor
                pending_credentials = None
            
            # Start monitoring if not already running
            if not monitor_thread or not monitor_thread.is_alive():
                monitor_thread = Thread(target=start_monitoring_thread, daemon=True)
                monitor_thread.start()
            
            logger.info(f"User {username} authenticated successfully")
            return jsonify({
                'success': True,
                'message': 'Authentication successful'
            }), 200
        else:
            # Authentication failed
            return jsonify({
                'success': False,
                'message': 'Authentication failed. Please check your credentials.'
            }), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
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
        
        # Run async auth in a separate thread
        def run_auth():
            global browser_auth
            
            async def do_auth():
                global browser_auth
                browser_auth = RingBrowserAuth(headless=False)
                
                try:
                    await browser_auth.start_browser()
                    await browser_auth.navigate_to_login()
                    
                    # Wait for authentication (5 minutes timeout)
                    auth_data = await browser_auth.wait_for_authentication(timeout_seconds=300)
                    
                    # Save the auth state
                    await browser_auth.save_auth_state(auth_state_file)
                    
                    # Store in session
                    session['auth_data'] = {
                        'timestamp': auth_data['timestamp'],
                        'has_cookies': len(auth_data['cookies']) > 0
                    }
                    session['authenticated'] = True
                    session['auth_method'] = 'browser'
                    
                    logger.info("Browser authentication successful")
                    
                    # Initialize monitor with the captured session
                    await initialize_monitor_from_browser_auth(auth_data)
                    
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
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/auth/browser/status', methods=['GET'])
def check_browser_auth_status():
    """Check status of browser authentication"""
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
    """Initialize Ring monitor using browser-captured authentication"""
    global monitor, monitor_thread
    
    config = load_config()
    if not config:
        raise RuntimeError("Failed to load configuration")
    
    # Try to extract refresh token from auth data
    refresh_token = None
    
    if auth_data.get('intercepted_tokens'):
        for token_data in auth_data['intercepted_tokens']:
            if isinstance(token_data, dict) and 'refresh_token' in token_data:
                refresh_token = token_data['refresh_token']
                logger.info("Found refresh token in intercepted API calls")
                break
    
    if auth_data.get('tokens'):
        for key, value in auth_data['tokens'].items():
            if isinstance(value, dict) and 'refresh_token' in value:
                refresh_token = value['refresh_token']
                logger.info(f"Found refresh token in browser storage: {key}")
                break
    
    if refresh_token:
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
                logger.info("Monitor initialized successfully with browser-captured tokens")
                
                # Start monitoring if not already running
                if not monitor_thread or not monitor_thread.is_alive():
                    monitor_thread = Thread(target=start_monitoring_thread, daemon=True)
                    monitor_thread.start()
            else:
                raise RuntimeError("Failed to authenticate monitor with captured tokens")
    else:
        logger.warning("No refresh token found in browser auth data")
        raise RuntimeError("Could not extract authentication tokens from browser session")


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
