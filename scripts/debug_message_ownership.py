import os
import sys
import logging
import asyncio
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_ownership.log')
    ]
)
logger = logging.getLogger(__name__)

async def debug_message_ownership():
    """Debug script to analyze message ownership detection"""
    handler = None
    try:
        handler = ActionHandler(headless=False)
        if not await handler.ensure_logged_in():
            logger.error("Failed to log in")
            return

        # Navigate to messages
        logger.info("Navigating to messages...")
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)

        # Click first conversation
        conversation_selectors = [
            "[data-testid='conversation']",
            "[data-testid='cellInnerDiv']",
            "div[role='row']"
        ]

        for selector in conversation_selectors:
            try:
                convs = WebDriverWait(handler.browser.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                if convs:
                    convs[0].click()
                    logger.info("Opened first conversation")
                    break
            except Exception as e:
                continue

        await asyncio.sleep(2)

        # Find messages
        message_selectors = [
            "[data-testid='messageEntry']",
            "[data-testid='tweetText']",
            "div[role='presentation']",
            "div[data-testid='dmConversationMessage']"
        ]

        for selector in message_selectors:
            try:
                logger.info(f"\nTrying selector: {selector}")
                msgs = WebDriverWait(handler.browser.driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                
                if msgs:
                    logger.info(f"Found {len(msgs)} messages")
                    
                    for i, msg in enumerate(msgs, 1):
                        try:
                            logger.info(f"\nMessage {i} details:")
                            
                            # Get message text
                            text = msg.text.strip()
                            logger.info(f"Text content: {text}")
                            
                            # Get class
                            msg_class = msg.get_attribute("class")
                            logger.info(f"Class: {msg_class}")
                            
                            # Get role
                            role = msg.get_attribute("role")
                            logger.info(f"Role: {role}")
                            
                            # Get data-testid
                            testid = msg.get_attribute("data-testid")
                            logger.info(f"Data-testid: {testid}")
                            
                            # Get style
                            style = msg.get_attribute("style")
                            logger.info(f"Style: {style}")
                            
                            # Check parent
                            try:
                                parent = msg.find_element(By.XPATH, "./..")
                                parent_class = parent.get_attribute("class")
                                logger.info(f"Parent class: {parent_class}")
                            except:
                                logger.info("Could not get parent info")
                                
                            # Print full HTML for analysis
                            html = msg.get_attribute('outerHTML')
                            logger.info(f"HTML: {html}")
                            
                            logger.info("-" * 50)
                            
                        except Exception as e:
                            logger.error(f"Error analyzing message {i}: {e}")
                            continue
                            
                    break  # Found messages with this selector
                    
            except Exception as e:
                logger.error(f"Error with selector {selector}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error in debug script: {e}")
    finally:
        try:
            if handler and handler.browser and handler.browser.driver:
                handler.browser.driver.quit()
                logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(debug_message_ownership())
    except KeyboardInterrupt:
        logger.info("\nScript stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}") 