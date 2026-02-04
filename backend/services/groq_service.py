"""
Groq AI integration for script generation (FREE and FAST!)

Groq provides free access to powerful LLMs with extremely fast inference.
Perfect for generating professional avatar scripts.
"""
from groq import Groq
from typing import Optional
from config import settings


class GroqService:
    """Service for generating AI avatar scripts using Groq's free API"""
    
    SYSTEM_PROMPT = """You are an expert scriptwriter for AI avatar videos. Transform the user's input into a professional, engaging script that sounds natural when spoken by a virtual presenter.

Guidelines:
- Use conversational, clear language appropriate for video presentation
- Keep sentences concise and easy to follow when spoken aloud
- Structure the content with a clear introduction, main points, and conclusion
- Make it engaging and personable - the avatar should sound helpful and knowledgeable
- Avoid complex jargon unless the topic requires it
- Do NOT include any stage directions, camera notes, or non-spoken text
- Output ONLY the refined script that the avatar will speak - nothing else

The script should be ready to use directly with a text-to-speech avatar system."""

    def __init__(self):
        """Initialize Groq client"""
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured")
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        print(f"[GroqService] Initialized with model: {self.model}")

    def generate_script(
        self,
        text: str,
        style: str = "professional",
        duration_hint: Optional[int] = None
    ) -> str:
        """
        Transform user input into a polished avatar script using Groq.
        
        Args:
            text: The raw input text to transform
            style: Script style (professional, casual, educational, friendly)
            duration_hint: Optional target duration in seconds
            
        Returns:
            The refined script ready for HeyGen avatar
        """
        
        # Build user prompt with context
        user_prompt = f"Transform this content into an avatar script:\n\n{text}"
        
        if style and style != "professional":
            user_prompt += f"\n\nStyle: Make it {style}."
            
        if duration_hint:
            # Rough estimate: ~150 words per minute for natural speech
            target_words = int((duration_hint / 60) * 150)
            user_prompt += f"\n\nTarget length: approximately {target_words} words (about {duration_hint} seconds when spoken)."
        
        print(f"[GroqService] Generating script with Groq ({self.model})...")
        
        try:
            # Call Groq API - it's SUPER fast!
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
                temperature=settings.GROQ_TEMPERATURE,
                max_tokens=settings.GROQ_MAX_TOKENS,
                top_p=1,
                stream=False
            )
            
            script = chat_completion.choices[0].message.content.strip()
            
            print(f"[GroqService] ✓ Script generated: {len(script)} characters")
            return script
            
        except Exception as e:
            print(f"[GroqService] ❌ ERROR: {type(e).__name__}: {e}")
            raise RuntimeError(f"Failed to generate script with Groq: {e}")

    def enhance_script(self, script: str) -> str:
        """
        Further enhance an existing script with better pacing and naturalness.
        
        Args:
            script: An existing script to enhance
            
        Returns:
            Enhanced script with better flow and pacing
        """
        
        enhance_prompt = f"""Enhance this avatar script for better spoken delivery:
1. Improve the flow and pacing for natural speech
2. Ensure sentences are clear and easy to understand
3. Keep the same content and meaning
4. Output ONLY the enhanced script

Script:
{script}"""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a script editor who enhances scripts for natural spoken delivery."
                    },
                    {
                        "role": "user",
                        "content": enhance_prompt
                    }
                ],
                model=self.model,
                temperature=0.5,
                max_tokens=settings.GROQ_MAX_TOKENS,
                stream=False
            )
            
            enhanced = chat_completion.choices[0].message.content.strip()
            return enhanced
            
        except Exception as e:
            print(f"[GroqService] Enhancement failed: {e}")
            # If enhancement fails, return original script
            return script
