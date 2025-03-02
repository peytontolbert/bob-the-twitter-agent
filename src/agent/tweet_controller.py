import logging
import asyncio
import random
import json
from pathlib import Path
import time
from typing import Dict, List, Optional
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime

logger = logging.getLogger(__name__)

class TweetController:
    """Controller for managing tweet operations."""
    
    def __init__(self, action_handler, bob=None, tweet_interval_minutes=20):
        """Initialize the tweet controller.
        
        Args:
            action_handler: The main ActionHandler instance
            bob: BobTheBuilder instance for generating tweets
            tweet_interval_minutes: Minutes between auto-tweets
        """
        self.handler = action_handler
        self.bob = bob
        self.tweet_queue = []
        self.posted_tweets = set()
        self.tweet_history = []  # To store the last 5 tweets
        self.tweet_history_file = Path("data/tweet_history.json")
        self.last_tweet_time = None
        self.tweet_interval_minutes = tweet_interval_minutes
        self._load_tweet_history()
        
    def _load_tweet_history(self):
        """Load tweet history from file."""
        try:
            if self.tweet_history_file.exists():
                with open(self.tweet_history_file, 'r') as f:
                    history = json.load(f)
                    self.posted_tweets = set(history.get('posted_tweets', []))
                    self.tweet_history = history.get('tweet_history', [])
                    # Convert the timestamp string back to datetime object
                    last_tweet_time = history.get('last_tweet_time')
                    if last_tweet_time:
                        self.last_tweet_time = datetime.fromisoformat(last_tweet_time)
                    else:
                        self.last_tweet_time = None
            else:
                self.posted_tweets = set()
                self.tweet_history = []
                self.last_tweet_time = None
        except Exception as e:
            logger.error(f"Error loading tweet history: {e}")
            self.posted_tweets = set()
            self.tweet_history = []
            self.last_tweet_time = None
            
    def _save_tweet_history(self):
        """Save tweet history to file."""
        try:
            self.tweet_history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tweet_history_file, 'w') as f:
                json.dump({
                    'posted_tweets': list(self.posted_tweets),
                    'tweet_history': self.tweet_history,
                    'last_tweet_time': self.last_tweet_time.isoformat() if self.last_tweet_time else None  # Save last tweet time
                }, f)
        except Exception as e:
            logger.error(f"Error saving tweet history: {e}")
            
    def add_to_queue(self, content: str, metadata: Optional[Dict] = None):
        """Add a tweet to the queue.
        
        Args:
            content: The tweet content
            metadata: Optional metadata about the tweet
        """
        self.tweet_queue.append({
            'content': content,
            'metadata': metadata or {},
            'added_time': asyncio.get_event_loop().time()
        })
        logger.info(f"Added tweet to queue: {content[:50]}...")
        
    async def post_tweet(self, content: str) -> bool:
        """Post a new tweet.
        
        Args:
            content: The tweet content
        
        Returns:
            bool: Whether the tweet was posted successfully
        """
        try:
            # Check if the tweet is in the last 5 tweets
            if content in self.tweet_history:
                logger.info("Skipping tweet as it is similar to recent tweets.")
                return False
            
            # Navigate to home
            self.handler.browser.navigate("https://twitter.com/home")
            await asyncio.sleep(3)
            
            # Find and click compose box
            compose_selectors = [
                "[data-testid='tweetTextarea_0']",
                "div[role='textbox'][data-testid='tweetTextarea_0']",
                "[data-testid='tweetTextarea_0_label']",
                "div[aria-label='Tweet text']",
                "div[aria-label='Post text']"
            ]
            
            compose_box = None
            for selector in compose_selectors:
                try:
                    compose_box = WebDriverWait(self.handler.browser.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    if compose_box:
                        logger.info(f"Found compose box with selector: {selector}")
                        break
                except:
                    continue
                    
            if not compose_box:
                logger.error("Could not find tweet compose box")
                return False
                
            # Click and enter tweet content
            compose_box.click()
            await asyncio.sleep(4)  # Wait after click
            
            # Additional wait to ensure compose box is ready
            await asyncio.sleep(7)  # Replace time.sleep with asyncio.sleep
            
            # Type content character by character with proper pacing
            actions = ActionChains(self.handler.browser.driver)
            for char in content:
                actions.send_keys(char)
                actions.pause(random.uniform(0.05, 0.1))
            actions.perform()
            await asyncio.sleep(3)  # Wait after typing completed
            
            # Find and click Post button with retry mechanism
            post_button = None
            post_button_selectors = [
                "button[data-testid='tweetButtonInline'][type='button']",
                "button[data-testid='tweetButton'][role='button']",
                "button[role='button'][data-testid='tweetButtonInline']",
                # Fallback to more specific XPath if CSS selectors fail
                "//button[@role='button' and @data-testid='tweetButtonInline']//span[contains(text(), 'Post')]/.."
            ]
            
            for _ in range(5):  # Retry up to 5 times
                try:
                    # Try each selector
                    for selector in post_button_selectors:
                        try:
                            if selector.startswith('//'):
                                # XPath selector
                                post_button = WebDriverWait(self.handler.browser.driver, 5).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                            else:
                                # CSS selector
                                post_button = WebDriverWait(self.handler.browser.driver, 5).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                            if post_button:
                                logger.info(f"Found post button with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not post_button:
                        continue  # Try next retry if button not found
                    
                    # Scroll into view
                    self.handler.browser.driver.execute_script("arguments[0].scrollIntoView(true);", post_button)
                    await asyncio.sleep(0.5)  # Wait for the button to stabilize
                    
                    # Attempt to click the button
                    post_button.click()
                    await asyncio.sleep(3)  # Wait for the tweet to post
                    break  # Exit the retry loop if successful
                    
                except Exception as e:
                    logger.error(f"Error clicking post button: {e}")
                    # Attempt to click using JavaScript if normal click fails
                    if post_button:
                        try:
                            self.handler.browser.driver.execute_script("arguments[0].click();", post_button)
                            await asyncio.sleep(3)  # Wait for the tweet to post
                            break  # Exit the retry loop if successful
                        except Exception as js_e:
                            logger.error(f"JavaScript click failed: {js_e}")
                    else:
                        logger.error("Post button not found, cannot click.")
            
            if not post_button:
                logger.error("Could not find or click the Post button")
                return False
            
            # Add to posted tweets
            self.posted_tweets.add(content)
            self.tweet_history.append(content)
            if len(self.tweet_history) > 5:
                self.tweet_history.pop(0)
            self.last_tweet_time = datetime.now()
            self._save_tweet_history()
            
            # Update Bob's memory with the new tweet
            if self.bob and hasattr(self.bob, 'memory'):
                self.bob.memory.add_message('tweets', {
                    'text': content,
                    'timestamp': datetime.now().isoformat(),
                    'is_from_us': True
                })
            
            logger.info(f"Successfully posted tweet: {content[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return False
            
    async def process_queue(self, max_tweets: int = 5):
        """Process tweets in the queue.
        
        Args:
            max_tweets: Maximum number of tweets to process
        """
        processed = 0
        while self.tweet_queue and processed < max_tweets:
            tweet = self.tweet_queue.pop(0)
            
            # Check if we've already posted this
            if tweet['content'] in self.posted_tweets:
                logger.info(f"Skipping already posted tweet: {tweet['content'][:50]}...")
                continue
                
            success = await self.post_tweet(tweet['content'])
            if success:
                processed += 1
                await asyncio.sleep(60)  # Rate limiting
            else:
                # Put back in queue if failed
                self.tweet_queue.append(tweet)
                break
                
    async def post_thread(self, tweets: List[str]) -> bool:
        """Post a thread of tweets.
        
        Args:
            tweets: List of tweet contents for the thread
        
        Returns:
            bool: Whether the thread was posted successfully
        """
        try:
            if not tweets:
                return False
                
            # Navigate to home
            self.handler.browser.navigate("https://twitter.com/home")
            await asyncio.sleep(3)
            
            for i, tweet in enumerate(tweets):
                # For first tweet
                if i == 0:
                    success = await self.post_tweet(tweet)
                    if not success:
                        return False
                    continue
                    
                # For subsequent tweets, find and click "Add to thread"
                try:
                    add_button = WebDriverWait(self.handler.browser.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='addButton']"))
                    )
                    add_button.click()
                    await asyncio.sleep(1)
                    
                    # Enter tweet content
                    compose_box = WebDriverWait(self.handler.browser.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']"))
                    )
                    
                    actions = ActionChains(self.handler.browser.driver)
                    for char in tweet:
                        actions.send_keys(char)
                        actions.pause(random.uniform(0.01, 0.05))
                    actions.perform()
                    await asyncio.sleep(2)
                    
                    # Click Post
                    post_button = WebDriverWait(self.handler.browser.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='tweetButton'][role='button']"))
                    )
                    post_button.click()
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Error adding tweet to thread: {e}")
                    return False
                    
            logger.info("Successfully posted thread")
            return True
            
        except Exception as e:
            logger.error(f"Error posting thread: {e}")
            return False
            
    def cleanup(self):
        """Clean up resources."""
        self._save_tweet_history()

    async def should_tweet(self):
        """Check if it's time to tweet based on the interval"""
        if not self.last_tweet_time:
            return True
            
        try:
            elapsed = (datetime.now() - self.last_tweet_time).total_seconds()
            should_tweet = elapsed >= (self.tweet_interval_minutes * 60)
            if not should_tweet:
                logger.info(f"Not time to tweet yet. {int((self.tweet_interval_minutes * 60 - elapsed) / 60)} minutes remaining.")
            return should_tweet
        except Exception as e:
            logger.error(f"Error checking tweet interval: {e}")
            return False

    async def process_auto_tweet(self):
        """Process automatic tweet if it's time"""
        try:
            if await self.should_tweet():
                tweet_content = await self.bob.generate_tweet()
                if tweet_content:
                    success = await self.post_tweet(tweet_content)
                    if success:
                        self.last_tweet_time = datetime.now()
                        logger.info(f"Posted auto-tweet: {tweet_content[:50]}...")
                    else:
                        logger.error("Failed to post auto-tweet")
                else:
                    logger.error("Failed to generate tweet content")

        except Exception as e:
            logger.error(f"Error in auto tweet process: {e}") 