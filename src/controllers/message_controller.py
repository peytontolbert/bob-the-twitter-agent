import logging
import asyncio
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class MessageController:
    def __init__(self, action_handler):
        self.handler = action_handler
        self.current_messages = []
        
    async def read_messages(self):
        """Read and analyze messages in the current conversation"""
        try:
            # Get all conversation cells
            cells = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='cellInnerDiv']"))
            )
            
            if not cells:
                logger.warning("No conversation cells found")
                return []

            messages = []
            
            # Process each cell
            for cell in cells:
                try:
                    # Skip system messages
                    if "You accepted the request" in cell.text or "Seen" in cell.text or "Sent" in cell.text:
                        continue
                        
                    # Try to get message entry
                    try:
                        msg = cell.find_element(By.CSS_SELECTOR, "[data-testid='messageEntry']")
                    except:
                        continue  # Skip cells without message entries
                        
                    text = msg.text.strip()
                    if not text:
                        continue
                        
                    # Get timestamp
                    try:
                        timestamp_elem = cell.find_element(By.XPATH, ".//time")
                        timestamp = timestamp_elem.get_attribute("datetime")
                        display_time = timestamp_elem.text
                    except:
                        timestamp = None
                        display_time = None
                    
                    # Message ownership detection based on message entry structure
                    entry_class = msg.get_attribute("class").lower()
                    entry_tag = msg.tag_name.lower()
                    
                    # Our messages are in a button element with r-obd0qt class
                    if entry_tag == "button" and "r-obd0qt" in entry_class:
                        is_from_us = True
                    # Their messages are in a div with r-1habvwh class
                    else:
                        is_from_us = False

                    messages.append({
                        'text': text,
                        'timestamp': timestamp,
                        'display_time': display_time,
                        'is_from_us': is_from_us
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue

            # Sort messages by timestamp if available
            messages.sort(key=lambda x: x['timestamp'] if x['timestamp'] else '')
            self.current_messages = messages
            return messages

        except Exception as e:
            logger.error(f"Error reading messages: {e}")
            return []

    async def send_message(self, text):
        """Send a message in the current conversation"""
        try:
            input_box = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='dmComposerTextInput']"))
            )
            input_box.click()
            input_box.send_keys(text)
            
            send_button = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='dmComposerSendButton']"))
            )
            send_button.click()
            
            await asyncio.sleep(1)  # Wait for message to send
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def get_recent_messages(self, num_messages=5):
        """Get the most recent messages"""
        return self.current_messages[-num_messages:] if self.current_messages else []

    def get_last_message(self):
        """Get the most recent message"""
        return self.current_messages[-1] if self.current_messages else None

    async def open_conversation(self, index=0):
        """Open a specific conversation by index"""
        try:
            conversation_selectors = [
                "[data-testid='conversation']",
                "[data-testid='cellInnerDiv']",
                "div[role='row']"
            ]

            for selector in conversation_selectors:
                try:
                    convs = WebDriverWait(self.handler.browser.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if convs and len(convs) > index:
                        convs[index].click()
                        await asyncio.sleep(1)
                        return True
                except Exception:
                    continue
                    
            logger.error("No conversations found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to open conversation: {e}")
            return False

    async def open_dms(self):
        """Navigate to DM section"""
        try:
            self.handler.browser.navigate("https://twitter.com/messages")
            await asyncio.sleep(2)  # Wait for page load
            return True
        except Exception as e:
            logger.error(f"Failed to open DMs: {e}")
            return False 