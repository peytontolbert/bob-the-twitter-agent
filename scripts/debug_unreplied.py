import asyncio
import os
import sys
import logging
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.action_handler import ActionHandler

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_unreplied():
    handler = None
    try:
        handler = ActionHandler(headless=False)
        
        # Check login
        logger.info("Checking login state...")
        is_logged_in = await handler.ensure_logged_in()
        if not is_logged_in:
            logger.error("Failed to log in")
            return
            
        # First check DMs
        logger.info("\n=== Checking DMs ===")
        logger.info("Navigating to messages...")
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)
        
        # Get all conversations
        conversations = await handler.check_dms()
        if conversations:
            logger.info(f"Found {len(conversations)} conversations")
            for i, conv in enumerate(conversations, 1):
                logger.info(f"\nConversation {i}:")
                logger.info(f"Sender: {conv.get('sender', 'Unknown')}")
                logger.info(f"Last message: {conv.get('preview', 'No preview')}")
                logger.info(f"Needs reply: {conv.get('needs_reply', False)}")
        else:
            logger.info("No conversations found")
            
        # Then check mentions
        logger.info("\n=== Checking Mentions ===")
        mentions = await handler.check_mentions()
        if mentions:
            logger.info(f"Found {len(mentions)} mentions")
            for i, mention in enumerate(mentions, 1):
                logger.info(f"\nMention {i}:")
                logger.info(f"From: {mention.get('username', 'Unknown')}")
                logger.info(f"Tweet: {mention.get('text', 'No text')}")
                logger.info(f"Tweet ID: {mention.get('tweet_id', 'No ID')}")
                logger.info(f"Already replied: {mention.get('tweet_id') in handler.replied_mentions}")
        else:
            logger.info("No mentions found")
            
    except Exception as e:
        logger.error(f"Error during debug: {e}")
    finally:
        if handler:
            handler.cleanup()

if __name__ == "__main__":
    asyncio.run(debug_unreplied()) 