"""
Configuration for Strang backend service
Groq (free) + HeyGen pipeline
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    GROQ_API_KEY: str = ""         # For Groq free AI script generation
    HEYGEN_API_KEY: str = ""       # For HeyGen avatar video generation
    
    # Server config
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Storage
    OUTPUT_DIR: Path = Path("./outputs")
    TEMP_DIR: Path = Path("./temp")
    MAX_VIDEO_AGE_HOURS: int = 24  # Auto-cleanup old videos
    
    # Video generation
    MAX_TEXT_LENGTH: int = 3000
    DEFAULT_VIDEO_WIDTH: int = 1280  # 720p - works with free/basic plans
    DEFAULT_VIDEO_HEIGHT: int = 720   # Lower res for free tier compatibility
    
    # Redis (for job queue)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Groq API settings (FREE and FAST!)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  # Free, fast, high-quality
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TEMPERATURE: float = 0.7
    
    # HeyGen settings
    HEYGEN_API_URL: str = "https://api.heygen.com"
    HEYGEN_AVATAR_ID: str = ""  # Optional: Leave empty to auto-select first available
    HEYGEN_VOICE_ID: str = "1bd001e7e50f421d891986aad5158bc8"  # Default voice
    HEYGEN_POLL_INTERVAL: int = 5  # Seconds between status polls
    HEYGEN_MAX_WAIT_TIME: int = 3600  # Max wait time in seconds (1 hour - effectively no timeout)
    
    # WebSocket settings
    WEBSOCKET_ENABLED: bool = True
    WEBSOCKET_PING_INTERVAL: int = 20  # seconds
    WEBSOCKET_PING_TIMEOUT: int = 20   # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields in .env for backward compatibility


settings = Settings()

# Ensure directories exist
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
