import os
import logging
import asyncio
from dotenv import load_dotenv
from src.agent.action_handler import ActionHandler
from src.agent.bob_agent import BobTheBuilder
from src.agent.tweet_controller import TweetController

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bob_tweet_pipeline.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def run_tweet_pipeline():
    """Run the tweeting pipeline."""
    # Initialize action handler
    action_handler = ActionHandler()
    
    # Initialize Bob with memory
    bob = BobTheBuilder(os.getenv('OPENAI_API_KEY'))
    
    # Initialize TweetController
    tweet_controller = TweetController(action_handler, bob=bob)
    
    # Ensure logged in
    if not await action_handler.ensure_logged_in():
        logger.error("Failed to log in")
        return
    
    # Generate a tweet from Bob
    tweet_content = await bob.generate_tweet()  # Assuming this method generates a tweet
    if tweet_content:
        logger.info(f"Generated tweet content: {tweet_content}")
        success = await tweet_controller.post_tweet(tweet_content)
        if success:
            logger.info("Tweet posted successfully.")
        else:
            logger.error("Failed to post the tweet.")
    else:
        logger.error("Failed to generate tweet content.")

if __name__ == "__main__":
    asyncio.run(run_tweet_pipeline()) 