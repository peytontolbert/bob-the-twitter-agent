from typing import Dict, List, Tuple, Optional
from pyannote.audio import Pipeline
import numpy as np
import asyncio
from .whisper_manager import WhisperManager
import logging
from gtts import gTTS
import io
import wave
import pyaudio

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self, hf_token: str = None):
        # Initialize Speaker Diarization
        self.diarization = None
        if hf_token:
            try:
                self.diarization = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize diarization: {e}")
        
        # Initialize Whisper Manager
        self.whisper = WhisperManager()
        
        # Audio buffer for processing
        self.audio_buffer = []
        
        # Initialize optional components
        self.speech_recognition_available = False
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.speech_recognition_available = True
        except ImportError:
            logger.warning("Speech recognition not available. Some features will be disabled.")

        self.pyaudio = pyaudio.PyAudio()
        self.stream = None
        self.is_listening = False

    async def get_stream(self) -> Optional[object]:
        """Initialize and return an audio stream"""
        try:
            # Implement basic audio stream functionality
            return None  # For now, return None as we're not using audio in initial tests
        except Exception as e:
            logger.error(f"Error getting audio stream: {e}")
            return None

    async def start_listening(self):
        """Start listening to the audio stream"""
        self.is_listening = True
        while self.is_listening:
            await asyncio.sleep(0.1)  # Placeholder for actual audio processing

    async def stop_listening(self):
        """Stop listening to the audio stream"""
        self.is_listening = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    async def speak(self, text: str) -> bool:
        """Convert text to speech and play it"""
        try:
            # Convert text to speech
            tts = gTTS(text=text, lang='en')
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            # Play the audio
            stream = self.pyaudio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=44100,
                output=True
            )
            
            # Convert mp3 to wav format for streaming
            audio_data = fp.read()
            stream.write(audio_data)
            stream.stop_stream()
            stream.close()
            
            return True
        except Exception as e:
            print(f"Error speaking: {e}")
            return False

    async def process_audio_segment(self, audio_data: np.ndarray) -> List[Dict]:
        """Process audio segment with speaker diarization and transcription"""
        if not self.diarization:
            return []
            
        try:
            # Process audio data if diarization is available
            diarization_result = self.diarization({
                "waveform": audio_data,
                "sample_rate": 16000  # Standard sample rate
            })
            
            # Return processed segments
            return [{
                "speaker": speaker,
                "start": turn.start,
                "end": turn.end,
                "text": ""  # Placeholder for transcription
            } for turn, _, speaker in diarization_result.itertracks(yield_label=True)]
            
        except Exception as e:
            logger.error(f"Error in process_audio_segment: {e}")
            return []

    def __del__(self):
        """Cleanup audio resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pyaudio:
            self.pyaudio.terminate() 