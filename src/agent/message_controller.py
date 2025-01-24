import logging
import asyncio
import random
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import List, Dict
import time
from .conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)

class MessageController:
    def __init__(self, handler, memory, bob):
        self.handler = handler
        self.memory = memory
        self.bob = bob  # Store Bob instance for generating replies
        self.logger = logging.getLogger(__name__)
        self.current_handle = None  # Track current conversation handle
        
    async def get_conversations(self):
        """Get all conversations and map them to handles"""
        try:
            # Wait for conversations to load
            await asyncio.sleep(2)
            
            # First try to get conversation elements
            conversations = await self.wait_and_find_elements("[data-testid='conversation']", timeout=5)
            if not conversations:
                self.logger.info("No conversations found with primary selector")
                # Fallback to cell divs
                conversations = await self.wait_and_find_elements("[data-testid='cellInnerDiv']", timeout=5)
                
            if not conversations:
                self.logger.info("No conversations found")
                return {}
                
            conversations = conversations[:10]  # Limit to 10 conversations
            self.logger.info(f"Found {len(conversations)} conversation elements")
                
            # Map conversations to handles
            handle_map = {}
            for conv in conversations:
                try:
                    # First try conversation name
                    sender_elem = await self.find_element_in_element(conv, "[data-testid='conversation-name']")
                    if not sender_elem:
                        # Try user name
                        sender_elem = await self.find_element_in_element(conv, "[data-testid='User-Name']")
                    if not sender_elem:
                        # Try any text element
                        sender_elem = await self.find_element_in_element(conv, "div[dir='ltr']")
                        
                    if sender_elem:
                        handle = sender_elem.text.strip()
                        # Ensure handle starts with @ and has no spaces
                        if handle and ' ' not in handle:
                            if not handle.startswith('@'):
                                handle = f'@{handle}'
                            handle_map[handle] = conv
                            self.logger.info(f"Found conversation with {handle}")
                            
                except Exception as e:
                    self.logger.debug(f"Error getting handle from conversation: {e}")
                    continue
                    
            self.logger.info(f"Mapped {len(handle_map)} conversations to handles")
            return handle_map
                    
        except Exception as e:
            self.logger.error(f"Error getting conversations: {e}")
            return {}

    async def get_conversation_details(self, conv):
        """Get details of a conversation including sender, preview and timestamp"""
        try:
            # Try to get sender name/handle
            sender_selectors = [
                "[data-testid='conversationSender']",
                "[data-testid='User-Name']",
                "[data-testid='DMConversationEntry-UserName']",
                "div[dir='ltr']",
                "span[dir='ltr']"
            ]
            
            sender = None
            for selector in sender_selectors:
                try:
                    elements = conv.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and '@' in text:  # Look for username format
                            sender = text
                            break
                    if sender:
                        break
                except:
                    continue

            # Try to get last message preview
            preview_selectors = [
                "[data-testid='last-message']",
                "[data-testid='messageEntry']",
                "div[data-testid='dmConversationMessage']"
            ]
            
            preview = None
            for selector in preview_selectors:
                try:
                    elements = conv.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        preview = elements[-1].text.strip()
                        break
                except:
                    continue

            # Try to get timestamp
            time_selectors = [
                "[data-testid='timestamp']",
                "time",
                "span[data-testid='timestamp']"
            ]
            
            timestamp = None
            for selector in time_selectors:
                try:
                    elements = conv.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        timestamp = elements[-1].text.strip()
                        break
                except:
                    continue

            # Return all details
            return {
                'sender': sender or 'Unknown',
                'preview': preview or 'No preview',
                'timestamp': timestamp or 'Unknown',
                'element': conv  # Keep the element reference for clicking
            }

        except Exception as e:
            self.logger.error(f"Error getting conversation details: {e}")
            return None

    async def process_dms(self, memory=None):
        """Process DMs using the proven debug_conversations.py pipeline."""
        try:
            self.logger.info("\nStarting DM processing")
            
            # Configure logging - only show INFO and above for selenium
            selenium_logger = logging.getLogger('selenium')
            selenium_logger.setLevel(logging.WARNING)
            urllib3_logger = logging.getLogger('urllib3')
            urllib3_logger.setLevel(logging.WARNING)
            
            # Step 1: Navigate to messages
            self.handler.browser.navigate("https://twitter.com/messages")
            await asyncio.sleep(2)
            
            # Step 2: Get DM previews with proven approach
            dm_previews = await self.get_conversations()
            if not dm_previews:
                self.logger.info("No DM conversations found")
                return True
            
            # Convert to list to avoid modification during iteration
            conversations = list(dm_previews.items())
            
            # Step 3: Process each conversation
            for i, (handle, conv_element) in enumerate(conversations, 1):
                try:
                    self.logger.info(f"\nProcessing conversation {i}/{len(conversations)} with {handle}")
                    
                    # Open conversation using proven approach
                    actions = ActionChains(self.handler.browser.driver)
                    actions.move_to_element(conv_element)
                    actions.click()
                    actions.perform()
                    await asyncio.sleep(2)
                    
                    # Get conversation details using proven approach
                    messages = await self.get_current_conversation_details()
                    if not messages:
                        self.logger.info("No messages found")
                        continue
                    
                    self.logger.info(f"Retrieved {len(messages)} messages")
                    
                    # Check if last message is from them
                    last_message = messages[-1]
                    if not last_message.get('is_from_us', False):
                        self.logger.info(f"Found unreplied message: {last_message['text']}")
                        
                        try:
                            # Generate and send reply
                            reply = await self.bob.generate_response(
                                handle,
                                last_message['text'],
                                context_type='dm'
                            )
                            
                            if reply:
                                self.logger.info(f"Generated reply: {reply[:50]}...")
                                if await self.send_message(reply):
                                    self.logger.info("Successfully sent reply")
                                    if memory:
                                        memory.add_dm(handle, {
                                            'text': reply,
                                            'timestamp': time.time(),
                                            'from_us': True
                                        })
                                else:
                                    self.logger.error("Failed to send reply")
                            else:
                                self.logger.error("No reply generated")
                                
                        except Exception as e:
                            self.logger.error(f"Error generating/sending response: {str(e)}")
                            
                    else:
                        self.logger.info("Last message was from us - no reply needed")
                
                except Exception as e:
                    self.logger.error(f"Error processing conversation: {str(e)}")
                    continue
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error in process_dms: {str(e)}")
            return False

    async def get_current_conversation_details(self):
        """Get conversation details using proven approach from debug_conversations.py"""
        try:
            # Get all message cells
            cells = await self.wait_and_find_elements("[data-testid='cellInnerDiv']", timeout=5)
            if not cells:
                return []
            
            messages = []
            seen_texts = set()
            
            self.logger.info(f"\nProcessing {len(cells)} message cells:")
            self.logger.info("-" * 40)
            
            # Process cells in normal order (oldest to newest)
            for i, cell in enumerate(cells):
                try:
                    # Get message entry first
                    msg = await self.find_element_in_element(cell, "[data-testid='messageEntry']")
                    if not msg:
                        # If no message entry, check if it's a system message
                        cell_text = cell.text.lower()
                        if any(skip in cell_text for skip in ["you accepted", "seen", "sent"]):
                            self.logger.debug(f"Skipping system notification: {cell_text[:30]}...")
                        continue
                    
                    text = msg.text.strip()
                    if not text or text in seen_texts:
                        continue
                    
                    # Clean up text
                    text_parts = text.split('\n')
                    clean_text = text_parts[0]
                    seen_texts.add(clean_text)
                    
                    # Check ownership - our messages have r-obd0qt class
                    msg_class = msg.get_attribute("class") or ""
                    is_from_us = "r-obd0qt" in msg_class
                    
                    # Add more detailed logging for ownership detection
                    self.logger.debug(f"Message ownership check:")
                    self.logger.debug(f"  Text: {clean_text[:50]}...")
                    self.logger.debug(f"  Class: {msg_class}")
                    self.logger.debug(f"  Contains r-obd0qt: {'r-obd0qt' in msg_class}")
                    self.logger.debug(f"  Final is_from_us: {is_from_us}")
                    
                    # Append to messages (maintain chronological order)
                    messages.append({
                        'text': clean_text,
                        'timestamp': time.time(),
                        'is_from_us': is_from_us
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error processing message {i+1}: {str(e)}")
                    continue
            
            if messages:
                self.logger.info("\nFinal message order:")
                for i, msg in enumerate(messages, 1):
                    self.logger.info(f"{i}. {'[US]' if msg['is_from_us'] else '[THEM]'} {msg['text']}")
                self.logger.info(f"\nLast message: {'[US]' if messages[-1]['is_from_us'] else '[THEM]'} {messages[-1]['text']}")
                
            return messages
            
        except Exception as e:
            self.logger.error(f"Error getting conversation details: {e}")
            return []

    async def read_conversation_messages(self):
        """Read all messages from the current conversation using proven approach from debug scripts."""
        messages = []
        try:
            # Wait for messages to load
            await asyncio.sleep(2)
            
            # Get all message cells using proven selector
            cells = await self.wait_and_find_elements("[data-testid='cellInnerDiv']", timeout=5)
            if not cells:
                self.logger.info("No message cells found")
                return messages

            seen_texts = set()  # Track seen messages to avoid duplicates
            
            # Process each cell
            for cell in cells:
                try:
                    # Skip system messages using proven approach
                    cell_text = cell.text.lower()
                    skip_texts = ["you accepted", "seen", "sent", "you joined", "request"]
                    if any(skip in cell_text for skip in skip_texts):
                        continue
                    
                    # Get message entry using proven selector
                    msg = await self.find_element_in_element(cell, "[data-testid='messageEntry']")
                    if not msg:
                        continue
                        
                    # Extract message text
                    text = msg.text.strip()
                    if not text or text in seen_texts:
                        continue
                    seen_texts.add(text)
                    
                    # Get timestamp if available
                    timestamp = time.time()  # Default to current time
                    display_time = "Now"
                    try:
                        time_elem = await self.find_element_in_element(cell, "time")
                        if time_elem:
                            display_time = time_elem.text
                            timestamp = time_elem.get_attribute("datetime") or timestamp
                    except:
                        pass
                    
                    # Message ownership detection based on proven approach
                    msg_class = msg.get_attribute("class") or ""
                    is_from_us = "r-obd0qt" in msg_class  # Proven class for our messages
                    
                    message_data = {
                        'text': text,
                        'timestamp': timestamp,
                        'display_time': display_time,
                        'is_from_us': is_from_us,
                        'ownership_signals': f"msg_class: {msg_class}"
                    }
                    
                    messages.append(message_data)
                    
                    # Debug logging
                    self.logger.debug(f"\nMessage found:")
                    self.logger.debug(f"Text: {text[:50]}...")
                    self.logger.debug(f"Time: {display_time}")
                    self.logger.debug(f"From us: {is_from_us}")
                    self.logger.debug(f"Signals: {message_data['ownership_signals']}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing message cell: {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"Error reading conversation messages: {str(e)}")
            
        return messages
            
    async def send_message(self, message: str):
        """Send a message in the current conversation"""
        try:
            # Find input box
            self.logger.info("Looking for message input box...")
            input_box = await self.wait_and_find_element(
                "div[data-testid='dmComposerTextInput'][role='textbox']"
            )
            
            if not input_box:
                self.logger.error("Could not find message input box")
                return False
            
            # Click input box
            actions = ActionChains(self.handler.browser.driver)
            actions.move_to_element(input_box)
            actions.pause(random.uniform(0.3, 0.7))
            actions.click()
            actions.perform()
            await asyncio.sleep(1)
            
            # Type message
            for char in message:
                actions = ActionChains(self.handler.browser.driver)
                actions.send_keys(char)
                actions.perform()
                await asyncio.sleep(random.uniform(0.03, 0.1))
                
            # Find send button
            self.logger.info("Looking for send button...")
            send_button = await self.wait_and_find_element(
                "button[data-testid='dmComposerSendButton']"
            )
            
            if not send_button:
                self.logger.error("Could not find send button")
                return False
            
            # Click send button
            actions = ActionChains(self.handler.browser.driver)
            actions.move_to_element(send_button)
            actions.pause(random.uniform(0.3, 0.7))
            actions.click()
            actions.perform()
            
            # Wait for message to appear in conversation
            self.logger.info("Waiting for message to appear in conversation...")
            await asyncio.sleep(2)  # Give time for message to send
            
            # Verify message appears in conversation
            messages = await self.get_current_conversation_details()
            if messages and messages[-1].get('is_from_us') and messages[-1]['text'] == message:
                self.logger.info("Message successfully sent and verified")
                return True
            else:
                self.logger.error("Could not verify message was sent")
                return False
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False
            
    async def return_to_messages_list(self):
        """Return to the messages list"""
        try:
            back_button = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='DM_Timeline_Back']"))
            )
            
            actions = ActionChains(self.handler.browser.driver)
            actions.move_to_element(back_button)
            actions.pause(random.uniform(0.3, 0.7))
            actions.click()
            actions.perform()
            await asyncio.sleep(2)
            return True
        except Exception as e:
            self.logger.error(f"Error returning to messages list: {e}")
            # Try to recover by navigating directly
            try:
                await self.navigate_to_messages()
                return True
            except:
                return False
                
    async def wait_and_find_elements(self, selector, timeout=5):
        """Wait for and find elements using WebDriverWait"""
        try:
            elements = WebDriverWait(self.handler.browser.driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
            )
            return elements
        except Exception as e:
            self.logger.debug(f"Could not find elements with selector {selector}: {e}")
            return []
            
    async def wait_and_find_element(self, selector, timeout=5):
        """Wait for and find a single element using WebDriverWait"""
        try:
            element = WebDriverWait(self.handler.browser.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except Exception as e:
            self.logger.debug(f"Could not find element with selector {selector}: {e}")
            return None
            
    async def find_element_in_element(self, element, selector):
        """Find an element within another element"""
        try:
            return element.find_element(By.CSS_SELECTOR, selector)
        except:
            return None

    async def get_message_requests(self):
        """Get message requests using proven approach"""
        try:
            # Navigate directly to requests
            self.handler.browser.navigate("https://twitter.com/messages/requests")
            await asyncio.sleep(2)  # Wait for page load
            
            # Get requests using proven selector
            requests = await self.wait_and_find_elements("[data-testid='conversation']", timeout=5)
            if not requests:
                self.logger.info("No message requests found")
                return []
                
            self.logger.info(f"Found {len(requests)} message requests")
            
            # Process each request to get details
            request_details = []
            for req in requests[:10]:  # Limit to 10 requests
                try:
                    # Get sender name using proven selector
                    sender_elem = await self.find_element_in_element(req, "[data-testid='conversation-name']")
                    if not sender_elem:
                        continue
                        
                    sender = sender_elem.text.strip()
                    if not sender:
                        continue
                        
                    # Ensure handle has @ prefix
                    if not sender.startswith('@'):
                        sender = f'@{sender}'
                        
                    # Get preview text
                    preview = ""
                    preview_elem = await self.find_element_in_element(req, "[data-testid='messageEntry']")
                    if preview_elem:
                        preview = preview_elem.text
                        
                    request_details.append({
                        'sender': sender,
                        'preview': preview or 'No preview',
                        'element': req
                    })
                    self.logger.info(f"\nRequest from: {sender}")
                    self.logger.info(f"Preview: {preview}")
                except Exception as e:
                    self.logger.error(f"Error processing request: {e}")
                    continue

            return request_details

        except Exception as e:
            self.logger.error(f"Error getting message requests: {e}")
            return []

    async def accept_request(self, request):
        """Accept a message request using proven approach"""
        try:
            # Click to open request
            actions = ActionChains(self.handler.browser.driver)
            actions.move_to_element(request["element"])
            actions.click()
            actions.perform()
            await asyncio.sleep(2)  # Wait for request to open

            # Find and click accept button using proven selector
            accept_button = await self.wait_and_find_element(
                "div[role='button'] div[dir='ltr'] span:not([dir])",
                timeout=5
            )
            
            if accept_button and "Accept" in accept_button.text:
                # Get the parent button element
                while accept_button.tag_name != "button":
                    accept_button = accept_button.find_element(By.XPATH, "./..")
                    
                # Click using JavaScript for reliability
                self.handler.browser.driver.execute_script("arguments[0].click();", accept_button)
                await asyncio.sleep(2)  # Wait for accept to process
                self.logger.info(f"Accepted request from {request['sender']}")
                return True
            else:
                self.logger.error(f"Could not find accept button for {request['sender']}")
                return False

        except Exception as e:
            self.logger.error(f"Error accepting request: {str(e)}")
            return False

    async def process_message_requests(self):
        """Process message requests using proven approach"""
        try:
            self.logger.info("\nProcessing message requests:")
            self.logger.info("-" * 30)

            # Get message requests
            requests = await self.get_message_requests()
            if not requests:
                self.logger.info("No message requests to process")
                return True

            # Process each request
            for request in requests:
                # Accept the request
                success = await self.accept_request(request)
                if success:
                    self.logger.info(f"Successfully accepted request from {request['sender']}")
                    # Store in memory that we accepted their request (using handle with @ prefix)
                    self.memory.add_dm(request['sender'], {
                        'text': 'Message request accepted',
                        'is_from_us': True,
                        'timestamp': time.time(),
                        'type': 'system'
                    })
                else:
                    self.logger.error(f"Failed to accept request from {request['sender']}")

            return True

        except Exception as e:
            self.logger.error(f"Error processing message requests: {str(e)}")
            return False 