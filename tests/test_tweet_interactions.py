import pytest
import asyncio
import os
import sys
import logging
from pathlib import Path
import time
from selenium.webdriver.common.by import By

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler
# @pytest.mark.asyncio
# async def test_post_tweet():
#     """Test posting a tweet"""
#     handler = ActionHandler(headless=False)
#     try:
#         # Ensure logged in first
#         is_logged_in = await handler.ensure_logged_in()
#         assert is_logged_in, "Should be logged in before posting tweet"
#         
#         # Create a test tweet with timestamp
#         timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
#         test_tweet = f"Bob the Builder test tweet - Can we fix it? Yes we can! ({timestamp})"
#         
#         # Post the tweet
#         success = await handler.post_tweet(test_tweet)
#         assert success, "Should successfully post tweet"
#         
#         # Wait for tweet to be posted
#         await asyncio.sleep(3)
#         
#     except Exception as e:
#         pytest.fail(f"Test failed: {e}")
#     finally:
#         handler.cleanup()

# Set up logging
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_process_mentions():
    """Test processing mentions"""
    handler = ActionHandler(headless=False)
    try:
        # Ensure logged in first
        is_logged_in = await handler.ensure_logged_in()
        assert is_logged_in, "Should be logged in before checking mentions"
        
        # Process mentions
        success = await handler.process_mentions()
        assert success, "Should successfully process mentions"
        
        # Check that we got mentions list
        mentions = await handler.check_mentions()
        assert isinstance(mentions, list), "Should return a list of mentions"
        
        # If we have mentions, verify their structure
        for mention in mentions:
            assert "username" in mention, "Mention should have username"
            assert "text" in mention, "Mention should have text"
            assert "tweet_element" in mention, "Mention should have tweet element"
        
    except Exception as e:
        pytest.fail(f"Test failed: {e}")
    finally:
        handler.cleanup()

@pytest.mark.asyncio
async def test_check_mentions_ids():
    """Test checking mentions and verifying tweet IDs"""
    handler = ActionHandler(headless=False)
    try:
        # Ensure logged in first
        is_logged_in = await handler.ensure_logged_in()
        assert is_logged_in, "Should be logged in before checking mentions"
        
        # Get mentions
        mentions = await handler.check_mentions()
        assert isinstance(mentions, list), "Should return a list of mentions"
        
        if mentions:
            logger.info(f"Found {len(mentions)} mentions")
            for mention in mentions:
                # Get all attributes of the tweet element
                tweet_element = mention["tweet_element"]
                logger.info("\nRaw tweet element attributes:")
                logger.info("---------------------------")
                
                # Print the element's HTML and attributes
                logger.info("Tweet element HTML:")
                logger.info(tweet_element.get_attribute('outerHTML'))
                logger.info("\nTweet element attributes:")
                logger.info(f"- tag name: {tweet_element.tag_name}")
                logger.info(f"- class: {tweet_element.get_attribute('class')}")
                logger.info(f"- data-testid: {tweet_element.get_attribute('data-testid')}")
                
                # Try to find any links that might contain the tweet ID
                links = tweet_element.find_elements(By.TAG_NAME, "a")
                logger.info("\nAll links in tweet:")
                for link in links:
                    href = link.get_attribute('href')
                    if href:
                        logger.info(f"- href: {href}")
                        if 'status' in href:
                            # Extract tweet ID from status URL
                            try:
                                tweet_id = href.split('status/')[1].split('?')[0]
                                logger.info(f"Found tweet ID from status link: {tweet_id}")
                            except:
                                pass
                
                logger.info("---------------------------")
                
                # Print other mention details
                logger.info(f"Current mention data:")
                logger.info(f"- Username: {mention['username']}")
                logger.info(f"- Text: {mention['text'][:50]}...")
                if 'tweet_id' in mention:
                    logger.info(f"- Current tweet_id: {mention['tweet_id']}")
                
    except Exception as e:
        logger.error(f"Error in test: {e}")
        pytest.fail(f"Test failed: {e}")
    finally:
        handler.cleanup()

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 