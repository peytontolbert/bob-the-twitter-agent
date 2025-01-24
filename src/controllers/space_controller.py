import logging
import asyncio
from typing import List, Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from src.agent.action_handler import ActionHandler
from src.agent.bob_agent import BobTheBuilder

logger = logging.getLogger(__name__)

class SpaceController:
    def __init__(self, action_handler: ActionHandler, bob_agent: BobTheBuilder):
        self.handler = action_handler
        self.bob = bob_agent
        self.current_space = None
        self.is_speaking = False
        self.last_analysis_time = None
        
    async def find_relevant_spaces(self) -> List[Dict]:
        """Find spaces relevant to Bob's interests."""
        spaces = []
        try:
            # Navigate to Spaces
            self.handler.browser.navigate("https://twitter.com/i/spaces")
            await asyncio.sleep(3)
            
            # Find space cards
            space_cards = WebDriverWait(self.handler.browser.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='SpaceCard']"))
            )
            
            for card in space_cards:
                try:
                    title = card.find_element(By.CSS_SELECTOR, "[data-testid='SpaceTitle']").text
                    description = card.find_element(By.CSS_SELECTOR, "[data-testid='SpaceDescription']").text
                    
                    # Check if space is relevant to Bob's interests
                    relevant = any(interest.lower() in (title + description).lower() 
                                 for interest in self.bob.interests)
                    
                    if relevant:
                        spaces.append({
                            'element': card,
                            'title': title,
                            'description': description
                        })
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error finding spaces: {e}")
            
        return spaces
        
    async def join_space(self, space_element) -> bool:
        """Join a specific space."""
        try:
            # Click on space card
            actions = ActionChains(self.handler.browser.driver)
            actions.move_to_element(space_element)
            actions.click()
            actions.perform()
            await asyncio.sleep(2)
            
            # Find and click join button
            join_button = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='joinSpaceButton']"))
            )
            join_button.click()
            await asyncio.sleep(2)
            
            self.current_space = space_element
            self.bob.reset_space_context()
            return True
            
        except Exception as e:
            logger.error(f"Error joining space: {e}")
            return False
            
    async def get_space_messages(self) -> List[Dict]:
        """Get messages/captions from current space."""
        messages = []
        try:
            container = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='spaceCaptionsContainer']"))
            )
            
            message_elements = container.find_elements(By.CSS_SELECTOR, "[data-testid='caption']")
            for msg in message_elements:
                try:
                    text = msg.text.strip()
                    speaker = msg.find_element(By.CSS_SELECTOR, "[data-testid='captionSpeaker']").text
                    
                    if text:
                        messages.append({
                            'text': text,
                            'speaker': speaker,
                            'element': msg
                        })
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error getting space messages: {e}")
            
        return messages
        
    async def request_to_speak(self) -> bool:
        """Request to speak in the current space."""
        try:
            request_button = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='requestToSpeakButton']"))
            )
            request_button.click()
            await asyncio.sleep(1)
            return True
            
        except Exception as e:
            logger.error(f"Error requesting to speak: {e}")
            return False
            
    async def start_speaking(self, message: str) -> bool:
        """Start speaking in the space."""
        try:
            if not self.is_speaking:
                unmute_button = WebDriverWait(self.handler.browser.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='unmuteButton']"))
                )
                unmute_button.click()
                await asyncio.sleep(1)
                
            # TODO: Implement text-to-speech integration
            logger.info(f"Would speak: {message}")
            self.is_speaking = True
            return True
            
        except Exception as e:
            logger.error(f"Error starting to speak: {e}")
            return False
            
    async def stop_speaking(self) -> bool:
        """Stop speaking in the space."""
        try:
            if self.is_speaking:
                mute_button = WebDriverWait(self.handler.browser.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='muteButton']"))
                )
                mute_button.click()
                await asyncio.sleep(1)
                self.is_speaking = False
            return True
            
        except Exception as e:
            logger.error(f"Error stopping speaking: {e}")
            return False
            
    async def leave_space(self) -> bool:
        """Leave the current space."""
        try:
            leave_button = WebDriverWait(self.handler.browser.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='leaveSpaceButton']"))
            )
            leave_button.click()
            await asyncio.sleep(1)
            
            self.current_space = None
            self.is_speaking = False
            self.bob.reset_space_context()
            return True
            
        except Exception as e:
            logger.error(f"Error leaving space: {e}")
            return False
            
    async def monitor_space(self) -> None:
        """Monitor the current space and decide when to speak."""
        try:
            while self.current_space:
                messages = await self.get_space_messages()
                if messages:
                    # Analyze space context periodically
                    analysis = await self.bob.analyze_space(messages)
                    
                    if analysis['should_speak'] and not self.is_speaking:
                        response = await self.bob.generate_space_response()
                        if response:
                            await self.request_to_speak()
                            await self.start_speaking(response)
                    elif self.is_speaking:
                        await self.stop_speaking()
                        
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except Exception as e:
            logger.error(f"Error monitoring space: {e}")
            await self.leave_space() 