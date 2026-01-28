"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from enum import Enum


class ExplanationStyle(str, Enum):
    """Video explanation style"""
    SIMPLE = "simple"
    ACADEMIC = "academic"
    CHILD_FRIENDLY = "child-friendly"
    TECHNICAL = "technical"


class VoiceAccent(str, Enum):
    """Voice accent options"""
    US = "us"
    UK = "uk"
    AU = "au"
    NEUTRAL = "neutral"


class SceneType(str, Enum):
    """Scene rendering type"""
    SLIDE = "slide"  # Manim text-based slide
    VISUAL = "visual"  # Mochi photorealistic B-roll


class Scene(BaseModel):
    """Individual scene in the storyboard"""
    id: str
    type: SceneType
    title: str
    content: str  # Slide text or visual description
    duration: float  # seconds
    animation_type: Optional[str] = "fade"  # fade, slide, write, etc.
    voiceover_text: Optional[str] = None


class Storyboard(BaseModel):
    """Complete video storyboard from Claude"""
    teaching_script: str
    bullet_breakdown: List[str]
    key_concepts: List[str]
    scenes: List[Scene]
    voiceover_script: str
    total_duration: float


class GenerateVideoRequest(BaseModel):
    """Request to generate explainer video"""
    text: str = Field(..., min_length=10, max_length=3000)
    style: ExplanationStyle = ExplanationStyle.SIMPLE
    duration: int = Field(60, ge=30, le=120)
    voice_accent: VoiceAccent = VoiceAccent.US
    include_mochi: bool = True  # Allow disabling Mochi if GPU unavailable


class JobStatus(str, Enum):
    """Job processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    GENERATING_STORYBOARD = "generating_storyboard"
    RENDERING_SLIDES = "rendering_slides"
    RENDERING_VISUALS = "rendering_visuals"
    GENERATING_VOICEOVER = "generating_voiceover"
    COMPOSITING = "compositing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobProgress(BaseModel):
    """Job progress information"""
    job_id: str
    status: JobStatus
    progress_percent: int = Field(0, ge=0, le=100)
    current_step: str = ""
    message: str = ""
    error: Optional[str] = None


class GenerateVideoResponse(BaseModel):
    """Response with job ID for async processing"""
    job_id: str
    status: JobStatus
    message: str
    estimated_time_seconds: int


class VideoResult(BaseModel):
    """Final video generation result"""
    job_id: str
    status: JobStatus
    video_url: Optional[str] = None
    srt_content: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None
