# Little Finger 🕵️

A headless monitoring application for Ring Neighborhood that tracks specified keywords and emojis in neighborhood posts, then visualizes matches on a real-time heat map.

> **⚠️ Important Note**: This application uses the unofficial `ring-doorbell` Python library to connect to Ring's API. Ring does not provide official public API access to neighborhood posts. The availability and functionality of neighborhood data access depends on Ring's current API implementation and your account type. See [RING_API_DETAILS.md](RING_API_DETAILS.md) for technical details and alternatives.

## Features

- 🔍 **Keyword & Emoji Monitoring**: Track specific words and emojis in Ring neighborhood posts
- 🗺️ **Live Heat Map**: Real-time visualization of matched posts with geographical intensity
- ⚡ **Real-Time Updates**: WebSocket-based streaming of new matches to the dashboard
- 🎯 **Filtering**: Filter heat map and matches by specific terms
- ⏰ **Precise Timestamps**: Each match includes exact detection time and post time
- 📍 **Location Tracking**: Captures and displays the geographical location of each match
- 📊 **Statistics Dashboard**: View match counts and monitoring statistics

## Architecture

The application consists of three main components:

1. **Ring Monitor** (`ring_monitor.py`): Polls Ring API for neighborhood posts and detects matches
2. **Web Server** (`server.py`): Flask-based REST API and WebSocket server
3. **Dashboard** (`templates/index.html`): Interactive heat map visualization with Leaflet.js

## Installation

### Prerequisites

- Python 3.8 or higher
- Ring account credentials
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone https://github.com/nabealcorrigan-art/little-finger.git
cd little-finger
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure monitoring settings in `config.json`:
```json
{
  "ring": {
    "username": "",
    "password": "",
    "refresh_token": "",
    "otp_code": ""
  },
  "monitoring": {
    "poll_interval_seconds": 60,
    "keywords": ["suspicious", "theft", "break-in", "burglar", "police"],
    "emojis": ["🚨", "🚔", "⚠️", "🔴"]
  },
  "server": {
    "host": "0.0.0.0",
    "port": 5777
  }
}
```

**Note**: You no longer need to add credentials to `config.json`. The application uses a web-based login interface.

### Authentication

The application supports **two authentication methods**:

#### 📝 Form-Based Login (Recommended - Works Reliably)

Traditional method where you enter credentials in the app:

1. Start the server (see Usage below)
2. Open your browser and navigate to `http://localhost:5777`
3. Enter your Ring email address and password in the form
4. If your account has 2FA enabled, enter the 6-digit OTP code sent via SMS
5. After successful authentication, you'll be redirected to the monitoring dashboard

**Security Features**:
- Credentials are only used to authenticate with Ring's API via the ring-doorbell library
- Session-based authentication with secure session keys
- Refresh tokens are stored securely in memory
- Logout functionality to clear your session

**⚠️ Important:** This is the **only authentication method that currently works reliably** with the Ring API.

#### 🔐 Browser-Based Login (Experimental - Not Fully Functional)

**⚠️ STATUS: This feature is EXPERIMENTAL and does NOT currently work for Ring API authentication.**

While the browser automation successfully opens Ring's website and allows you to login, it **cannot currently extract the OAuth tokens** needed to authenticate with Ring's API. This is because:

- Ring's OAuth tokens are not stored in accessible browser storage (localStorage/sessionStorage)
- The Ring website uses a different authentication flow than what the ring-doorbell library expects
- API endpoint interception has not been successfully implemented to capture the refresh tokens

**What it does:**
- Opens a browser window to Ring's login page
- Allows you to login through Ring's official website
- Captures cookies and browser session data

**What it CANNOT do (currently):**
- Extract the OAuth refresh token needed for the ring-doorbell library
- Successfully authenticate the Ring monitor
- Enable neighborhood post monitoring

**If you want to help fix this:** The implementation needs work in `ring_browser_auth.py` to properly intercept Ring's OAuth token API calls or extract tokens from the authenticated browser session. Contributions welcome!

For now, **please use the Form-Based Login method** which works reliably.

## Usage

### Quick Start with Shell Script

The easiest way to start:
```bash
./start.sh
```

This will:
- Create a virtual environment if needed
- Install dependencies
- Start the server

### Manual Start

Run the application directly:
```bash
python server.py
```

### Docker Deployment

For containerized deployment:

1. Start with Docker Compose:
```bash
docker-compose up -d
```

2. Or build and run manually:
```bash
docker build -t little-finger .
docker run -p 5777:5777 little-finger
```

The server will start on `http://0.0.0.0:5777` by default.

### Accessing the Application

1. Open your browser and navigate to:
   - `http://localhost:5777` (if running locally)
   - `http://YOUR_SERVER_IP:5777` (if running on a remote server)

2. You'll be automatically redirected to the login page

3. Enter your Ring credentials:
   - Ring email address
   - Ring password
   - OTP code (if 2FA is enabled on your account)

4. After successful login, the monitoring dashboard will appear and monitoring will begin automatically

### Configuration Options

