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
from src.agent.conversation_memory import ConversationMemory

# Configure logging - only show INFO level for our script
logging.getLogger('selenium').setLevel(logging.WARNING)  # Suppress selenium logs
logging.getLogger('urllib3').setLevel(logging.WARNING)  # Suppress urllib3 logs
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',  # Simplified format
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dm_previews.log')
    ]
)
logger = logging.getLogger(__name__)

async def get_handle_from_conversation(conv, selectors):
    """Extract handle from conversation element"""
    for selector in selectors:
        try:
            elements = conv.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                text = elem.text.strip()
                if text and '@' in text:  # Look for username format
                    return text
        except:
            continue
    return None

async def list_dm_previews(memory: ConversationMemory = None, existing_handler: ActionHandler = None):
    """List all DM conversations and match them with memory handles"""
    if memory is None:
        memory = ConversationMemory()
        
    handler = existing_handler
    cleanup_needed = False
    
    try:
        if handler is None:
            cleanup_needed = True
            handler = ActionHandler(headless=False)
            if not await handler.ensure_logged_in():
                logger.error("Failed to log in")
                return []

        # Navigate to messages
        logger.info("Navigating to messages...")
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)
        await handler.handle_notifications()

        # Get conversation elements
        conversations = WebDriverWait(handler.browser.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='conversation']"))
        )

        if not conversations:
            logger.info("No conversations found")
            return []

        logger.info(f"\nFound {len(conversations)} conversations")
        logger.info("-" * 30)
        
        # Map conversations to handles
        handle_map = {}
        
        handle_selectors = [
            "[data-testid='conversationSender']",
            "[data-testid='User-Name']",
            "[data-testid='DMConversationEntry-UserName']",
            "div[dir='ltr']",
            "span[dir='ltr']"
        ]

        for conv in conversations:
            handle = await get_handle_from_conversation(conv, handle_selectors)
            if handle:
                handle_map[handle] = conv
                logger.info(f"Found conversation with {handle}")

        return handle_map

    except Exception as e:
        logger.error(f"Error: {e}")
        return []
    finally:
        if cleanup_needed and handler:
            handler.cleanup()

if __name__ == "__main__":
    try:
        memory = ConversationMemory()
        handle_map = asyncio.run(list_dm_previews(memory))
        
        if handle_map:
            logger.info("\nMatched conversations:")
            for handle in handle_map:
                logger.info(f"- {handle}")
                # Show recent context from memory if available
                recent = memory.get_recent_context(handle, limit=1)
                if recent:
                    last_msg = recent[-1]
                    logger.info(f"  Last interaction: {last_msg.get('preview', 'No preview')} ({last_msg.get('type', 'unknown')})")
        else:
            logger.info("No conversations matched")
    except KeyboardInterrupt:
        logger.info("\nScript stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}") 