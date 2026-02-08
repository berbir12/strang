"""
HeyGen integration for AI Avatar video generation

Handles video generation via HeyGen API and polling for completion.
Supports multiple scenes, backgrounds, and visual elements for creative videos.
"""
import httpx
import asyncio
import logging
import re
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from config import settings

# Set up logging
logger = logging.getLogger(__name__)


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

    def _estimate_video_duration(self, script: str) -> float:
        """
        Estimate video duration in seconds based on script length.
        
        Args:
            script: The script text
            
        Returns:
            Estimated duration in seconds
        """
        # Rough estimate: ~150 words per minute = ~2.5 words per second
        # Average word length is ~5 characters, so ~12.5 characters per second
        word_count = len(script.split())
        estimated_seconds = (word_count / 150) * 60
        return estimated_seconds

    def _truncate_script_to_duration(self, script: str, max_duration: int) -> tuple[str, bool]:
        """
        Truncate script to fit within maximum duration, cutting at sentence boundaries.
        
        Args:
            script: The script text to truncate
            max_duration: Maximum duration in seconds
            
        Returns:
            Tuple of (truncated_script, was_truncated)
        """
        # Calculate target word count for max duration
        # ~150 words per minute = 2.5 words per second
        target_words = int((max_duration / 60) * 150)
        
        words = script.split()
        if len(words) <= target_words:
            return script, False
        
        # Truncate to target word count
        truncated_words = words[:target_words]
        truncated_text = ' '.join(truncated_words)
        
        # Find the last sentence boundary (., !, ?) to cut cleanly
        last_period = max(
            truncated_text.rfind('.'),
            truncated_text.rfind('!'),
            truncated_text.rfind('?')
        )
        
        if last_period > len(truncated_text) * 0.7:  # Only use if it's in the last 30% of text
            truncated_text = truncated_text[:last_period + 1]
        
        # Add ellipsis if truncated
        if truncated_text != script:
            truncated_text = truncated_text.rstrip() + "..."
            return truncated_text, True
        
        return script, False

    def _format_error_message(self, error: any) -> str:
        """
        Format error message for better readability.
        
        Args:
            error: Error object (dict, str, or other)
            
        Returns:
            Formatted error message string
        """
        if isinstance(error, dict):
            error_code = error.get("code", "")
            error_detail = error.get("message", error.get("detail", str(error)))
            
            if "PAYMENT" in error_code or "CREDIT" in error_code or "INSUFFICIENT" in error_code:
                return (
                    f"Insufficient HeyGen credits. "
                    f"Please add credits to your HeyGen account at https://app.heygen.com. "
                    f"Error: {error_detail}"
                )
            elif "TOO_LONG" in error_code or "VIDEO_IS_TOO_LONG" in error_code:
                return (
                    f"Video is too long (HeyGen limit: {settings.HEYGEN_MAX_VIDEO_DURATION}s). "
                    f"Please shorten your input text or upgrade your HeyGen plan at https://app.heygen.com. "
                    f"Error: {error_detail}"
                )
            else:
                return f"HeyGen error ({error_code}): {error_detail}"
        elif isinstance(error, str):
            return error
        else:
            return str(error)

    def _split_script_into_scenes(self, script: str, max_scene_length: int = 500) -> list:
        """
        Split a script into multiple scenes for more dynamic video generation.
        
        Args:
            script: The full script text
            max_scene_length: Maximum characters per scene
            
        Returns:
            List of script segments (scenes)
        """
        # If script is short, return as single scene
        if len(script) <= max_scene_length:
            return [script]
        
        # Split by natural breaks (periods, exclamation, question marks followed by space)
        sentences = re.split(r'([.!?]\s+)', script)
        
        scenes = []
        current_scene = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            # If adding this sentence would exceed max length, start new scene
            if len(current_scene) + len(sentence) > max_scene_length and current_scene:
                scenes.append(current_scene.strip())
                current_scene = sentence
            else:
                current_scene += sentence
        
        # Add remaining scene
        if current_scene.strip():
            scenes.append(current_scene.strip())
        
        return scenes if scenes else [script]

    async def generate_avatar_video(
        self,
        script: str,
        avatar_id: Optional[str] = None,
        voice_id: Optional[str] = None,
        video_title: Optional[str] = None,
        avatar_style: Optional[str] = None,
        background_url: Optional[str] = None,
        use_multiple_scenes: Optional[bool] = None,
        scenes: Optional[list[dict]] = None
    ) -> str:
        """
        Start avatar video generation with HeyGen.
        
        Args:
            script: The script for the avatar to speak
            avatar_id: HeyGen avatar ID (uses first available if not specified)
            voice_id: HeyGen voice ID (uses default if not specified)
            video_title: Optional title for the video
            avatar_style: Avatar style (normal, casual, professional, etc.) - uses "normal" if not specified
            
        Returns:
            video_id: The HeyGen video ID for tracking
        """
        
        # If avatar_id is provided, use it; otherwise auto-select first available
        if not avatar_id:
            avatars = await self.list_avatars()
            
            if not avatars:
                raise RuntimeError("No avatars available in your HeyGen account. Please check your API key and account access.")
            
            # Use the first available avatar if none specified
            first_avatar = avatars[0]
            avatar_id = first_avatar.get("avatar_id")
            avatar_name = first_avatar.get("avatar_name", "Unknown")
            print(f"[HeyGenService] Auto-selected first available avatar: {avatar_name} (ID: {avatar_id})")
        else:
            print(f"[HeyGenService] Using provided avatar ID: {avatar_id}")
        
        voice_id = voice_id or self.default_voice_id
        avatar_style = avatar_style or "normal"  # Default to normal if not specified
        
        # Use config setting if not explicitly provided
        if use_multiple_scenes is None:
            use_multiple_scenes = settings.HEYGEN_USE_MULTIPLE_SCENES
        
        # Split script into multiple scenes for more dynamic videos
        if scenes:
            scene_items = scenes
        elif use_multiple_scenes and len(script) > 400:
            scene_items = [
                {"spoken_text": s, "visual_prompt": ""} for s in self._split_script_into_scenes(script, max_scene_length=600)
            ]
            print(f"[HeyGenService] Split script into {len(scene_items)} scenes for dynamic video")
        else:
            scene_items = [{"spoken_text": script, "visual_prompt": ""}]
        
        # Build video inputs for each scene
        video_inputs = []
        for i, scene in enumerate(scene_items):
            scene_script = scene.get("spoken_text", "")
            visual_prompt = scene.get("visual_prompt", "")

            character_payload = {
                "type": "avatar",
                "avatar_id": avatar_id,
                "avatar_style": avatar_style
            }

            # Dynamic B-roll: move avatar to corner on visual-heavy scenes
            if settings.HEYGEN_DYNAMIC_BROLL and visual_prompt and i not in (0, len(scene_items) - 1):
                character_payload["scale"] = 0.3
                character_payload["position"] = {"x": 0.85, "y": 0.15}

            scene_input = {
                "character": character_payload,
                "voice": {
                    "type": "text",
                    "input_text": scene_script,
                    "voice_id": voice_id
                }
            }
            
            # Add background if provided
            if background_url:
                scene_input["background"] = {
                    "type": "image",
                    "url": background_url
                }
            
            # Add visual elements using HeyGen's assets array (correct API format)
            # HeyGen supports: images, videos, text overlays as assets
            # Note: Motion Designer is a studio UI feature; API uses assets
            if visual_prompt:
                # Store the prompt as metadata for potential future image generation
                scene_input["visual_prompt"] = visual_prompt

                # Add assets array for visual elements (image URL can be injected later)
                scene_input["assets"] = [
                    {
                        "type": "text",
                        "content": f"[Visual: {visual_prompt[:80]}...]",
                        "position": {"x": 0.5, "y": 0.9},
                        "style": "caption"
                    }
                ]

                print(f"[HeyGenService] Adding visual asset to scene {i+1}: {visual_prompt[:50]}...")
            
            video_inputs.append(scene_input)
        
        # Use cost-saving resolution if enabled
        if settings.HEYGEN_ULTRA_LOW_COST:
            # Ultra-low cost: 480p resolution
            video_width = 854
            video_height = 480
            print(f"[HeyGenService] Ultra-low cost mode: Using {video_width}x{video_height} resolution (minimal credit usage)")
        elif settings.HEYGEN_COST_SAVING_MODE:
            # Lower resolution saves credits significantly (~40-50% reduction)
            video_width = min(settings.DEFAULT_VIDEO_WIDTH, 854)  # Max 480p
            video_height = min(settings.DEFAULT_VIDEO_HEIGHT, 480)
            print(f"[HeyGenService] Cost-saving mode: Using {video_width}x{video_height} resolution to minimize credit usage")
        else:
            video_width = settings.DEFAULT_VIDEO_WIDTH
            video_height = settings.DEFAULT_VIDEO_HEIGHT
        
        # Build the video generation request
        payload = {
            "video_inputs": video_inputs,
            "dimension": {
                "width": video_width,
                "height": video_height
            }
        }
        
        # Visual elements are handled via assets per scene
        if scenes:
            print(f"[HeyGenService] Visual assets enabled: {len(scenes)} scene(s) with potential diagrams/illustrations")
        
        # Add background settings if available
        if background_url and len(video_inputs) > 0:
            payload["background"] = {
                "type": "image",
                "url": background_url
            }
        
        if video_title:
            payload["title"] = video_title

        max_retries = 3
        retry_delays = [2, 5, 10]  # Exponential backoff in seconds
        
        for attempt in range(max_retries):
            try:
                print(f"[HeyGenService] Submitting video generation request... (attempt {attempt + 1}/{max_retries})")
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/v2/video/generate",
                        headers=self.headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("error"):
                            error_data = data.get("error", {})
                            error_code = error_data.get("code", "unknown")
                            error_message = error_data.get("message", str(data.get("error")))
                            
                            # Handle specific error codes
                            if error_code == "RESOLUTION_NOT_ALLOWED":
                                raise RuntimeError(
                                    f"Video resolution {settings.DEFAULT_VIDEO_WIDTH}x{settings.DEFAULT_VIDEO_HEIGHT} "
                                    f"requires a higher HeyGen plan. Please upgrade your plan or use lower resolution."
                                )
                            elif "PAYMENT" in error_code or "CREDIT" in error_code or "INSUFFICIENT" in error_code:
                                raise RuntimeError(
                                    f"HeyGen account has insufficient credits. "
                                    f"Please add credits to your HeyGen account at https://app.heygen.com. "
                                    f"Error: {error_message}"
                                )
                            elif "TOO_LONG" in error_code or "VIDEO_IS_TOO_LONG" in error_code:
                                # Estimate duration from script
                                estimated_duration = self._estimate_video_duration(script)
                                formatted_error = (
                                    f"Video script is too long (estimated {estimated_duration:.1f}s). "
                                    f"HeyGen free plan limit is 180 seconds. "
                                    f"Please shorten your input text or upgrade your HeyGen plan at https://app.heygen.com. "
                                    f"Error: {error_message}"
                                )
                                raise RuntimeError(formatted_error)
                            elif error_code == "internal_error" and "avatar" in error_message.lower():
                                raise RuntimeError(
                                    f"Avatar '{avatar_id}' not found. The system will auto-select an available avatar. "
                                    f"Use GET /api/avatars to see available avatars."
                                )
                            else:
                                # Use the formatting method for consistent error messages
                                formatted_error = self._format_error_message(error_data)
                                raise RuntimeError(formatted_error)
                        
                        video_id = data.get("data", {}).get("video_id")
                        
                        if not video_id:
                            raise RuntimeError("No video_id returned from HeyGen API")
                        
                        print(f"[HeyGenService] ✓ Video generation started: {video_id}")
                        logger.info(f"Video generation started: {video_id}")
                        return video_id
                    
                    elif response.status_code == 401:
                        error_msg = "HeyGen API authentication failed. Please check your HEYGEN_API_KEY in .env file."
                        print(f"[HeyGenService] ❌ {error_msg}")
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)
                    
                    elif response.status_code == 429:
                        if attempt < max_retries - 1:
                            wait_time = retry_delays[attempt]
                            error_msg = f"Rate limit exceeded. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                            print(f"[HeyGenService] ⚠️ {error_msg}")
                            logger.warning(error_msg)
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_msg = "HeyGen API rate limit exceeded. Please wait a moment and try again."
                            print(f"[HeyGenService] ❌ {error_msg}")
                            logger.error(error_msg)
                            raise RuntimeError(error_msg)
                    
                    elif response.status_code == 404:
                        error_text = response.text
                        if "avatar" in error_text.lower():
                            error_msg = (
                                f"Avatar '{avatar_id}' not found in your HeyGen account. "
                                f"Please use GET /api/avatars to see available avatars."
                            )
                        else:
                            error_msg = f"HeyGen resource not found: {error_text}"
                        print(f"[HeyGenService] ❌ {error_msg}")
                        logger.error(f"404 error: {error_text}")
                        raise RuntimeError(error_msg)
                    
                    else:
                        error_text = response.text
                        error_msg = f"HeyGen API error ({response.status_code}): {error_text}"
                        print(f"[HeyGenService] ❌ {error_msg}")
                        logger.error(error_msg)
                        
                        if attempt < max_retries - 1:
                            wait_time = retry_delays[attempt]
                            print(f"[HeyGenService] Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise RuntimeError(error_msg)
                            
            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    error_msg = f"Request timeout. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                    print(f"[HeyGenService] ⚠️ {error_msg}")
                    logger.warning(f"{error_msg} - {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    error_msg = "HeyGen API request timed out. Please check your internet connection and try again."
                    print(f"[HeyGenService] ❌ {error_msg}")
                    logger.error(f"Timeout after {max_retries} attempts: {e}")
                    raise RuntimeError(error_msg)
                    
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    error_msg = f"Connection error. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                    print(f"[HeyGenService] ⚠️ {error_msg}")
                    logger.warning(f"{error_msg} - {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    error_msg = f"Failed to connect to HeyGen API: {str(e)}. Please check your internet connection."
                    print(f"[HeyGenService] ❌ {error_msg}")
                    logger.error(f"Connection error after {max_retries} attempts: {e}")
                    raise RuntimeError(error_msg)
                    
            except RuntimeError:
                # Re-raise RuntimeError (these are our custom errors)
                raise
                
            except Exception as e:
                error_type = type(e).__name__
                error_msg = f"Unexpected error from HeyGen API: {error_type} - {str(e)}"
                print(f"[HeyGenService] ❌ {error_msg}")
                logger.error(f"Unexpected error: {error_type} - {e}", exc_info=True)
                
                if attempt < max_retries - 1:
                    wait_time = retry_delays[attempt]
                    print(f"[HeyGenService] Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(f"Failed to generate video after {max_retries} attempts: {error_msg}")
        
        # Should never reach here, but just in case
        raise RuntimeError("Failed to generate video: Maximum retries exceeded")

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
                # Try V2 status endpoint first, fallback to V1 if needed
                # V2 format: /v2/video_status with query param
                response = await client.get(
                    f"{self.base_url}/v2/video_status",
                    headers=self.headers,
                    params={"video_id": video_id}
                )
                
                # If V2 returns 404, try V1 endpoint (backward compatibility)
                if response.status_code == 404:
                    print(f"[HeyGenService] V2 status endpoint not found, trying V1...")
                    response = await client.get(
                        f"{self.base_url}/v1/video_status.get",
                        headers=self.headers,
                        params={"video_id": video_id}
                    )
                
                if response.status_code != 200:
                    error_text = response.text if hasattr(response, 'text') else str(response.status_code)
                    return HeyGenVideoResult(
                        video_id=video_id,
                        status=HeyGenVideoStatus.FAILED,
                        error=f"API error: {response.status_code} - {error_text}"
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
                error_msg = result.error
                # Format error message for better readability
                formatted_error = self._format_error_message(error_msg)
                
                print(f"[HeyGenService] ❌ Video failed: {formatted_error}")
                if progress_callback:
                    await progress_callback(0, f"Video failed: {formatted_error}", result)
                # Store formatted error in result for better error messages
                result.error = formatted_error
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
