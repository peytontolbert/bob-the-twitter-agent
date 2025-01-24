from typing import Dict, List
import openai
from datetime import datetime
from .memory import Memory
from .personality import BobPersonality
from .confidence_manager import ConfidenceManager
from .action_handler import ActionHandler
from .audio_processor import AudioProcessor
import asyncio
import numpy as np
from .conversation_manager import ConversationManager
from .cognitive_streams import CognitiveStreams

class BobTheBuilder:
    def __init__(self, api_key: str, hf_token: str):
        self.memory = Memory()
        self.personality = BobPersonality()
        self.confidence_manager = ConfidenceManager()
        self.action_handler = ActionHandler()
        
        # Initialize OpenAI clients for dual processing
        self.large_model = "gpt-4o"  # For deep thinking
        self.small_model = "gpt-4o-mini"  # For quick responses
        openai.api_key = api_key
        
        self.audio_processor = AudioProcessor(hf_token)
        self.current_speakers = set()
        self.speaker_history = {}
        self.conversation_manager = ConversationManager()
        self.cognitive_streams = CognitiveStreams(self)
        
    async def process_space(self, space_data: Dict):
        """Process a space conversation with concurrent cognitive streams"""
        # Start audio processing
        audio_task = asyncio.create_task(self.audio_processor.start_listening())
        
        # Log the space joining
        self._log_action(f"Joined space: {space_data['title']}")
        
        try:
            # Start cognitive processes
            await self.cognitive_streams.start_cognitive_processes()
            
        except Exception as e:
            self._log_action(f"Error in space processing: {e}")
            self.audio_processor.stop_listening()
            audio_task.cancel()
            self.cognitive_streams.is_processing = False
            
    async def _analyze_conversation(self, segment: Dict) -> str:
        """Analyze conversation segment using the large model"""
        prompt = f"""
        Speaker {segment['speaker']} said: "{segment['text']}"
        
        As Bob the Builder, analyze this statement and provide thoughts on:
        1. The technical content and accuracy
        2. Potential areas where you could contribute
        3. Any concerns or corrections needed
        """
        
        # Use GPT-4 for deep analysis
        response = await openai.ChatCompletion.create(
            model=self.large_model,
            messages=[
                {"role": "system", "content": self.personality.get_persona_prompt()},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
            
    def _log_action(self, action: str):
        """Log actions to log.txt"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("log.txt", "a") as f:
            f.write(f"[{timestamp}] {action}\n")
            
    def _record_thoughts(self, thoughts: str):
        """Record thoughts to thoughts.txt"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("thoughts.txt", "a") as f:
            f.write(f"[{timestamp}] {thoughts}\n")
            
    async def _generate_response(self, space_data: Dict, context: Dict) -> str:
        """Generate a contextually appropriate response"""
        recent_messages = self._get_recent_context(context)
        current_topic = self._extract_topic(recent_messages)
        
        # First use GPT-4 to analyze the conversation deeply
        analysis = await openai.ChatCompletion.create(
            model=self.large_model,
            messages=[
                {"role": "system", "content": self.personality.get_persona_prompt()},
                {"role": "user", "content": f"""
                Analyze this conversation context as Bob the Builder:
                Topic: {current_topic}
                Recent messages: {recent_messages}
                
                Provide:
                1. Key technical points discussed
                2. Areas where construction/building expertise could add value
                3. Potential concerns or corrections needed
                4. Suggested approach for contribution
                """}
            ]
        )
        
        # Then use GPT-3.5 to quickly formulate the response
        response = await openai.ChatCompletion.create(
            model=self.small_model,
            messages=[
                {"role": "system", "content": self.personality.get_persona_prompt()},
                {"role": "user", "content": f"""
                Based on this analysis: {analysis.choices[0].message.content}
                
                Craft a helpful, humble response that:
                - Acknowledges others' contributions
                - Shares relevant building/construction expertise
                - Asks thoughtful questions when uncertain
                - Keeps the response concise and focused
                """}
            ]
        )
        
        return response.choices[0].message.content
    
    def _get_recent_context(self, context: Dict, window: int = 5) -> List[Dict]:
        """Get recent messages for context"""
        recent_messages = []
        for speaker, messages in self.speaker_history.items():
            recent_messages.extend(messages[-window:])
        return sorted(recent_messages, key=lambda x: x['timestamp'])
    
    def _extract_topic(self, messages: List[Dict]) -> str:
        """Extract topic from recent messages"""
        topics = set()
        for message in messages:
            topics.add(message['text'].split(':')[0].strip())
        return ', '.join(topics) 

    async def shutdown(self):
        """Gracefully shutdown all processes"""
        try:
            self.cognitive_streams.is_processing = False
            self.audio_processor.stop_listening()
            await self.memory.save_state()  # New method needed in Memory class
            self._log_action("Bot shutting down gracefully")
        except Exception as e:
            self._log_action(f"Error during shutdown: {e}") 

    async def start(self):
        """Start Bob's processing"""
        try:
            # Start all processes
            tasks = [
                self.cognitive_streams.start_cognitive_processes(),
                self.action_handler.process_space_queue(),
                self.action_handler.process_tweet_queue()
            ]
            
            # Wait for tasks
            await asyncio.gather(*tasks)
            
        except Exception as e:
            self._log_action(f"Error in main processing: {e}")
            await self.shutdown()

    async def join_space_from_url(self, space_url: str):
        """Add a space to the queue"""
        success = self.action_handler.space_queue.add_space(space_url, {
            "added_by": "manual",
            "timestamp": datetime.now().isoformat()
        })
        if success:
            self._log_action(f"Added space to queue: {space_url}")
        return success 

    async def generate_response(self, handle: str, message: str, context_type: str = "dm") -> str:
        """Generate a contextual response using dual LLM processing with RAG"""
        try:
            # Update confidence based on interaction
            self.confidence_manager.update_confidence(handle, context_type)
                
            # Get relevant context from memory
            history = self.memory.get_recent_context(handle, limit=5)
            
            # Format conversation history for RAG
            conversation_context = []
            for msg in history:
                role = "assistant" if msg.get('is_from_us') else "user"
                conversation_context.append({
                    "role": role,
                    "content": msg.get('text', '')
                })
            
            # First use large model for deep analysis
            analysis = await openai.ChatCompletion.create(
                model=self.large_model,
                messages=[
                    {"role": "system", "content": self.personality.get_persona_prompt()},
                    *conversation_context,
                    {"role": "user", "content": f"Analyze this conversation with {handle} and provide key points to address in our response."}
                ]
            )
            
            # Then use small model for quick response generation
            messages = [
                {"role": "system", "content": f"""You are {self.personality.name}. Use this analysis to craft a response: {analysis.choices[0].message.content}"""},
                *conversation_context,
                {"role": "user", "content": message}
            ]
            
            response = await openai.ChatCompletion.create(
                model=self.small_model,
                messages=messages,
                temperature=0.7,
                max_tokens=150,
                presence_penalty=0.6,
                frequency_penalty=0.3
            )
            
            reply = response.choices[0].message.content.strip()
            
            # Store interaction in memory
            current_time = datetime.now().isoformat()
            self.memory.add_interaction(handle, message, reply, current_time, context_type)
            
            return reply
            
        except Exception as e:
            self._log_action(f"Error generating response: {e}")
            return "Hi! I'm Bob the Builder, and I'd love to help you build something! What are you working on?" 