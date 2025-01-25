import os
import logging
import asyncio
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from src.agent.action_handler import ActionHandler
from src.agent.bob_agent import BobTheBuilder
from src.agent.message_controller import MessageController
from src.agent.mention_controller import MentionController
from src.agent.tweet_controller import TweetController
from src.agent.auto_tweet_controller import AutoTweetController
from src.agent.conversation_memory import ConversationMemory
import json
from pathlib import Path
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bob.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BobController:
    def __init__(self, tweet_interval_minutes=60):
        # Initialize shared memory
        self.memory = ConversationMemory()
        
        # Initialize action handler first
        self.action_handler = ActionHandler()
        
        # Initialize Bob with memory
        self.bob = BobTheBuilder(os.getenv('OPENAI_API_KEY'), memory=self.memory)
        
        # Initialize controllers
        self.tweet_controller = TweetController(
            self.action_handler, 
            bob=self.bob,
            tweet_interval_minutes=tweet_interval_minutes
        )
        self.message_controller = MessageController(self.action_handler, memory=self.memory, bob=self.bob)
        self.mention_controller = MentionController(self.action_handler, memory=self.memory, bob=self.bob)
        
        # Control flags
        self.running = False
        
    async def run(self):
        """Main run loop with auto-tweeting."""
        self.running = True
        try:
            # Ensure logged in
            if not await self.action_handler.ensure_logged_in():
                logger.error("Failed to log in")
                return
                
            while self.running:
                try:
                    logger.info("\nStarting new processing cycle")
                    logger.info("=" * 50)
                    
                    # Process auto-tweets
                    logger.info("\nChecking auto-tweet schedule...")
                    await self.tweet_controller.process_auto_tweet()
                    
                    # Check and accept any pending message requests
                    logger.info("\nChecking message requests...")
                    await self.message_controller.process_message_requests()
                    await asyncio.sleep(2)
                    
                    # Process DMs
                    logger.info("\nProcessing DMs...")
                    await self.message_controller.process_dms()
                    await asyncio.sleep(2)
                    
                    # Process mentions
                    logger.info("\nProcessing mentions...")
                    await self.mention_controller.process_mentions()
                    
                    # Save memory state
                    self.memory.save_all_conversations()
                    logger.info("\nCompleted processing cycle")
                    logger.info("=" * 50)
                    
                    # Sleep between cycles (shorter interval for responsiveness)
                    await asyncio.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Error in processing cycle: {e}")
                    await asyncio.sleep(30)
                    continue
                
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.memory.save_all_conversations()
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources."""
        try:
            self.running = False
            if hasattr(self, 'tweet_controller'):
                self.tweet_controller.cleanup()
            if hasattr(self, 'mention_controller'):
                self.mention_controller.cleanup()
            if hasattr(self, 'action_handler'):
                self.action_handler.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
async def main():
    # Create controller with 60-minute tweet interval
    controller = BobController(tweet_interval_minutes=60)
    await controller.run()
    
if __name__ == "__main__":
    asyncio.run(main()) 