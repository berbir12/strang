"""
Video compositor - stitches Manim slides + Mochi visuals + audio + subtitles
"""
from pathlib import Path
from typing import List, Optional
import subprocess
import json
from models import Scene, Storyboard
from config import settings


class VideoCompositor:
    """Compose final video from rendered clips"""
    
    def __init__(self):
        self.output_dir = settings.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def compose_final_video(
        self,
        video_clips: List[Path],
        storyboard: Storyboard,
        audio_path: Optional[Path],
        job_id: str
    ) -> tuple[Path, str]:
        """
        Combine all video clips, add audio and subtitles
        
        Args:
            video_clips: List of paths to rendered scene videos (in order)
            storyboard: Original storyboard with timing metadata
            audio_path: Path to voiceover audio (or None)
            job_id: Job identifier for naming
        
        Returns:
            (video_path, srt_content) tuple
        """
        
        print(f"Compositing {len(video_clips)} clips...")
        
        # Step 1: Concatenate video clips
        concat_video = self._concatenate_clips(video_clips, job_id)
        
        # Step 2: Generate SRT subtitles
        srt_content = self._generate_srt(storyboard)
        srt_path = self.output_dir / f"{job_id}.srt"
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        # Step 3: Add audio (if available)
        if audio_path and audio_path.exists():
            video_with_audio = self._add_audio(concat_video, audio_path, job_id)
        else:
            video_with_audio = concat_video
        
        # Step 4: Burn in subtitles
        final_video = self._add_subtitles(video_with_audio, srt_path, job_id)
        
        print(f"✓ Final video: {final_video}")
        
        return final_video, srt_content
    
    def _concatenate_clips(self, clips: List[Path], job_id: str) -> Path:
        """Concatenate multiple video clips"""
        
        if len(clips) == 1:
            return clips[0]
        
        # Create concat file for ffmpeg
        concat_file = settings.TEMP_DIR / f"{job_id}_concat.txt"
        with open(concat_file, 'w') as f:
            for clip in clips:
                f.write(f"file '{clip.absolute()}'\n")
        
        output_path = settings.TEMP_DIR / f"{job_id}_concatenated.mp4"
        
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            # If copy codec fails, re-encode
            print("Copy codec failed, re-encoding...")
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                str(output_path)
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        
        return output_path
    
    def _add_audio(self, video_path: Path, audio_path: Path, job_id: str) -> Path:
        """Add voiceover audio to video"""
        
        output_path = settings.TEMP_DIR / f"{job_id}_with_audio.mp4"
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",  # Match shortest stream duration
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return output_path
    
    def _add_subtitles(self, video_path: Path, srt_path: Path, job_id: str) -> Path:
        """Burn subtitles into video"""
        
        final_path = self.output_dir / f"{job_id}.mp4"
        
        # Escape path for subtitles filter
        srt_path_escaped = str(srt_path).replace('\\', '/').replace(':', '\\:')
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vf", f"subtitles='{srt_path_escaped}':force_style='FontSize=20,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=2'",
            "-c:a", "copy",
            "-preset", "fast",
            "-crf", "23",
            str(final_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return final_path
    
    def _generate_srt(self, storyboard: Storyboard) -> str:
        """Generate SRT subtitle file from storyboard"""
        
        srt_lines = []
        current_time = 0.0
        
        for i, scene in enumerate(storyboard.scenes, start=1):
            start_time = current_time
            end_time = current_time + scene.duration
            
            # Format timestamps
            start_str = self._format_srt_time(start_time)
            end_str = self._format_srt_time(end_time)
            
            # Get subtitle text (prefer voiceover_text, fallback to title)
            subtitle_text = scene.voiceover_text or scene.title
            
            # SRT entry
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(subtitle_text)
            srt_lines.append("")  # Blank line
            
            current_time = end_time
        
        return "\n".join(srt_lines)
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format time in SRT format: HH:MM:SS,mmm"""
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def create_thumbnail(self, video_path: Path, job_id: str) -> Path:
        """Extract thumbnail from video (first frame)"""
        
        thumb_path = self.output_dir / f"{job_id}_thumb.jpg"
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vf", "select=eq(n\\,0)",
            "-vframes", "1",
            "-q:v", "2",
            str(thumb_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        
        return thumb_path
