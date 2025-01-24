import logging
import asyncio
import random
from typing import Dict, List, Optional
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SpaceController:
    """Controller for managing Twitter Spaces interactions."""
    
    def __init__(self, action_handler):
        """Initialize the space controller.
        
        Args:
            action_handler: The main ActionHandler instance
        """
        self.handler = action_handler
        self.current_space = None
        self.is_speaking = False
        self.confidence_level = 0.0  # 0.0 to 1.0
        self.joined_spaces = set()
        self.space_understanding = {}
        
    async def find_relevant_spaces(self, keywords: List[str]) -> List[Dict]:
        """Find spaces matching given keywords."""
        try:
            self.handler.browser.navigate("https://twitter.com/i/spaces")
            await asyncio.sleep(3)
            
            spaces = []
            space_elements = WebDriverWait(self.handler.browser.driver, self.handler.timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid='space-item']"))
            )
            
            for space in space_elements:
                try:
                    title = space.find_element(By.CSS_SELECTOR, "[data-testid='space-title']").text
                    host = space.find_element(By.CSS_SELECTOR, "[data-testid='space-host']").text
                    participant_count = space.find_element(By.CSS_SELECTOR, "[data-testid='participant-count']").text
                    
                    # Check if space matches keywords
                    if any(keyword.lower() in title.lower() for keyword in keywords):
                        spaces.append({
                            "title": title,
                            "host": host,
                            "participants": participant_count,
                            "element": space
                        })
                except Exception as e:
                    logger.warning(f"Error processing space element: {e}")
                    continue
            
            return spaces
            
        except Exception as e:
            logger.error(f"Error finding spaces: {e}")
            return []
            
    async def join_space(self, space_data: Dict) -> bool:
        """Join a specific space."""
        try:
            if not space_data.get("element"):
                logger.error("No space element provided")
                return False
            
            # Click on the space to join
            space_data["element"].click()
            await asyncio.sleep(2)
            
            # Wait for space to load
            WebDriverWait(self.handler.browser.driver, self.handler.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='audioSpaceRoom']"))
            )
            
            # Initially join as listener
            join_button = WebDriverWait(self.handler.browser.driver, self.handler.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='joinSpaceButton']"))
            )
            join_button.click()
            
            self.current_space = space_data
            self.confidence_level = 0.0  # Reset confidence when joining new space
            self.joined_spaces.add(space_data.get("title", ""))
            logger.info(f"Successfully joined space: {space_data['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to join space: {e}")
            return False
            
    async def join_space_by_url(self, space_url: str) -> bool:
        """Join a space directly using its URL."""
        try:
            # Validate URL
            parsed_url = urlparse(space_url)
            if not parsed_url.netloc in ['twitter.com', 'x.com']:
                logger.error("Invalid space URL")
                return False
            
            # Navigate to space
            self.handler.browser.navigate(space_url)
            await asyncio.sleep(3)
            
            # Wait for space to load
            WebDriverWait(self.handler.browser.driver, self.handler.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='audioSpaceRoom']"))
            )
            
            # Join as listener
            join_button = WebDriverWait(self.handler.browser.driver, self.handler.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='joinSpaceButton']"))
            )
            join_button.click()
            
            # Update current space info
            space_title = self.handler.browser.driver.find_element(By.CSS_SELECTOR, "[data-testid='audioSpaceTitle']").text
            self.current_space = {
                "url": space_url,
                "title": space_title
            }
            self.confidence_level = 0.0
            self.joined_spaces.add(space_title)
            
            logger.info(f"Successfully joined space: {space_title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to join space by URL: {e}")
            return False
            
    async def request_to_speak(self) -> bool:
        """Request speaking privileges in current space."""
        try:
            if not self.current_space:
                logger.error("Not currently in a space")
                return False
                
            if self.confidence_level < 0.7:  # Require 70% confidence to speak
                logger.info("Not confident enough to request speaking privileges yet")
                return False
                
            request_button = WebDriverWait(self.handler.browser.driver, self.handler.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='requestToSpeakButton']"))
            )
            request_button.click()
            await asyncio.sleep(1)
            
            logger.info("Successfully requested to speak")
            return True
            
        except Exception as e:
            logger.error(f"Failed to request speaking privileges: {e}")
            return False
            
    async def speak_in_space(self, message: str) -> bool:
        """Handle speaking in the space."""
        try:
            if not self.current_space:
                logger.error("Not currently in a space")
                return False
                
            if not self.is_speaking:
                if self.confidence_level < 0.7:
                    logger.info("Not confident enough to speak yet")
                    return False
                    
                # Request to speak if not already speaking
                success = await self.request_to_speak()
                if not success:
                    return False
                    
                # Wait for speaking permission
                try:
                    WebDriverWait(self.handler.browser.driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='speakerMicrophoneButton']"))
                    )
                    self.is_speaking = True
                except TimeoutException:
                    logger.warning("Did not receive speaking permission")
                    return False
                    
            # Use text-to-speech if available
            if self.handler.audio_processor:
                success = await self.handler.audio_processor.speak(message)
                if success:
                    logger.info(f"Successfully spoke in space: {message[:50]}...")
                    return True
                    
            logger.warning("Audio processor not available, message not spoken")
            return False
            
        except Exception as e:
            logger.error(f"Error speaking in space: {e}")
            return False
            
    async def leave_space(self):
        """Leave the current space."""
        try:
            if not self.current_space:
                return
                
            leave_button = WebDriverWait(self.handler.browser.driver, self.handler.timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='leaveSpaceButton']"))
            )
            leave_button.click()
            await asyncio.sleep(1)
            
            self.current_space = None
            self.is_speaking = False
            self.confidence_level = 0.0
            logger.info("Successfully left space")
            
        except Exception as e:
            logger.error(f"Error leaving space: {e}")
            
    async def update_confidence(self, context_understanding: float):
        """Update confidence level based on understanding of the space context.
        
        Args:
            context_understanding: Float between 0 and 1 indicating how well we understand the current context
        """
        if not self.current_space:
            return
            
        # Slowly increase confidence based on understanding
        self.confidence_level = min(1.0, self.confidence_level + (context_understanding * 0.1))
        
        # Decrease confidence if we don't understand context well
        if context_understanding < 0.3:
            self.confidence_level = max(0.0, self.confidence_level - 0.1)
            
        logger.info(f"Updated confidence level to {self.confidence_level:.2f}")
        
    async def get_space_participants(self) -> List[Dict]:
        """Get information about participants in the space."""
        try:
            if not self.current_space:
                return []
                
            participants = []
            participant_elements = self.handler.browser.driver.find_elements(
                By.CSS_SELECTOR, "[data-testid='audioSpaceParticipant']"
            )
            
            for elem in participant_elements:
                try:
                    name = elem.find_element(By.CSS_SELECTOR, "[data-testid='User-Name']").text
                    role = "speaker" if "speaker" in elem.get_attribute("class").lower() else "listener"
                    participants.append({
                        "name": name,
                        "role": role
                    })
                except:
                    continue
                    
            return participants
            
        except Exception as e:
            logger.error(f"Error getting space participants: {e}")
            return []
            
    async def get_space_understanding(self) -> Dict:
        """Get the current understanding of the space context."""
        try:
            if not self.current_space or not self.handler.conversation_manager:
                return {}
                
            understanding = {
                "topic_analysis": await self.handler.conversation_manager.get_topic_analysis(),
                "key_points": await self.handler.conversation_manager.get_key_points(),
                "speaker_profiles": await self.handler.conversation_manager.get_speaker_profiles()
            }
            
            # Update confidence based on our understanding
            topic_confidence = len(understanding.get("topic_analysis", [])) > 0
            points_confidence = len(understanding.get("key_points", [])) > 0
            speakers_confidence = len(understanding.get("speaker_profiles", [])) > 0
            
            confidence_score = (
                (1 if topic_confidence else 0) +
                (1 if points_confidence else 0) +
                (1 if speakers_confidence else 0)
            ) / 3.0
            
            await self.update_confidence(confidence_score)
            return understanding
            
        except Exception as e:
            logger.error(f"Error getting space understanding: {e}")
            return {} 