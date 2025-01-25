import logging
import asyncio
import os
import time
import random
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from dotenv import load_dotenv
from urllib.parse import urlparse
from .space_controller import SpaceController
from .tweet_controller import TweetController
from .message_controller import MessageController
from .mention_controller import MentionController
from ..utils.browser_controller import BrowserController
from .audio_processor import AudioProcessor
from .conversation_manager import ConversationManager
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger(__name__)

class ActionHandler:
    """Main handler for Twitter/X platform interactions.
    
    This class serves as the central coordinator for all platform interactions,
    delegating specific tasks to specialized controllers.
    """
    
    def __init__(self, headless: bool = False, retry_attempts: int = 3, timeout: int = 10):
        """Initialize the action handler with configurable parameters.
        
        Args:
            headless: Whether to run browser in headless mode
            retry_attempts: Number of retry attempts for operations
            timeout: Default timeout for web operations in seconds
        """
        # Core configuration
        self.retry_attempts = retry_attempts
        self.timeout = timeout
        self.is_logged_in = False
        
        # Initialize browser
        self.browser = BrowserController(
            window_width=1200, 
            window_height=800, 
            headless=headless
        )
        
        # Load environment variables
        load_dotenv()
        
        # Initialize optional components with error handling
        self._init_optional_components()
        
        # Create data directory if it doesn't exist
        Path("data").mkdir(exist_ok=True)
        
    def _init_optional_components(self):
        """Initialize optional components with proper error handling."""
        try:
            self.audio_processor = AudioProcessor()
        except Exception as e:
            logger.warning(f"Failed to initialize audio processor: {e}")
            self.audio_processor = None
            
        try:
            self.conversation_manager = ConversationManager()
        except Exception as e:
            logger.warning(f"Failed to initialize conversation manager: {e}")
            self.conversation_manager = None
            
    async def retry_operation(self, operation, *args, custom_retry_count=None, **kwargs):
        """Retry an operation with exponential backoff.
        
        Args:
            operation: Async function to retry
            custom_retry_count: Optional custom retry count
            *args, **kwargs: Arguments to pass to operation
        
        Returns:
            Result of the operation or None if all retries failed
        """
        retries = custom_retry_count or self.retry_attempts
        for attempt in range(retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"Operation failed after {retries} attempts: {e}")
                    return None
                wait_time = min(2 ** attempt, 30)  # Exponential backoff capped at 30s
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
                
    async def ensure_logged_in(self) -> bool:
        """Ensure user is logged in with retry mechanism."""
        return await self.retry_operation(self._ensure_logged_in_impl)
        
    async def _ensure_logged_in_impl(self) -> bool:
        """Implementation of login check and process."""
        if self.is_logged_in:
            return True
            
        try:
            # Try loading saved session
            if self.browser.load_cookies():
                self.browser.navigate("https://twitter.com/home")
                await asyncio.sleep(3)
                
                # Verify login state
                try:
                    WebDriverWait(self.browser.driver, self.timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 
                            "[data-testid='SideNav_AccountSwitcher_Button']"
                        ))
                    )
                    self.is_logged_in = True
                    logger.info("Successfully logged in using saved session")
                    return True
                except:
                    logger.warning("Saved session invalid or expired")
            
            # Manual login required
            logger.info("Manual login required")
            self.browser.navigate("https://twitter.com/login")
            await asyncio.sleep(5)  # Wait for manual login
            
            # Wait for navigation to home page
            try:
                WebDriverWait(self.browser.driver, 300).until(  # 5 minute timeout for manual login
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        "[data-testid='SideNav_AccountSwitcher_Button']"
                    ))
                )
                self.is_logged_in = True
                self._save_session()
                logger.info("Manual login successful")
                return True
            except:
                logger.error("Manual login failed or timed out")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
            
    def _save_session(self) -> bool:
        """Save session data using browser controller."""
        try:
            # Ensure we're on a twitter page before saving cookies
            current_url = self.browser.driver.current_url
            if not any(domain in current_url for domain in ['twitter.com', 'x.com']):
                self.browser.navigate("https://twitter.com/home")
                time.sleep(3)
            
            success = self.browser.save_cookies()
            if success:
                logger.info("Successfully saved session cookies")
            else:
                logger.warning("Failed to save session cookies")
            return success
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return False
            
    async def handle_notifications(self):
        """Handle any notifications that appear, like 'Got it!' popups."""
        try:
            notification_selectors = [
                "//span[text()='Got it!']/ancestor::div[@role='button']",
                "//div[@role='button']//span[contains(text(), 'Got it')]",
                "//span[text()='Got it!']",
                "[data-testid='toast']"
            ]
            
            for selector in notification_selectors:
                try:
                    button = WebDriverWait(self.browser.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    button.click()
                    await asyncio.sleep(0.5)
                    return True
                except:
                    continue
                    
            return False
        except Exception as e:
            logger.debug(f"No notifications found: {e}")
            return False
            
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.browser:
                self._save_session()
                self.browser.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
    def __del__(self):
        """Cleanup when the object is destroyed."""
        self.cleanup() 