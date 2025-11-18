# Browser-Based Authentication Guide

## ⚠️ CRITICAL STATUS NOTICE ⚠️

**This browser-based authentication feature is EXPERIMENTAL and NOT CURRENTLY FUNCTIONAL for Ring API authentication.**

### What Works
- ✅ Opens a browser window to Ring's login page
- ✅ Allows you to login through Ring's official website  
- ✅ Captures browser cookies and session data
- ✅ Monitors for successful authentication redirect

### What Does NOT Work
- ❌ **Cannot extract OAuth refresh tokens needed for Ring API**
- ❌ **Cannot authenticate the ring-doorbell library**
- ❌ **Cannot enable neighborhood post monitoring**
- ❌ **The monitor will fail to initialize after browser login**

### Why It Doesn't Work

Ring's authentication system does not expose OAuth tokens in ways this implementation can capture:

1. **Browser Storage**: OAuth tokens are NOT stored in localStorage or sessionStorage
2. **API Interception**: Token endpoints may use different domains or be CORS-protected
3. **Token Format**: Ring may use proprietary token formats not compatible with ring-doorbell library
4. **Session Isolation**: Browser sessions don't translate directly to API authentication

### What You Should Use Instead

**✅ FORM-BASED LOGIN (Recommended - Works Reliably)**

Use the traditional form-based login on the login page:
- Enter your Ring email address
- Enter your Ring password
- Include 2FA code if required
- This method works reliably with the ring-doorbell library

---

## Overview

This document describes an **experimental** browser-based authentication feature that was intended to allow users to login through Ring's official website. However, it **does not currently work** for Ring API authentication.

## Authentication Methods

### ✅ Form-Based Login (WORKS - Use This!)

**Status: FULLY FUNCTIONAL**

The traditional form-based login works reliably with Ring's API.

**How It Works:**
1. Enter your Ring email and password
2. Include 2FA SMS code if required
3. Application uses ring-doorbell library to authenticate
4. Receives OAuth refresh token from Ring's API
5. Monitoring begins successfully

**Benefits:**
- ✅ Works reliably every time
- ✅ Full 2FA support via SMS codes
- ✅ Direct API authentication
- ✅ No additional dependencies
- ✅ Session persistence with refresh tokens

### ❌ Browser-Based Login (EXPERIMENTAL - Does Not Work)

**Status: NOT FUNCTIONAL**

This was an attempt to authenticate by capturing tokens from Ring's website.

**What Happens:**
1. Click "Login via Ring Website" (currently disabled in UI)
2. Browser window opens to Ring's login page
3. You login successfully on Ring's website
4. Application attempts to extract OAuth tokens
5. ❌ **FAILS** - Cannot find refresh_token
6. ❌ Monitor initialization fails
7. ❌ You're left without authentication

**Why It Fails:**
- Ring's OAuth tokens are not in accessible browser storage
- API call interception doesn't capture the right endpoints
- Browser cookies alone are not sufficient for ring-doorbell library
- Different authentication flow than what the library expects

**Do Not Use This Method** - It will waste your time and not result in successful authentication.

## Getting Started

### Prerequisites

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Browser Automation:**
   ```bash
   playwright install chromium
   ```

### Using Browser Authentication

1. **Start the Server:**
   ```bash
   python server.py
   ```

2. **Open the Login Page:**
   Navigate to `http://localhost:5777` in your web browser

3. **Choose Browser Login:**
   - Click the "🔐 Login via Ring Website" button
   - A new browser window will open showing Ring's official login page

4. **Complete Ring Login:**
   - Enter your Ring email and password on Ring's website
   - Complete any 2FA verification if enabled
   - Accept any security prompts from Ring

5. **Automatic Redirect:**
   - Once logged in, Little Finger detects the successful authentication
   - You'll be automatically redirected to the monitoring dashboard
   - The browser auth window will close

## Technical Details

### Authentication Flow

```
User clicks "Login via Ring"
    ↓
Server starts Playwright browser (/auth/browser/start)
    ↓
Browser opens Ring's login page (https://account.ring.com/account/login)
    ↓
User completes authentication on Ring's site
    ↓
Browser is redirected to Ring dashboard
    ↓
Little Finger captures session cookies & OAuth tokens
    ↓
Tokens are used to initialize Ring monitor
    ↓
Authentication state is saved to ring_auth_state.json
    ↓
User is redirected to Little Finger dashboard
```

### Security Features

1. **No Credential Storage:** Credentials are entered directly on Ring's website
2. **Session Isolation:** Each authentication session is isolated in a browser context
3. **Token Extraction:** OAuth refresh tokens are captured from authenticated session
4. **State Persistence:** Authentication state is saved locally for session continuity
5. **Secure Storage:** Auth state files are gitignored and should be kept secure

### API Endpoints

#### Start Browser Authentication
```
POST /auth/browser/start
```

Starts a browser automation session that opens Ring's login page.

**Response:**
```json
{
  "success": true,
  "message": "Browser authentication started. Please complete login in the browser window."
}
```

#### Check Authentication Status
```
GET /auth/browser/status
```

