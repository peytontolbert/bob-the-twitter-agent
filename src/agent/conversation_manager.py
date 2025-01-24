import asyncio
from typing import Dict, List
import openai
from datetime import datetime, timedelta

class ConversationManager:
    def __init__(self):
        self.context = {
            "topic": None,
            "participants": {},
            "conversation_history": [],
            "confidence_level": 0.0,
            "start_time": None,
            "last_update": None
        }
        self.gpt4_client = openai.Client()  # Large model for deep understanding
        self.gpt35_client = openai.Client()  # Small model for quick responses

    async def update_context(self, message: Dict):
        """Update conversation context with new message"""
        if not self.context["start_time"]:
            self.context["start_time"] = datetime.now()
        
        self.context["last_update"] = datetime.now()
        self.context["conversation_history"].append(message)
        
        # Update confidence based on participation time and understanding
        time_factor = min((datetime.now() - self.context["start_time"]).seconds / 300, 1.0)  # Max after 5 minutes
        self.context["confidence_level"] = min(0.3 + (time_factor * 0.7), 1.0)

    async def get_context(self) -> Dict:
        """Get current conversation context"""
        return self.context

    async def get_topic_analysis(self) -> Dict:
        """Analyze conversation topic using GPT-4"""
        try:
            if not self.context["conversation_history"]:
                return {"main_topic": None, "subtopics": []}
            
            response = await self.gpt4_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Analyze the conversation and identify the main topic and subtopics."},
                    {"role": "user", "content": str(self.context["conversation_history"][-10:])}  # Last 10 messages
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error in topic analysis: {e}")
            return {"main_topic": None, "subtopics": []}

    async def get_key_points(self) -> List[str]:
        """Extract key points from conversation using GPT-3.5"""
        try:
            if not self.context["conversation_history"]:
                return []
            
            response = await self.gpt35_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Extract the main points from this conversation."},
                    {"role": "user", "content": str(self.context["conversation_history"][-5:])}  # Last 5 messages
                ]
            )
            return response.choices[0].message.content.split("\n")
        except Exception as e:
            print(f"Error getting key points: {e}")
            return []

    async def get_speaker_profiles(self) -> Dict:
        """Build profiles of active speakers"""
        try:
            speakers = {}
            for message in self.context["conversation_history"]:
                speaker = message.get("speaker")
                if speaker and speaker not in speakers:
                    speakers[speaker] = {
                        "message_count": 1,
                        "first_seen": message.get("timestamp"),
                        "topics": []
                    }
                elif speaker:
                    speakers[speaker]["message_count"] += 1
            return speakers
        except Exception as e:
            print(f"Error getting speaker profiles: {e}")
            return {}

    async def should_speak(self) -> bool:
        """Determine if Bob should speak based on context and confidence"""
        if self.context["confidence_level"] < 0.7:
            return False
            
        try:
            response = await self.gpt35_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Bob the Builder, deciding whether to speak in a conversation about building things. Consider the context and your confidence level."},
                    {"role": "user", "content": f"Context: {str(self.context)}"}
                ]
            )
            return "yes" in response.choices[0].message.content.lower()
        except Exception as e:
            print(f"Error in should_speak decision: {e}")
            return False

    async def generate_response(self, prompt: str) -> str:
        """Generate a response using the appropriate model based on complexity"""
        try:
            # Use GPT-4 for complex topics or when deep understanding is needed
            if self.context["confidence_level"] > 0.8 or "technical" in prompt.lower():
                response = await self.gpt4_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are Bob the Builder, an enthusiastic expert in building and construction. Keep responses helpful and construction-focused."},
                        {"role": "user", "content": prompt}
                    ]
                )
            else:
                # Use GPT-3.5 for quicker, simpler responses
                response = await self.gpt35_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are Bob the Builder, an enthusiastic expert in building and construction. Keep responses helpful and construction-focused."},
                        {"role": "user", "content": prompt}
                    ]
                )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating response: {e}")
            return "" 