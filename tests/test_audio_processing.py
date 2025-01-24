import pytest
import numpy as np
from src.agent.audio_processor import AudioProcessor
from src.agent.whisper_manager import WhisperManager
import sounddevice as sd
import asyncio
import os

class TestAudioProcessing:
    @pytest.fixture
    def audio_processor(self):
        return AudioProcessor(hf_token=os.getenv("HF_TOKEN"))
        
    @pytest.fixture
    def test_audio_file(self):
        """Generate a test audio signal"""
        duration = 3  # seconds
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate * duration))
        test_signal = 0.5 * np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        return test_signal.astype(np.float32), sample_rate
    
    async def test_audio_capture(self, audio_processor):
        """Test audio capture functionality"""
        # Start listening
        listen_task = asyncio.create_task(audio_processor.start_listening())
        
        # Wait for a short period
        await asyncio.sleep(2)
        
        # Stop listening
        audio_processor.stop_listening()
        await listen_task
        
        # Check if audio was captured
        assert audio_processor.whisper.buffer is not None
        
    async def test_transcription(self, audio_processor, test_audio_file):
        """Test audio transcription"""
        audio_data, sample_rate = test_audio_file
        
        # Process audio segment
        segments = await audio_processor.process_audio_segment(audio_data)
        
        # Check if segments were processed
        assert isinstance(segments, list)
        
    def test_whisper_manager_initialization(self):
        """Test WhisperManager initialization"""
        whisper = WhisperManager()
        assert whisper.model is not None
        assert whisper.processor is not None 