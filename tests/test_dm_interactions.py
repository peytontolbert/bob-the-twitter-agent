import pytest
import asyncio
import os
import sys
from pathlib import Path
import time
from contextlib import asynccontextmanager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import random

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler

@pytest.fixture
async def action_handler():
    """Setup and teardown for ActionHandler"""
    handler = ActionHandler(headless=False)  # Set to True for headless testing
    try:
        yield handler
    finally:
        handler.cleanup()
# @pytest.mark.asyncio
# async def test_login():
#     """Test basic login functionality"""
#     handler = None
#     try:
#         # First test: Fresh login
#         handler = ActionHandler(headless=False)
#         is_logged_in = await handler.ensure_logged_in()
#         assert is_logged_in, "Should successfully log in"
#         assert handler.is_logged_in, "Should be marked as logged in"
#         
#         # Save session and properly cleanup
#         assert handler._save_session(), "Should save session successfully"
#         handler.cleanup()
#         handler = None
#         
#         # Test session persistence with new handler
#         handler = ActionHandler(headless=False)
#         assert handler._load_session(), "Should load saved session"
#         await asyncio.sleep(3)  # Wait for session to be applied
#         
#         # Navigate to home and verify login state
#         handler.browser.navigate("https://twitter.com/home")
#         await asyncio.sleep(3)  # Wait for navigation
#         
#         is_still_logged = handler.check_login_state()
#         assert is_still_logged, "Should still be logged in after session load"
#         
#     finally:
#         if handler:
#             handler.cleanup()
#             # End of Selection

@pytest.mark.asyncio
async def test_load_dms():
    """Test loading DM messages"""
    handler = ActionHandler(headless=False)
    try:
        # Ensure logged in first
        is_logged_in = await handler.ensure_logged_in()
        assert is_logged_in, "Should be logged in before checking DMs"
        
        # Navigate to messages
        handler.browser.navigate("https://twitter.com/messages")
        await asyncio.sleep(3)  # Wait for page load
        await handler.handle_notifications()
        
        # Get all conversations
        conversations = WebDriverWait(handler.browser.driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='conversation']"))
        )
        
        print(f"\nFound {len(conversations)} conversations")
        
        # Process each conversation
        for i, conv in enumerate(conversations, 1):
            try:
                # Create ActionChains for hover
                actions = ActionChains(handler.browser.driver)
                actions.move_to_element(conv)
                actions.pause(random.uniform(0.5, 1.0))  # Random pause while hovering
                actions.perform()
                await asyncio.sleep(0.5)
                
                # Try multiple selectors for sender and preview
                sender_selectors = [
                    "[data-testid='conversationSender']",
                    "[data-testid='User-Name']",
                    "[data-testid='DMConversationEntry-UserName']",
                    "span[dir='ltr']"
                ]
                
                preview_selectors = [
                    "[data-testid='messagePreview']",
                    "[data-testid='messageEntry']",
                    "[data-testid='DMConversationEntry-Preview']"
                ]
                
                # Try to find sender
                sender = "Unknown"
                for selector in sender_selectors:
                    try:
                        sender_elem = conv.find_element(By.CSS_SELECTOR, selector)
                        if sender_elem and sender_elem.text.strip():
                            sender = sender_elem.text.strip()
                            break
                    except:
                        continue
                
                # Try to find preview
                preview = "No preview"
                for selector in preview_selectors:
                    try:
                        preview_elem = conv.find_element(By.CSS_SELECTOR, selector)
                        if preview_elem and preview_elem.text.strip():
                            preview = preview_elem.text.strip()
                            break
                    except:
                        continue
                
                print(f"\nConversation {i}:")
                print(f"From: {sender}")
                print(f"Preview: {preview}")
                
                # Click to open conversation using ActionChains
                actions = ActionChains(handler.browser.driver)
                actions.click(conv)
                actions.perform()
                await asyncio.sleep(2)
                
                # Get all messages in the conversation
                messages = WebDriverWait(handler.browser.driver, 5).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='messageEntry']"))
                )
                
                # Check last message
                if messages:
                    last_message = messages[-1]
                    is_from_us = "sent" in last_message.get_attribute("class").lower()
                    print(f"Last message was {'from us' if is_from_us else 'from them'}")
                    print(f"Message count: {len(messages)}")
                
                # Find and click back button
                back_button = WebDriverWait(handler.browser.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='DM_Timeline_Back']"))
                )
                
                # Hover and click back button
                actions = ActionChains(handler.browser.driver)
                actions.move_to_element(back_button)
                actions.pause(random.uniform(0.3, 0.7))
                actions.click()
                actions.perform()
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error processing conversation: {e}")
                # Try to go back to messages list if we're stuck
                try:
                    back_button = WebDriverWait(handler.browser.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='DM_Timeline_Back']"))
                    )
                    back_button.click()
                    await asyncio.sleep(1)
                except:
                    # If we can't find back button, navigate directly to messages
                    handler.browser.navigate("https://twitter.com/messages")
                    await asyncio.sleep(2)
                continue
            
    except Exception as e:
        pytest.fail(f"Test failed: {e}")
    finally:
        handler.cleanup()

