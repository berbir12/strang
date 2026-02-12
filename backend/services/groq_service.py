"""
Groq AI integration for script generation (FREE and FAST!)

Groq provides free access to powerful LLMs with extremely fast inference.
Perfect for generating professional cinematic scripts for OpenAI Sora.
"""
from groq import Groq
from typing import Optional, List, Dict
import time
import logging
import re
import json
from config import settings

# Set up logging
logger = logging.getLogger(__name__)

# Try to import Groq-specific exceptions, fallback to generic if not available
try:
    from groq import RateLimitError, APIError
except ImportError:
    # Fallback if these exceptions don't exist
    RateLimitError = Exception
    APIError = Exception


class GroqService:
    """Service for generating AI video scripts using Groq's free API"""
    
    SYSTEM_PROMPT = """You are a professional screenwriter and cinematographer. 
    You create detailed scripts for AI video generation (OpenAI Sora).
    
    Your goal is to take a topic or text and convert it into a JSON structure containing "Scenes".
    Each Scene has:
    1. "narration": The voiceover text (engaging, natural).
    2. "video_prompt": A highly detailed, cinematic prompt for OpenAI Sora to generate a 5-10s video clip.
    
    Guidelines for Sora Prompts:
    - Be extremely descriptive. Mention camera angles, lighting, movement, style.
    - Examples: "Wide drone shot of...", "Close up of...", "Cinematic lighting", "4k resolution", "Slow motion".
    - Describe the motion in the scene.
    - Keep narration concise to match the visual duration.
    
    Output Format:
    You must output strictly Valid JSON. The structure is:
    {
      "scenes": [
        {
          "narration": "Text for voiceover...",
          "video_prompt": "Detailed prompt for Sora..."
        },
        ...
      ]
    }
    """

    def __init__(self):
        """Initialize Groq client"""
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured")
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        print(f"[GroqService] Initialized with model: {self.model}")

    def generate_script_json(self, text: str, style: str = "documentary") -> List[Dict]:
        """
        Generate a list of scenes with narration and video prompts.
        
        Args:
            text: Input text
            style: Video style
            
        Returns:
            List of dicts: [{"narration": "...", "video_prompt": "..."}, ...]
        """
        user_prompt = f"""Create a {style} style video script for the following content.
        Break it down into 3-5 scenes.
        
        Content:
        {text}
        """
        
        print(f"[GroqService] Generating script JSON with Groq ({self.model})...")
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                model=self.model,
                temperature=0.7,
                max_tokens=self.SYSTEM_PROMPT.count(" ") + 2048, # Rough estimate
                response_format={"type": "json_object"},
                stream=False
            )
            
            content = chat_completion.choices[0].message.content.strip()
            data = json.loads(content)
            
            scenes = data.get("scenes", [])
            print(f"[GroqService] ✓ Generated {len(scenes)} scenes")
            return scenes
            
        except Exception as e:
            logger.error(f"Groq Script generation failed: {e}")
            raise RuntimeError(f"Groq Script generation failed: {e}")

