"""
Google Gemma 2 integration for intelligent storyboard generation

Uses the Generative Language API via google-generativeai, with a JSON-only
response format compatible with the previous Claude-based Storyboard.
"""
from typing import Dict, Any
import json
import google.generativeai as genai

from config import settings
from models import ExplanationStyle, Storyboard, Scene, SceneType


class GemmaService:
    """Service for generating intelligent video storyboards using Gemma 2"""

    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY is not configured")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMMA_MODEL)

    def generate_storyboard(
        self,
        text: str,
        style: ExplanationStyle,
        duration: int,
        voice_accent: str,
    ) -> Storyboard:
        """
        Generate a complete video storyboard with intelligent scene classification.

        Gemma decides which scenes should be:
        - SLIDE (Manim): definitions, lists, key points, equations
        - VISUAL (Mochi): real-world examples, demonstrations, B-roll
        """

        prompt = self._build_storyboard_prompt(text, style, duration, voice_accent)

        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        # response.text should be raw JSON because of response_mime_type
        content = response.text
        storyboard_data = self._extract_json(content)

        return self._parse_storyboard(storyboard_data, duration)

    def _build_storyboard_prompt(
        self,
        text: str,
        style: ExplanationStyle,
        duration: int,
        voice_accent: str,
    ) -> str:
        """Build the prompt for Gemma to generate the storyboard"""

        style_guidelines = {
            ExplanationStyle.SIMPLE: "Use simple language, short sentences, everyday analogies. Target: general audience.",
            ExplanationStyle.ACADEMIC: "Use precise terminology, formal structure, and references to underlying principles. Target: students/researchers.",
            ExplanationStyle.CHILD_FRIENDLY: "Use playful language, fun analogies, and very simple concepts. Target: children 8-12.",
            ExplanationStyle.TECHNICAL: "Use technical jargon, detailed explanations, and assume prior knowledge. Target: experts.",
        }

        return f"""You are a professional educational video script writer and storyboard artist.
Your job is to transform the following text into an engaging {duration}-second explainer video.

INPUT TEXT:
{text}

STYLE: {style.value}
GUIDELINES: {style_guidelines[style]}
TARGET DURATION: {duration} seconds
VOICE ACCENT: {voice_accent}

YOUR TASK:
1. Create a teaching script that explains the concept clearly in the specified style.
2. Break down key points into bullet format.
3. Identify 3-5 key concepts/keywords.
4. Design a scene-by-scene storyboard with intelligent type classification:

SCENE TYPES:
- "slide": for text-heavy content like definitions, bullet lists, formulas, steps, diagrams, intro/outro cards.
- "visual": for photorealistic B-roll like real-world examples, demonstrations, visual metaphors, natural phenomena.

Aim for ~60% slide scenes and ~40% visual scenes.

OUTPUT FORMAT:
Return a single JSON object ONLY (no markdown, no commentary), with this exact shape:
{{
  "teaching_script": "string",
  "bullet_breakdown": ["string", "string", "string"],
  "key_concepts": ["string", "string", "string"],
  "scenes": [
    {{
      "id": "scene_1",
      "type": "slide",
      "title": "string",
      "content": "string with \\n for line breaks",
      "duration": 5.0,
      "animation_type": "fade",
      "voiceover_text": "string"
    }},
    {{
      "id": "scene_2",
      "type": "visual",
      "title": "string",
      "content": "detailed visual prompt for photorealistic B-roll (lighting, mood, motion, style)",
      "duration": 6.0,
      "animation_type": "none",
      "voiceover_text": "string"
    }}
  ],
  "voiceover_script": "full narration text",
  "total_duration": {duration}
}}

REQUIREMENTS:
- The JSON MUST be valid and parseable.
- No markdown code fences, no explanations; JSON only.
- Scene durations should roughly sum to {duration} seconds.
- For slide scenes: "content" is what appears on screen (with \\n between lines).
- For visual scenes: "content" is a rich visual description for a video diffusion model.
"""

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from model response (defensive against extra text)"""
        content = content.strip()

        # If model accidentally returned markdown code fences, strip them
        if content.startswith("```"):
            lines = content.split("\n")
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
                voiceover_text=scene_data.get("voiceover_text", ""),
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
            total_duration=target_duration,
        )

