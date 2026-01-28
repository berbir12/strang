"""
Mochi AI integration for photorealistic B-roll generation
"""
from pathlib import Path
import sys
from typing import Optional
from config import settings
from models import Scene as StoryboardScene


class MochiService:
    """Service for generating photorealistic videos using Mochi"""
    
    def __init__(self):
        self.enabled = settings.MOCHI_ENABLED
        self.output_dir = settings.TEMP_DIR / "mochi_renders"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if self.enabled:
            self._init_mochi_pipeline()
    
    def _init_mochi_pipeline(self):
        """Initialize Mochi pipeline (lazy load)"""
        try:
            # Add Mochi to path if installed
            mochi_path = Path(settings.MOCHI_WEIGHTS_PATH).parent
            if str(mochi_path) not in sys.path:
                sys.path.insert(0, str(mochi_path))
            
            from genmo.mochi_preview.pipelines import (
                DecoderModelFactory,
                DitModelFactory,
                MochiSingleGPUPipeline,
                T5ModelFactory,
                linear_quadratic_schedule,
            )
            
            self.pipeline = MochiSingleGPUPipeline(
                text_encoder_factory=T5ModelFactory(),
                dit_factory=DitModelFactory(
                    model_path=f"{settings.MOCHI_WEIGHTS_PATH}/dit.safetensors",
                    model_dtype="bf16"
                ),
                decoder_factory=DecoderModelFactory(
                    model_path=f"{settings.MOCHI_WEIGHTS_PATH}/decoder.safetensors",
                ),
                cpu_offload=settings.MOCHI_CPU_OFFLOAD,
                decode_type="tiled_spatial",
            )
            
            self.linear_quadratic_schedule = linear_quadratic_schedule
            
            print("✓ Mochi pipeline initialized successfully")
            
        except Exception as e:
            print(f"⚠ Warning: Failed to initialize Mochi: {e}")
            print("  Falling back to placeholder videos")
            self.enabled = False
            self.pipeline = None
    
    def render_scene(self, scene_data: StoryboardScene, scene_index: int) -> Path:
        """
        Generate photorealistic B-roll using Mochi
        
        Args:
            scene_data: Scene with visual description in content field
            scene_index: Scene number for naming
        
        Returns:
            Path to rendered .mp4 file
        """
        
        if not self.enabled or self.pipeline is None:
            return self._generate_placeholder(scene_data, scene_index)
        
        try:
            # Extract parameters
            prompt = scene_data.content
            duration_frames = int(scene_data.duration * settings.DEFAULT_FPS)
            
            # Clamp to Mochi's supported range (up to ~10 seconds = 300 frames at 30fps)
            duration_frames = min(duration_frames, 163)  # Mochi supports up to 163 frames
            
            # Ensure odd number of frames for Mochi
            if duration_frames % 2 == 0:
                duration_frames += 1
            
            # Generate video using Mochi
            print(f"Generating Mochi scene {scene_index}: {prompt[:50]}...")
            
            video_array = self.pipeline(
                height=settings.DEFAULT_VIDEO_HEIGHT,
                width=settings.DEFAULT_VIDEO_WIDTH,
                num_frames=duration_frames,
                num_inference_steps=settings.MOCHI_NUM_INFERENCE_STEPS,
                sigma_schedule=self.linear_quadratic_schedule(
                    settings.MOCHI_NUM_INFERENCE_STEPS, 0.025
                ),
                cfg_schedule=[6.0] * settings.MOCHI_NUM_INFERENCE_STEPS,
                batch_cfg=False,
                prompt=prompt,
                negative_prompt="blurry, low quality, distorted, ugly, bad anatomy",
                seed=42 + scene_index,  # Deterministic per scene
            )
            
            # Save to file
            output_path = self.output_dir / f"scene_{scene_index}.mp4"
            self._save_video_array(video_array, output_path)
            
            return output_path
            
        except Exception as e:
            print(f"⚠ Mochi generation failed for scene {scene_index}: {e}")
            return self._generate_placeholder(scene_data, scene_index)
    
    def _save_video_array(self, video_array, output_path: Path):
        """Save Mochi's numpy array output to .mp4 file"""
        import numpy as np
        import subprocess
        import tempfile
        
        # video_array shape: (num_frames, height, width, channels)
        frames = video_array
        
        # Normalize to 0-255 uint8
        if frames.dtype != np.uint8:
            frames = (frames * 255).astype(np.uint8)
        
        # Write raw frames to pipe and encode with ffmpeg
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{frames.shape[2]}x{frames.shape[1]}",
            "-r", str(settings.DEFAULT_FPS),
            "-i", "-",  # Read from stdin
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            str(output_path)
        ]
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Write frames to stdin
        process.stdin.write(frames.tobytes())
        process.stdin.close()
        process.wait()
        
        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg encoding failed: {process.stderr.read().decode()}")
    
    def _generate_placeholder(self, scene_data: StoryboardScene, scene_index: int) -> Path:
        """Generate placeholder video when Mochi is unavailable"""
        from PIL import Image, ImageDraw, ImageFont
        import subprocess
        
        print(f"Generating placeholder for scene {scene_index}")
        
        # Create placeholder image
        img = Image.new('RGB', (settings.DEFAULT_VIDEO_WIDTH, settings.DEFAULT_VIDEO_HEIGHT), color='#2c3e50')
        draw = ImageDraw.Draw(img)
        
        # Try to load font
        try:
            font_large = ImageFont.truetype("arial.ttf", 48)
            font_small = ImageFont.truetype("arial.ttf", 32)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw placeholder text
        text = "B-Roll Placeholder"
        bbox = draw.textbbox((0, 0), text, font=font_large)
        text_width = bbox[2] - bbox[0]
        x = (settings.DEFAULT_VIDEO_WIDTH - text_width) // 2
        draw.text((x, settings.DEFAULT_VIDEO_HEIGHT // 2 - 50), text, fill='white', font=font_large)
        
        # Draw scene description (truncated)
        desc = scene_data.content[:60] + "..." if len(scene_data.content) > 60 else scene_data.content
        bbox = draw.textbbox((0, 0), desc, font=font_small)
        desc_width = bbox[2] - bbox[0]
        x = (settings.DEFAULT_VIDEO_WIDTH - desc_width) // 2
        draw.text((x, settings.DEFAULT_VIDEO_HEIGHT // 2 + 20), desc, fill='#95a5a6', font=font_small)
        
        # Save image
        img_path = self.output_dir / f"placeholder_{scene_index}.png"
        img.save(img_path)
        
        # Convert to video
        video_path = self.output_dir / f"scene_{scene_index}.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-c:v", "libx264",
            "-t", str(scene_data.duration),
            "-pix_fmt", "yuv420p",
            "-r", str(settings.DEFAULT_FPS),
            str(video_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return video_path
