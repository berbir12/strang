"""
Configuration for Strang backend service
"""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Keys
    GOOGLE_API_KEY: str = ""   # For Gemma 2 / Generative Language API
    OPENAI_API_KEY: str = ""   # For TTS
    
    # Model paths
    MOCHI_WEIGHTS_PATH: str = "./weights"  # Path to Mochi model weights
    
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
    DEFAULT_VIDEO_WIDTH: int = 1280
    DEFAULT_VIDEO_HEIGHT: int = 720
    DEFAULT_FPS: int = 30
    
    # Mochi settings
    MOCHI_NUM_INFERENCE_STEPS: int = 64
    MOCHI_ENABLED: bool = True  # Set False if no GPU available
    MOCHI_CPU_OFFLOAD: bool = True
    
    # Redis (for job queue)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Gemma / Generative Language model
    GEMMA_MODEL: str = "gemma-2-9b-it"  # or gemma-2-27b-it
    
    # TTS settings
    TTS_PROVIDER: str = "openai"  # "openai" or "elevenlabs" or "none"
    TTS_VOICE: str = "alloy"      # OpenAI voice
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
