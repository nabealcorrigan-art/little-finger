"""
Web Server for Ring Neighborhood Heat Map
Serves real-time heat map of detected Ring neighborhood posts
"""
import json
import logging
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from threading import Thread
from ring_monitor import RingMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'little-finger-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global monitor instance
monitor = None
monitor_thread = None


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


@app.route('/')
def index():
    """Serve the heat map dashboard"""
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
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return
    
    # Initialize monitor
    monitor = RingMonitor(config)
    
    # Start monitoring in background thread
    monitor_thread = Thread(target=start_monitoring_thread, daemon=True)
    monitor_thread.start()
    
    # Start web server
    host = config['server']['host']
    port = config['server']['port']
    
    logger.info(f"Starting Little Finger Monitor on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
