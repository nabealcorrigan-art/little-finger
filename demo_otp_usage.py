#!/usr/bin/env python3
"""
Demo script showing how to use the OTP/2FA authentication feature
"""
import json

print("╔══════════════════════════════════════════════════════════════╗")
print("║  Little Finger - SMS/2FA Authentication Demo                ║")
print("╚══════════════════════════════════════════════════════════════╝")
print()

print("When Ring requires 2FA/SMS authentication, you have two options:\n")

print("─" * 62)
print("OPTION 1: Add OTP code to config.json")
print("─" * 62)
print("""
Edit your config.json file and add the OTP code:

{
  "ring": {
    "username": "your-email@example.com",
    "password": "your-password",
    "refresh_token": "",
    "otp_code": "123456"   <-- Add your SMS code here
  },
  ...
}

Then start the application normally:
  $ python server.py
""")

print("─" * 62)
print("OPTION 2: Interactive prompt (when running manually)")
print("─" * 62)
print("""
Leave otp_code empty in config.json:

{
  "ring": {
    "username": "your-email@example.com",
    "password": "your-password",
    "refresh_token": "",
    "otp_code": ""   <-- Leave empty
  },
  ...
}

When you start the app, if 2FA is required, you'll be prompted:
  $ python server.py
  2025-11-18 00:00:00,000 - INFO - 2FA/SMS authentication required
  2025-11-18 00:00:00,000 - INFO - Please enter the verification code you received via SMS:
  Enter OTP code: 123456   <-- Enter your code here
""")

print("─" * 62)
print("IMPORTANT NOTES")
print("─" * 62)
print("""
✓ After successful authentication, a refresh_token is automatically saved
✓ You won't need the OTP code for subsequent runs
✓ For security, remove the OTP code from config.json after first login
✓ For headless/automated deployments, use Option 1 (config file)
✓ For interactive use, Option 2 is more convenient

Example workflow:
1. Get SMS code from Ring: "Your Ring verification code is: 123456"
2. Add it to config.json OR prepare to enter it interactively
3. Start the app: python server.py
4. App authenticates and saves refresh_token
5. Remove OTP code from config.json (optional but recommended)
6. For next runs, app uses refresh_token automatically
""")

print("\n📖 For more details, see README.md\n")
