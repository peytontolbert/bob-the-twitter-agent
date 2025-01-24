import asyncio
import os
import sys
import logging
from pathlib import Path
import random
from datetime import datetime
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import json

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.agent.action_handler import ActionHandler
from src.agent.message_controller import MessageController
from src.agent.mention_controller import MentionController

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Load or initialize state
def load_state():
    try:
        with open('state.json', 'r') as f:
            return json.load(f)
    except:
        return {
            'replied_dms': set(),
            'replied_mentions': set(),
            'last_check': None
        }

def save_state(state):
    with open('state.json', 'w') as f:
        # Convert sets to lists for JSON serialization
        state_copy = state.copy()
        state_copy['replied_dms'] = list(state['replied_dms'])
        state_copy['replied_mentions'] = list(state['replied_mentions'])
        json.dump(state_copy, f)

async def wait_for_page_load(handler, timeout=20):
    """Wait for page to load with timeout"""
    try:
        # Wait for any of these common elements that indicate page load
        selectors = [
            "[data-testid='primaryColumn']",
            "[data-testid='DM_Timeline_Header']",
            "[data-testid='DM_conversation']",
            "[data-testid='DMDrawer']",
            "[data-testid='cellInnerDiv']",
            "[data-testid='tweet']",
            "div[data-testid='primaryColumn']"
        ]
        
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout:
            for selector in selectors:
                try:
                    elements = handler.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        await asyncio.sleep(2)  # Wait a bit more for content to load
                        return True
                except:
                    continue
            await asyncio.sleep(1)
        return False
    except Exception as e:
        logger.error(f"Error waiting for page load: {e}")
        return False

async def process_dms(handler, message_controller):
    """Process direct messages"""
    try:
        await message_controller.process_dms()
    except Exception as e:
        logger.error(f"Error processing DMs: {e}")
        
async def process_message_requests(handler, message_controller):
    """Process message requests"""
    try:
        await message_controller.process_message_requests()
    except Exception as e:
        logger.error(f"Error processing message requests: {e}")
        
async def process_mentions(handler, mention_controller):
    """Process mentions"""
    try:
        # Navigate to mentions page
        success = await mention_controller.navigate_to_mentions()
        if not success:
            logger.error("Failed to navigate to mentions page")
            return
            
        # Process mentions
        await mention_controller.process_mentions()
        
    except Exception as e:
        logger.error(f"Error processing mentions: {e}")

async def main_loop():
    """Main bot loop"""
    handler = None
    try:
        # Initialize handlers and controllers
        handler = ActionHandler()
        message_controller = MessageController(handler)
        mention_controller = MentionController(handler)
        
        # Check login state
        if not handler.ensure_logged_in():
            logger.error("Failed to log in")
            return
            
        while True:
            try:
                # Process message requests first
                logger.info("Processing message requests...")
                await message_controller.process_message_requests()
                await asyncio.sleep(random.uniform(3, 5))
                
                # Process regular DMs
                logger.info("Processing DMs...")
                await message_controller.process_dms()
                await asyncio.sleep(random.uniform(3, 5))
                
                # Process mentions
                logger.info("Processing mentions...")
                await mention_controller.process_mentions()
                
                # Wait before next cycle (45-90 seconds)
                delay = random.uniform(45, 90)
                logger.info(f"Waiting {delay:.1f} seconds before next cycle...")
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                # Try to recover by going back to home page
                try:
                    handler.browser.navigate("https://twitter.com/home")
                    await asyncio.sleep(5)
                except:
                    pass
                    
                # Wait longer after an error (2-5 minutes)
                error_delay = random.uniform(120, 300)
                logger.info(f"Error occurred, waiting {error_delay:.1f} seconds before retry...")
                await asyncio.sleep(error_delay)
                
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
    finally:
        if handler:
            try:
                handler.cleanup()
                logger.info("Successfully cleaned up resources")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("\nScript stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}") 