- **poll_interval_seconds**: How often to check for new posts (default: 60 seconds)
- **keywords**: List of case-insensitive keywords to monitor
- **emojis**: List of emojis to detect in posts
- **host**: Server bind address (use "0.0.0.0" to allow external access)
- **port**: Server port number

## API Endpoints

### Authentication
- `GET /login`: Login page with form-based authentication (browser auth is experimental)
- `POST /login`: Form-based authentication endpoint (accepts JSON with username, password, otp_code)
- `POST /auth/browser/start`: ⚠️ EXPERIMENTAL - Start browser-based authentication (does not currently work for Ring API)
- `GET /auth/browser/status`: ⚠️ EXPERIMENTAL - Check browser authentication status (not functional)
- `GET /logout`: Logout and clear session

### Application
- `GET /`: Dashboard interface (requires authentication)
- `GET /api/matches`: Get all detected matches
- `GET /api/matches/filter?term=<term>`: Filter matches by keyword or emoji
- `GET /api/stats`: Get monitoring statistics
- `GET /api/config`: Get current monitoring configuration
- WebSocket `/`: Real-time match updates

## Dashboard Features

### Authentication
- **Form-Based Login (Recommended)**: Enter Ring credentials to authenticate with Ring's API - WORKS RELIABLY
- **Browser-Based Login (Experimental)**: ⚠️ Opens Ring's website but cannot extract API tokens - NOT FUNCTIONAL
- **2FA Support**: Full support for Ring's two-factor authentication via SMS OTP codes in form-based login
- **Session Management**: Stay logged in across browser sessions
- **Logout**: Clear session and return to login page

### Heat Map
- **Intensity Colors**: Blue (low) → Green → Yellow → Orange → Red (high)
- **Markers**: Click on red circle markers to see match details
- **Auto-Zoom**: Map automatically adjusts to show all matches

### Filtering
- Click on any keyword or emoji tag to filter the view
- Click "All" to show all matches
- Filters apply to both the heat map and the matches list

### Statistics
- Total match count
- Number of monitored terms
- Real-time connection status indicator

## Development

### Project Structure
```
little-finger/
├── ring_monitor.py      # Ring API monitoring logic
├── server.py            # Flask web server and API
├── templates/
│   └── index.html       # Dashboard interface
├── config.json          # Configuration template
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Adding Mock Data for Testing

The application includes robust testing capabilities:

1. **Automatic Mock Mode**: When Ring API is unavailable, the system runs in mock mode
2. **Demo Data Generator**: Use `generate_demo_data.py` to create realistic test data:
   ```bash
   python generate_demo_data.py
   ```
3. **Manual Mock Data**: Modify `_get_mock_posts()` in `ring_monitor.py` to customize test posts

**Note**: Mock mode is perfect for development, testing the heat map visualization, and demonstrating the system without Ring API access.

## Security Considerations

### Built-in Security Features
- **No Hardcoded Credentials**: All authentication happens through the web UI
- **Session-based Authentication**: Credentials are not stored in files
- **Secure Session Keys**: Generated randomly on each server start
- **Logout Functionality**: Clear sessions when done
- **In-memory Token Storage**: Refresh tokens stored only in session, not persisted to disk

### Production Recommendations
- Use HTTPS when exposing the server over the internet (use reverse proxy like nginx/caddy)
- Consider adding rate limiting on login endpoint
- Use environment variables or secrets manager for sensitive configuration
- Regular dependency updates for security patches
- Monitor access logs for suspicious activity

## Headless Operation

The application is designed to run headless (without a GUI) on servers like Kali Linux:

```bash
# Run in background with nohup
nohup python server.py > app.log 2>&1 &

# Or use screen
screen -S little-finger
python server.py
# Press Ctrl+A then D to detach
```

Access the web interface from any browser on your network.

## Troubleshooting

### Ring API Connection
- **Neighborhood Access**: The `ring-doorbell` library may not support neighborhood posts for all accounts
- **API Limitations**: Ring's unofficial API can change without notice
- **Testing**: Use mock mode and demo data generator for development
- **See**: [RING_API_DETAILS.md](RING_API_DETAILS.md) for detailed information about Ring API access

### Authentication Issues
- **Login Page Not Loading**: Ensure the server is running and accessible
- **Invalid Credentials**: Verify your Ring email and password are correct
- **2FA Required**: The OTP field will appear automatically when needed - enter the 6-digit code sent via SMS
- **Session Expired**: Simply reload the page and login again
- **Connection Failed**: Check network connectivity and server logs

### No Matches Appearing
- Verify keywords/emojis are configured correctly in `config.json`
- Check the poll interval isn't too long
- Ensure Ring neighborhood posts are available in your area
- Check logs for any API errors

### Map Not Loading
- Ensure internet connection for loading Leaflet.js CDN resources
- Check browser console for JavaScript errors
- Verify WebSocket connection is established (green indicator)

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This application is for educational and security awareness purposes. Always respect privacy and local laws when monitoring public information. Ring and related trademarks are property of their respective owners.
