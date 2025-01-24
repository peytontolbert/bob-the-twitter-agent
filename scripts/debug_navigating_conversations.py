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
        logging.FileHandler('conversation_navigation.log')
    ]
)
logger = logging.getLogger(__name__)

async def get_conversations(handler, limit=10):
    """Get all conversations up to limit"""
    try:
        conversations = WebDriverWait(handler.browser.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='conversation']"))
        )
        
        if not conversations:
            logger.info("No conversations found")
            return []
            
        # Limit number of conversations
        conversations = conversations[:limit]
        logger.info(f"Found {len(conversations)} conversations (limited to {limit})")
        return conversations
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return []

async def get_handle_from_conversation(handler, conv):
    """Extract handle from conversation element"""
    try:
        sender_selectors = [
            "[data-testid='conversationSender']",
            "[data-testid='User-Name']",
            "[data-testid='DMConversationEntry-UserName']",
            "div[dir='ltr']",
            "span[dir='ltr']"
        ]
        
        for selector in sender_selectors:
            try:
                elements = conv.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.strip()
                    if text and '@' in text:  # Look for username format
                        return text
            except:
                continue
        return None
    except Exception as e:
        logger.error(f"Error getting handle: {e}")
        return None

async def read_conversation_messages(handler):
    """Read messages from current conversation"""
    try:
        cells = WebDriverWait(handler.browser.driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='cellInnerDiv']"))
        )
        
        if not cells:
            logger.info("No messages found")
            return []
            
        logger.info(f"Found {len(cells)} message cells")
        return cells
        
    except Exception as e:
        logger.error(f"Error reading messages: {e}")
        return []

async def navigate_conversations(handler, limit=10):
    """Test navigation between conversations"""
    try:
        # Get list of conversations
        conversations = await get_conversations(handler, limit)
        if not conversations:
            return
            
        # Process each conversation
        for i, conv in enumerate(conversations, 1):
            try:
                # Get handle before clicking
                handle = await get_handle_from_conversation(handler, conv)
                logger.info(f"\nProcessing conversation {i}/{len(conversations)}")
                logger.info(f"Handle: {handle}")
                
                # Click to open conversation
                actions = ActionChains(handler.browser.driver)
                actions.move_to_element(conv)
                actions.click()
                actions.perform()
                await asyncio.sleep(2)
                
                # Read messages
                messages = await read_conversation_messages(handler)
                if messages:
                    logger.info(f"Successfully read {len(messages)} messages")
                    
                    # Log last message details
                    try:
                        last_msg = messages[-1]
                        msg_text = last_msg.find_element(By.CSS_SELECTOR, "[data-testid='messageEntry']").text
                        logger.info(f"Last message: {msg_text[:50]}...")
                    except:
                        logger.error("Could not get last message details")
                
                # No need to go back, just open next conversation
                
            except Exception as e:
                logger.error(f"Error processing conversation {i}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error navigating conversations: {e}")

async def open_conversation(handler, conversation):
    """Open a specific conversation and return success"""
    try:
        # Click to open conversation using ActionChains
        actions = ActionChains(handler.browser.driver)
        actions.move_to_element(conversation)
        actions.click()
        actions.perform()
        await asyncio.sleep(2)
        
        # Verify conversation opened
        try:
            WebDriverWait(handler.browser.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='messageEntry']"))
            )
            return True
        except:
            logger.error("Failed to verify conversation opened")
            return False
            
    except Exception as e:
        logger.error(f"Error opening conversation: {e}")
        return False

async def main():
    """Main function to test conversation navigation"""
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
        
        # Test navigation between conversations
        await navigate_conversations(handler)
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        if handler:
            handler.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nScript stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}") 