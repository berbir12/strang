"""
Text-to-Speech Service using EdgeTTS (Free)
Generates high-quality mp3 audio from text.
"""
import edge_tts
import asyncio
from pathlib import Path
import logging
from config import settings

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self):
        # Voice constants
        self.VOICE_MALE_1 = "en-US-GuyNeural"
        self.VOICE_FEMALE_1 = "en-US-JennyNeural"
        self.VOICE_MALE_2 = "en-US-ChristopherNeural" 
        self.VOICE_FEMALE_2 = "en-US-AriaNeural"
        
        self.output_dir = settings.TEMP_DIR / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def generate_audio(self, text: str, voice: str = "en-US-GuyNeural", file_name: str = "output.mp3") -> Path:
        """
        Generate MP3 audio from text.
        
        Args:
            text: Text to speak
            voice: EdgeTTS voice identifier
            file_name: Output filename
            
        Returns:
            Path to the generated file
        """
        if not text.strip():
            raise ValueError("TTS text cannot be empty")
            
        output_path = self.output_dir / file_name
        
        print(f"[TTSService] Generating audio: {text[:30]}... ({voice})")
        
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            
            if not output_path.exists() or output_path.stat().st_size == 0:
                 raise RuntimeError("TTS Output file is empty or missing")
                 
            return output_path
            
        except Exception as e:
            logger.error(f"TTS Generation failed: {e}")
            raise RuntimeError(f"TTS Generation failed: {e}")
            
    def get_voices(self):
        """Return list of available basic voices"""
        return [
            {"id": self.VOICE_MALE_1, "name": "Guy (Male)", "gender": "Male"},
            {"id": self.VOICE_FEMALE_1, "name": "Jenny (Female)", "gender": "Female"},
            {"id": self.VOICE_MALE_2, "name": "Christopher (Male)", "gender": "Male"},
            {"id": self.VOICE_FEMALE_2, "name": "Aria (Female)", "gender": "Female"},
        ]
