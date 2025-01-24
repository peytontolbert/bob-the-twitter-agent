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
import json
from pathlib import Path
from src.agent.conversation_memory import ConversationMemory

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
    def __init__(self):
        # Initialize shared memory
        self.memory = ConversationMemory()
        
        # Initialize action handler first
        self.action_handler = ActionHandler()
        
        # Initialize Bob with memory
        self.bob = BobTheBuilder(os.getenv('OPENAI_API_KEY'), memory=self.memory)
        
        # Initialize controllers with action handler, memory, and Bob
        self.message_controller = MessageController(self.action_handler, memory=self.memory, bob=self.bob)
        self.mention_controller = MentionController(self.action_handler, memory=self.memory, bob=self.bob)
        
        # Control flags
        self.running = False
        
    async def run(self):
        """Main run loop."""
        self.running = True
        try:
            # Ensure logged in
            if not await self.action_handler.ensure_logged_in():
                logger.error("Failed to log in")
                return
                
            while self.running:
                try:
                    # Process message requests and DMs using message controller
                    logger.info("\nStarting new processing cycle")
                    logger.info("=" * 50)
                    
                    # Check and accept any pending message requests first
                    logger.info("\nChecking message requests...")
                    await self.message_controller.process_message_requests()
                    await asyncio.sleep(2)  # Brief pause after handling requests
                    
                    # Process DMs
                    logger.info("\nProcessing DMs...")
                    await self.message_controller.process_dms(memory=self.memory)
                    await asyncio.sleep(2)  # Brief pause before mentions
                    
                    # Process mentions
                    logger.info("\nProcessing mentions...")
                    await self.mention_controller.process_mentions()
                    
                    # Save memory state after each cycle
                    self.memory.save_all_conversations()
                    logger.info("\nCompleted processing cycle")
                    logger.info("=" * 50)
                    
                    # Sleep between cycles
                    await asyncio.sleep(10)
                    
                except Exception as e:
                    logger.error(f"Error in processing cycle: {e}")
                    await asyncio.sleep(30)  # Longer sleep on error
                    continue
                
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            # Save final memory state
            self.memory.save_all_conversations()
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources."""
        try:
            self.running = False
            if hasattr(self, 'mention_controller'):
                self.mention_controller.cleanup()
            if hasattr(self, 'action_handler'):
                self.action_handler.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
async def main():
    controller = BobController()
    await controller.run()
    
if __name__ == "__main__":
    asyncio.run(main()) 