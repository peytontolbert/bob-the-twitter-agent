import logging
import asyncio
import random
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json

logger = logging.getLogger(__name__)

class MentionController:
    def __init__(self, handler, memory, bob):
        self.handler = handler
        self.memory = memory
        self.bob = bob
        self.logger = logging.getLogger(__name__)

    async def process_mentions(self):
        """Process mentions using tweet IDs as unique identifiers"""
        try:
            self.logger.info("\nProcessing mentions")
            
            # Navigate to mentions
            await self.navigate_to_mentions()
            
            # Get all mention tweets
            mentions = await self.get_mentions()
            if not mentions:
                self.logger.info("No mentions found")
                return True
                
            self.logger.info(f"Found {len(mentions)} mentions")
            
            # Process each mention
            for mention in mentions:
                try:
                    # Get tweet ID and handle from the element
                    tweet_id = await self.get_tweet_id(mention)
                    handle = await self.get_handle_from_mention(mention)
                    
                    if not tweet_id or not handle:
                        self.logger.debug("Could not get tweet ID or handle, skipping")
                        continue
                        
                    # Skip if we already replied to this tweet
                    if self.memory.has_replied_to_tweet(tweet_id):
                        self.logger.info(f"Already replied to tweet {tweet_id} from {handle}")
                        continue
                        
                    # Get tweet text
                    tweet_text = await self.get_tweet_text(mention)
                    if not tweet_text:
                        continue
                        
                    self.logger.info(f"Processing mention from {handle}: {tweet_text[:50]}...")
                    
                    # Generate and send reply
                    try:
                        reply = await self.bob.generate_response(
                            handle,
                            tweet_text,
                            context_type='mention'
                        )
                        
                        if reply:
                            self.logger.info(f"Generated reply: {reply[:50]}...")
                            if await self.reply_to_tweet(mention, reply):
                                self.logger.info("Successfully sent reply")
                                self.memory.add_tweet_reply(tweet_id)
                                # Store in memory
                                self.memory.add_mention(handle, {
                                    'tweet_id': tweet_id,
                                    'text': tweet_text,
                                    'reply': reply,
                                    'timestamp': time.time(),
                                    'is_from_us': False
                                })
                            else:
                                self.logger.error("Failed to send reply")
                        else:
                            self.logger.error("No reply generated")
                            
                    except Exception as e:
                        self.logger.error(f"Error generating/sending response: {str(e)}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing mention: {str(e)}")
                    continue
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing mentions: {str(e)}")
            return False

    async def get_tweet_id(self, mention):
        """Extract tweet ID from mention element"""
        try:
            links = mention.find_elements(By.CSS_SELECTOR, "a[href*='status']")
            for link in links:
                href = link.get_attribute('href')
                if href and 'status' in href:
                    return href.split('status/')[1].split('?')[0]
            return None
        except Exception as e:
            self.logger.error(f"Error getting tweet ID: {e}")
            return None

    async def get_tweet_text(self, mention):
        """Extract tweet text from mention element"""
        try:
            text_element = await self.find_element_in_element(mention, "[data-testid='tweetText']")
            if text_element:
                return text_element.text
            return None
        except Exception as e:
            self.logger.error(f"Error getting tweet text: {e}")
            return None

    async def navigate_to_mentions(self):
        """Navigate to the mentions page"""
        try:
            self.handler.browser.navigate("https://twitter.com/notifications/mentions")
            await asyncio.sleep(3)
            return True
        except Exception as e:
            self.logger.error(f"Error navigating to mentions: {e}")
            return False
            
    async def get_mentions(self):
        """Get all mentions"""
        try:
            tweet_selectors = [
                "[data-testid='tweet']",
                "article[role='article']",
                "[data-testid='cellInnerDiv']"
            ]
            
            mentions = []
            for selector in tweet_selectors:
                try:
                    self.logger.info(f"Trying selector: {selector}")
                    tweets = WebDriverWait(self.handler.browser.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if tweets:
                        mentions = tweets
                        self.logger.info(f"Found {len(tweets)} mentions using selector: {selector}")
                        break
                except Exception as e:
                    self.logger.error(f"Error with selector {selector}: {e}")
                    continue
                    
            return mentions
        except Exception as e:
            self.logger.error(f"Error getting mentions: {e}")
            return []
            
    async def reply_to_tweet(self, mention, reply_text):
        """Reply to a tweet using proven approach from debug_mentions"""
        try:
            # Find reply button
            reply_button = None
            reply_selectors = [
                "[data-testid='reply']",
                "[aria-label*='Reply']",
                "[role='button'][aria-label*='Reply']"
            ]
            
            for selector in reply_selectors:
                buttons = mention.find_elements(By.CSS_SELECTOR, selector)
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        reply_button = button
                        break
                if reply_button:
                    break
                        
            if not reply_button:
                self.logger.error("Could not find reply button")
                return False

            # Click reply button with multiple fallbacks
            try:
                self.handler.browser.driver.execute_script("arguments[0].scrollIntoView(true);", reply_button)
                await asyncio.sleep(1)
                
                self.handler.browser.driver.execute_script("arguments[0].click();", reply_button)
                await asyncio.sleep(1)
                
                # If JavaScript click didn't work, try regular click
                input_box = await self.wait_and_find_element("div[data-testid='tweetTextarea_0']", timeout=3)
                if not input_box:
                    actions = ActionChains(self.handler.browser.driver)
                    actions.move_to_element(reply_button)
                    actions.click()
                    actions.perform()
                    await asyncio.sleep(1)
                    
                # Type reply
                input_box = await self.wait_and_find_element(
                    "div[data-testid='tweetTextarea_0'][role='textbox']"
                )
                if not input_box:
                    return False
                    
                actions = ActionChains(self.handler.browser.driver)
                actions.move_to_element(input_box)
                actions.click()
                actions.perform()
                await asyncio.sleep(1)
                
                for char in reply_text:
                    actions = ActionChains(self.handler.browser.driver)
                    actions.send_keys(char)
                    actions.perform()
                    await asyncio.sleep(random.uniform(0.03, 0.1))
                    
                # Find and click post button
                post_button = await self.wait_and_find_element("div[data-testid='tweetButton']")
                if not post_button:
                    return False
                    
                self.handler.browser.driver.execute_script("arguments[0].click();", post_button)
                await asyncio.sleep(2)
                
                # Verify reply was sent
                textarea = self.handler.browser.driver.find_elements(
                    By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"
                )
                if not textarea:
                    return True
                    
                return False
                
            except Exception as e:
                self.logger.error(f"Error sending reply: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in reply_to_tweet: {e}")
            return False

    async def get_handle_from_mention(self, mention_element):
        """Extract handle from mention element"""
        try:
            handle_element = await self.find_element_in_element(
                mention_element,
                "[data-testid='User-Name']"
            )
            if handle_element:
                handle_text = handle_element.text
                # Extract handle from text (usually in format "Name @handle")
                if '@' in handle_text:
                    return '@' + handle_text.split('@')[1].split()[0]
            return None
        except Exception as e:
            self.logger.error(f"Error getting handle: {e}")
            return None

    async def find_element_in_element(self, parent_element, selector, timeout=5):
        """Find an element within another element using a CSS selector"""
        try:
            # First check if element exists directly
            elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                return elements[0]
                
            # If not found immediately, wait and try again
            start_time = time.time()
            while time.time() - start_time < timeout:
                elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return elements[0]
                await asyncio.sleep(0.5)
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding element with selector {selector}: {e}")
            return None

    async def wait_and_find_elements(self, selector, timeout=5):
        """Wait for and find all elements matching a CSS selector"""
        try:
            elements = WebDriverWait(self.handler.browser.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            return elements
        except Exception as e:
            self.logger.error(f"Error finding elements with selector {selector}: {e}")
            return []

    def load_replied_mentions(self):
        """Load previously replied mentions"""
        try:
            with open('data/replied_mentions.json', 'r') as f:
                return set(json.load(f))
        except:
            return set()

    def save_replied_mentions(self, mentions):
        """Save replied mentions"""
        with open('data/replied_mentions.json', 'w') as f:
            json.dump(list(mentions), f) 