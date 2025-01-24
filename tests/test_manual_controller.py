import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import sys
import datetime
# Add src to Python path
sys.path.append(str(Path(__file__).parent.parent))

from tests.manual_test_actions import ManualActionTester

class TestManualController:
    @pytest.fixture
    async def controller(self):
        with patch('tests.manual_test_actions.ActionHandler') as mock_handler:
            controller = ManualActionTester()
            controller.handler = Mock()
            controller.handler.ensure_logged_in = AsyncMock(return_value=True)
            yield controller
    
    @pytest.mark.asyncio
    async def test_menu_navigation(self, controller):
        """Test menu navigation logic"""
        # Test main menu navigation
        controller.handle_main_menu("1")
        assert controller.current_menu == "spaces"
        
        controller.handle_main_menu("2")
        assert controller.current_menu == "tweets"
        
        controller.handle_main_menu("3")
        assert controller.current_menu == "dms"
        
        # Test exit
        controller.handle_main_menu("0")
        assert not controller.running
    
    @pytest.mark.asyncio
    async def test_space_menu_actions(self, controller):
        """Test space menu actions"""
        # Mock space-related methods
        controller.handler.find_relevant_spaces = AsyncMock(return_value=[
            {"title": "Test Space", "host": "Test Host"}
        ])
        controller.handler.join_space_by_url = AsyncMock(return_value=True)
        controller.handler.current_space = {"title": "Current Space"}
        controller.handler.request_to_speak = AsyncMock(return_value=True)
        controller.handler.speak_in_space = AsyncMock(return_value=True)
        
        # Test find spaces
        with patch('builtins.input', return_value="building,construction"):
            await controller.handle_space_menu("1")
            controller.handler.find_relevant_spaces.assert_called_once()
        
        # Test join space
        with patch('builtins.input', return_value="https://x.com/i/spaces/123"):
            await controller.handle_space_menu("2")
            controller.handler.join_space_by_url.assert_called_once()
        
        # Test request to speak
        await controller.handle_space_menu("3")
        controller.handler.request_to_speak.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tweet_menu_actions(self, controller):
        """Test tweet menu actions"""
        # Mock tweet-related methods
        controller.handler.post_tweet = AsyncMock(return_value=True)
        controller.handler.tweet_queue.add_tweet = Mock()
        
        # Test single tweet posting
        with patch('builtins.input', return_value="Test tweet"):
            await controller.handle_tweet_menu("1")
            controller.handler.post_tweet.assert_called_once_with("Test tweet")
        
        # Test adding to queue
        with patch('builtins.input', return_value="Queued tweet"):
            await controller.handle_tweet_menu("2")
            controller.handler.tweet_queue.add_tweet.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dm_menu_actions(self, controller):
        """Test DM menu actions"""
        # Mock DM-related methods
        controller.handler.check_dms = AsyncMock(return_value=[
            {"sender": "TestUser", "preview": "Test DM"}
        ])
        
        # Test checking DMs
        await controller.handle_dm_menu("1")
        controller.handler.check_dms.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_navigation_functions(self, controller):
        """Test navigation functions"""
        with patch('builtins.input', return_value=""):
            await controller.test_navigation()
            assert controller.handler.driver.get.call_count == 3
    
    @pytest.mark.asyncio
    async def test_login_session(self, controller):
        """Test login session management"""
        controller.handler._save_session = Mock()
        controller.handler._load_session = Mock(return_value=True)
        
        await controller.test_login_session()
        controller.handler._save_session.assert_called_once()
        controller.handler._load_session.assert_called_once()


@pytest.mark.integration
class TestManualControllerIntegration:
    @pytest.fixture
    async def live_controller(self):
        controller = ManualActionTester()
        yield controller
        controller.handler.cleanup()
    
    @pytest.mark.asyncio
    async def test_login_flow(self, live_controller):
        """Test actual login flow"""
        success = await live_controller.handler.ensure_logged_in()
        assert success, "Login should succeed"
    
    @pytest.mark.asyncio
    async def test_space_navigation(self, live_controller):
        """Test actual space navigation"""
        spaces = await live_controller.handler.find_relevant_spaces(["test"])
        assert isinstance(spaces, list), "Should return list of spaces"
    
    @pytest.mark.asyncio
    async def test_tweet_posting(self, live_controller):
        """Test actual tweet posting"""
        test_tweet = f"Test tweet {datetime.now().isoformat()}"
        success = await live_controller.handler.post_tweet(test_tweet)
        assert success, "Tweet posting should succeed" 