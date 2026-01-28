"""
Manim scene generator for text-based slides
"""
from pathlib import Path
import subprocess
import tempfile
import os
from models import Scene as StoryboardScene
from config import settings

# Try to import manimlib, but don't crash if it's not available
try:
    from manimlib import Scene, Text, FadeIn, FadeOut, Write, ReplacementTransform, VGroup, UP, DOWN, LEFT
    MANIM_AVAILABLE = True
except ImportError:
    print("⚠ Warning: manimlib not installed. Manim rendering will use fallback.")
    MANIM_AVAILABLE = False


class ManimGenerator:
    """Generate animated slides using Manim"""
    
    def __init__(self):
        self.output_dir = settings.TEMP_DIR / "manim_renders"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def render_scene(self, scene_data: StoryboardScene, scene_index: int) -> Path:
        """
        Render a single slide scene using Manim
        
        Returns path to rendered .mp4 file
        """
        
        # If Manim not available, use fallback immediately
        if not MANIM_AVAILABLE:
            print(f"Manim not available, using fallback for scene {scene_index}")
            fallback = SimpleManimFallback()
            return fallback.render_scene(scene_data, scene_index)
        
        # Generate Python code for the Manim scene
        scene_code = self._generate_scene_code(scene_data, scene_index)
        
        # Write to temporary Python file
        scene_file = self.output_dir / f"scene_{scene_index}.py"
        with open(scene_file, 'w', encoding='utf-8') as f:
            f.write(scene_code)
        
        # Render using manimgl CLI
        output_file = self._render_with_manim(scene_file, scene_index)
        
        return output_file
    
    def _generate_scene_code(self, scene_data: StoryboardScene, scene_index: int) -> str:
        """Generate Python code for Manim scene"""
        
        # Escape special characters in content
        content_lines = scene_data.content.split('\\n')
        title_text = scene_data.title.replace('"', '\\"')
        
        # Build text objects for each line
        text_objects = []
        for i, line in enumerate(content_lines):
            line = line.strip()
            if not line:
                continue
            
            # Escape quotes
            line = line.replace('"', '\\"')
            
            # Determine font size based on position (title vs body)
            font_size = 48 if i == 0 else 36
            position = f"UP * {2 - i * 0.8}" if i == 0 else f"UP * {1 - i * 0.6}"
            
            text_objects.append(f"""
        text_{i} = Text(
            "{line}",
            font_size={font_size},
            color=WHITE
        ).move_to({position})""")
        
        # Choose animation based on animation_type
        animation_map = {
            "fade": "FadeIn",
            "write": "Write",
            "slide": "FadeIn"  # Can customize later
        }
        animation = animation_map.get(scene_data.animation_type, "FadeIn")
        
        # Generate complete scene class
        scene_code = f'''"""
Auto-generated Manim scene for: {title_text}
"""
from manimlib import *

class ExplainerScene{scene_index}(Scene):
    """Scene: {title_text}"""
    
    def construct(self):
        # Set background color
        self.camera.background_color = "#1a1a1a"
        
        # Create text objects
{"".join(text_objects)}
        
        # Group all text
        all_text = VGroup({"".join([f"text_{i}" for i in range(len(text_objects))])})
        
        # Animate
        self.play({animation}(all_text))
        self.wait({scene_data.duration - 1})
        self.play(FadeOut(all_text))
'''
        
        return scene_code
    
    def _render_with_manim(self, scene_file: Path, scene_index: int) -> Path:
        """
        Execute manimgl to render the scene
        
        Returns path to output video file
        """
        
        output_path = self.output_dir / f"scene_{scene_index}.mp4"
        
        # Run manimgl command
        cmd = [
            "manimgl",
            str(scene_file),
            f"ExplainerScene{scene_index}",
            "-w",  # Write to file
            "--resolution", f"{settings.DEFAULT_VIDEO_WIDTH},{settings.DEFAULT_VIDEO_HEIGHT}",
            "--frame_rate", str(settings.DEFAULT_FPS),
            "-o", str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout per scene
                check=True
            )
            
            if not output_path.exists():
                raise RuntimeError(f"Manim did not produce output file: {output_path}")
            
            return output_path
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Manim rendering timed out for scene {scene_index}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Manim rendering failed: {e.stderr}")
    
    def cleanup(self):
        """Remove temporary files"""
        # Keep rendered videos, only clean up .py files
        for py_file in self.output_dir.glob("scene_*.py"):
            py_file.unlink()


# Simplified fallback for when manimgl is not available or fails
class SimpleManimFallback:
    """Generate simple text slides using PIL as fallback"""
    
    def __init__(self):
        from PIL import Image, ImageDraw, ImageFont
        self.Image = Image
        self.ImageDraw = ImageDraw
        self.ImageFont = ImageFont
        self.output_dir = settings.TEMP_DIR / "simple_renders"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def render_scene(self, scene_data: StoryboardScene, scene_index: int) -> Path:
        """Create a simple static image and convert to video"""
        
        # Create image
        img = self.Image.new('RGB', (settings.DEFAULT_VIDEO_WIDTH, settings.DEFAULT_VIDEO_HEIGHT), color='#1a1a1a')
        draw = self.ImageDraw.Draw(img)
        
        # Try to load a nice font
        try:
            font_title = self.ImageFont.truetype("arial.ttf", 60)
            font_body = self.ImageFont.truetype("arial.ttf", 40)
        except:
            font_title = self.ImageFont.load_default()
            font_body = self.ImageFont.load_default()
        
        # Draw title
        title_bbox = draw.textbbox((0, 0), scene_data.title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (settings.DEFAULT_VIDEO_WIDTH - title_width) // 2
        draw.text((title_x, 100), scene_data.title, fill='white', font=font_title)
        
        # Draw content lines
        lines = scene_data.content.split('\\n')
        y_offset = 250
        for line in lines[:5]:  # Max 5 lines
            if not line.strip():
                continue
            bbox = draw.textbbox((0, 0), line, font=font_body)
            line_width = bbox[2] - bbox[0]
            x = (settings.DEFAULT_VIDEO_WIDTH - line_width) // 2
            draw.text((x, y_offset), line, fill='white', font=font_body)
            y_offset += 80
        
        # Save image
        img_path = self.output_dir / f"scene_{scene_index}.png"
        img.save(img_path)
        
        # Convert to video using ffmpeg
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