@pytest.mark.asyncio
async def test_dm_monitoring():
    """Test continuous monitoring of DMs"""
    handler = ActionHandler(headless=False)
    try:
        # Ensure logged in first
        is_logged_in = await handler.ensure_logged_in()
        assert is_logged_in, "Should be logged in before checking DMs"
        
        print("\nMonitoring DMs for 30 seconds...")
        start_time = time.time()
        check_interval = 5  # Check every 5 seconds
        
        while time.time() - start_time < 30:
            messages = await handler.check_dms()
            if messages:
                print(f"\nFound {len(messages)} new messages:")
                for msg in messages:
                    print(f"From: {msg['sender']}")
                    print(f"Preview: {msg['preview']}")
                    
                    # Try to reply to each new message
                    msg["thread_element"].click()
                    await asyncio.sleep(1)
                    
                    reply = f"Hi {msg['sender'].split('@')[0]}! Bob the Builder here. I noticed your message about: {msg['preview'][:30]}..."
                    success = await handler.reply_to_dm(reply)
                    if success:
                        print(f"Replied to {msg['sender']}")
                    
                    await asyncio.sleep(1)
            
            await asyncio.sleep(check_interval)
            print(".", end="", flush=True)  # Progress indicator
            
    except Exception as e:
        pytest.fail(f"Test failed: {e}")
    finally:
        handler.cleanup()
# @pytest.mark.asyncio
# async def test_post_tweet():
#     """Test posting a tweet"""
#     handler = ActionHandler(headless=False)
#     try:
#         # Ensure logged in first
#         is_logged_in = await handler.ensure_logged_in()
#         assert is_logged_in, "Should be logged in before posting tweet"
        
#         # Create a test tweet with timestamp
#         test_tweet = " Bob the Builder - Can we fix it? Yes we can!"
        
#         # Post the tweet
#         success = await handler.post_tweet(test_tweet)
#         assert success, "Should successfully post tweet"
        
#         # Wait for tweet to be posted
#         await asyncio.sleep(3)
        
#     except Exception as e:
#         pytest.fail(f"Test failed: {e}")
#     finally:
#         handler.cleanup()

@pytest.mark.asyncio
async def test_message_requests():
    """Test handling message requests"""
    handler = ActionHandler(headless=False)
    try:
        # Ensure logged in first
        is_logged_in = await handler.ensure_logged_in()
        assert is_logged_in, "Should be logged in before checking message requests"
        
        # Check for message requests
        requests = await handler.check_message_requests()
        
        # Verify we got a list (even if empty)
        assert isinstance(requests, list), "Should return a list of message requests"
        
        # Print request count
        print(f"\nFound {len(requests)} message requests")
        
        # If we have requests, verify their structure and process them
        for i, req in enumerate(requests, 1):
            print(f"\nRequest {i}:")
            assert "sender" in req, "Request should have a sender"
            assert "preview" in req, "Request should have a preview"
            assert "thread_element" in req, "Request should have thread element"
            print(f"From: {req['sender']}")
            print(f"Preview: {req['preview']}")
            
            # Try to accept the request
            success = await handler.accept_message_request(req["thread_element"])
            if success:
                print(f"Successfully accepted request from {req['sender']}")
            else:
                print(f"Failed to accept request from {req['sender']}")
            
            await asyncio.sleep(2)  # Wait before checking next request
            
    except Exception as e:
        pytest.fail(f"Test failed: {e}")
    finally:
        handler.cleanup()

@pytest.mark.asyncio
async def test_message_request_monitoring():
    """Test continuous monitoring of message requests"""
    handler = ActionHandler(headless=False)
    try:
        # Ensure logged in first
        is_logged_in = await handler.ensure_logged_in()
        assert is_logged_in, "Should be logged in before checking message requests"
        
        print("\nMonitoring message requests for 30 seconds...")
        start_time = time.time()
        check_interval = 5  # Check every 5 seconds
        
        while time.time() - start_time < 30:
            await handler.process_message_requests()  # This will check, accept, and reply to requests
            await asyncio.sleep(check_interval)
            print(".", end="", flush=True)  # Progress indicator
            
    except Exception as e:
        pytest.fail(f"Test failed: {e}")
    finally:
        handler.cleanup()

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 