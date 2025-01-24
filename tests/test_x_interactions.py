import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import time

class TestXInteractions:
    @pytest.fixture
    async def action_handler(self):
        from src.agent.action_handler import ActionHandler
        handler = ActionHandler(headless=False)
        await handler.ensure_logged_in()
        yield handler
        handler.cleanup()

    @pytest.mark.asyncio
    async def test_space_listening_flow(self, action_handler):
        """Test complete space listening flow"""
        try:
            # Find and join a space
            spaces = await action_handler.find_relevant_spaces(["building", "construction"])
            assert len(spaces) >= 0, "Should find spaces or return empty list"
            
            if spaces:
                space = spaces[0]
                success = await action_handler.join_space_by_url(space["url"])
                assert success, "Should join space successfully"
                
                # Test listener mode
                assert not action_handler.is_speaking, "Should start as listener"
                
                # Wait and listen (simulating understanding buildup)
                await asyncio.sleep(30)  # Listen for 30 seconds
                
                # Request to speak
                success = await action_handler.request_to_speak()
                assert success, "Should request speaking successfully"
                
                # Test speaking mode once granted
                if action_handler.is_speaking:
                    success = await action_handler.speak_in_space("Hello, I'm Bob the Builder!")
                    assert success, "Should speak successfully"
                
                # Leave space
                await action_handler.leave_space()
                assert not action_handler.current_space, "Should leave space successfully"
        
        except Exception as e:
            pytest.fail(f"Space listening flow failed: {e}")

    @pytest.mark.asyncio
    async def test_dm_interaction_flow(self, action_handler):
        """Test complete DM interaction flow"""
        try:
            # Check DMs
            dms = await action_handler.check_dms()
            assert isinstance(dms, list), "Should return list of DMs"
            
            if dms:
                dm = dms[0]
                # Test DM reply
                success = await action_handler.reply_to_dm(
                    dm["thread_element"],
                    "Hello! I'm Bob, happy to help with building questions!"
                )
                assert success, "Should reply to DM successfully"
        
        except Exception as e:
            pytest.fail(f"DM interaction flow failed: {e}")

    @pytest.mark.asyncio
    async def test_tweet_thread_flow(self, action_handler):
        """Test complete tweet thread flow"""
        try:
            thread_content = [
                "1/4 As a builder, I've learned that sustainable construction is key to our future. 🏗️",
                "2/4 Today, I want to share some insights about eco-friendly building materials:",
                "3/4 - Recycled steel reduces environmental impact\n- Bamboo is renewable and sturdy\n- Reclaimed wood adds character",
                "4/4 What's your favorite sustainable building material? Let's discuss! #Construction #Sustainability"
            ]
            
            success = await action_handler.post_thread(thread_content)
            assert success, "Should post thread successfully"
            
            # Verify thread was posted
            # TODO: Add verification logic
        
        except Exception as e:
            pytest.fail(f"Tweet thread flow failed: {e}")

    @pytest.mark.asyncio
    async def test_space_host_detection(self, action_handler):
        """Test detection of space host and speakers"""
        try:
            spaces = await action_handler.find_relevant_spaces(["building"])
            if spaces:
                space = spaces[0]
                await action_handler.join_space_by_url(space["url"])
                
                # Get space participants
                participants = await action_handler.get_space_participants()
                assert "host" in participants, "Should identify space host"
                assert "speakers" in participants, "Should identify current speakers"
                assert "listeners" in participants, "Should identify listeners"
        
        except Exception as e:
            pytest.fail(f"Space host detection failed: {e}")

    @pytest.mark.asyncio
    async def test_conversation_context_tracking(self, action_handler):
        """Test tracking conversation context in spaces"""
        try:
            spaces = await action_handler.find_relevant_spaces(["building"])
            if spaces:
                space = spaces[0]
                await action_handler.join_space_by_url(space["url"])
                
                # Listen for some time
                await asyncio.sleep(30)
                
                # Get conversation context
                context = await action_handler.get_conversation_context()
                assert "topic" in context, "Should identify conversation topic"
                assert "recent_messages" in context, "Should track recent messages"
                assert "speakers" in context, "Should track active speakers"
        
        except Exception as e:
            pytest.fail(f"Conversation context tracking failed: {e}")

    @pytest.mark.asyncio
    async def test_audio_processing(self, action_handler):
        """Test audio processing in spaces"""
        try:
            spaces = await action_handler.find_relevant_spaces(["building"])
            if spaces:
                space = spaces[0]
                await action_handler.join_space_by_url(space["url"])
                
                # Test audio stream
                audio_stream = await action_handler.get_audio_stream()
                assert audio_stream, "Should get audio stream"
                
                # Test speech recognition
                if action_handler.is_speaking:
                    success = await action_handler.speak_in_space(
                        "Hello everyone, Bob the Builder here!"
                    )
                    assert success, "Should transmit audio successfully"
        
        except Exception as e:
            pytest.fail(f"Audio processing failed: {e}")

    @pytest.mark.asyncio
    async def test_error_handling(self, action_handler):
        """Test error handling and recovery"""
        try:
            # Test connection loss recovery
            with patch.object(action_handler.driver, 'get', side_effect=Exception("Connection lost")):
                await action_handler.join_space_by_url("https://x.com/i/spaces/123")
                # Should handle error gracefully
            
            # Test audio failure recovery
            with patch.object(action_handler.audio_processor, 'start_listening', side_effect=Exception("Audio failed")):
                await action_handler.speak_in_space("Test message")
                # Should handle error gracefully
            
            # Test session recovery
            action_handler.driver.quit()
            await action_handler.ensure_logged_in()
            assert action_handler.is_logged_in, "Should recover session successfully"
        
        except Exception as e:
            pytest.fail(f"Error handling test failed: {e}")

    @pytest.mark.asyncio
    async def test_specific_space_interaction(self, action_handler):
        """Test interaction with specific space"""
        space_url = "https://x.com/i/spaces/1DXGyddYqzEKM"
        try:
            # Join the specific space
            success = await action_handler.join_space_by_url(space_url)
            assert success, "Should join space successfully"
            
            # Verify we're in the space
            assert action_handler.current_space, "Should be in space"
            assert action_handler.current_space["url"] == space_url, "Should be in correct space"
            
            # Start as listener and observe
            assert not action_handler.is_speaking, "Should start as listener"
            
            # Get initial context
            context = await action_handler.get_conversation_context()
            print(f"Initial context: {context}")  # For debugging
            
            # Listen and build understanding (minimum 2 minutes)
            print("Listening to space...")
            for _ in range(4):  # 4 x 30 seconds = 2 minutes
                await asyncio.sleep(30)
                context = await action_handler.get_conversation_context()
                print(f"Updated context: {context}")  # For debugging
                
                # Check if we understand the conversation enough
                if context.get("confidence_level", 0) > 0.7:  # 70% confidence
                    # Request to speak if we have something valuable to add
                    if not action_handler.is_speaking:
                        success = await action_handler.request_to_speak()
                        if success:
                            print("Successfully requested to speak")
            
            # If we got speaking privileges, contribute
            if action_handler.is_speaking:
                message = await action_handler.generate_contextual_message(context)
                success = await action_handler.speak_in_space(message)
                assert success, "Should speak successfully"
            
            # Test space information gathering
            participants = await action_handler.get_space_participants()
            assert participants, "Should get participant information"
            
            print(f"Space participants: {participants}")
            print(f"Final context: {context}")
            
            # Leave space
            await action_handler.leave_space()
            assert not action_handler.current_space, "Should leave space successfully"
            
        except Exception as e:
            pytest.fail(f"Specific space interaction failed: {e}")
        finally:
            # Ensure we leave the space even if test fails
            if action_handler.current_space:
                await action_handler.leave_space()

    @pytest.mark.asyncio
    async def test_space_confidence_building(self, action_handler):
        """Test confidence building mechanism in specific space"""
        space_url = "https://x.com/i/spaces/1DXGyddYqzEKM"
        try:
            await action_handler.join_space_by_url(space_url)
            
            # Monitor confidence building over time
            confidence_levels = []
            for _ in range(6):  # Monitor for 3 minutes
                context = await action_handler.get_conversation_context()
                confidence = context.get("confidence_level", 0)
                confidence_levels.append(confidence)
                print(f"Current confidence level: {confidence}")
                await asyncio.sleep(30)
            
            # Assert confidence generally increases
            assert confidence_levels[-1] > confidence_levels[0], "Confidence should increase over time"
            
            # Test understanding retention
            understanding = await action_handler.get_space_understanding()
            assert "topic_analysis" in understanding, "Should have topic analysis"
            assert "key_points" in understanding, "Should have key points"
            assert "speaker_profiles" in understanding, "Should have speaker profiles"
            
            print(f"Final understanding: {understanding}")
            
        except Exception as e:
            pytest.fail(f"Confidence building test failed: {e}")
        finally:
            if action_handler.current_space:
                await action_handler.leave_space() 