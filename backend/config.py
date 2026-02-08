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
    MAX_TEXT_LENGTH: int = 1500  # Ultra-low cost: reduced to generate very short, cheap videos
    DEFAULT_VIDEO_WIDTH: int = 854  # 480p - lower resolution saves credits
    DEFAULT_VIDEO_HEIGHT: int = 480  # Lower resolution = lower cost
    
    # Redis (for job queue)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Groq API settings (FREE and FAST!)
    GROQ_MODEL: str = "llama-3.3-70b-versatile"  # Free, fast, high-quality
    GROQ_MAX_TOKENS: int = 2048  # Increased for longer, more creative scripts with visual descriptions
    GROQ_TEMPERATURE: float = 0.85  # Higher temperature for more creative scripts
    
    # HeyGen settings
    HEYGEN_API_URL: str = "https://api.heygen.com"
    HEYGEN_AVATAR_ID: str = ""  # Optional: Leave empty to auto-select first available
    HEYGEN_VOICE_ID: str = "1bd001e7e50f421d891986aad5158bc8"  # Default voice
    HEYGEN_POLL_INTERVAL: int = 5  # Seconds between status polls
    HEYGEN_MAX_WAIT_TIME: int = 3600  # Max wait time in seconds (1 hour - effectively no timeout)
    HEYGEN_USE_MULTIPLE_SCENES: bool = False  # Enable multi-scene videos (uses more credits but more creative)
    HEYGEN_MAX_VIDEO_DURATION: int = 90  # Ultra-low cost: 90s max (free plan allows up to 180s)
    HEYGEN_AUTO_TRUNCATE: bool = True  # Automatically truncate scripts that exceed max duration
    HEYGEN_COST_SAVING_MODE: bool = True  # Enable cost-saving optimizations (lower res, shorter videos)
    HEYGEN_DYNAMIC_BROLL: bool = True  # Move avatar to corner on visual-heavy scenes
    HEYGEN_ULTRA_LOW_COST: bool = True  # Ultra-low cost mode: 90s max, 480p, aggressive truncation
    
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
