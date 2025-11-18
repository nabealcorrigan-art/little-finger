"""
Web Server for Ring Neighborhood Heat Map
Serves real-time heat map of detected Ring neighborhood posts
"""
import json
import logging
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from threading import Thread
from ring_monitor import RingMonitor
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'little-finger-secret-key'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global monitor instance
monitor = None
monitor_thread = None
is_authenticated = False


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


def save_config(config):
    """Save configuration to JSON file"""
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False


def check_credentials_configured():
    """Check if Ring credentials are configured"""
    config = load_config()
    if not config:
        return False
    ring_config = config.get('ring', {})
    username = ring_config.get('username', '').strip()
    password = ring_config.get('password', '').strip()
    refresh_token = ring_config.get('refresh_token', '').strip()
    
    # Valid if we have refresh token OR username+password
    return bool(refresh_token or (username and password))


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        global is_authenticated
        if not is_authenticated and not session.get('authenticated'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def on_new_match(match):
    """Callback for new matches - emit via SocketIO"""
    logger.info(f"Broadcasting new match: {match['id']}")
    socketio.emit('new_match', match, namespace='/')


def start_monitoring_thread():
    """Start the Ring monitoring in a background thread"""
    global monitor
    if monitor:
        monitor.start_monitoring(callback=on_new_match)


@app.route('/')
@login_required
def index():
    """Serve the heat map dashboard"""
    return render_template('index.html')


@app.route('/login')
def login_page():
    """Serve the login page"""
    global is_authenticated
    # If already authenticated, redirect to dashboard
    if is_authenticated or session.get('authenticated'):
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/api/login', methods=['POST'])
def login():
    """Handle login request"""
    global monitor, monitor_thread, is_authenticated
    
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        otp_code = data.get('otp_code', '').strip()
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Load config and update credentials
        config = load_config()
        if not config:
            return jsonify({'error': 'Failed to load configuration'}), 500
        
        config['ring']['username'] = username
        config['ring']['password'] = password
        config['ring']['otp_code'] = otp_code
        
        # Save config
        if not save_config(config):
            return jsonify({'error': 'Failed to save credentials'}), 500
        
        # Try to authenticate
        test_monitor = RingMonitor(config)
        auth_result = test_monitor.authenticate()
        
        if auth_result:
            # Authentication successful
            session['authenticated'] = True
            is_authenticated = True
            
            # Update global monitor and start monitoring
            monitor = test_monitor
            if not monitor_thread or not monitor_thread.is_alive():
                monitor_thread = Thread(target=start_monitoring_thread, daemon=True)
                monitor_thread.start()
            
            # Clear OTP from config after successful auth
            config['ring']['otp_code'] = ''
            save_config(config)
            
            logger.info(f"User {username} logged in successfully")
            return jsonify({'success': True})
        else:
            # Check if OTP is needed
            error_msg = 'Authentication failed. Please check your credentials.'
            requires_otp = not otp_code
            
            if requires_otp:
                return jsonify({
                    'success': False,
                    'requires_otp': True,
                    'message': '2FA verification required'
                })
            
            return jsonify({'error': error_msg}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    """Handle logout request"""
    global is_authenticated
    session.clear()
    is_authenticated = False
    logger.info("User logged out")
    return jsonify({'success': True})


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
    global monitor, monitor_thread, is_authenticated
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return
    
    # Check if credentials are configured and valid
    if check_credentials_configured():
        logger.info("Credentials found in config, attempting authentication...")
        # Initialize monitor
        monitor = RingMonitor(config)
        
        # Try to authenticate
        if monitor.authenticate():
            is_authenticated = True
            # Start monitoring in background thread
            monitor_thread = Thread(target=start_monitoring_thread, daemon=True)
            monitor_thread.start()
            logger.info("Authenticated successfully, monitoring started")
        else:
            logger.warning("Authentication failed with existing credentials")
            logger.info("Please login through the web interface")
    else:
        logger.info("No credentials configured, login required")
        logger.info("Please navigate to the web interface to login")
    
    # Start web server
    host = config['server']['host']
    port = config['server']['port']
    
    logger.info(f"Starting Little Finger Monitor on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
