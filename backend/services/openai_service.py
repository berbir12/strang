"""
OpenAI Sora Integration Service
Handles interactions with the OpenAI API for video generation.
Follows: https://developers.openai.com/api/docs/guides/video-generation
- Create job (POST /videos) -> poll status (GET /videos/{id}) -> download MP4 (GET /videos/{id}/content)
"""
import httpx
from openai import OpenAI
from config import settings
import logging
import asyncio
import time
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

# Retry config for rate limits (429)
SORA_RATE_LIMIT_MAX_RETRIES = 4
SORA_RATE_LIMIT_INITIAL_WAIT = 15
SORA_RATE_LIMIT_BACKOFF_FACTOR = 2

# Poll interval (guide: "every 10–20 seconds")
SORA_POLL_INTERVAL = 10

class OpenAIService:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        # Use a custom httpx client to avoid OpenAI SDK passing 'proxies' (incompatible with httpx 0.28+)
        _http_client = httpx.Client()
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY, http_client=_http_client)
        self.model = settings.SORA_MODEL
        print(f"[OpenAIService] Initialized with model: {self.model}")

    def generate_video_clip(self, prompt: str, size: str = "1280x720", duration_seconds: int = 5) -> str:
        """
        Generate a single video clip using Sora.
        Blocking call (sync) - should be run in executor or thread.
        
        Args:
            prompt: detailed visual description
            size: resolution "WxH"
            duration_seconds: duration in seconds (usually 4, 8, 12, max 20)
            
        Returns:
            Local filesystem path to the generated MP4 video
        """
        # Clamp duration to available buckets if needed, or rely on API validation
        # Sora typically supports specific increments
        
        print(f"[OpenAIService] Generating clip for prompt: {prompt[:50]}...")

        def _is_rate_limit(err: Exception) -> bool:
            msg = str(err).lower()
            return "429" in msg or "rate limit" in msg or "rate_limit" in msg

        # Map arbitrary duration to Sora's supported buckets: 4, 8, 12
        if duration_seconds <= 4:
            sora_seconds = "4"
        elif duration_seconds <= 8:
            sora_seconds = "8"
        else:
            sora_seconds = "12"

        # Resolve output dir before any API calls (avoids confusion with API response objects)
        temp_dir = getattr(settings, "TEMP_DIR", None) or Path("./temp")
        output_dir = Path(temp_dir) if not isinstance(temp_dir, Path) else temp_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        for attempt in range(SORA_RATE_LIMIT_MAX_RETRIES):
            try:
                # Kick off a video job (returns a job object with .id, .status; no .url)
                video_job = self.client.videos.create(
                    model=self.model,
                    prompt=prompt,
                    size=size,
                    seconds=sora_seconds,
                )
                video_id = getattr(video_job, "id", None)
                if not video_id:
                    raise RuntimeError("Sora create() did not return a job id")

                # Poll until completed or failed (no timeout; Sora can take several minutes)
                while True:
                    job = self.client.videos.retrieve(video_id)
                    if job.status == "completed":
                        break
                    if job.status == "failed":
                        err = getattr(job, "error", None)
                        message = getattr(err, "message", "Video generation failed") if err else "Video generation failed"
                        code = getattr(err, "code", "unknown") if err else "unknown"
                        raise RuntimeError(f"Sora job failed: {code} - {message}")

                    time.sleep(SORA_POLL_INTERVAL)

                # Download the MP4 (guide: GET /videos/{id}/content, then write_to_file)
                content = self.client.videos.download_content(video_id, variant="video")
                file_path = output_dir / f"{video_id}.mp4"
                content.write_to_file(str(file_path))

                return str(file_path)

            except Exception as e:
                if _is_rate_limit(e) and attempt < SORA_RATE_LIMIT_MAX_RETRIES - 1:
                    wait = SORA_RATE_LIMIT_INITIAL_WAIT * (SORA_RATE_LIMIT_BACKOFF_FACTOR ** attempt)
                    logger.warning(
                        f"Sora rate limited (429), retry {attempt + 1}/{SORA_RATE_LIMIT_MAX_RETRIES} in {wait}s: {e}"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"Sora generation failed: {e}")
                    raise RuntimeError(f"Sora generation failed: {e}")

    async def generate_scene_video(self, scene_prompt: str) -> str:
        """
        Async wrapper for video generation
        """
        # Run blocking OpenAI call in thread pool
        # For Sora, generation might take 10-60s or be async polling
        # This is a simplified "create" call assumption
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_video_clip, scene_prompt)
