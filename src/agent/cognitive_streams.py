from typing import Dict, List, Optional
import asyncio
from datetime import datetime
import openai
from collections import deque
import numpy as np

class CognitiveStreams:
    def __init__(self, bob_instance):
        self.bob = bob_instance
        self.thought_queue = asyncio.Queue()  # For processing thoughts
        self.speech_queue = asyncio.Queue()   # For processing speech
        self.memory_buffer = deque(maxlen=100)  # Short-term memory buffer
        self.is_processing = True
        self.current_context = {}
        
    async def start_cognitive_processes(self):
        """Start all cognitive processes concurrently"""
        cognitive_tasks = [
            self.listening_stream(),
            self.thinking_stream(),
            self.speaking_stream(),
            self.memory_stream(),
            self.attention_stream()
        ]
        await asyncio.gather(*cognitive_tasks)
    
    async def listening_stream(self):
        """Process incoming audio and transcriptions"""
        while self.is_processing:
            try:
                transcription = self.bob.audio_processor.whisper.get_transcription()
                if transcription and transcription != "No speech detected.":
                    audio_data = np.array(self.bob.audio_processor.whisper.buffer)
                    if len(audio_data) > 0:
                        segments = await self.bob.audio_processor.process_audio_segment(audio_data)
                        for segment in segments:
                            await self.thought_queue.put({
                                "type": "new_speech",
                                "data": segment
                            })
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error in listening stream: {e}")
    
    async def thinking_stream(self):
        """Process thoughts and analyze conversation"""
        while self.is_processing:
            try:
                thought = await self.thought_queue.get()
                if thought["type"] == "new_speech":
                    segment = thought["data"]
                    
                    # Parallel processing of different aspects
                    analysis_tasks = [
                        self._analyze_content(segment),
                        self._analyze_social_context(segment),
                        self._analyze_relevance(segment)
                    ]
                    
                    results = await asyncio.gather(*analysis_tasks)
                    content, social, relevance = results
                    
                    combined_analysis = {
                        "content": content,
                        "social": social,
                        "relevance": relevance,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await self.memory_buffer.append(combined_analysis)
                    
                    # Update confidence based on understanding
                    if relevance > 0.7:  # High relevance
                        await self.speech_queue.put({
                            "type": "potential_response",
                            "data": combined_analysis
                        })
                
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error in thinking stream: {e}")
    
    async def speaking_stream(self):
        """Handle speech generation and delivery"""
        while self.is_processing:
            try:
                speech_data = await self.speech_queue.get()
                if speech_data["type"] == "potential_response":
                    analysis = speech_data["data"]
                    
                    # Check if we should speak
                    if await self._should_speak(analysis):
                        response = await self._generate_response(analysis)
                        await self.bob.action_handler.speak_in_space(response)
                        self.bob.conversation_manager.last_spoke = datetime.now()
                
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error in speaking stream: {e}")
    
    async def memory_stream(self):
        """Process and consolidate memories"""
        while self.is_processing:
            try:
                if len(self.memory_buffer) > 50:  # Batch process memories
                    memories = list(self.memory_buffer)
                    consolidated = await self._consolidate_memories(memories)
                    self.bob.memory.add_interaction(consolidated)
                    self.memory_buffer.clear()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error in memory stream: {e}")
    
    async def attention_stream(self):
        """Monitor and adjust attention focus"""
        while self.is_processing:
            try:
                # Update current context and focus
                current_speakers = set(self.bob.speaker_history.keys())
                current_topic = self._extract_current_topic()
                
                # Adjust confidence thresholds based on context
                self.bob.confidence_manager.update_confidence(
                    self.current_context,
                    self.bob.speaker_history
                )
                
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Error in attention stream: {e}")
    
    async def _analyze_content(self, segment: Dict) -> Dict:
        """Analyze technical content of speech"""
        response = await openai.ChatCompletion.create(
            model=self.bob.large_model,
            messages=[
                {"role": "system", "content": self.bob.personality.get_persona_prompt()},
                {"role": "user", "content": f"Analyze technical content: {segment['text']}"}
            ]
        )
        return {"technical_analysis": response.choices[0].message.content}
    
    async def _analyze_social_context(self, segment: Dict) -> Dict:
        """Analyze social context and dynamics"""
        response = await openai.ChatCompletion.create(
            model=self.bob.small_model,
            messages=[
                {"role": "system", "content": self.bob.personality.get_persona_prompt()},
                {"role": "user", "content": f"Analyze social dynamics: {segment['text']}"}
            ]
        )
        return {"social_analysis": response.choices[0].message.content}
    
    async def _analyze_relevance(self, segment: Dict) -> float:
        """Calculate relevance score for the segment"""
        # Implementation of relevance scoring
        return 0.8  # Placeholder
    
    async def _should_speak(self, analysis: Dict) -> bool:
        """Determine if we should speak based on multiple factors"""
        confidence = self.bob.confidence_manager.confidence_score
        relevance = analysis.get("relevance", 0)
        last_spoke = self.bob.conversation_manager.last_spoke
        
        return (confidence > 0.7 and 
                relevance > 0.7 and 
                (not last_spoke or 
                 (datetime.now() - last_spoke).seconds > 30))

    async def _consolidate_memories(self, memories: List[Dict]) -> Dict:
        """Consolidate memories into a summary"""
        try:
            memory_text = "\n".join([
                f"{mem['timestamp']}: {mem['content']['technical_analysis']}"
                for mem in memories
            ])
            
            response = await openai.ChatCompletion.create(
                model=self.bob.large_model,
                messages=[
                    {"role": "system", "content": "Summarize these conversation memories"},
                    {"role": "user", "content": memory_text}
                ]
            )
            
            return {
                "summary": response.choices[0].message.content,
                "period": {
                    "start": memories[0]["timestamp"],
                    "end": memories[-1]["timestamp"]
                },
                "raw_memories": memories
            }
        except Exception as e:
            print(f"Error consolidating memories: {e}")
            return {}

    def _extract_current_topic(self) -> str:
        """Extract current topic from context"""
        try:
            recent_messages = [
                msg for msg in self.memory_buffer 
                if "content" in msg and "technical_analysis" in msg["content"]
            ][-5:]  # Last 5 messages
            
            if not recent_messages:
                return ""
                
            topics = set()
            for msg in recent_messages:
                analysis = msg["content"]["technical_analysis"]
                if isinstance(analysis, str):
                    topics.add(analysis.split('\n')[0])  # First line usually contains topic
            
            return ", ".join(topics)
        except Exception as e:
            print(f"Error extracting topic: {e}")
            return ""

    async def _generate_response(self, analysis: Dict) -> str:
        """Generate response based on analysis"""
        try:
            prompt = f"""
            Based on this analysis:
            Technical: {analysis['content']['technical_analysis']}
            Social: {analysis['social']['social_analysis']}
            
            Generate a response that:
            1. Shows understanding of the technical points
            2. Maintains appropriate social dynamics
            3. Adds value from a builder's perspective
            4. Remains humble and helpful
            """
            
            response = await openai.ChatCompletion.create(
                model=self.bob.small_model,
                messages=[
                    {"role": "system", "content": self.bob.personality.get_persona_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating response: {e}")
            return ""

    async def _recover_stream(self, stream_name: str):
        """Attempt to recover a failed stream"""
        try:
            self._log_action(f"Attempting to recover {stream_name} stream")
            if stream_name == "listening":
                await self.bob.audio_processor.restart()
            elif stream_name == "thinking":
                self.thought_queue = asyncio.Queue()  # Reset queue
            elif stream_name == "speaking":
                self.speech_queue = asyncio.Queue()  # Reset queue
            self._log_action(f"Successfully recovered {stream_name} stream")
        except Exception as e:
            self._log_action(f"Failed to recover {stream_name} stream: {e}") 