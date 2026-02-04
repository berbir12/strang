"""
Pydantic models for API requests and responses
Groq (FREE) + HeyGen pipeline
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class ScriptStyle(str, Enum):
    """Script style options"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    EDUCATIONAL = "educational"
    FRIENDLY = "friendly"


class JobStatus(str, Enum):
    """Job processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    SCRIPTING = "scripting"          # Groq is generating script
    RENDERING = "rendering"           # HeyGen is rendering video
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessVideoRequest(BaseModel):
    """Request to process text into avatar video"""
    text: str = Field(..., min_length=10, max_length=3000)
    style: ScriptStyle = ScriptStyle.PROFESSIONAL
    avatar_id: Optional[str] = None    # HeyGen avatar ID
    voice_id: Optional[str] = None     # HeyGen voice ID


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
    style: ScriptStyle = ScriptStyle.PROFESSIONAL
    duration_hint: Optional[int] = Field(None, ge=30, le=300)


class ScriptOnlyResponse(BaseModel):
    """Response with generated script"""
    original_text: str
    script: str
    style: str
    word_count: int
    estimated_duration_seconds: int


class AvatarInfo(BaseModel):
    """HeyGen avatar information"""
    avatar_id: str
    name: str
    preview_url: Optional[str] = None


class VoiceInfo(BaseModel):
    """HeyGen voice information"""
    voice_id: str
    name: str
    language: Optional[str] = None
    gender: Optional[str] = None


class AvailableAvatarsResponse(BaseModel):
    """Response with available avatars"""
    avatars: List[AvatarInfo]


class AvailableVoicesResponse(BaseModel):
    """Response with available voices"""
    voices: List[VoiceInfo]
