"""
HeyGen integration for AI Avatar video generation

Handles video generation via HeyGen API and polling for completion.
"""
import httpx
import asyncio
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from config import settings


class HeyGenVideoStatus(str, Enum):
    """HeyGen video generation status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HeyGenVideoResult:
    """Result of HeyGen video generation"""
    video_id: str
    status: HeyGenVideoStatus
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None


class HeyGenService:
    """Service for generating AI avatar videos using HeyGen"""
    
    def __init__(self):
        """Initialize HeyGen service"""
        if not settings.HEYGEN_API_KEY:
            raise RuntimeError("HEYGEN_API_KEY is not configured")
        
        self.api_key = settings.HEYGEN_API_KEY
        self.base_url = settings.HEYGEN_API_URL
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Default voice setting (avatar will be auto-selected if not provided)
        self.default_voice_id = settings.HEYGEN_VOICE_ID
        self.default_avatar_id = settings.HEYGEN_AVATAR_ID or None  # None means auto-select
        
        if self.default_avatar_id:
            print(f"[HeyGenService] Initialized with default avatar: {self.default_avatar_id}")
        else:
            print(f"[HeyGenService] Initialized - will auto-select first available avatar")

    async def generate_avatar_video(
        self,
        script: str,
        avatar_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        video_title: Optional[str] = None
    ) -> str:
        """
        Start avatar video generation with HeyGen.
        
        Args:
            script: The script for the avatar to speak
            avatar_id: Ignored - always uses first available avatar
            voice_id: HeyGen voice ID (uses default if not specified)
            video_title: Optional title for the video
            
        Returns:
            video_id: The HeyGen video ID for tracking
        """
        
        # Always get available avatars and use the first one (completely ignore any provided avatar_id)
        avatars = await self.list_avatars()
        
        if not avatars:
            raise RuntimeError("No avatars available in your HeyGen account. Please check your API key and account access.")
        
        # Always use the first available avatar (ignore any provided avatar_id)
        first_avatar = avatars[0]
        avatar_id = first_avatar.get("avatar_id")
        avatar_name = first_avatar.get("avatar_name", "Unknown")
        print(f"[HeyGenService] Auto-selected first available avatar: {avatar_name} (ID: {avatar_id})")
        
        voice_id = voice_id or self.default_voice_id
        
        # Build the video generation request
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal"
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": voice_id
                    }
                }
            ],
            "dimension": {
                "width": settings.DEFAULT_VIDEO_WIDTH,
                "height": settings.DEFAULT_VIDEO_HEIGHT
            }
        }
        
        if video_title:
            payload["title"] = video_title

        try:
            print(f"[HeyGenService] Submitting video generation request...")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/v2/video/generate",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    print(f"[HeyGenService] API Error: {response.status_code} - {error_text}")
                    
                    # Provide helpful error message for avatar not found
                    if response.status_code == 404 and "avatar" in error_text.lower():
                        error_msg = (
                            f"Avatar '{avatar_id}' not found in your HeyGen account. "
                            f"Please use GET /api/avatars to see available avatars, "
                            f"or update HEYGEN_AVATAR_ID in your .env file."
                        )
                        raise RuntimeError(error_msg)
                    
                    raise RuntimeError(f"HeyGen API error: {response.status_code} - {error_text}")
                
                data = response.json()
                
                if data.get("error"):
                    raise RuntimeError(f"HeyGen error: {data['error']}")
                
                video_id = data.get("data", {}).get("video_id")
                
                if not video_id:
                    raise RuntimeError("No video_id returned from HeyGen")
                
                print(f"[HeyGenService] ✓ Video generation started: {video_id}")
                return video_id
                
        except httpx.RequestError as e:
            print(f"[HeyGenService] ❌ Request failed: {e}")
            raise RuntimeError(f"Failed to connect to HeyGen API: {e}")

    async def get_video_status(self, video_id: str) -> HeyGenVideoResult:
        """
        Check the status of a video generation job.
        
        Args:
            video_id: The HeyGen video ID
            
        Returns:
            HeyGenVideoResult with current status and video URL if complete
        """
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/v1/video_status.get",
                    headers=self.headers,
                    params={"video_id": video_id}
                )
                
                if response.status_code != 200:
                    return HeyGenVideoResult(
                        video_id=video_id,
                        status=HeyGenVideoStatus.FAILED,
                        error=f"API error: {response.status_code}"
                    )
                
                data = response.json()
                video_data = data.get("data", {})
                
                status_str = video_data.get("status", "pending").lower()
                
                # Map HeyGen status to our enum
                if status_str in ["completed", "complete"]:
                    status = HeyGenVideoStatus.COMPLETED
                elif status_str in ["failed", "error"]:
                    status = HeyGenVideoStatus.FAILED
                elif status_str in ["processing", "rendering"]:
                    status = HeyGenVideoStatus.PROCESSING
                else:
                    status = HeyGenVideoStatus.PENDING
                
                return HeyGenVideoResult(
                    video_id=video_id,
                    status=status,
                    video_url=video_data.get("video_url"),
                    thumbnail_url=video_data.get("thumbnail_url"),
                    duration=video_data.get("duration"),
                    error=video_data.get("error")
                )
                
        except httpx.RequestError as e:
            print(f"[HeyGenService] Status check failed: {e}")
            return HeyGenVideoResult(
                video_id=video_id,
                status=HeyGenVideoStatus.FAILED,
                error=f"Failed to check status: {e}"
            )

    async def wait_for_completion(
        self,
        video_id: str,
        progress_callback: Optional[callable] = None
    ) -> HeyGenVideoResult:
        """
        Poll for video completion with progress updates.
        
        Args:
            video_id: The HeyGen video ID
            progress_callback: Optional async callback for progress updates
            
        Returns:
            HeyGenVideoResult with final status and video URL
        """
        
        poll_interval = settings.HEYGEN_POLL_INTERVAL
        elapsed = 0
        
        print(f"[HeyGenService] Waiting for video completion: {video_id} (no timeout)")
        
        # Wait indefinitely until video completes or fails
        while True:
            result = await self.get_video_status(video_id)
            
            if result.status == HeyGenVideoStatus.COMPLETED:
                print(f"[HeyGenService] ✓ Video completed: {result.video_url}")
                if progress_callback:
                    await progress_callback(100, "Video rendering complete!", result)
                return result
                
            elif result.status == HeyGenVideoStatus.FAILED:
                print(f"[HeyGenService] ❌ Video failed: {result.error}")
                if progress_callback:
                    await progress_callback(0, f"Video failed: {result.error}", result)
                return result
            
            # Update progress (show elapsed time)
            if progress_callback:
                # Show progress based on elapsed time (rough estimate)
                progress_percent = min(95, 35 + int((elapsed / 600) * 60))  # Rough estimate: 0-95% over ~10 min
                await progress_callback(
                    progress_percent,
                    f"HeyGen is rendering your avatar video... ({elapsed}s elapsed)",
                    result
                )
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

    async def list_avatars(self) -> list:
        """
        Get list of available avatars.
        
        Returns:
            List of avatar dictionaries with id, name, preview_url, etc.
        """
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/v2/avatars",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    print(f"[HeyGenService] Failed to list avatars: {response.status_code}")
                    return []
                
                data = response.json()
                avatars = data.get("data", {}).get("avatars", [])
                return avatars
                
        except httpx.RequestError as e:
            print(f"[HeyGenService] Failed to list avatars: {e}")
            return []

    async def list_voices(self) -> list:
        """
        Get list of available voices.
        
        Returns:
            List of voice dictionaries with voice_id, name, language, etc.
        """
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/v2/voices",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    print(f"[HeyGenService] Failed to list voices: {response.status_code}")
                    return []
                
                data = response.json()
                voices = data.get("data", {}).get("voices", [])
                return voices
                
        except httpx.RequestError as e:
            print(f"[HeyGenService] Failed to list voices: {e}")
            return []
