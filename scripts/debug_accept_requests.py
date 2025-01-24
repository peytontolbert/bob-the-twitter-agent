import os
import sys
import logging
import asyncio
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agent.action_handler import ActionHandler

# Configure logging
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('message_requests.log')
    ]
)
logger = logging.getLogger(__name__)

async def get_message_requests(handler):
    """Get all message requests"""
    try:
        # Navigate to message requests
        logger.info("Navigating to message requests...")
        handler.browser.navigate("https://twitter.com/messages/requests")
        await asyncio.sleep(1)  # Reduced sleep time
        
        # Quick check for requests using the most reliable selector
        try:
            requests = await handler.wait_and_find_elements("[data-testid='conversation']", timeout=5)
            if not requests:
                logger.info("No message requests found")
                return []
        except:
            logger.info("No message requests found")
            return []

        logger.info(f"Found {len(requests)} message requests")
        
        # Process each request to get details
        request_details = []
        for req in requests:
            try:
                # Get sender (using most reliable selector first)
                sender = None
                elements = req.find_elements(By.CSS_SELECTOR, "[data-testid='conversationSender']")
                if elements:
                    for elem in elements:
                        text = elem.text.strip()
                        if text and '@' in text:
                            sender = text
                            break
                
                if not sender:
                    continue  # Skip if no sender found

                # Get preview (using most reliable selector)
                preview = None
                elements = req.find_elements(By.CSS_SELECTOR, "[data-testid='last-message']")
                if elements:
                    preview = elements[-1].text.strip()

                request_details.append({
                    "sender": sender,
                    "preview": preview or "No preview",
                    "element": req
                })
                logger.info(f"Found request from: {sender}")

            except Exception as e:
                logger.error(f"Error processing request: {e}")
                continue

        return request_details

    except Exception as e:
        logger.error(f"Error getting message requests: {e}")
        return []

async def accept_request(handler, request):
    """Accept a specific message request"""
    try:
        # Click to open request
        actions = ActionChains(handler.browser.driver)
        actions.move_to_element(request["element"])
        actions.click()
        actions.perform()
        await asyncio.sleep(2)

        # Try multiple selectors for accept button
        accept_selectors = [
            "span.css-1jxf684.r-bcqeeo.r-1ttztb7.r-qvutc0.r-poiln3",  # Direct span selector
            "button[role='button'][type='button'] span.css-1jxf684",    # Button > span
            "button[type='button'] div[dir='ltr'] span.css-1jxf684",    # Button > div > span
            "button[role='button'] div[dir='ltr'] span.r-poiln3"        # Using one of the unique classes
        ]
        
        accept_button = None
        for selector in accept_selectors:
            try:
                elements = handler.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and "Accept" in element.text:
                        # Get the parent button element
                        accept_button = element
                        while accept_button.tag_name != "button":
                            accept_button = accept_button.find_element(By.XPATH, "./..")
                        break
                if accept_button:
                    break
            except:
                continue

        if accept_button:
            # Click accept button
            handler.browser.driver.execute_script("arguments[0].click();", accept_button)
            await asyncio.sleep(2)
            logger.info(f"Accepted request from {request['sender']}")
            return True
        else:
            logger.error(f"Could not find accept button for {request['sender']}")
            return False

    except Exception as e:
        logger.error(f"Error accepting request from {request['sender']}: {e}")
        return False

async def return_to_requests(handler):
    """Return to the message requests list"""
    try:
        back_button = WebDriverWait(handler.browser.driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='DM_Timeline_Back']"))
        )
        
        actions = ActionChains(handler.browser.driver)
        actions.move_to_element(back_button)
        actions.click()
        actions.perform()
        await asyncio.sleep(2)
        return True
    except:
        # Try to recover by navigating directly
        try:
            handler.browser.navigate("https://twitter.com/messages/requests")
            await asyncio.sleep(3)
            return True
        except:
            return False

async def main():
    """Main function to process message requests"""
    handler = None
    try:
        # Initialize handler and login
        handler = ActionHandler(headless=False)
        if not await handler.ensure_logged_in():
            logger.error("Failed to log in")
            return

        # Get message requests
        requests = await get_message_requests(handler)
        
        if not requests:
            logger.info("No message requests to process")
            return

        # Process each request
        for request in requests:
            # Accept the request
            success = await accept_request(handler, request)
            if success:
                logger.info(f"Successfully accepted request from {request['sender']}")
            else:
                logger.error(f"Failed to accept request from {request['sender']}")
            
            # Return to requests list
            await return_to_requests(handler)
            await asyncio.sleep(2)

    except KeyboardInterrupt:
        logger.info("\nScript stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if handler:
            handler.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nScript stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}") 