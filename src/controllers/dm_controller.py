import logging
import asyncio
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

logger = logging.getLogger(__name__)

class DMController:
    def __init__(self, action_handler):
        self.handler = action_handler
        self.current_conversation = None
        self._is_closed = False
        
    async def cleanup(self):
        """Clean up resources and close sessions"""
        if self._is_closed:
            return
            
        try:
            if self.handler and self.handler.browser and self.handler.browser.driver:
                # Quit the driver first
                self.handler.browser.driver.quit()
                # Clear the driver reference
                self.handler.browser.driver = None
                logger.info("Browser session cleaned up")
                
            self._is_closed = True
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

    def __del__(self):
        """Destructor to ensure cleanup"""
        if not self._is_closed:
            asyncio.create_task(self.cleanup())

    async def open_dms(self):
        """Navigate to DM section"""
        try:
            self.handler.browser.navigate("https://twitter.com/messages")
            await asyncio.sleep(2)  # Wait for page load
            return True
        except Exception as e:
            logger.error(f"Failed to open DMs: {e}")
            return False
            
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

    async def read_conversation(self):
        """Read and analyze the current conversation"""
        try:
            msgs = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='messageEntry']"))
            )
            
            if not msgs:
                logger.warning("No messages found in conversation")
                return []

            messages = []
            
            for msg in msgs:
                try:
                    text = msg.text.strip()
                    if not text:
                        continue
                        
                    # Get timestamp
                    try:
                        timestamp_elem = msg.find_element(By.XPATH, "./ancestor::article//time")
                        timestamp = datetime.fromisoformat(timestamp_elem.get_attribute("datetime").replace('Z', '+00:00'))
                    except:
                        timestamp = None
                    
                    # Check message ownership
                    msg_class = msg.get_attribute("class").lower()
                    is_from_us = False
                    ownership_signals = []

                    # Direct class checks
                    ownership_classes = ["obd0qt", "r-obd0qt"]
                    for cls in ownership_classes:
                        if cls in msg_class:
                            is_from_us = True
                            ownership_signals.append(f"direct_class_{cls}")
                    
                    # Parent class checks
                    try:
                        parent = msg.find_element(By.XPATH, "./..")
                        parent_class = parent.get_attribute("class").lower()
                        for cls in ownership_classes:
                            if cls in parent_class:
                                is_from_us = True
                                ownership_signals.append(f"parent_class_{cls}")
                    except:
                        pass

                    # Bob's signature phrases
                    bob_phrases = ["bob the builder", "i'm bob", "i am bob"]
                    text_lower = text.lower()
                    for phrase in bob_phrases:
                        if phrase in text_lower:
                            is_from_us = True
                            ownership_signals.append(f"signature_phrase_{phrase}")

                    # Message alignment
                    try:
                        style = msg.get_attribute("style")
                        if style and "margin-left: auto" in style:
                            is_from_us = True
                            ownership_signals.append("right_aligned")
                    except:
                        pass

                    messages.append({
                        'text': text,
                        'timestamp': timestamp,
                        'is_from_us': is_from_us,
                        'ownership_signals': ownership_signals
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue

            # Sort by timestamp
            messages.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min)
            self.current_conversation = messages
            return messages

        except Exception as e:
            logger.error(f"Error reading conversation: {e}")
            return []

    async def send_message(self, text):
        """Send a message in the current conversation"""
        try:
            # Find and click the message input
            input_box = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='dmComposerTextInput']"))
            )
            input_box.click()
            input_box.send_keys(text)
            
            # Find and click the send button
            send_button = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='dmComposerSendButton']"))
            )
            send_button.click()
            
            await asyncio.sleep(1)  # Wait for message to send
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def get_conversation_context(self, num_messages=5):
        """Get the most recent messages for context"""
        if not self.current_conversation:
            return []
        return self.current_conversation[-num_messages:]

    def get_last_message(self):
        """Get the most recent message"""
        if not self.current_conversation:
            return None
        return self.current_conversation[-1] 