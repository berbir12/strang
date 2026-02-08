"""
Groq AI integration for script generation (FREE and FAST!)

Groq provides free access to powerful LLMs with extremely fast inference.
Perfect for generating professional avatar scripts.
"""
from groq import Groq
from typing import Optional
import time
import logging
import re
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
    """Service for generating AI avatar scripts using Groq's free API"""
    
    SYSTEM_PROMPT = """You are a creative scriptwriter for AI avatar videos with visual illustrations and diagrams. Transform the user's input into an engaging, dynamic script that brings the content to life with vivid visual descriptions and creative storytelling.

Guidelines:
- Be creative and add personality - don't just paraphrase, make it interesting and engaging
- Use storytelling techniques, examples, analogies, and vivid visual descriptions
- For medical/technical content: Write as if the avatar is pointing to and describing detailed diagrams, illustrations, and anatomical structures visible on screen
- Describe what visual elements, illustrations, diagrams, or scenes would enhance each part of the content
- Break content into natural scenes with different visual focuses (e.g., "As you can see in this diagram...", "Notice in this illustration...", "Picture this scenario...", "Visualize...")
- Use spatial language for diagrams (e.g., "On the left side...", "In the upper portion...", "Below this structure...")
- Reference visual elements explicitly (e.g., "This arrow shows...", "The highlighted area indicates...", "As illustrated here...")
- Vary sentence structure and pacing for natural, dynamic speech
- Add enthusiasm, emotion, and energy to make the content compelling
- Use rhetorical questions, transitions, and engaging hooks to maintain interest
- Feel free to expand on ideas, add context, or provide examples that enhance understanding
- Make it conversational and personable - the avatar should sound authentic and engaging
- Structure with clear flow but allow for natural digressions and emphasis
- Include vivid descriptions of concepts, processes, or ideas that can be visualized
- Structure the script using [SCENE: Descriptive Name] markers.
- Every 2-3 sentences, start a new [SCENE].
- Each [SCENE] must have a [VISUAL: Detailed prompt for the illustration/diagram].
- The spoken text should lead the eye, e.g., "If you look at the top right..."
- Do NOT include any stage directions, camera notes, or non-spoken text
- Output ONLY the creative script that the avatar will speak - nothing else

Create a script that transforms the input into something more engaging, creative, and memorable than a simple paraphrase. The script should naturally describe visual concepts, diagrams, and illustrations as if they are visible on screen."""

    def __init__(self):
        """Initialize Groq client"""
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured")
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        print(f"[GroqService] Initialized with model: {self.model}")

    def generate_image_prompts(self, text: str) -> list[str]:
        """
        Generate image prompts for diagrams/illustrations based on content.
        
        Args:
            text: The content text
            
        Returns:
            List of image generation prompts for visual elements
        """
        # Check if content is medical/technical
        is_medical_technical = any(keyword in text.lower() for keyword in [
            'heart', 'ventricular', 'septal', 'defect', 'blood', 'lung', 'medical', 'anatomy',
            'diagram', 'organ', 'system', 'disease', 'condition', 'symptom', 'treatment',
            'process', 'mechanism', 'function', 'structure', 'component', 'part'
        ])
        
        if not is_medical_technical:
            return []
        
        prompt = f"""
Create a 'Visual Storyboard' for this content.
For each key concept, describe a 'Cinematic Medical Diagram'.
Use keywords like: 'high-resolution 3D medical render', 'labeled cross-section',
'microscopic view', 'schematic diagram with arrows', 'clean white background'.

Content:
{text}

Output ONLY a simple list of image prompts, one per line, without numbering or bullets.
Each prompt should be a detailed description of a medical diagram or illustration.
"""
        
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at creating detailed prompts for medical and technical diagram generation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.8,
                max_tokens=500,
                stream=False
            )
            
            result = chat_completion.choices[0].message.content.strip()
            # Split by lines and filter empty
            prompts = [p.strip() for p in result.split('\n') if p.strip() and len(p.strip()) > 20]
            return prompts[:3]  # Limit to 3 prompts
            
        except Exception as e:
            logger.warning(f"Failed to generate image prompts: {e}")
            return []

    def parse_scenes(self, generated_script: str) -> list[dict]:
        """
        Parse the script into a list of scenes with spoken text and visual prompts.
        """
        scenes = []
        if not generated_script:
            return scenes

        raw_scenes = re.split(r'\[SCENE:.*?\]', generated_script, flags=re.IGNORECASE)
        for scene in raw_scenes:
            if not scene.strip():
                continue
            visual_match = re.search(r'\[VISUAL:\s*(.*?)\]', scene, flags=re.IGNORECASE | re.DOTALL)
            visual_prompt = visual_match.group(1).strip() if visual_match else ""
            spoken_text = re.sub(r'\[VISUAL:.*?\]', '', scene, flags=re.IGNORECASE | re.DOTALL).strip()
            if spoken_text:
                scenes.append({
                    "spoken_text": spoken_text,
                    "visual_prompt": visual_prompt
                })
        return scenes

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
        
        # Build user prompt with context - encourage creativity and visual descriptions
        # Check if content is medical/technical and needs diagrams
        is_medical_technical = any(keyword in text.lower() for keyword in [
            'heart', 'ventricular', 'septal', 'defect', 'blood', 'lung', 'medical', 'anatomy',
            'diagram', 'organ', 'system', 'disease', 'condition', 'symptom', 'treatment',
            'process', 'mechanism', 'function', 'structure', 'component', 'part'
        ])
        
        if is_medical_technical:
            user_prompt = f"""Transform this medical/technical content into a highly visual, diagram-focused script.

CRITICAL: This is medical/technical content that requires visual diagrams and illustrations. The script should:
- Describe detailed anatomical diagrams (e.g., "As you can see in this diagram of the heart...", "Notice in this illustration...")
- Reference specific visual elements (e.g., "The left ventricle shown here...", "This arrow indicates...", "In this cross-section...")
- Break down complex concepts with visual references (e.g., "Imagine a detailed medical diagram showing...", "Picture an anatomical illustration where...")
- Describe what should be visible in diagrams (e.g., "A diagram showing the heart's four chambers with a hole in the septum...")
- Use spatial and visual language (e.g., "On the left side of the diagram...", "The upper portion shows...", "Below this, you can see...")
- Make the avatar describe visual elements as if pointing to a diagram on screen
- Be very specific about anatomical structures, locations, and relationships
- Structure the script using [SCENE: Descriptive Name] markers.
- Every 2-3 sentences, start a new [SCENE].
- Each [SCENE] must have a [VISUAL: Detailed prompt for the illustration/diagram].
- The spoken text should lead the eye, e.g., "If you look at the top right..."

The video will display medical diagrams and illustrations, so the script must reference them explicitly.

Content to transform:
{text}"""
        else:
            user_prompt = f"""Transform this content into a creative, engaging avatar script with visual descriptions. 
            
The video will have visual illustrations and creative elements, so:
- Describe concepts visually (e.g., "Imagine a graph showing...", "Picture this...", "Visualize...")
- Break content into natural visual scenes or segments
- Add vivid descriptions of what could be illustrated on screen
- Use storytelling and examples that can be visualized
- Make it dynamic and engaging, not just a person standing and talking
- Structure the script using [SCENE: Descriptive Name] markers.
- Every 2-3 sentences, start a new [SCENE].
- Each [SCENE] must have a [VISUAL: Detailed prompt for the illustration/diagram].
- The spoken text should lead the eye, e.g., "If you look at the top right..."

Content to transform:
{text}"""
        
        if style and style != "professional":
            user_prompt += f"\n\nStyle: Make it {style} and add creative flair appropriate for that style with visual descriptions."
        else:
            user_prompt += "\n\nBe creative and engaging - don't just paraphrase. Add examples, stories, vivid visual descriptions, and scene transitions to make it memorable and visually interesting."
            
        if duration_hint:
            # Rough estimate: ~150 words per minute for natural speech
            target_words = int((duration_hint / 60) * 150)
            user_prompt += f"\n\nTarget length: approximately {target_words} words (about {duration_hint} seconds when spoken)."
        
        print(f"[GroqService] Generating script with Groq ({self.model})...")
        
        max_retries = 3
        retry_delays = [2, 5, 10]  # Exponential backoff in seconds
        
        for attempt in range(max_retries):
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
                    temperature=max(settings.GROQ_TEMPERATURE, 0.85),  # Ensure minimum creativity
                    max_tokens=min(settings.GROQ_MAX_TOKENS, 2048),  # Allow longer scripts for visual descriptions
                    top_p=0.95,  # Allow more diverse token selection
                    stream=False
                )
                
                script = chat_completion.choices[0].message.content.strip()
                
                if not script:
                    raise ValueError("Groq returned empty script")
                
                print(f"[GroqService] ✓ Script generated: {len(script)} characters")
                logger.info(f"Script generated successfully: {len(script)} characters")
                return script
                
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__
                
                # Check for rate limit errors
                if "rate limit" in error_str or "429" in error_str or isinstance(e, RateLimitError):
                    if attempt < max_retries - 1:
                        wait_time = retry_delays[attempt]
                        error_msg = f"Rate limit hit. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                        print(f"[GroqService] ⚠️ {error_msg}")
                        logger.warning(error_msg)
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = "Groq API rate limit exceeded. Please wait a moment and try again."
                        print(f"[GroqService] ❌ {error_msg}")
                        logger.error(f"Rate limit error after {max_retries} attempts: {e}")
                        raise RuntimeError(error_msg)
                
                # Check for API/auth errors
                elif "401" in error_str or "unauthorized" in error_str or "api key" in error_str or isinstance(e, APIError):
                    error_msg = f"Groq API authentication failed: {str(e)}. Please check your GROQ_API_KEY in .env file."
                    print(f"[GroqService] ❌ {error_msg}")
                    logger.error(f"Authentication error: {e}")
                    raise RuntimeError(error_msg)
                
                # Other errors - retry if possible
                else:
                    if attempt < max_retries - 1:
                        wait_time = retry_delays[attempt]
                        error_msg = f"API error ({error_type}). Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                        print(f"[GroqService] ⚠️ {error_msg}")
                        logger.warning(f"{error_msg} - {e}")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_msg = f"Groq API error: {error_type} - {str(e)}. Please check your API key and try again."
                        print(f"[GroqService] ❌ {error_msg}")
                        logger.error(f"API error after {max_retries} attempts: {e}")
                        raise RuntimeError(error_msg)
        
        # Should never reach here, but just in case
        raise RuntimeError("Failed to generate script: Maximum retries exceeded")

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
            error_msg = f"Script enhancement failed: {type(e).__name__} - {str(e)}"
            print(f"[GroqService] ⚠️ {error_msg}")
            logger.warning(f"Enhancement failed: {e}")
            # If enhancement fails, return original script (graceful degradation)
            return script
