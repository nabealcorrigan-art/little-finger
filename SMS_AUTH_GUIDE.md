# SMS/2FA Authentication - Quick Start Guide

## Problem Solved
You received an SMS authentication code from Ring but had no way to provide it to the application. This update adds full support for SMS/2FA authentication codes.

## Solution Overview
The app now supports two methods to provide your SMS verification code:
1. **Config File Method** - Add the code to `config.json`
2. **Interactive Method** - Enter the code when prompted

## How to Use

### Method 1: Add Code to Config File (Recommended for Headless/Automated Use)

1. Get your SMS code from Ring (e.g., "Your Ring verification code is: 123456")

2. Edit `config.json` and add the code:
```json
{
  "ring": {
    "username": "your-email@example.com",
    "password": "your-password",
    "refresh_token": "",
    "otp_code": "123456"
  },
  ...
}
```

3. Start the application:
```bash
python server.py
```

4. The app will authenticate using the OTP code and save a refresh token

5. **Important**: Remove the OTP code from config.json after successful authentication for security

### Method 2: Interactive Prompt (Recommended for Manual Use)

1. Make sure `otp_code` is empty in `config.json`:
```json
{
  "ring": {
    "username": "your-email@example.com",
    "password": "your-password",
    "refresh_token": "",
    "otp_code": ""
  },
  ...
}
```

2. Start the application:
```bash
python server.py
```

3. If 2FA is required, you'll see:
```
2025-11-18 00:00:00,000 - INFO - 2FA/SMS authentication required
2025-11-18 00:00:00,000 - INFO - Please enter the verification code you received via SMS:
Enter OTP code: 
```

4. Enter your SMS code when prompted

5. The app will authenticate and save a refresh token for future use

## After First Successful Authentication

Once you've successfully authenticated:
- A `refresh_token` is automatically saved to your config.json
- You won't need the OTP code for subsequent runs
- The app will use the refresh token automatically
- You can remove the OTP code from config.json

## Testing Your Setup

Run the included tests to verify everything works:

```bash
# Test the OTP configuration
python test_auth_with_otp.py

# Test the core monitoring functionality
python test_monitor.py

# View usage examples
python demo_otp_usage.py
```

All tests should pass.

## Common Scenarios

### First Time Setup with 2FA
1. Request SMS code from Ring
2. Add to config.json OR prepare to enter interactively
3. Run `python server.py`
4. After success, refresh_token is saved
5. Remove OTP code from config

### Running on a Headless Server
1. Use Method 1 (config file)
2. SSH to your server
3. Edit config.json with the OTP code
4. Run the app
5. After authentication, the app continues running

### Docker Deployment with 2FA
1. Add OTP code to your config file before building
2. Build and run the container
3. Container authenticates on startup
4. After first run, you can remove OTP from config

### Restarting After Successful Auth
1. No OTP code needed
2. The app uses the saved refresh_token
3. Just run `python server.py` as normal

## Troubleshooting

### "2FA code required but running in non-interactive mode"
- You're running the app in a way that doesn't allow keyboard input
- Solution: Add the OTP code to config.json

### Authentication still failing with OTP code
- Make sure the code hasn't expired (they're usually valid for a few minutes)
- Check for typos in the code
- Ensure no extra spaces before/after the code (though the app strips them)
- Request a new code from Ring

### OTP code field not in config.json
- Update your config.json to include the `otp_code` field
- See config.example.json for the correct format

## Security Best Practices

1. **Never commit OTP codes to git**
   - Use `config.local.json` for personal credentials
   - This file is already in .gitignore

2. **Remove OTP codes after use**
   - Once you have a refresh token, delete the OTP code from config

3. **Protect your config files**
   - Set appropriate file permissions: `chmod 600 config.json`
   - Don't share config files containing credentials

4. **Use environment variables in production**
   - Consider reading credentials from environment instead of files
   - This is more secure for production deployments

## Files Changed

- `ring_monitor.py` - Added OTP authentication logic
- `config.json` - Added `otp_code` field
- `config.example.json` - Added `otp_code` field with documentation
- `README.md` - Added 2FA documentation
- `test_auth_with_otp.py` - Tests for OTP functionality
- `demo_otp_usage.py` - Usage demonstration script

## Summary

✅ **Two flexible methods** to provide SMS/OTP codes
✅ **Automatic fallback** to interactive prompt if needed
✅ **Smart detection** of 2FA requirements
✅ **Refresh token persistence** - authenticate once, use forever
✅ **Works in both interactive and headless modes**
✅ **Backward compatible** - existing configs still work
✅ **Fully tested** - all tests passing
✅ **Security focused** - clear guidance on protecting credentials

You can now easily authenticate with Ring even when 2FA is enabled!
