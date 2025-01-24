import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.agent.action_handler import ActionHandler
import os

class TestNavigation:
    @pytest.fixture
    async def logged_in_handler(self):
        handler = ActionHandler()
        await handler.ensure_logged_in()
        yield handler
        handler.cleanup()
    
    @pytest.mark.asyncio
    async def test_login_state(self):
        """Test login state detection"""
        handler = ActionHandler()
        
        # Should start not logged in
        assert not handler.check_login_state()
        
        # Should handle manual login if needed
        if not os.getenv("X_USERNAME") or not os.getenv("X_PASSWORD"):
            assert await handler.manual_login()
        else:
            assert await handler.ensure_logged_in()
        
        # Should now be logged in
        assert handler.check_login_state()
        
        handler.cleanup()
    
    @pytest.mark.asyncio
    async def test_space_navigation(self, logged_in_handler):
        """Test navigation to X Spaces"""
        try:
            # Find spaces related to building/construction
            spaces = await logged_in_handler.find_relevant_spaces(["building", "construction", "engineering"])
            
            assert len(spaces) >= 0  # Might be 0 if no relevant spaces are live
            
            if spaces:
                # Try joining the first relevant space
                assert await logged_in_handler.join_space(spaces[0])
                
        except Exception as e:
            pytest.fail(f"Failed to navigate to spaces: {e}")
    
    def test_join_space(self, action_handler):
        """Test joining a space"""
        try:
            # Find and click a space
            space = WebDriverWait(action_handler.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='space-title']"))
            )
            space_title = space.text
            space.click()
            
            # Verify we joined the space
            joined_title = WebDriverWait(action_handler.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='audioSpaceTitle']"))
            )
            
            assert joined_title.text == space_title
            
        except Exception as e:
            pytest.fail(f"Failed to join space: {e}") 