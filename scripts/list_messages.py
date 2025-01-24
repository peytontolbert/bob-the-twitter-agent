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
        logging.FileHandler('list_messages.log')
    ]
)
logger = logging.getLogger(__name__)

async def list_messages():
    """List all messages from the messages page"""
    handler = None
    try:
        # Initialize handler and login
        handler = ActionHandler(headless=False)
        if not await handler.ensure_logged_in():
            logger.error("Failed to log in")
            return

        # Navigate to messages
        logger.info("Navigating to messages...")
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)
        await handler.handle_notifications()

        # Try different selectors for message conversations
        conversation_selectors = [
            "[data-testid='conversation']",
            "[data-testid='cellInnerDiv']",
            "div[role='row']"
        ]

        conversations = []
        for selector in conversation_selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                elements = WebDriverWait(handler.browser.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                if elements:
                    conversations = elements
                    logger.info(f"Found {len(elements)} conversations with selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"No conversations found with selector {selector}")
                continue

        if not conversations:
            logger.info("No conversations found")
            return

        # Process each conversation
        logger.info("\nMessage List:")
        logger.info("-" * 50)
        
        for i, conv in enumerate(conversations, 1):
            try:
                # Try to get sender name/handle
                sender_selectors = [
                    "[data-testid='conversationSender']",
                    "[data-testid='User-Name']",
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
                            if text and '@' in text:
                                sender = text
                                break
                        if sender:
                            break
                    except:
                        continue

                # Try to get last message preview
                preview_selectors = [
                    "[data-testid='last-message']",
                    "[data-testid='messageEntry']",
                    "div[data-testid='dmConversationMessage']"
                ]
                
                preview = None
                for selector in preview_selectors:
                    try:
                        elements = conv.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            preview = elements[-1].text.strip()
                            break
                    except:
                        continue

                # Try to get timestamp
                time_selectors = [
                    "[data-testid='timestamp']",
                    "time",
                    "span[data-testid='timestamp']"
                ]
                
                timestamp = None
                for selector in time_selectors:
                    try:
                        elements = conv.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            timestamp = elements[-1].text.strip()
                            break
                    except:
                        continue

                # Print conversation info
                logger.info(f"\nConversation {i}:")
                logger.info(f"Sender: {sender or 'Unknown'}")
                logger.info(f"Last Message: {preview[:50] + '...' if preview and len(preview) > 50 else preview or 'No preview'}")
                logger.info(f"Time: {timestamp or 'Unknown'}")
                logger.info("-" * 30)

            except Exception as e:
                logger.error(f"Error processing conversation {i}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error listing messages: {e}")
    finally:
        if handler:
            handler.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(list_messages())
    except KeyboardInterrupt:
        logger.info("\nScript stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}") 