"""
Pydantic models for API requests and responses
Groq (Script) + Sora (Video) + EdgeTTS (Audio)
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class ScriptStyle(str, Enum):
    """Script style options"""
    DOCUMENTARY = "documentary"
    CINEMATIC = "cinematic"
    NEWS = "news"
    EDUCATIONAL = "educational"
    STORYTELLING = "storytelling"


class JobStatus(str, Enum):
    """Job processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    SCRIPTING = "scripting"          # Groq is generating script
    RENDERING = "rendering"          # Sora/Composer is rendering
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessVideoRequest(BaseModel):
    """Request to process text into video"""
    text: str = Field(..., min_length=10, max_length=3000)
    style: ScriptStyle = ScriptStyle.DOCUMENTARY
    voice_id: Optional[str] = None     # EdgeTTS voice ID


class JobProgress(BaseModel):
    """Job progress information"""
    job_id: str
    status: JobStatus
    progress_percent: int = Field(0, ge=0, le=100)
    current_step: str = ""
    message: str = ""
    error: Optional[str] = None


class ProcessVideoResponse(BaseModel):
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
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    script: Optional[str] = None      # The generated script
    error: Optional[str] = None


class ScriptOnlyRequest(BaseModel):
    """Request to generate script only (without video)"""
    text: str = Field(..., min_length=10, max_length=3000)
    style: ScriptStyle = ScriptStyle.DOCUMENTARY
    duration_hint: Optional[int] = Field(None, ge=30, le=300)


class ScriptOnlyResponse(BaseModel):
    """Response with generated script"""
    original_text: str
    script: str
    style: str
    word_count: int
    estimated_duration_seconds: int


class VoiceInfo(BaseModel):
    """TTS voice information"""
    voice_id: str
    name: str
    language: Optional[str] = None
    gender: Optional[str] = None


class AvailableVoicesResponse(BaseModel):
    """Response with available voices"""
    voices: List[VoiceInfo]

