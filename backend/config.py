"""
Configuration for Strang backend service
Groq (Script) + OpenAI Sora (Video) + EdgeTTS (Audio)
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    GROQ_API_KEY: str = ""         # For script generation
    OPENAI_API_KEY: str = ""       # For Sora video generation
    
    # Server config
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Storage
    OUTPUT_DIR: Path = Path("./outputs")
    TEMP_DIR: Path = Path("./temp")
    MAX_VIDEO_AGE_HOURS: int = 24
    
    # Groq Settings
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_MAX_TOKENS: int = 2048
    GROQ_TEMPERATURE: float = 0.7
    
    # OpenAI Sora Settings
    # Default to a strong general-purpose Sora model.
    SORA_MODEL: str = "sora-2-pro-2025-10-06"
    
    # Video Generation Settings
    DEFAULT_VIDEO_WIDTH: int = 1280
    DEFAULT_VIDEO_HEIGHT: int = 720
    MAX_SCENE_DURATION: int = 10   # Max seconds per Sora clip
    
    # WebSocket settings
    WEBSOCKET_ENABLED: bool = True
    WEBSOCKET_PING_INTERVAL: int = 20
    WEBSOCKET_PING_TIMEOUT: int = 20
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

# Ensure directories exist
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)

