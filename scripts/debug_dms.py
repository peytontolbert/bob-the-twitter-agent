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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler

async def debug_dms():
    """Debug DM functionality with detailed logging"""
    handler = None
    try:
        handler = ActionHandler(headless=False)
        
        # Login
        logger.info("Logging in...")
        is_logged_in = await handler.ensure_logged_in()
        if not is_logged_in:
            logger.error("Failed to log in")
            return
        
        # Navigate to messages
        logger.info("Navigating to messages...")
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)
        await handler.handle_notifications()
        
        # Wait for conversations to load
        logger.info("Waiting for conversations to load...")
        conversations = WebDriverWait(handler.browser.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='conversation']"))
        )
        
        logger.info(f"Found {len(conversations)} conversations")
        
        # Process each conversation
        for i, conv in enumerate(conversations, 1):
            try:
                logger.info(f"\nProcessing conversation {i}...")
                
                # Log conversation attributes
                logger.info("Conversation attributes:")
                logger.info(f"Class: {conv.get_attribute('class')}")
                logger.info(f"Role: {conv.get_attribute('role')}")
                logger.info(f"Data-testid: {conv.get_attribute('data-testid')}")
                
                # Create hover action
                logger.info("Hovering over conversation...")
                actions = ActionChains(handler.browser.driver)
                actions.move_to_element(conv)
                actions.pause(random.uniform(0.5, 1.0))
                actions.perform()
                await asyncio.sleep(1)
                
                # Try to find sender with multiple selectors
                sender_selectors = [
                    "[data-testid='User-Name']",
                    "[data-testid='conversationSender']",
                    "[data-testid='DMConversationEntry-UserName']",
                    "div[dir='ltr']",
                    "span[dir='ltr']"
                ]
                
                sender = None
                for selector in sender_selectors:
                    try:
                        elements = conv.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            text = elem.text.strip()
                            if text and '@' in text:  # Look for username format
                                sender = text
                                logger.info(f"Found sender with selector {selector}: {sender}")
                                break
                        if sender:
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                
                if not sender:
                    logger.warning("Could not find sender name")
                
                # Click to open conversation
                logger.info("Opening conversation...")
                actions = ActionChains(handler.browser.driver)
                actions.click(conv)
                actions.perform()
                await asyncio.sleep(2)
                
                # Handle any notifications that might appear
                await handler.handle_notifications()
                
                # Try to get messages
                logger.info("Looking for messages...")
                messages = WebDriverWait(handler.browser.driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='messageEntry']"))
                )
                
                logger.info(f"Found {len(messages)} messages")
                
                # Log details of last message
                if messages:
                    last_message = messages[-1]
                    logger.info("Last message details:")
                    logger.info(f"Text: {last_message.text}")
                    logger.info(f"Class: {last_message.get_attribute('class')}")
                    logger.info(f"Role: {last_message.get_attribute('role')}")
                
                # Try to find message input box
                logger.info("Looking for message input box...")
                input_box = None
                try:
                    input_box = WebDriverWait(handler.browser.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 
                            "div[data-testid='dmComposerTextInput'][role='textbox']"))
                    )
                    logger.info("Found input box")
                    
                    # Test interaction with input box
                    logger.info("Testing input interaction...")
                    actions = ActionChains(handler.browser.driver)
                    actions.move_to_element(input_box)
                    actions.pause(random.uniform(0.3, 0.7))
                    actions.click()
                    actions.perform()
                    await asyncio.sleep(1)
                    
                    # Type test message
                    test_msg = "Test message"
                    for char in test_msg:
                        actions = ActionChains(handler.browser.driver)
                        actions.send_keys(char)
                        actions.perform()
                        await asyncio.sleep(random.uniform(0.05, 0.1))
                    logger.info("Successfully typed test message")
                    
                    # Find and hover over send button
                    logger.info("Looking for send button...")
                    send_button = WebDriverWait(handler.browser.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 
                            "button[data-testid='dmComposerSendButton']"))
                    )
                    
                    # Hover over send button
                    actions = ActionChains(handler.browser.driver)
                    actions.move_to_element(send_button)
                    actions.pause(random.uniform(0.5, 1.5))
                    actions.perform()
                    logger.info("Successfully hovered over send button")
                    await asyncio.sleep(1)
                    
                    # Click send button if flag is set
                    SHOULD_SEND = True  # Set to False to only hover without sending
                    if SHOULD_SEND:
                        actions = ActionChains(handler.browser.driver)
                        actions.click(send_button)
                        actions.perform()
                        logger.info("Clicked send button")
                        await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error with message input/send: {e}")
                    if not input_box:
                        logger.warning("Could not find message input box")
                
                # Find and click back button
                logger.info("Looking for back button...")
                back_button = WebDriverWait(handler.browser.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='DM_Timeline_Back']"))
                )
                
                # Hover and click back
                logger.info("Clicking back button...")
                actions = ActionChains(handler.browser.driver)
                actions.move_to_element(back_button)
                actions.pause(random.uniform(0.3, 0.7))
                actions.click()
                actions.perform()
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing conversation {i}: {str(e)}")
                # Try to recover by going back to messages
                try:
                    logger.info("Attempting to recover...")
                    back_button = WebDriverWait(handler.browser.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='DM_Timeline_Back']"))
                    )
                    back_button.click()
                    await asyncio.sleep(2)
                except:
                    logger.warning("Could not find back button, navigating to messages directly")
                    handler.browser.navigate("https://twitter.com/messages")
                    await asyncio.sleep(3)
                continue
        
        logger.info("Completed processing all conversations")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        if handler:
            handler.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_dms()) 