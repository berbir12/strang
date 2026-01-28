"""
Text-to-Speech service for voiceover generation
"""
from pathlib import Path
from typing import Optional
import subprocess
from config import settings


class TTSService:
    """Generate voiceover audio from script"""
    
    def __init__(self):
        self.provider = settings.TTS_PROVIDER
        self.output_dir = settings.TEMP_DIR / "audio"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_voiceover(
        self,
        script: str,
        voice: str,
        job_id: str
    ) -> Optional[Path]:
        """
        Generate voiceover audio from script
        
        Args:
            script: Full voiceover text
            voice: Voice ID or accent
            job_id: Unique job identifier
        
        Returns:
            Path to generated .mp3 or .wav file, or None if TTS disabled
        """
        
        if self.provider == "none":
            print("TTS disabled, skipping voiceover")
            return None
        
        output_path = self.output_dir / f"{job_id}_voiceover.mp3"
        
        if self.provider == "openai":
            return self._generate_openai_tts(script, voice, output_path)
        elif self.provider == "elevenlabs":
            return self._generate_elevenlabs_tts(script, voice, output_path)
        else:
            print(f"Unknown TTS provider: {self.provider}")
            return None
    
    def _generate_openai_tts(self, script: str, voice: str, output_path: Path) -> Path:
        """Generate using OpenAI TTS API"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            print(f"Generating voiceover with OpenAI TTS (voice: {voice})...")
            
            response = client.audio.speech.create(
                model="tts-1",  # or "tts-1-hd" for higher quality
                voice=voice if voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] else "alloy",
                input=script,
                speed=1.0
            )
            
            # Stream to file
            response.stream_to_file(output_path)
            
            print(f"✓ Voiceover generated: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"⚠ OpenAI TTS failed: {e}")
            return None
    
    def _generate_elevenlabs_tts(self, script: str, voice: str, output_path: Path) -> Path:
        """Generate using ElevenLabs API"""
        try:
            import requests
            
            # ElevenLabs API (requires ELEVENLABS_API_KEY in env)
            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                print("⚠ ELEVENLABS_API_KEY not set")
                return None
            
            # Map voice accents to ElevenLabs voice IDs (example)
            voice_map = {
                "us": "21m00Tcm4TlvDq8ikWAM",  # Rachel
                "uk": "XB0fDUnXU5powFXDhCwa",  # Charlotte
                "au": "pNInz6obpgDQGcFmaJgB",  # Adam
                "neutral": "21m00Tcm4TlvDq8ikWAM"
            }
            
            voice_id = voice_map.get(voice, voice_map["neutral"])
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "text": script,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            print(f"Generating voiceover with ElevenLabs (voice: {voice})...")
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✓ Voiceover generated: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"⚠ ElevenLabs TTS failed: {e}")
            return None
    
    def adjust_audio_duration(self, audio_path: Path, target_duration: float) -> Path:
        """
        Adjust audio speed to match target video duration
        
        Uses ffmpeg's atempo filter to speed up or slow down
        """
        
        # Get current audio duration
        import subprocess
        import json
        
        probe_cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(audio_path)
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        probe_data = json.loads(result.stdout)
        current_duration = float(probe_data["format"]["duration"])
        
        # Calculate speed factor
        speed_factor = current_duration / target_duration
        
        # Clamp to reasonable range (0.5x to 2.0x)
        speed_factor = max(0.5, min(2.0, speed_factor))
        
        if abs(speed_factor - 1.0) < 0.05:
            # No adjustment needed
            return audio_path
        
        # Apply speed adjustment
        adjusted_path = audio_path.parent / f"{audio_path.stem}_adjusted.mp3"
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(audio_path),
            "-filter:a", f"atempo={speed_factor}",
            str(adjusted_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        print(f"Adjusted audio speed by {speed_factor:.2f}x to match video duration")
        
        return adjusted_path
