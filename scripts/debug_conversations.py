import os
import sys
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler
from src.agent.conversation_memory import ConversationMemory
from scripts.list_dm_previews import list_dm_previews
from scripts.debug_accept_requests import get_message_requests, accept_request, return_to_requests
from scripts.debug_conversation import get_current_conversation_details
from scripts.debug_navigating_conversations import navigate_conversations, open_conversation

# Load environment variables
load_dotenv()

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/conversation_debug.log')
    ]
)
logger = logging.getLogger(__name__)

async def debug_conversations():
    """Orchestrate our existing scripts to get complete DM details"""
    memory = ConversationMemory()
    handler = None
    
    try:
        logger.info("\nStarting conversation debugging")
        logger.info("=" * 80)
        
        # Initialize handler and login
        handler = ActionHandler(headless=False)
        if not await handler.ensure_logged_in():
            logger.error("Failed to log in")
            return
            
        # Step 1: Check and accept message requests
        logger.info("\nChecking message requests...")
        requests = await get_message_requests(handler)
        if requests:
            logger.info(f"Found {len(requests)} message requests")
            for request in requests:
                logger.info(f"Accepting request from {request['sender']}...")
                if await accept_request(handler, request):
                    await return_to_requests(handler)
        else:
            logger.info("No pending message requests")
            
        # Step 2: Get list of DM previews with handles
        logger.info("\nGetting DM previews...")
        dm_previews = await list_dm_previews(memory, handler)
        if not dm_previews:
            logger.info("No DM conversations found")
            return
            
        # Step 3: Process each conversation
        logger.info("\nProcessing conversations...")
        for i, (handle, conv_element) in enumerate(dm_previews.items(), 1):
            logger.info(f"\nProcessing conversation {i}/{len(dm_previews)}")
            logger.info("-" * 80)
            logger.info(f"Conversation with: {handle}")
            
            try:
                # Open conversation using navigation function
                if not await open_conversation(handler, conv_element):
                    logger.error("Failed to open conversation")
                    continue
                
                # Get conversation details
                messages = await get_current_conversation_details(handler, memory, handle)
                if messages:
                    logger.info(f"Retrieved {len(messages)} messages from conversation")
                else:
                    logger.error("Failed to get messages from conversation")
                
            except Exception as e:
                logger.error(f"Error processing conversation {i}: {e}")
            finally:
                await asyncio.sleep(2)  # Brief pause between conversations
                
        logger.info("\nFinished processing all conversations")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error in debug_conversations: {str(e)}")
    finally:
        if handler:
            try:
                handler.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(debug_conversations())
    except KeyboardInterrupt:
        logger.info("\nScript interrupted by user")
    except Exception as e:
        logger.error(f"Error running script: {e}") 