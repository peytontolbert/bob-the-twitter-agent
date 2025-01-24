import os
import sys
import logging
import asyncio
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
import atexit
import signal
from datetime import datetime

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('conversation_details.log')
    ]
)
logger = logging.getLogger(__name__)

def cleanup_browser(handler):
    """Clean browser exit"""
    if not hasattr(cleanup_browser, 'already_cleaned'):
        cleanup_browser.already_cleaned = False
    
    if cleanup_browser.already_cleaned:
        return
        
    cleanup_browser.already_cleaned = True
    
    if handler and handler.browser:
        try:
            # Save any pending data if needed
            if handler.browser.driver:
                try:
                    handler.browser.driver.close()  # Close browser window first
                except:
                    pass
                try:
                    handler.browser.driver.quit()  # Then quit the driver
                except:
                    pass
                logger.info("Browser closed cleanly")
                handler.browser.driver = None  # Clear the reference immediately
            
            # Additional cleanup
            if hasattr(handler.browser, 'service') and handler.browser.service.is_running():
                try:
                    handler.browser.service.stop()
                    logger.info("Browser service stopped")
                except:
                    pass
                handler.browser.service = None  # Clear the service reference
                
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")
        finally:
            # Force cleanup of any remaining processes
            try:
                import psutil
                current_process = psutil.Process()
                children = current_process.children(recursive=True)
                for child in children:
                    try:
                        child.kill()  # Use kill instead of terminate for faster cleanup
                    except:
                        pass
                logger.info("Cleaned up all child processes")
            except Exception as e:
                logger.error(f"Error cleaning up processes: {e}")

def signal_handler(signum, frame, handler=None):
    """Handle shutdown signals"""
    logger.info(f"\nReceived signal {signum}. Cleaning up...")
    cleanup_browser(handler)
    sys.exit(0)

