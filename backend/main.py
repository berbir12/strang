"""
Strang Backend API - Hybrid Manim + Mochi video generation
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn

from config import settings
from models import (
    GenerateVideoRequest,
    GenerateVideoResponse,
    JobProgress,
    VideoResult,
    JobStatus
)
from utils.job_manager import job_manager
from services.gemma_service import GemmaService
from services.manim_generator import ManimGenerator, SimpleManimFallback
from services.mochi_service import MochiService
from services.tts_service import TTSService
from services.compositor import VideoCompositor

# Initialize FastAPI app
app = FastAPI(
    title="Strang Video Generation API",
    description="Hybrid Manim + Mochi explainer video generator",
    version="1.0.0"
)

# CORS middleware for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated videos as static files
app.mount("/outputs", StaticFiles(directory=str(settings.OUTPUT_DIR)), name="outputs")

# Initialize services
claude_service = GemmaService()
manim_generator = ManimGenerator()
mochi_service = MochiService()
tts_service = TTSService()
compositor = VideoCompositor()


def process_video_generation(
    job_id: str,
    request: GenerateVideoRequest
) -> dict:
    """
    Main video generation pipeline
    
    This function runs in the background and updates job progress
    """
    
    try:
        # Step 1: Generate storyboard with Claude (10%)
        job_manager.update_progress(
            job_id,
            JobStatus.GENERATING_STORYBOARD,
            10,
            "generating_storyboard",
            "Generating intelligent storyboard with Claude..."
        )
        
        storyboard = claude_service.generate_storyboard(
            text=request.text,
            style=request.style,
            duration=request.duration,
            voice_accent=request.voice_accent.value
        )
        
        print(f"✓ Storyboard generated: {len(storyboard.scenes)} scenes")
        
        # Step 2: Render scenes (10-60%)
        video_clips = []
        total_scenes = len(storyboard.scenes)
        
        for i, scene in enumerate(storyboard.scenes):
            progress = 10 + int(50 * (i / total_scenes))
            
            if scene.type.value == "slide":
                # Render with Manim
                job_manager.update_progress(
                    job_id,
                    JobStatus.RENDERING_SLIDES,
                    progress,
                    "rendering_slides",
                    f"Rendering slide {i+1}/{total_scenes}: {scene.title}"
                )
                
                try:
                    clip_path = manim_generator.render_scene(scene, i)
                except Exception as e:
                    print(f"Manim failed, using fallback: {e}")
                    fallback = SimpleManimFallback()
                    clip_path = fallback.render_scene(scene, i)
                
            else:  # visual scene
                # Render with Mochi
                job_manager.update_progress(
                    job_id,
                    JobStatus.RENDERING_VISUALS,
                    progress,
                    "rendering_visuals",
                    f"Generating B-roll {i+1}/{total_scenes}: {scene.title}"
                )
                
                if request.include_mochi:
                    clip_path = mochi_service.render_scene(scene, i)
                else:
                    # Use placeholder if Mochi disabled
                    clip_path = mochi_service._generate_placeholder(scene, i)
            
            video_clips.append(clip_path)
            print(f"✓ Scene {i+1} rendered: {clip_path}")
        
        # Step 3: Generate voiceover (60-70%)
        job_manager.update_progress(
            job_id,
            JobStatus.GENERATING_VOICEOVER,
            65,
            "generating_voiceover",
            "Generating voiceover with TTS..."
        )
        
        audio_path = tts_service.generate_voiceover(
            script=storyboard.voiceover_script,
            voice=request.voice_accent.value,
            job_id=job_id
        )
        
        if audio_path:
            # Adjust audio duration to match video
            audio_path = tts_service.adjust_audio_duration(audio_path, request.duration)
            print(f"✓ Voiceover generated: {audio_path}")
        
        # Step 4: Composite final video (70-95%)
        job_manager.update_progress(
            job_id,
            JobStatus.COMPOSITING,
            75,
            "compositing",
            "Stitching scenes, adding audio and subtitles..."
        )
        
        final_video, srt_content = compositor.compose_final_video(
            video_clips=video_clips,
            storyboard=storyboard,
            audio_path=audio_path,
            job_id=job_id
        )
        
        # Step 5: Generate thumbnail (95-100%)
        job_manager.update_progress(
            job_id,
            JobStatus.COMPOSITING,
            95,
            "finalizing",
            "Generating thumbnail..."
        )
        
        thumbnail_path = compositor.create_thumbnail(final_video, job_id)
        
        # Build URLs
        video_url = f"/outputs/{final_video.name}"
        thumbnail_url = f"/outputs/{thumbnail_path.name}"
        
        # Complete!
        job_manager.update_progress(
            job_id,
            JobStatus.COMPLETED,
            100,
            "completed",
            "Video generation complete!"
        )
        
        return {
            "video_url": video_url,
            "srt_content": srt_content,
            "thumbnail_url": thumbnail_url,
            "duration": float(request.duration),
            "metadata": {
                "style": request.style.value,
                "voice_accent": request.voice_accent.value,
                "num_scenes": len(storyboard.scenes),
                "scenes": [
                    {"type": s.type.value, "title": s.title, "duration": s.duration}
                    for s in storyboard.scenes
                ]
            }
        }
        
    except Exception as e:
        print(f"❌ Video generation failed: {e}")
        raise


@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "Strang Video Generation API",
        "status": "running",
        "version": "1.0.0",
        "mochi_enabled": settings.MOCHI_ENABLED
    }


@app.post("/generate-video", response_model=GenerateVideoResponse)
async def generate_video(request: GenerateVideoRequest, background_tasks: BackgroundTasks):
    """
    Start video generation job
    
    Returns job ID immediately, actual processing happens in background
    """
    
    # Validate
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")
    
    # Create job
    job_id = job_manager.create_job()
    
    # Start processing in background
    job_manager.start_job_async(
        job_id,
        process_video_generation,
        request
    )
    
    # Estimate time based on duration and Mochi usage
    estimated_time = request.duration + (30 if request.include_mochi else 10)
    
    return GenerateVideoResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Video generation started. Use /job/{job_id} to check progress.",
        estimated_time_seconds=estimated_time
    )


@app.get("/job/{job_id}/progress", response_model=JobProgress)
async def get_job_progress(job_id: str):
    """Get job progress"""
    
    progress = job_manager.get_job_progress(job_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return progress


@app.get("/job/{job_id}/result", response_model=VideoResult)
async def get_job_result(job_id: str):
    """Get job final result (video URL + SRT)"""
    
    result = job_manager.get_job_result(job_id)
    
    if not result:
        # Check if job is still processing
        progress = job_manager.get_job_progress(job_id)
        if progress and progress.status != JobStatus.COMPLETED:
            raise HTTPException(status_code=202, detail="Job still processing")
        
        raise HTTPException(status_code=404, detail="Job not found")
    
    return result


@app.get("/job/{job_id}/video")
async def download_video(job_id: str):
    """Download final video file"""
    
    result = job_manager.get_job_result(job_id)
    
    if not result or not result.video_url:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_path = settings.OUTPUT_DIR / f"{job_id}.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"strang_explainer_{job_id}.mp4"
    )


@app.get("/job/{job_id}/srt")
async def download_srt(job_id: str):
    """Download SRT subtitle file"""
    
    result = job_manager.get_job_result(job_id)
    
    if not result or not result.srt_content:
        raise HTTPException(status_code=404, detail="Subtitles not found")
    
    from fastapi.responses import Response
    
    return Response(
        content=result.srt_content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=strang_explainer_{job_id}.srt"}
    )


if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     🎬 Strang Video Generation Backend                  ║
║                                                          ║
║     Hybrid Manim + Mochi Pipeline                       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

Config:
  • Mochi: {'✓ Enabled' if settings.MOCHI_ENABLED else '✗ Disabled'}
  • TTS: {settings.TTS_PROVIDER}
  • Output: {settings.OUTPUT_DIR}
  • Port: {settings.PORT}

Starting server...
""")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
