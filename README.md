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

This application uses the **`ring-doorbell` Python library** to authenticate with Ring's API. This is the standard, reliable method used by the Ring developer community.

#### 📝 Login via ring-doorbell Library

The login form uses the proven **ring-doorbell Python library** to authenticate directly with Ring's OAuth API. This is the standard authentication method and works reliably.

**How it works:**

1. **Start the server** (see Usage section below)
2. **Navigate to login page**: Open `http://localhost:5777` in your browser
3. **Enter Ring credentials**:
   - Ring account email address (not username)
   - Ring account password
4. **Handle 2FA if enabled** (see 2FA section below)
5. **Authentication complete**: Redirected to monitoring dashboard

**What happens behind the scenes:**

- The `ring-doorbell` library exchanges your credentials with Ring's OAuth API
- Ring returns OAuth access and refresh tokens
- These tokens are used for all subsequent API calls
- Tokens are automatically refreshed when they expire
- Your credentials are NOT stored - only OAuth tokens are kept in session

**Security features:**

- ✅ Industry-standard OAuth 2.0 authentication via ring-doorbell library
- ✅ Credentials only transmitted once to Ring's API (not stored locally)
- ✅ Session-based authentication with secure random session keys
- ✅ Refresh tokens stored only in memory (session), not persisted to disk
- ✅ Automatic token refresh by ring-doorbell when tokens expire
- ✅ Logout functionality to clear session and tokens

#### 🔐 Two-Factor Authentication (2FA / SMS Verification)

If your Ring account has two-factor authentication enabled (SMS verification), the login process involves an additional step:

**2FA Login Flow:**

1. **Initial login attempt**: Enter email and password, leave OTP field blank
2. **Ring sends SMS**: If 2FA is enabled, Ring texts a 6-digit code to your phone
3. **Prompt for OTP**: The UI displays a message asking for the verification code
4. **Enter OTP code**: Input the 6-digit code from the SMS in the OTP field
5. **Submit again**: Click login with all three fields filled (email, password, OTP)
6. **Authentication complete**: The ring-doorbell library validates the OTP with Ring

**2FA Technical Details:**

- Ring's 2FA uses SMS-based one-time passwords (OTP)
- OTP codes are 6 digits and expire after a few minutes
- The ring-doorbell library handles 2FA through its `fetch_token()` method
- First auth attempt without OTP will fail if 2FA is enabled
- Second auth attempt with OTP completes the authentication
- After successful 2FA login, the refresh token can be used for future logins

**2FA Tips:**

- You can enter the OTP code upfront if you know 2FA is enabled
- If the code expires, simply request a new login to get a fresh SMS
- OTP codes are single-use - each login attempt needs a fresh code if it fails
- Keep your phone nearby during first login if 2FA is enabled

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
- `GET /login`: Login page with ring-doorbell authentication form
- `POST /login`: Authentication endpoint (accepts JSON with username, password, otp_code)
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
- **Login via ring-doorbell**: Enter Ring credentials to authenticate with Ring's API
- **2FA Support**: Full support for Ring's two-factor authentication via SMS OTP codes
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

### Authentication Issues

This section covers common authentication problems and their solutions when using the ring-doorbell library to connect to Ring's API.

#### Wrong Email or Password

**Symptoms:**
- Error message: "Authentication failed. Please check your credentials."
- Error type: `invalid_credentials`
- Cannot login even without 2FA

**Solutions:**
1. **Verify email format**: Ring requires your account email address, not a username
   - ✅ Correct: `user@example.com`
   - ❌ Wrong: `myusername` or `MyRingAccount`

2. **Check password carefully**: Passwords are case-sensitive
   - Try copying and pasting to avoid typos
   - Ensure no extra spaces before or after

3. **Test on Ring's website**: Visit https://account.ring.com and verify you can login there
   - If you can't login on Ring's website, reset your password there first
   - Once Ring website login works, the app will work too

4. **Check account status**: Ensure your Ring account is active and not suspended

#### 2FA / OTP Issues

**Symptoms:**
- Message: "Two-factor authentication code required"
- Login fails even after entering OTP code
- Error: "Invalid verification code"

**Common Problems and Solutions:**

**Problem 1: OTP Code Expired**
- SMS codes typically expire after 5-10 minutes
- **Solution**: Request a new code by attempting login again (leave OTP field blank initially)
- Ring will send a fresh SMS code

**Problem 2: Wrong OTP Code**
- Typo in the 6-digit code
- Using an old code from a previous attempt
- **Solution**: 
  - Double-check the most recent SMS from Ring
  - Enter exactly 6 digits with no spaces or dashes
  - Don't use codes from previous login attempts

