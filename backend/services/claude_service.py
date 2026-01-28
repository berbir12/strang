"""
Claude API integration for intelligent storyboard generation
"""
import anthropic
from typing import Dict, Any
import json
from config import settings
from models import ExplanationStyle, Storyboard, Scene, SceneType


class ClaudeService:
    """Service for generating intelligent video storyboards using Claude"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    def generate_storyboard(
        self,
        text: str,
        style: ExplanationStyle,
        duration: int,
        voice_accent: str
    ) -> Storyboard:
        """
        Generate a complete video storyboard with intelligent scene classification.
        
        Claude decides which scenes should be:
        - SLIDE (text-heavy, Manim): definitions, lists, key points, equations
        - VISUAL (photorealistic, Mochi): real-world examples, demonstrations, B-roll
        """
        
        prompt = self._build_storyboard_prompt(text, style, duration, voice_accent)
        
        response = self.client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4096,
            temperature=0.7,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Parse Claude's structured JSON response
        content = response.content[0].text
        storyboard_data = self._extract_json(content)
        
        # Convert to Pydantic models
        return self._parse_storyboard(storyboard_data, duration)
    
    def _build_storyboard_prompt(
        self,
        text: str,
        style: ExplanationStyle,
        duration: int,
        voice_accent: str
    ) -> str:
        """Build the prompt for Claude to generate the storyboard"""
        
        style_guidelines = {
            ExplanationStyle.SIMPLE: "Use simple language, short sentences, everyday analogies. Target: general audience.",
            ExplanationStyle.ACADEMIC: "Use precise terminology, formal structure, citations style. Target: students/researchers.",
            ExplanationStyle.CHILD_FRIENDLY: "Use playful language, fun analogies, simple concepts. Target: children 8-12.",
            ExplanationStyle.TECHNICAL: "Use technical jargon, detailed explanations, assume prior knowledge. Target: experts."
        }
        
        return f"""You are a professional educational video script writer and storyboard artist. Your job is to transform the following text into an engaging {duration}-second explainer video.

INPUT TEXT:
{text}

STYLE: {style.value}
GUIDELINES: {style_guidelines[style]}
TARGET DURATION: {duration} seconds
VOICE ACCENT: {voice_accent}

YOUR TASK:
1. Create a teaching script that explains the concept clearly in the specified style
2. Break down key points into bullet format
3. Identify 3-5 key concepts/keywords
4. Design a scene-by-scene storyboard with intelligent type classification:

SCENE TYPES:
- **SLIDE** (rendered with Manim): Use for text-heavy content like:
  * Definitions and key terms
  * Bullet point lists
  * Equations or formulas
  * Step-by-step processes
  * Title/intro/outro cards
  * Diagrams (simple shapes and text)

- **VISUAL** (rendered with Mochi AI): Use for photorealistic content like:
  * Real-world examples ("a busy city street", "neurons firing in a brain")
  * Physical demonstrations ("water flowing", "gears turning")
  * Atmospheric B-roll between concepts
  * Visual metaphors ("a seed growing into a tree")
  * Natural phenomena

5. Write a natural voiceover script that narrates smoothly across all scenes

CRITICAL: Balance SLIDE and VISUAL scenes. Aim for 60% slides (text-heavy teaching) and 40% visuals (engagement/examples).

OUTPUT FORMAT (JSON only, no markdown):
{{
  "teaching_script": "...",
  "bullet_breakdown": ["point 1", "point 2", "point 3"],
  "key_concepts": ["concept1", "concept2", "concept3"],
  "scenes": [
    {{
      "id": "scene_1",
      "type": "slide",
      "title": "Introduction",
      "content": "Welcome to our explainer\\nKey topic: ...",
      "duration": 5.0,
      "animation_type": "fade",
      "voiceover_text": "Welcome! Today we'll explore..."
    }},
    {{
      "id": "scene_2",
      "type": "visual",
      "title": "Real World Example",
      "content": "A photorealistic shot of a bustling marketplace with people exchanging goods, warm afternoon lighting, dynamic movement",
      "duration": 6.0,
      "animation_type": "none",
      "voiceover_text": "Imagine a marketplace where..."
    }}
  ],
  "voiceover_script": "Complete narration text with natural pacing...",
  "total_duration": {duration}
}}

IMPORTANT:
- Keep scene durations balanced to match {duration}s total
- For SLIDE scenes: "content" = text to display on screen (use \\n for line breaks)
- For VISUAL scenes: "content" = detailed visual prompt for Mochi (describe lighting, mood, motion, style)
- Make voiceover_text natural and conversational
- Ensure smooth transitions between scenes

Return ONLY valid JSON, no extra text."""

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from Claude's response (handles markdown code blocks)"""
        content = content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Skip first line (```json or ```) and last line (```)
            content = "\n".join(lines[1:-1])
        
        return json.loads(content)
    
    def _parse_storyboard(self, data: Dict[str, Any], target_duration: int) -> Storyboard:
        """Parse raw JSON into Pydantic Storyboard model"""
        
        scenes = []
        for scene_data in data.get("scenes", []):
            scene = Scene(
                id=scene_data["id"],
                type=SceneType(scene_data["type"]),
                title=scene_data["title"],
                content=scene_data["content"],
                duration=scene_data.get("duration", 5.0),
                animation_type=scene_data.get("animation_type", "fade"),
                voiceover_text=scene_data.get("voiceover_text", "")
            )
            scenes.append(scene)
        
        # Normalize durations to match target
        total_scene_duration = sum(s.duration for s in scenes)
        if total_scene_duration > 0:
            scale_factor = target_duration / total_scene_duration
            for scene in scenes:
                scene.duration *= scale_factor
        
        return Storyboard(
            teaching_script=data.get("teaching_script", ""),
            bullet_breakdown=data.get("bullet_breakdown", []),
            key_concepts=data.get("key_concepts", []),
            scenes=scenes,
            voiceover_script=data.get("voiceover_script", ""),
            total_duration=target_duration
        )
