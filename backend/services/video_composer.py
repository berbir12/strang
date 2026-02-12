"""
Video Composer Service
Stitches Video Clips (MP4) and Audio (MP3) into final video.
"""
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx.Loop import Loop
from pathlib import Path
import logging
from typing import List, Dict
from config import settings

logger = logging.getLogger(__name__)

class VideoComposer:
    def __init__(self):
        self.output_dir = settings.OUTPUT_DIR
        
    def compose_video(self, scenes: List[Dict], job_id: str) -> str:
        """
        Compose final video from a list of scene dictionaries.
        
        Args:
            scenes: List of dicts, each containing:
                - video_path: Path/URL to local MP4 clip
                - audio_path: Path to local MP3 audio
            job_id: Unique Job ID
            
        Returns:
            Path string to the final video
        """
        print(f"[VideoComposer] Composing {len(scenes)} scenes...")
        
        final_clips = []
        
        try:
            for i, scene in enumerate(scenes):
                video_path = scene.get('video_path')
                audio_path = scene.get('audio_path')
                
                if not video_path:
                    logger.warning(f"Scene {i} missing video, skipping...")
                    continue
                    
                # Load Video
                # Note: If video_path is a URL, moviepy might not handle it directly optimally.
                # Ideally, we should double check these are local paths.
                # Assuming caller performs download if needed.
                clip = VideoFileClip(str(video_path))
                
                # Load Audio if present
                if audio_path:
                    audio = AudioFileClip(str(audio_path))
                    # Set video duration to match audio (loop or cut video?)
                    # For Sora clips (e.g. 5s), if audio is long (10s), we loop or reverse-loop
                    # If audio is short, we cut video.
                    
                    if audio.duration > clip.duration:
                        # Loop video to match audio (MoviePy 2.x: use Loop effect)
                        clip = clip.with_effects([Loop(duration=audio.duration)])
                    else:
                        # Trim video to match audio (MoviePy 2.x: subclipped)
                        clip = clip.subclipped(0, audio.duration)

                    clip = clip.with_audio(audio)
                
                final_clips.append(clip)
            
            if not final_clips:
                raise RuntimeError("No valid clips to compose")
                
            # Concatenate all scenes
            final_video = concatenate_videoclips(final_clips, method="compose")
            
            output_filename = f"strang_{job_id}.mp4"
            output_path = self.output_dir / output_filename
            
            # Write file
            final_video.write_videofile(
                str(output_path),
                fps=24,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger=None # Silence standard logger
            )
            
            print(f"[VideoComposer] ✓ Video rendered: {output_path}")
            return f"/outputs/{output_filename}"
            
        except Exception as e:
            logger.error(f"Composition failed: {e}")
            raise RuntimeError(f"Composition failed: {e}")
        finally:
            # Cleanup resources
            # MoviePy often leaves handles open, explicit close helps
            try:
                for clip in final_clips:
                    clip.close()
                    if clip.audio: clip.audio.close()
            except:
                pass
