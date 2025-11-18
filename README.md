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
- 🔐 **Web-Based Login**: User-friendly login interface with session management and 2FA support

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

3. Start the application:
```bash
python server.py
```

4. Open your web browser and navigate to `http://localhost:5777`

5. **Login through the web interface**:
   - You'll be automatically redirected to the login page if not authenticated
   - Enter your Ring email address and password
   - If 2FA is enabled, enter the verification code when prompted
   - Your credentials will be saved securely and monitoring will start automatically

**Alternative: Manual Configuration** (optional for advanced users or automated deployments):

You can pre-configure credentials by editing `config.json`:
```json
{
  "ring": {
    "username": "your-ring-email@example.com",
    "password": "your-ring-password",
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

**Important**: Create a copy as `config.local.json` for your personal credentials (this file is ignored by git).

### Two-Factor Authentication (2FA/SMS)

The application fully supports 2FA through the web interface:

**Web Interface (Recommended)**:
- Enter your email and password on the login page
- If 2FA is required, an OTP input field will appear automatically
- Enter the 6-digit code you received via SMS
- The application will authenticate and save your session

**Manual Configuration** (for automated/headless deployments):
```json
{
  "ring": {
    "username": "your-ring-email@example.com",
    "password": "your-ring-password",
    "otp_code": "123456"
  }
}
```

**Note**: After successful authentication, a refresh token is saved automatically, so you won't need the OTP code for subsequent runs.

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

1. Copy your config file:
```bash
cp config.example.json config.local.json
# Edit config.local.json with your credentials
```

2. Start with Docker Compose:
```bash
docker-compose up -d
```

3. Or build and run manually:
```bash
docker build -t little-finger .
docker run -p 5777:5777 -v $(pwd)/config.local.json:/app/config.json little-finger
```

The server will start on `http://0.0.0.0:5777` by default.

### Accessing the Dashboard

Open your browser and navigate to:
- `http://localhost:5777` (if running locally)
- `http://YOUR_SERVER_IP:5777` (if running on a remote server)

**First Time Setup**:
1. You'll be redirected to the login page automatically
2. Enter your Ring credentials
3. Complete 2FA verification if required
4. You'll be redirected to the dashboard upon successful authentication

**Subsequent Visits**:
- If you have a valid session, you'll see the dashboard directly
- If your session expired or you logged out, you'll be prompted to login again
- Use the logout button in the dashboard header to end your session

### Configuration Options

- **poll_interval_seconds**: How often to check for new posts (default: 60 seconds)
- **keywords**: List of case-insensitive keywords to monitor
- **emojis**: List of emojis to detect in posts
- **host**: Server bind address (use "0.0.0.0" to allow external access)
- **port**: Server port number

## API Endpoints

- `GET /`: Dashboard interface (requires authentication)
- `GET /login`: Login page
- `POST /api/login`: Authenticate with Ring credentials
- `POST /api/logout`: End current session
- `GET /api/matches`: Get all detected matches
- `GET /api/matches/filter?term=<term>`: Filter matches by keyword or emoji
- `GET /api/stats`: Get monitoring statistics
- `GET /api/config`: Get current monitoring configuration
- WebSocket `/`: Real-time match updates

## Dashboard Features

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

- **Session Management**: The application uses Flask sessions with HTTP-only cookies for security
- **Credential Storage**: Credentials are stored in `config.json` - ensure this file has appropriate permissions (chmod 600)
- Never commit your `config.local.json` or `config.json` with real credentials to version control
- Use HTTPS when exposing the server over the internet (consider using a reverse proxy like nginx)
- **Production Deployment**: Use a production WSGI server (like Gunicorn) instead of Flask's development server
- Refresh tokens are automatically saved when received from Ring API
- The application implements CSRF protection through Flask's secret key
- Keep your Ring credentials secure and rotate passwords regularly
- Consider using environment variables for sensitive configuration in production

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

## Troubleshooting

### Ring API Connection
- **Neighborhood Access**: The `ring-doorbell` library may not support neighborhood posts for all accounts
- **API Limitations**: Ring's unofficial API can change without notice
- **Testing**: Use mock mode and demo data generator for development
- **See**: [RING_API_DETAILS.md](RING_API_DETAILS.md) for detailed information about Ring API access

### Authentication Issues
- **Web Login (Recommended)**: Use the web interface at `http://localhost:5777/login` to enter credentials
- Verify your Ring credentials are correct
- **2FA/SMS Code**: If you have 2FA enabled:
  - The web interface will automatically prompt for the OTP code
  - Enter the 6-digit code you received via SMS
  - After successful login, the refresh token is saved automatically
- **Manual Config**: Alternatively, add credentials to `config.json` and restart the server
- If authentication fails, check the server logs for detailed error messages
- For automated/headless deployments, pre-configure credentials in config.json with OTP if needed
- Look for refresh_token in the logs after first successful authentication
- For non-interactive/headless mode, always provide `otp_code` in config.json if 2FA is required

### No Matches Appearing
- Verify keywords/emojis are configured correctly
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
