"""
Ring Browser-Based Authentication
Redirects to Ring's login page and captures authentication tokens
"""
import json
import logging
import asyncio
from typing import Optional, Dict
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RingBrowserAuth:
    """Handles browser-based authentication with Ring"""
    
    # Ring URLs
    RING_LOGIN_URL = "https://account.ring.com/account/login"
    RING_OAUTH_URL = "https://oauth.ring.com/oauth/token"
    RING_DASHBOARD_URL = "https://account.ring.com/dashboard"
    
    def __init__(self, headless: bool = True):
        """
        Initialize browser authentication
        
        Args:
            headless: Run browser in headless mode (no visible window)
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    async def start_browser(self):
        """Start the browser instance"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        logger.info("Browser started successfully")
        
    async def navigate_to_login(self):
        """Navigate to Ring's login page"""
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        logger.info(f"Navigating to Ring login page: {self.RING_LOGIN_URL}")
        await self.page.goto(self.RING_LOGIN_URL, wait_until="networkidle")
        logger.info("Login page loaded")
        return self.page.url
        
    async def wait_for_authentication(self, timeout_seconds: int = 300):
        """
        Wait for user to complete authentication on Ring's page
        
        Args:
            timeout_seconds: Maximum time to wait for login (default: 5 minutes)
            
        Returns:
            Dict containing authentication tokens and cookies
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        logger.info("Waiting for user to complete authentication...")
        start_time = time.time()
        
        # Wait for redirect to dashboard or successful login indicator
        while time.time() - start_time < timeout_seconds:
            current_url = self.page.url
            
            # Check if we've been redirected to dashboard (successful login)
            if "dashboard" in current_url or "account.ring.com" in current_url and "login" not in current_url:
                logger.info(f"Authentication successful! Redirected to: {current_url}")
                break
                
            await asyncio.sleep(1)
        else:
            raise TimeoutError(f"Authentication not completed within {timeout_seconds} seconds")
        
        # Extract cookies and tokens
        cookies = await self.context.cookies()
        storage_state = await self.context.storage_state()
        
        logger.info(f"Captured {len(cookies)} cookies from Ring session")
        
        # Try to extract OAuth tokens from local storage or cookies
        tokens = await self._extract_oauth_tokens()
        
        return {
            'cookies': cookies,
            'storage_state': storage_state,
            'tokens': tokens,
            'timestamp': time.time()
        }
    
    async def _extract_oauth_tokens(self) -> Optional[Dict]:
        """
        Extract OAuth tokens from browser storage
        
        Returns:
            Dictionary with access_token, refresh_token, etc. if available
        """
        if not self.page:
            return None
            
        try:
            # Try to extract tokens from localStorage
            local_storage = await self.page.evaluate("""() => {
                const storage = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    storage[key] = localStorage.getItem(key);
                }
                return storage;
            }""")
            
            logger.info(f"LocalStorage keys: {list(local_storage.keys())}")
            
            # Look for OAuth-related keys
            token_data = {}
            for key, value in local_storage.items():
                if any(keyword in key.lower() for keyword in ['token', 'auth', 'oauth', 'session']):
                    try:
                        # Try to parse as JSON
                        parsed = json.loads(value)
                        token_data[key] = parsed
                    except:
                        token_data[key] = value
            
            if token_data:
                logger.info(f"Found token-related data: {list(token_data.keys())}")
                return token_data
                
        except Exception as e:
            logger.warning(f"Could not extract OAuth tokens from localStorage: {e}")
        
        # Try sessionStorage as well
        try:
            session_storage = await self.page.evaluate("""() => {
                const storage = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    storage[key] = sessionStorage.getItem(key);
                }
                return storage;
            }""")
            
            logger.info(f"SessionStorage keys: {list(session_storage.keys())}")
            
        except Exception as e:
            logger.warning(f"Could not extract from sessionStorage: {e}")
        
        return None
    
    async def intercept_api_calls(self, callback):
        """
        Intercept API calls to capture OAuth tokens
        
        Args:
            callback: Function to call with intercepted request/response data
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        async def handle_response(response):
            """Handle network responses"""
            url = response.url
            
            # Look for OAuth token endpoint
            if "oauth" in url or "token" in url:
                try:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Intercepted OAuth response from: {url}")
                        await callback(data)
                except Exception as e:
                    logger.debug(f"Could not parse response from {url}: {e}")
        
        self.page.on("response", handle_response)
        logger.info("API interception enabled")
    
    async def get_cookies_as_dict(self) -> Dict[str, str]:
        """Get cookies as a simple key-value dictionary"""
        if not self.context:
            return {}
        
        cookies = await self.context.cookies()
        return {cookie['name']: cookie['value'] for cookie in cookies}
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")
    
    async def save_auth_state(self, filepath: str):
        """
        Save authentication state to file for reuse
        
        Args:
            filepath: Path to save the state JSON file
        """
        if not self.context:
            raise RuntimeError("No browser context available")
        
        state = await self.context.storage_state()
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Authentication state saved to: {filepath}")
    
    async def load_auth_state(self, filepath: str):
        """
        Load previously saved authentication state
        
        Args:
            filepath: Path to the saved state JSON file
        """
        if not self.browser:
            await self.start_browser()
        
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        # Create new context with saved state
        if self.context:
            await self.context.close()
        
        self.context = await self.browser.new_context(storage_state=state)
        self.page = await self.context.new_page()
        
        logger.info(f"Authentication state loaded from: {filepath}")


# Convenience function for quick authentication
async def authenticate_with_browser(headless: bool = False, timeout: int = 300) -> Dict:
    """
    Convenience function to authenticate using browser
    
    Args:
        headless: Run browser in headless mode
        timeout: Maximum time to wait for user to login
        
    Returns:
        Dictionary with cookies, tokens, and storage state
    """
    auth = RingBrowserAuth(headless=headless)
    
    try:
        await auth.start_browser()
        await auth.navigate_to_login()
        
        # Set up token interception
        captured_tokens = []
        
        async def token_callback(data):
            captured_tokens.append(data)
        
        await auth.intercept_api_calls(token_callback)
        
        # Wait for authentication
        auth_data = await auth.wait_for_authentication(timeout_seconds=timeout)
        
        # Add any intercepted tokens
        if captured_tokens:
            auth_data['intercepted_tokens'] = captured_tokens
            logger.info(f"Captured {len(captured_tokens)} OAuth token responses")
        
        return auth_data
        
    finally:
        await auth.close()


# Example usage
if __name__ == "__main__":
    async def main():
        print("Starting Ring Browser Authentication...")
        print("A browser window will open. Please login to Ring.")
        
        auth_data = await authenticate_with_browser(headless=False, timeout=300)
        
        print("\n=== Authentication Complete ===")
        print(f"Cookies captured: {len(auth_data['cookies'])}")
        
        if auth_data.get('tokens'):
            print("OAuth tokens found:")
            for key in auth_data['tokens'].keys():
                print(f"  - {key}")
        
        if auth_data.get('intercepted_tokens'):
            print(f"Intercepted {len(auth_data['intercepted_tokens'])} token responses")
        
        # Save state for future use
        with open('ring_auth_state.json', 'w') as f:
            json.dump({
                'cookies': auth_data['cookies'],
                'storage_state': auth_data['storage_state'],
                'timestamp': auth_data['timestamp']
            }, f, indent=2)
        
        print("\nAuthentication state saved to: ring_auth_state.json")
    
    asyncio.run(main())