Polls the authentication status to detect when login is complete.

**Response (Not Authenticated):**
```json
{
  "authenticated": false,
  "browser_active": true
}
```

**Response (Authenticated):**
```json
{
  "authenticated": true,
  "method": "browser"
}
```

### Files Created

- **ring_auth_state.json**: Contains authentication cookies and tokens
  - ⚠️ This file should not be committed to version control
  - ⚠️ Keep this file secure as it contains authentication data

## Troubleshooting

### Browser Window Doesn't Open

**Problem:** Clicking "Login via Ring Website" shows an error

**Solutions:**
1. Ensure Playwright browsers are installed:
   ```bash
   playwright install chromium
   ```

2. Check that you have display access (if on Linux server):
   ```bash
   export DISPLAY=:0
   ```

3. For headless servers, ensure X11 forwarding is configured

### Authentication Times Out

**Problem:** Browser window opens but never completes authentication

**Solutions:**
1. Ensure you complete the login within 5 minutes
2. Check for CAPTCHA or security prompts on Ring's page
3. Verify your Ring account credentials are correct
4. Try the form-based login method as fallback

### Session Expires Quickly

**Problem:** Need to re-authenticate frequently

**Solutions:**
1. Check that `ring_auth_state.json` is being created and saved
2. Ensure the file has proper permissions
3. Verify the refresh token is being captured (check server logs)

### Can't Find OAuth Tokens

**Problem:** Authentication completes but can't initialize monitor

**Solutions:**
1. The browser auth will try to intercept OAuth API calls
2. If token extraction fails, the app will show an error
3. Try using form-based login which doesn't require token extraction
4. Check server logs for specific error messages

## Development & Testing

### Running in Development Mode

```python
# Test browser auth module directly
python ring_browser_auth.py
```

This will:
1. Open a browser window (non-headless for visibility)
2. Navigate to Ring's login page
3. Wait for you to complete login
4. Display captured authentication data
5. Save auth state to `ring_auth_state.json`

### Headless Mode

For production deployment on servers without displays, the browser runs in headless mode by default. The authentication flow works the same, but you won't see the browser window.

### Custom Configuration

You can adjust timeout settings in `server.py`:

```python
# Change authentication timeout (default: 300 seconds)
await browser_auth.wait_for_authentication(timeout_seconds=600)
```

## Production Deployment

### Docker

When deploying with Docker, ensure Playwright browsers are installed in the container:

```dockerfile
# In your Dockerfile
RUN pip install playwright
RUN playwright install --with-deps chromium
```

### Headless Server

For headless servers (no display), install Xvfb for virtual display:

```bash
sudo apt-get install xvfb
Xvfb :99 -ac &
export DISPLAY=:99
```

Or use the headless mode which is enabled by default in production.

## Security Recommendations

1. **Protect Auth State Files:**
   - `ring_auth_state.json` contains sensitive authentication data
   - Set appropriate file permissions: `chmod 600 ring_auth_state.json`
   - Never commit this file to version control

2. **Use HTTPS in Production:**
   - Deploy behind a reverse proxy (nginx, caddy)
   - Enable SSL/TLS for all connections
   - Use secure session cookies

3. **Monitor Authentication:**
   - Check server logs for authentication attempts
   - Set up alerts for failed authentication
   - Regularly rotate credentials

4. **Network Security:**
   - Use firewall rules to restrict access
   - Consider VPN for remote access
   - Keep dependencies updated

## Comparison: Browser vs Form Login

| Feature | Browser Login | Form Login |
|---------|--------------|------------|
| Security | ✅ High - credentials never touch app | ⚠️ Moderate - credentials sent to app |
| 2FA Support | ✅ Full Ring 2FA support | ⚠️ Manual OTP entry required |
| CAPTCHA | ✅ Handled by Ring | ❌ May fail on CAPTCHA |
| Setup Complexity | ⚠️ Requires Playwright | ✅ No extra dependencies |
| Headless Server | ⚠️ Needs Xvfb or headless mode | ✅ Works anywhere |
| User Experience | ✅ Familiar Ring interface | ⚠️ Custom form |
| Session Persistence | ✅ Saved to file | ✅ Saved to session |

## FAQ

**Q: Is browser authentication more secure?**
A: Yes! Your credentials go directly to Ring, never passing through Little Finger.

**Q: Do I need to install a browser?**
A: Playwright installs its own Chromium browser automatically. No separate browser installation needed.

**Q: Can I use browser auth on a headless server?**
A: Yes! The browser runs in headless mode by default on servers without displays.

**Q: What happens to my session when I restart the server?**
A: Your authentication state is saved to `ring_auth_state.json` and can be reused across restarts (if tokens are still valid).

**Q: Can I switch between authentication methods?**
A: Yes! Both methods are available and you can use whichever works best for your situation.

**Q: How long does the authentication session last?**
A: Ring's OAuth tokens typically last 30 days. The app will attempt to refresh them automatically.

## Support

For issues or questions:
1. Check server logs for detailed error messages
2. Review this documentation for troubleshooting steps
3. Try the alternative authentication method
4. Open an issue on GitHub with logs and error details