async def get_conversation_details():
    """Get detailed information about the current conversation"""
    handler = None
    try:
        # Initialize handler
        handler = ActionHandler(headless=False)
        if not await handler.ensure_logged_in():
            logger.error("Failed to log in")
            return
            
        # Navigate to messages
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)
        await handler.handle_notifications()
        
        # Get first conversation
        conversation = WebDriverWait(handler.browser.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='conversation']"))
        )
        
        # Log conversation attributes
        logger.info("\nConversation attributes:")
        logger.info(f"Class: {conversation.get_attribute('class')}")
        logger.info(f"Role: {conversation.get_attribute('role')}")
        logger.info(f"Data-testid: {conversation.get_attribute('data-testid')}")
        
        # Get handle
        sender_selectors = [
            "[data-testid='conversationSender']",
            "[data-testid='User-Name']",
            "[data-testid='DMConversationEntry-UserName']",
            "div[dir='ltr']",
            "span[dir='ltr']"
        ]
        
        handle = None
        for selector in sender_selectors:
            try:
                elements = conversation.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text and '@' in text:
                        handle = text
                        logger.info(f"Found sender with selector {selector}: {handle}")
                        break
                if handle:
                    break
            except:
                continue
                
        # Open conversation
        logger.info("Opening conversation...")
        actions = ActionChains(handler.browser.driver)
        actions.move_to_element(conversation)
        actions.click()
        actions.perform()
        await asyncio.sleep(2)
        
        # Get messages
        logger.info("Looking for messages...")
        cells = WebDriverWait(handler.browser.driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='cellInnerDiv']"))
        )
        
        if cells:
            logger.info(f"Found {len(cells)} messages")
            messages = []
            seen_texts = set()
            
            # Process each cell
            for cell in cells:
                try:
                    # Skip system messages
                    if any(skip_text in cell.text for skip_text in ["You accepted the request", "Seen", "Sent"]):
                        continue
                        
                    # Get message entry
                    try:
                        msg = cell.find_element(By.CSS_SELECTOR, "[data-testid='messageEntry']")
                    except:
                        continue
                        
                    text = msg.text.strip()
                    if not text or text in seen_texts:
                        continue
                    seen_texts.add(text)
                    
                    # Get timestamp
                    try:
                        timestamp_elem = cell.find_element(By.XPATH, ".//time")
                        timestamp = timestamp_elem.get_attribute("datetime")
                        display_time = timestamp_elem.text
                    except:
                        timestamp = None
                        display_time = None
                        
                    # Get message details
                    entry_class = msg.get_attribute("class")
                    entry_tag = msg.tag_name
                    entry_role = msg.get_attribute("role")
                    
                    # Log message details
                    logger.info(f"\nMessage details:")
                    logger.info(f"Text: {text}")
                    logger.info(f"Tag: {entry_tag}")
                    logger.info(f"Class: {entry_class}")
                    logger.info(f"Role: {entry_role}")
                    if timestamp:
                        logger.info(f"Timestamp: {timestamp}")
                        logger.info(f"Display time: {display_time}")
                        
                    # Check for any child elements
                    children = msg.find_elements(By.XPATH, ".//*")
                    if children:
                        logger.info("\nChild elements:")
                        for child in children[:5]:  # Limit to first 5 children
                            try:
                                logger.info(f"Tag: {child.tag_name}")
                                logger.info(f"Class: {child.get_attribute('class')}")
                                logger.info(f"Role: {child.get_attribute('role')}")
                            except:
                                continue
                                
                    messages.append({
                        'text': text,
                        'timestamp': timestamp,
                        'display_time': display_time,
                        'entry_tag': entry_tag,
                        'entry_class': entry_class,
                        'entry_role': entry_role
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
                    
            # Log final stats
            logger.info(f"\nProcessed {len(messages)} valid messages")
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if handler:
            handler.cleanup()

async def get_current_conversation_details(handler, memory=None, handle=None):
    """Get detailed information about the currently open conversation"""
    try:
        logger.info("\nGetting conversation details...")
        
        # Get all message cells
        cells = WebDriverWait(handler.browser.driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='cellInnerDiv']"))
        )
        
        if not cells:
            logger.info("No messages found in conversation")
            return []
            
        logger.info(f"Found {len(cells)} message cells")
        messages = []
        seen_texts = set()
        
        # Process each cell
        for cell in cells:
            try:
                # Skip system messages
                cell_text = cell.text.lower()
                if any(skip_text in cell_text for skip_text in ["you accepted the request", "seen", "sent"]):
                    continue
                    
                # Get message entry
                try:
                    msg = cell.find_element(By.CSS_SELECTOR, "[data-testid='messageEntry']")
                except:
                    continue
                    
                text = msg.text.strip()
                if not text or text in seen_texts:
                    continue
                seen_texts.add(text)
                
                # Get message details and ownership signals
                msg_class = msg.get_attribute("class") or ""
                
                # Check ownership - our messages have r-obd0qt class
                from_us = "r-obd0qt" in msg_class
                
                # Create message object
                message = {
                    'text': text,
                    'time': 'Now',  # Twitter DMs often just show "Now" for recent messages
                    'from_us': from_us,
                    'ownership_signals': f"msg: {msg_class}"
                }
                
                # Log message details
                logger.info("\nMessage Details:")
                logger.info("-" * 50)
                logger.info(f"Text: {text}")
                logger.info(f"Time: Now")
                logger.info(f"From us: {from_us}")
                logger.info(f"Ownership signals: {message['ownership_signals']}")
                logger.info("-" * 50)
                
                messages.append(message)
                
                # Save to memory if provided
                if memory and handle:
                    memory.add_dm(handle, message)
                    logger.info(f"Saved memory for {handle}")
            
            except Exception as e:
                # Only log error if we haven't found any messages yet
                if not messages:
                    logger.error(f"Error processing message: {e}")
                continue
                
        return messages
        
    except Exception as e:
        logger.error(f"Error getting conversation details: {e}")
        return []

if __name__ == "__main__":
    try:
        # Register signal handlers
        signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, None))  # Don't pass handler to avoid double cleanup
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, None))
        
        asyncio.run(get_conversation_details())
    except KeyboardInterrupt:
        logger.info("\nScript stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        sys.exit(0)  # Exit immediately after cleanup 