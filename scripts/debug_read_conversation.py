import asyncio
import os
import sys
import logging
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import random

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for maximum detail
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_conversation.log')
    ]
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler

async def debug_read_conversation():
    """Debug script to read and analyze DM conversations with detailed logging"""
    handler = None
    try:
        handler = ActionHandler(headless=False)
        
        # Login check
        logger.info("Checking login state...")
        is_logged_in = await handler.ensure_logged_in()
        if not is_logged_in:
            logger.error("Failed to log in")
            return
        
        # Navigate to messages
        logger.info("\nNavigating to messages...")
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)
        await handler.handle_notifications()
        
        # Find conversations
        logger.info("\nLooking for conversations...")
        conversation_selectors = [
            "[data-testid='conversation']",
            "[data-testid='cellInnerDiv']",
            "div[role='row']"
        ]
        
        conversations = []
        for selector in conversation_selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                convs = WebDriverWait(handler.browser.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                if convs:
                    conversations = convs
                    logger.info(f"Found {len(convs)} conversations using selector: {selector}")
                    
                    # Log details about each conversation element
                    for i, conv in enumerate(convs):
                        logger.info(f"\nConversation {i+1} details:")
                        logger.info(f"Class: {conv.get_attribute('class')}")
                        logger.info(f"Role: {conv.get_attribute('role')}")
                        logger.info(f"Data-testid: {conv.get_attribute('data-testid')}")
                    break
            except Exception as e:
                logger.error(f"Error with selector {selector}: {e}")
                continue
        
        if not conversations:
            logger.error("No conversations found")
            return
        
        # Process first conversation for debugging
        logger.info("\nProcessing first conversation...")
        conv = conversations[0]
        
        # Try to get sender info before clicking
        sender_selectors = [
            "[data-testid='conversationSender']",
            "[data-testid='User-Name']",
            "div[dir='ltr']"
        ]
        
        sender = None
        for selector in sender_selectors:
            try:
                logger.info(f"Trying to find sender with selector: {selector}")
                sender_elem = conv.find_element(By.CSS_SELECTOR, selector)
                if sender_elem:
                    sender = sender_elem.text
                    logger.info(f"Found sender: {sender} using selector: {selector}")
                    break
            except:
                continue
        
        # Click to open conversation
        logger.info("\nOpening conversation...")
        actions = ActionChains(handler.browser.driver)
        actions.move_to_element(conv)
        actions.pause(0.5)
        actions.click()
        actions.perform()
        await asyncio.sleep(2)
        
        # Try different selectors for messages
        message_selectors = [
            "[data-testid='messageEntry']",
            "[data-testid='tweetText']",
            "div[role='presentation']",
            "div[data-testid='dmConversationMessage']",
            "div[data-testid='messageEntry']",
            "article[role='article']"
        ]
        
        messages = []
        for selector in message_selectors:
            try:
                logger.info(f"\nTrying to find messages with selector: {selector}")
                found_messages = WebDriverWait(handler.browser.driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                if found_messages:
                    messages = found_messages
                    logger.info(f"Found {len(messages)} messages using selector: {selector}")
                    
                    # Analyze each message
                    for i, msg in enumerate(messages):
                        logger.info(f"\nMessage {i+1} details:")
                        logger.info(f"Class: {msg.get_attribute('class')}")
                        logger.info(f"Role: {msg.get_attribute('role')}")
                        logger.info(f"Data-testid: {msg.get_attribute('data-testid')}")
                        logger.info(f"Style: {msg.get_attribute('style')}")
                        logger.info(f"Text content: {msg.text}")
                        
                        # Try to find sender info within message
                        for sender_selector in [
                            "[data-testid='messageSender']",
                            "[data-testid='User-Name']",
                            "div[dir='ltr']"
                        ]:
                            try:
                                sender_elem = msg.find_element(By.CSS_SELECTOR, sender_selector)
                                logger.info(f"Found sender element with selector {sender_selector}: {sender_elem.text}")
                            except:
                                continue
                        
                        # Check if message is from us
                        is_from_us = False
                        if "sent" in msg.get_attribute("class").lower():
                            is_from_us = True
                            logger.info("Message is from us (class contains 'sent')")
                        elif msg.get_attribute("style") and ("right" in msg.get_attribute("style").lower() or "flex-end" in msg.get_attribute("style").lower()):
                            is_from_us = True
                            logger.info("Message is from us (right-aligned)")
                        
                        logger.info(f"Is from us: {is_from_us}")
                        logger.info("-" * 50)
                    break
            except Exception as e:
                logger.error(f"Error with message selector {selector}: {e}")
                continue
        
        if not messages:
            logger.error("No messages found in conversation")
        
        # Log the full HTML of the conversation area for analysis
        try:
            conversation_area = handler.browser.driver.find_element(By.CSS_SELECTOR, "[data-testid='DM_conversation']")
            logger.debug(f"\nFull conversation HTML:\n{conversation_area.get_attribute('outerHTML')}")
        except Exception as e:
            logger.error(f"Could not get conversation HTML: {e}")
        
        logger.info("\nDebug reading completed")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if handler:
            handler.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_read_conversation()) 