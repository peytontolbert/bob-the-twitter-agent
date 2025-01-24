import asyncio
import os
import sys
import logging
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import random
import json

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_mentions.log')
    ]
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler

def load_replied_mentions():
    """Load previously replied mentions"""
    try:
        with open('data/replied_mentions.json', 'r') as f:
            return set(json.load(f))
    except:
        return set()

def save_replied_mentions(mentions):
    """Save replied mentions"""
    with open('data/replied_mentions.json', 'w') as f:
        json.dump(list(mentions), f)

async def debug_mentions():
    """Debug script to test mention handling with detailed logging"""
    handler = None
    try:
        handler = ActionHandler(headless=False)
        replied_mentions = load_replied_mentions()
        
        # Login check
        logger.info("Checking login state...")
        is_logged_in = await handler.ensure_logged_in()
        if not is_logged_in:
            logger.error("Failed to log in")
            return
            
        # Navigate to mentions
        logger.info("\nNavigating to mentions...")
        handler.browser.navigate("https://twitter.com/notifications/mentions")
        await asyncio.sleep(3)
        
        # Handle any notifications
        await handler.handle_notifications()
        
        # Find all mention tweets
        logger.info("\nLooking for mentions...")
        tweet_selectors = [
            "[data-testid='tweet']",
            "article[role='article']",
            "[data-testid='cellInnerDiv']"
        ]
        
        mentions = []
        for selector in tweet_selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                tweets = WebDriverWait(handler.browser.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                )
                if tweets:
                    mentions = tweets
                    logger.info(f"Found {len(tweets)} mentions using selector: {selector}")
                    
                    # Log each mention's details to help debug
                    for i, tweet in enumerate(tweets):
                        try:
                            logger.info(f"\nAnalyzing mention {i+1}:")
                            
                            # Try to get tweet ID
                            links = tweet.find_elements(By.CSS_SELECTOR, "a[href*='status']")
                            tweet_id = None
                            for link in links:
                                href = link.get_attribute('href')
                                if href and 'status' in href:
                                    tweet_id = href.split('status/')[1].split('?')[0]
                                    break
                            
                            if tweet_id:
                                logger.info(f"Tweet ID: {tweet_id}")
                                logger.info(f"Already replied: {tweet_id in replied_mentions}")
                                
                                # Try to find reply button to verify it's replyable
                                reply_buttons = tweet.find_elements(By.CSS_SELECTOR, "[data-testid='reply']")
                                logger.info(f"Reply buttons found: {len(reply_buttons)}")
                                
                                # Log the tweet text if possible
                                try:
                                    tweet_text = tweet.find_element(By.CSS_SELECTOR, "[data-testid='tweetText']").text
                                    logger.info(f"Tweet text: {tweet_text[:100]}...")
                                except:
                                    logger.info("Could not find tweet text")
                            else:
                                logger.info("Could not find tweet ID")
                        except Exception as e:
                            logger.error(f"Error analyzing mention {i+1}: {e}")
                    break
            except Exception as e:
                logger.error(f"Error with selector {selector}: {e}")
                continue
                
        if not mentions:
            logger.error("No mentions found")
            return
            
        # Process first unreplied mention for testing
        logger.info("\nProcessing first unreplied mention...")
        for mention in mentions:
            try:
                # Get tweet ID
                tweet_id = None
                links = mention.find_elements(By.CSS_SELECTOR, "a[href*='status']")
                for link in links:
                    href = link.get_attribute('href')
                    if href and 'status' in href:
                        tweet_id = href.split('status/')[1].split('?')[0]
                        break
                        
                if not tweet_id:
                    logger.warning("Could not find tweet ID, skipping...")
                    continue
                    
                if tweet_id in replied_mentions:
                    logger.info(f"Already replied to tweet {tweet_id}, skipping...")
                    continue
                
                # Find reply button
                logger.info("Looking for reply button...")
                reply_button = None
                reply_selectors = [
                    "[data-testid='reply']",
                    "[aria-label*='Reply']",
                    "[role='button'][aria-label*='Reply']"
                ]
                
                for selector in reply_selectors:
                    try:
                        buttons = mention.find_elements(By.CSS_SELECTOR, selector)
                        for button in buttons:
                            if button.is_displayed() and button.is_enabled():
                                reply_button = button
                                logger.info(f"Found reply button with selector: {selector}")
                                break
                        if reply_button:
                            break
                    except:
                        continue
                        
                if not reply_button:
                    logger.error("Could not find reply button")
                    continue
                    
                # Click reply button
                logger.info("Clicking reply button...")
                try:
                    # First scroll the button into view
                    handler.browser.driver.execute_script("arguments[0].scrollIntoView(true);", reply_button)
                    await asyncio.sleep(1)
                    
                    # Try clicking with JavaScript first
                    handler.browser.driver.execute_script("arguments[0].click();", reply_button)
                    await asyncio.sleep(1)
                    
                    # If JavaScript click didn't work, try regular click
                    if not WebDriverWait(handler.browser.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']"))
                    ):
                        actions = ActionChains(handler.browser.driver)
                        actions.move_to_element(reply_button)
                        actions.pause(random.uniform(0.3, 0.7))
                        actions.click()
                        actions.perform()
                except Exception as e:
                    logger.error(f"Error clicking reply button: {e}")
                    continue
                    
                await asyncio.sleep(2)
                
                # Find tweet input
                logger.info("Looking for tweet input...")
                input_box = WebDriverWait(handler.browser.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        "div[data-testid='tweetTextarea_0'][role='textbox']"))
                )
                
                # Type reply
                reply_text = "Hi! I'm Bob the Builder, an AI assistant who loves to help people build things! How can I help you today?"
                logger.info(f"Typing reply: {reply_text}")
                
                actions = ActionChains(handler.browser.driver)
                actions.move_to_element(input_box)
                actions.click()
                actions.perform()
                await asyncio.sleep(1)
                
                for char in reply_text:
                    actions = ActionChains(handler.browser.driver)
                    actions.send_keys(char)
                    actions.perform()
                    await asyncio.sleep(random.uniform(0.03, 0.1))
                    
                # Find post button
                logger.info("Looking for post button...")
                post_button = None
                post_selectors = [
                    "button[data-testid='tweetButton']",
                    "button[role='button'][data-testid='tweetButton']",
                    "div[role='button'][data-testid='tweetButton']"
                ]
                
                for selector in post_selectors:
                    try:
                        post_button = WebDriverWait(handler.browser.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"Found post button with selector: {selector}")
                        break
                    except:
                        continue
                
                if not post_button:
                    logger.error("Could not find post button")
                    continue
                
                # Click post button
                logger.info("Clicking post button...")
                try:
                    # First scroll the button into view
                    handler.browser.driver.execute_script("arguments[0].scrollIntoView(true);", post_button)
                    await asyncio.sleep(1)
                    
                    # Try clicking with JavaScript first
                    handler.browser.driver.execute_script("arguments[0].click();", post_button)
                    logger.info("Attempted JavaScript click")
                    await asyncio.sleep(2)
                    
                    # Save mention right after clicking post button
                    replied_mentions.add(tweet_id)
                    save_replied_mentions(replied_mentions)
                    logger.info(f"Added tweet {tweet_id} to replied mentions")
                    logger.info(f"Total replied mentions: {len(replied_mentions)}")
                    
                    # If JavaScript click didn't work, try ActionChains
                    if post_button.is_displayed():
                        logger.info("JavaScript click failed, trying ActionChains...")
                        actions = ActionChains(handler.browser.driver)
                        actions.move_to_element(post_button)
                        actions.pause(random.uniform(0.3, 0.7))
                        actions.click()
                        actions.perform()
                        logger.info("Attempted ActionChains click")
                        await asyncio.sleep(1)
                        
                        # If ActionChains failed, try direct click
                        if post_button.is_displayed():
                            logger.info("ActionChains failed, trying direct click...")
                            post_button.click()
                            logger.info("Attempted direct click")
                            
                except Exception as e:
                    logger.error(f"Error clicking post button: {e}")
                    continue
                
                await asyncio.sleep(2)
                
                # Verify the reply was sent
                try:
                    # Check if the tweet textarea is gone (indicating successful send)
                    textarea = handler.browser.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']")
                    if not textarea:
                        logger.info("Reply sent successfully")
                        logger.info(f"Successfully verified reply to tweet {tweet_id}")
                        break
                    else:
                        logger.error("Reply may not have been sent - textarea still present")
                        # Try to get error message if any
                        try:
                            error_messages = handler.browser.driver.find_elements(By.CSS_SELECTOR, "[data-testid='toast']")
                            if error_messages:
                                for error in error_messages:
                                    logger.error(f"Error toast found: {error.text}")
                        except:
                            pass
                except Exception as e:
                    logger.error(f"Error verifying reply: {e}")
                    
                # Log final status of the attempt
                logger.info(f"Finished processing tweet {tweet_id}")
                
            except Exception as e:
                logger.error(f"Error processing mention: {e}")
                continue
                
        logger.info("\nDebug mentions completed")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if handler:
            try:
                handler.cleanup()
                logger.info("Successfully cleaned up resources")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(debug_mentions())
    except KeyboardInterrupt:
        logger.info("\nScript stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}") 