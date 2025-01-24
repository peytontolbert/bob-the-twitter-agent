import logging
import asyncio
from typing import List, Dict, Optional
import openai
from datetime import datetime, timedelta
import os
from .conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)

class BobTheBuilder:
    def __init__(self, api_key: str, memory: Optional[ConversationMemory] = None):
        """Initialize Bob with his personality and memory"""
        self.api_key = api_key
        self.client = openai.AsyncOpenAI(api_key=api_key)  # Create AsyncOpenAI client
        self.memory = memory if memory else ConversationMemory()
        self.personality = {
            "name": "Bob the Builder",
            "role": "AI assistant who loves to help people build things",
            "traits": [
                "helpful and encouraging",
                "knowledgeable about building and creating",
                "patient with beginners",
                "enthusiastic about projects",
                "careful to understand before giving advice"
            ],
            "interests": [
                "construction and building",
                "DIY projects",
                "technology and coding",
                "helping others learn",
                "problem-solving"
            ]
        }
        self.confidence = {}  # Track confidence per conversation
        
    def _get_confidence(self, handle: str) -> float:
        """Get confidence level for interacting with a specific handle"""
        return self.confidence.get(handle, 0.0)
        
    def _update_confidence(self, handle: str, delta: float):
        """Update confidence level for a handle"""
        current = self._get_confidence(handle)
        self.confidence[handle] = max(0.0, min(1.0, current + delta))
        
    def _format_conversation_history(self, handle: str, limit: int = 5) -> str:
        """Format recent conversation history for context"""
        history = self.memory.get_recent_context(handle, limit)
        if not history:
            return "No previous conversation history."
            
        formatted = "Recent conversation history:\n"
        for msg in history:
            speaker = "Bob" if msg.get('is_from_us') else handle
            formatted += f"{speaker}: {msg.get('text', 'No text')}\n"
        return formatted
        
    def _create_prompt(self, handle: str, current_message: str, context_type: str) -> str:
        """Create a prompt with personality and context"""
        confidence = self._get_confidence(handle)
        history = self._format_conversation_history(handle)
        
        prompt = f"""You are {self.personality['name']}, {self.personality['role']}.
Your traits: {', '.join(self.personality['traits'])}
Your interests: {', '.join(self.personality['interests'])}

Current confidence level with {handle}: {confidence:.2f}

{history}

Current message from {handle} ({context_type}): {current_message}

Based on your personality and the conversation history, craft a response that:
1. Maintains your builder/helper personality
2. Shows appropriate confidence level ({confidence:.2f})
3. References relevant context from history if available
4. Focuses on helping them build or create something

Response:"""

        return prompt
        
    async def generate_response(self, handle: str, message: str, context_type: str = "dm") -> str:
        """Generate a contextual response using ChatGPT with RAG"""
        try:
            if not message:
                logger.error("Empty message received")
                return None
                
            logger.info(f"\nGenerating response for {context_type} from {handle}")
            logger.info(f"Input message: {message}")
            
            # Update confidence based on interaction
            if context_type == "space":
                self._update_confidence(handle, 0.05)
            elif context_type == "mention":
                self._update_confidence(handle, 0.1)
            elif context_type == "dm":
                self._update_confidence(handle, 0.15)
            
            logger.info(f"Current confidence with {handle}: {self._get_confidence(handle):.2f}")
            
            try:
                # Generate response with ChatGPT
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Use standard model name
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are Bob the Builder, an AI who loves to help people build things. Keep responses friendly and focused on building/making things."
                        },
                        {
                            "role": "user",
                            "content": message
                        }
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                
                logger.debug(f"Raw OpenAI response: {response}")
                
                if response and response.choices:
                    reply = response.choices[0].message.content.strip()
                    logger.info(f"Generated response: {reply[:100]}...")
                    return reply
                else:
                    logger.error("No choices in OpenAI response")
                    return None
                    
            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}")
                logger.error(f"Request context: {message}")
                return None
            
        except Exception as e:
            logger.error(f"Error in generate_response: {str(e)}")
            logger.exception("Full traceback:")
            return None
            
    def should_speak_in_space(self, handle: str, context: str) -> bool:
        """Determine if Bob should speak in a space based on confidence"""
        confidence = self._get_confidence(handle)
        
        # Basic rules for speaking:
        # 1. Need at least 0.3 confidence to speak
        # 2. More likely to speak if the context matches interests
        # 3. Won't speak if confidence is too low
        
        if confidence < 0.3:
            return False
            
        # Check if context matches interests
        context_relevance = any(interest.lower() in context.lower() 
                              for interest in self.personality['interests'])
                              
        # Higher confidence threshold if context isn't relevant
        if not context_relevance and confidence < 0.5:
            return False
            
        # Probability of speaking increases with confidence
        import random
        speak_probability = confidence * (1.5 if context_relevance else 1.0)
        return random.random() < speak_probability
        
    def get_memory_for_handle(self, handle: str) -> Dict[str, List[Dict]]:
        """Get all conversation history for a handle"""
        return self.memory.get_all_conversations(handle)
        
    def get_confidence_for_handle(self, handle: str) -> float:
        """Get current confidence level for a handle"""
        return self._get_confidence(handle)

    async def process_message(self, message: str, context: Dict) -> str:
        """Process a direct message using the fast model for quick responses."""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._get_personality_prompt()},
                    {"role": "system", "content": f"Context: {context}"},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error processing message with fast model: {e}")
            return "I apologize, but I'm having trouble processing your message right now. Could you try again in a moment?"
            
    async def analyze_space(self, space_messages: List[Dict]) -> Dict:
        """Analyze space conversation using the large model for deep understanding."""
        try:
            # Update space context
            self.space_context.extend([msg['text'] for msg in space_messages])
            if len(self.space_context) > 20:  # Keep last 20 messages for context
                self.space_context = self.space_context[-20:]
                
            # Calculate time spent in space
            if not self.space_join_time:
                self.space_join_time = datetime.now()
            time_spent = (datetime.now() - self.space_join_time).total_seconds() / 60
            
            # Analyze space context
            response = await openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_personality_prompt()},
                    {"role": "system", "content": "Analyze the space conversation and determine:\n1. The main topics being discussed\n2. The expertise level of participants\n3. Whether Bob's expertise would be valuable\n4. A confidence score (0-1) for Bob to speak\n5. Potential contributions Bob could make"},
                    {"role": "user", "content": f"Space Context:\n{self.space_context}\n\nTime spent listening: {time_spent} minutes"}
                ],
                temperature=0.7
            )
            
            # Parse response
            analysis = response.choices[0].message.content
            
            # Update confidence based on time spent and analysis
            base_confidence = min(time_spent / 30, 0.5)  # Max 0.5 from time alone
            self.space_confidence = base_confidence + (float(analysis.split("confidence score: ")[1].split()[0]) * 0.5)
            
            return {
                'analysis': analysis,
                'confidence': self.space_confidence,
                'should_speak': self.space_confidence >= self.min_confidence_to_speak
            }
            
        except Exception as e:
            logger.error(f"Error analyzing space with large model: {e}")
            return {
                'analysis': "Error analyzing space",
                'confidence': self.space_confidence,
                'should_speak': False
            }
            
    async def generate_space_response(self) -> Optional[str]:
        """Generate a response for the space conversation if confidence is high enough."""
        if self.space_confidence < self.min_confidence_to_speak:
            return None
            
        try:
            response = await openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_personality_prompt()},
                    {"role": "system", "content": "Generate a thoughtful contribution to the space conversation that:\n1. Adds value to the discussion\n2. Demonstrates expertise without being overbearing\n3. Encourages further discussion\n4. Maintains Bob's friendly and helpful personality"},
                    {"role": "user", "content": f"Space Context:\n{self.space_context}"}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating space response: {e}")
            return None
            
    def reset_space_context(self):
        """Reset space-related tracking when leaving a space."""
        self.space_confidence = 0.0
        self.space_join_time = None
        self.space_context = []
        
    def _get_personality_prompt(self) -> str:
        """Get Bob's personality prompt for the LLM."""
        return f"""You are {self.name}, a friendly and knowledgeable {self.role}. Your personality traits:

1. Helpful and encouraging - You love helping others build and create
2. Practical and experienced - You provide realistic, actionable advice
3. Safety-conscious - You always emphasize proper safety measures
4. Community-minded - You value collaboration and sharing knowledge
5. Humble - You're confident in your expertise but never boastful
6. Patient - You understand that learning and building take time
7. Environmentally conscious - You promote sustainable building practices

Your interests include: {', '.join(self.interests)}

When speaking:
- Use clear, practical language
- Share specific examples and tips
- Encourage safe practices
- Be positive and supportive
- Ask questions to better understand needs
- Share relevant personal experiences
- Promote sustainable solutions

Remember: You're here to help people build and create, not to dominate the conversation.""" 