**Problem 3: SMS Not Arriving**
- SMS delivery can be delayed or fail
- **Solutions**:
  - Wait 1-2 minutes for SMS to arrive
  - Check if phone has signal
  - Verify phone number is correct in Ring account settings
  - Try requesting another code (attempt login again)

**Problem 4: 2FA Disabled on Ring Account**
- You're entering an OTP code but 2FA isn't actually enabled
- **Solution**: 
  - Leave OTP field blank on first attempt
  - Only fill it in if the UI prompts you for it
  - Check Ring account settings to see if 2FA is enabled

**Problem 5: Wrong Phone Number in Ring Account**
- SMS codes going to old/wrong phone number
- **Solution**:
  - Login to Ring's website at https://account.ring.com
  - Update phone number in account settings
  - Disable and re-enable 2FA with correct number

**2FA Best Practices:**
- ✅ Keep your phone nearby during first login
- ✅ Leave OTP blank initially, fill it only when prompted
- ✅ Use fresh codes - each login needs a new SMS
- ✅ Wait for SMS before retrying
- ❌ Don't reuse old OTP codes
- ❌ Don't spam login attempts (may temporarily lock account)

#### Network and Connection Issues

**Symptoms:**
- "Network error connecting to Ring"
- "Connection to Ring timed out"
- "Connection error. Please try again."

**Solutions:**

1. **Check Internet Connection**:
   ```bash
   # Test connectivity to Ring's servers
   ping api.ring.com
   ```

2. **Firewall/Proxy Issues**:
   - Ensure outbound HTTPS (port 443) is allowed
   - Ring API uses `https://api.ring.com` and `https://oauth.ring.com`
   - If behind corporate firewall, may need to whitelist these domains

3. **Server/App Issues**:
   - Check if Flask server is running: `ps aux | grep python`
   - Check server logs: Look for error messages in terminal
   - Restart the application: `Ctrl+C` then `python server.py`

4. **Ring API Status**:
   - Ring's API may be temporarily down (rare)
   - Check Ring's status page or community forums
   - Wait and try again later

#### Session and Cookie Issues

**Symptoms:**
- "Session Expired" message
- Redirected to login page unexpectedly
- "Not authenticated" errors

**Solutions:**

1. **Session Timeout**:
   - Sessions expire after period of inactivity
   - **Solution**: Simply login again - it's quick with 2FA already done once

2. **Browser Cookies Disabled**:
   - App requires cookies for session management
   - **Solution**: Enable cookies in browser settings

3. **Multiple Tabs/Windows**:
   - Logging out in one tab affects all tabs
   - **Solution**: Refresh other tabs to re-authenticate

4. **Server Restart**:
   - Session data is lost when server restarts
   - **Solution**: Login again after server restarts

#### Ring API / ring-doorbell Library Issues

**Symptoms:**
- Authentication works but features don't load
- "Ring API not available" messages
- Neighborhood data not appearing

**Solutions:**

1. **ring-doorbell Library Not Installed**:
   ```bash
   pip install ring-doorbell==0.8.8
   ```

2. **Incompatible Library Version**:
   - Ring may update their API, breaking older library versions
   - **Solution**: Update ring-doorbell library
   ```bash
   pip install --upgrade ring-doorbell
   ```
   - Check project requirements.txt for compatible version

3. **Neighborhood Posts Not Supported**:
   - ring-doorbell library may not support neighborhood features for all accounts
   - Ring's unofficial API has limitations
   - **Solution**: See [RING_API_DETAILS.md](RING_API_DETAILS.md) for alternatives
   - Use mock mode for development/testing

4. **Ring API Changes**:
   - Ring may change their API without notice (unofficial API)
   - **Solution**: 
     - Check for ring-doorbell library updates
     - Report issues on GitHub
     - See if others have similar problems in ring-doorbell issues

#### Getting Help

If you've tried all troubleshooting steps and still can't login:

1. **Check server logs**: Look for detailed error messages in terminal output
2. **Check Ring account**: Verify you can login at https://account.ring.com
3. **Test ring-doorbell directly**: Try the library independently to isolate the issue
4. **Check GitHub issues**: Search for similar problems in this repo and ring-doorbell repo
5. **Report the issue**: Open a GitHub issue with:
   - Exact error message
   - Steps to reproduce
   - Server logs (remove sensitive info)
   - ring-doorbell library version: `pip show ring-doorbell`

### Ring API Connection

- **Neighborhood Access**: The `ring-doorbell` library may not support neighborhood posts for all accounts
- **API Limitations**: Ring's unofficial API can change without notice
- **Testing**: Use mock mode and demo data generator for development
- **See**: [RING_API_DETAILS.md](RING_API_DETAILS.md) for detailed information about Ring API access

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
