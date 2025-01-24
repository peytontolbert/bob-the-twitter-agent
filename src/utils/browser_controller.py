from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
from PIL import Image, ImageDraw, ImageFont
import os
import json
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BrowserController:
    def __init__(self, window_width=1200, window_height=800, headless=False, audio_output_device=None):
        """Initialize browser controller.
        
        Args:
            window_width: Browser window width
            window_height: Browser window height
            headless: Whether to run in headless mode
        """
        self.window_width = window_width
        self.window_height = window_height
        self.headless = headless
        self.driver = self._setup_driver()
        self.cookies_file = Path("data/cookies.json")
        
        # Configure viewport dimensions
        self.viewport_width = self.driver.execute_script("return window.innerWidth")
        self.viewport_height = self.driver.execute_script("return window.innerHeight")
        
        # Adjust window size
        width_diff = window_width - self.viewport_width
        height_diff = window_height - self.viewport_height
        self.driver.set_window_size(window_width + width_diff, window_height + height_diff)
        
        self.screenshot_width = 1008    
        self.screenshot_height = 1008
        
        self.actions = ActionChains(self.driver)
        self.last_mouse_position = None
        
        logger.info(f"Initialized browser with viewport dimensions: {self.viewport_width}x{self.viewport_height}")

    def _setup_driver(self):
        """Set up and configure the Edge webdriver."""
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument(f'--window-size={self.window_width},{self.window_height}')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Add user data directory to persist session
        user_data_dir = os.path.abspath("browser_data")
        options.add_argument(f"user-data-dir={user_data_dir}")
        
        # Configure audio preferences
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        options.add_argument("--use-fake-ui-for-media-stream")
        
        # Set up preferences for audio devices with echo cancellation
        prefs = {
            # Enable microphone with echo cancellation
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_settings.media_stream_mic": 1,
            
            # Enable audio output with echo cancellation
            "profile.default_content_setting_values.media_stream_sound": 1,
            "profile.default_content_settings.sound": 1,
            "profile.managed_default_content_settings.sound": 1,
            
            # Enable echo cancellation and noise suppression
            "media.navigator.audio.force_noecho": True,
            "media.navigator.audio.force_noise_suppression": True,
            
            # Disable device selection prompt
            "profile.default_content_setting_values.media_stream_camera": 1,
            
            # Additional audio settings
            "managed_default_content_settings.media_stream_mic": 1,
            "managed_default_content_settings.media_stream_sound": 1
        }
        
        options.add_experimental_option("prefs", prefs)
        
        # Add additional Edge-specific arguments for audio
        options.add_argument("--disable-features=PreloadMediaEngagementData,AutoplayIgnoreWebAudio,MediaEngagementBypassAutoplayPolicies")
        options.add_argument("--enable-features=WebRtcHideLocalIpsWithMdns,WebRtcAudioDsp")
        
        driver = webdriver.Edge(options=options)
        driver.set_window_size(self.window_width, self.window_height)
        return driver
        
    def navigate(self, url: str):
        """Navigate to a URL."""
        self.driver.get(url)
        logger.info(f"Navigated to {url}")
        time.sleep(2)  # Wait for the page to load

    def locate_element_by_text(self, text, element_type="link"):
        """
        Locate an element by text and return its center coordinates.
        """
        try:
            element = None
            if element_type == "link":
                element = self.driver.find_element(By.LINK_TEXT, text)
            elif element_type == "input":
                # Try different strategies for input fields
                selectors = [
                    f"//input[@placeholder='{text}']",
                    f"//input[@name='{text}']",
                    f"//input[@type='{text}']",
                    f"//label[contains(text(), '{text}')]//following::input[1]",
                    f"//div[contains(text(), '{text}')]//following::input[1]"
                ]
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        break
                    except:
                        continue
            elif element_type == "button":
                # Try different strategies for buttons
                selectors = [
                    f"//button[contains(text(), '{text}')]",
                    f"//button[@type='{text}']",
                    f"//div[contains(@class, 'button') and contains(text(), '{text}')]",
                    f"//*[contains(@class, 'button') and contains(text(), '{text}')]"
                ]
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        break
                    except:
                        continue

            if element:
                location = element.location
                size = element.size
                center_x = location['x'] + (size['width'] / 2)
                center_y = location['y'] + (size['height'] / 2)
                logger.info(f"Located {element_type} element '{text}' at ({center_x}, {center_y})")
                return element, (center_x, center_y)
            else:
                logger.warning(f"Could not locate {element_type} element with text '{text}'")
                return None, (None, None)
            
        except Exception as e:
            logger.error(f"Error locating {element_type} element '{text}': {e}")
            return None, (None, None)

    def click_element(self, element):
        """Click on a web element."""
        try:
            element.click()
            logger.info("Clicked element successfully")
            return True
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return False

    def type_text(self, element, text):
        """Type text into an element."""
        try:
            element.clear()
            element.send_keys(text)
            logger.info(f"Typed text into element")
            return True
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False

    def save_cookies(self) -> bool:
        """Save cookies to file.
        
        Returns:
            bool: Whether cookies were saved successfully
        """
        try:
            cookies = self.driver.get_cookies()
            self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            logger.info("Cookies saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")
            return False
            
    def load_cookies(self) -> bool:
        """Load cookies from file.
        
        Returns:
            bool: Whether cookies were loaded successfully
        """
        try:
            if not self.cookies_file.exists():
                logger.warning("No saved cookies found")
                return False
                
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
                
            # Navigate to domain before setting cookies
            self.navigate("https://twitter.com")
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Error adding cookie: {e}")
                    
            logger.info("Cookies loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False

    def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
            
    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup() 