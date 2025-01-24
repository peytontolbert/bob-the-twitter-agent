import pytest
from datetime import datetime, timedelta
from src.agent.conversation_manager import ConversationManager
from src.agent.bob import BobTheBuilder
import os

class TestConversation:
    @pytest.fixture
    def conversation_manager(self):
        return ConversationManager()
    
    @pytest.fixture
    def bob(self):
        return BobTheBuilder(
            api_key=os.getenv("OPENAI_API_KEY"),
            hf_token=os.getenv("HF_TOKEN")
        )
    
    def test_speaking_decision(self, conversation_manager):
        """Test speaking decision logic"""
        # Test cooldown period
        conversation_manager.last_spoke = datetime.now()
        assert not conversation_manager.should_speak(1.0, "construction project")
        
        # Test topic relevance
        conversation_manager.last_spoke = datetime.now() - timedelta(minutes=1)
        assert conversation_manager.should_speak(0.9, "construction project")
        assert not conversation_manager.should_speak(0.9, "unrelated topic")
        
    async def test_response_generation(self, bob):
        """Test response generation"""
        context = {
            'recent_messages': [
                {
                    'text': 'What do you think about sustainable building materials?',
                    'timestamp': datetime.now().isoformat()
                }
            ],
            'speaker_count': 1,
            'topic': 'Sustainable Construction'
        }
        
        response = await bob._generate_response({'title': 'Building Materials'}, context)
        assert isinstance(response, str)
        assert len(response) > 0 