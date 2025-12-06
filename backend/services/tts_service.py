"""
Text-to-Speech Service - Offline using pyttsx3
Supports multiple accents with male British as default
"""
import os
from typing import Optional, Dict, List
from pathlib import Path
import uuid


class TTSService:
    """Text-to-Speech service using pyttsx3 for offline generation"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            self.output_dir = Path(__file__).parent.parent / "uploads" / "generated_audio"
        else:
            self.output_dir = Path(output_dir)
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.engine = None
        self._initialized = False
    
    def _init_engine(self):
        """Initialize pyttsx3 engine lazily"""
        if self._initialized:
            return
        
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            
            # Try to find and set a British male voice
            voices = self.engine.getProperty('voices')
            british_male = None
            male_voice = None
            
            for voice in voices:
                voice_lower = voice.name.lower()
                # Look for British/UK English male voice
                if 'david' in voice_lower or 'george' in voice_lower:
                    british_male = voice.id
                    break
                elif 'hazel' in voice_lower or 'uk' in voice_lower or 'british' in voice_lower:
                    british_male = voice.id
                elif 'male' in voice_lower or 'david' in voice_lower:
                    male_voice = voice.id
            
            # Set the best available voice
            if british_male:
                self.engine.setProperty('voice', british_male)
                print(f"Using British voice: {british_male}")
            elif male_voice:
                self.engine.setProperty('voice', male_voice)
                print(f"Using male voice: {male_voice}")
            elif voices:
                # Default to first available voice
                self.engine.setProperty('voice', voices[0].id)
                print(f"Using default voice: {voices[0].name}")
            
            # Set properties for clearer speech
            self.engine.setProperty('rate', 150)  # Speed (words per minute)
            self.engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
            
            self._initialized = True
            print("pyttsx3 TTS engine initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize pyttsx3: {e}")
            self.engine = None
    
    async def generate_speech(self, text: str, 
                               accent: str = "british",
                               gender: str = "male",
                               rate: str = "+0%",
                               pitch: str = "+0Hz",
                               output_path: str = None) -> Dict:
        """Generate speech audio from text"""
        self._init_engine()
        
        if not self.engine:
            raise Exception("TTS engine not available")
        
        # Generate unique filename if not provided
        if output_path is None:
            filename = f"tts_{accent}_{uuid.uuid4().hex[:8]}.wav"
            output_path = str(self.output_dir / filename)
        
        # Ensure .wav extension for pyttsx3
        if not output_path.endswith('.wav'):
            output_path = output_path.replace('.mp3', '.wav')
        
        try:
            # Adjust rate based on parameter
            base_rate = 150
            rate_value = 0
            if rate.startswith("+"):
                rate_value = int(rate[1:-1])
            elif rate.startswith("-"):
                rate_value = -int(rate[1:-1])
            
            adjusted_rate = int(base_rate * (1 + rate_value / 100))
            self.engine.setProperty('rate', adjusted_rate)
            
            # Save to file
            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()
            
            # Get duration estimate
            duration = self._estimate_duration(text, rate)
            
            return {
                "audio_path": output_path,
                "duration": duration,
                "voice": "British Male (Offline)",
                "accent": accent,
                "text": text
            }
            
        except Exception as e:
            print(f"TTS generation error: {e}")
            raise Exception(f"Failed to generate speech: {str(e)}")
    
    async def generate_british_pronunciation(self, text: str, slow: bool = False) -> Dict:
        """Generate correct British English pronunciation"""
        rate = "-20%" if slow else "+0%"
        return await self.generate_speech(
            text=text,
            accent="british",
            gender="male",
            rate=rate
        )
    
    def _estimate_duration(self, text: str, rate: str) -> float:
        """Estimate audio duration based on text and rate"""
        word_count = len(text.split())
        base_duration = (word_count / 150) * 60
        
        rate_value = 0
        if rate.startswith("+"):
            rate_value = int(rate[1:-1])
        elif rate.startswith("-"):
            rate_value = -int(rate[1:-1])
        
        rate_multiplier = 1 - (rate_value / 100)
        return base_duration * rate_multiplier
    
    def list_available_voices(self) -> List[Dict]:
        """List all available voices on the system"""
        self._init_engine()
        
        if not self.engine:
            return []
        
        voices = self.engine.getProperty('voices')
        return [
            {
                "id": voice.id,
                "name": voice.name,
                "languages": voice.languages if hasattr(voice, 'languages') else []
            }
            for voice in voices
        ]


# Singleton instance
tts_service = TTSService()
