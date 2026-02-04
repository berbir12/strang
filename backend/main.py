"""
Strang Backend API - Groq (FREE) + HeyGen Avatar Video Generation
Clean, efficient pipeline rebuilt from scratch
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
from typing import Optional

from config import settings
from models import (
    ProcessVideoRequest,
    ProcessVideoResponse,
    JobProgress,
    VideoResult,
    JobStatus,
    ScriptOnlyRequest,
    ScriptOnlyResponse,
    AvatarInfo,
    VoiceInfo,
    AvailableAvatarsResponse,
    AvailableVoicesResponse
)
from utils.job_manager import job_manager
from services.groq_service import GroqService
from services.heygen_service import HeyGenService, HeyGenVideoStatus

# Initialize FastAPI app
app = FastAPI(
    title="Strang Video Generation API",
    description="Groq (Free AI) + HeyGen Avatar Video Generator",
    version="3.0.0"
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

# Initialize services (lazy loading)
_groq_service: Optional[GroqService] = None
_heygen_service: Optional[HeyGenService] = None


def get_groq_service() -> GroqService:
    """Get or initialize Groq service"""
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqService()
    return _groq_service


def get_heygen_service() -> HeyGenService:
    """Get or initialize HeyGen service"""
    global _heygen_service
    if _heygen_service is None:
        _heygen_service = HeyGenService()
    return _heygen_service


async def process_video_generation(
    job_id: str,
    request: ProcessVideoRequest
) -> dict:
    """
    Main video generation pipeline:
    1. Groq generates enhanced script (FREE and FAST)
    2. HeyGen renders avatar video
    """
    
    try:
        # ============================================
        # Stage 1: Generate script with Groq (0-30%)
        # ============================================
        job_manager.update_progress(
            job_id,
            JobStatus.SCRIPTING,
            10,
            "scripting",
            "Groq AI is writing your script..."
        )
        
        groq = get_groq_service()
        script = await asyncio.to_thread(
            groq.generate_script,
            text=request.text,
            style=request.style.value
        )
        
        print(f"✓ Script generated: {len(script)} characters", flush=True)
        
        job_manager.update_progress(
            job_id,
            JobStatus.SCRIPTING,
            30,
            "scripting",
            "Script generation complete!"
        )
        
        # ============================================
        # Stage 2: Generate video with HeyGen (30-95%)
        # ============================================
        print(f"[{job_id[:8]}] Initializing HeyGen service...", flush=True)
        job_manager.update_progress(
            job_id,
            JobStatus.RENDERING,
            35,
            "rendering",
            "HeyGen is rendering your avatar video..."
        )
        
        heygen = get_heygen_service()
        print(f"[{job_id[:8]}] Submitting video to HeyGen...", flush=True)
        
        # Submit video generation request
        video_id = await heygen.generate_avatar_video(
            script=script,
            avatar_id=request.avatar_id,
            voice_id=request.voice_id,
            video_title=f"Strang_{job_id}"
        )
        
        # Progress callback for HeyGen polling
        async def heygen_progress_callback(percent, message, result):
            # Map HeyGen progress (0-100) to our range (35-95)
            mapped_percent = 35 + int(percent * 0.6)
            job_manager.update_progress(
                job_id,
                JobStatus.RENDERING,
                mapped_percent,
                "rendering",
                message
            )
        
        # Wait for video completion
        result = await heygen.wait_for_completion(
            video_id=video_id,
            progress_callback=heygen_progress_callback
        )
        
        if result.status != HeyGenVideoStatus.COMPLETED:
            raise RuntimeError(result.error or "HeyGen video generation failed")
        
        print(f"✓ Video rendered: {result.video_url}")
        
        # ============================================
        # Stage 3: Complete (95-100%)
        # ============================================
        job_manager.update_progress(
            job_id,
            JobStatus.COMPLETED,
            100,
            "completed",
            "Video generation complete!"
        )
        
        return {
            "video_url": result.video_url,
            "thumbnail_url": result.thumbnail_url,
            "duration": result.duration,
            "script": script
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
        "version": "3.0.0",
        "pipeline": "Groq (FREE) + HeyGen",
        "ai_provider": "Groq API (Free)",
        "video_provider": "HeyGen"
    }


@app.post("/api/process-video", response_model=ProcessVideoResponse)
async def process_video(request: ProcessVideoRequest):
    """
    Start video generation job
    
    Pipeline:
    1. Groq AI (free) enhances the text into a professional script
    2. HeyGen generates an AI avatar video
    
    Returns job ID immediately, actual processing happens in background
    """
    
    # Validate API keys
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    if not settings.HEYGEN_API_KEY:
        raise HTTPException(status_code=500, detail="HEYGEN_API_KEY not configured")
    
    # Create job
    job_id = job_manager.create_job()
    
    # Start processing in background
    job_manager.start_job_async(
        job_id,
        process_video_generation,
        request
    )
    
    # Estimate time: ~5s for script + ~2-5min for HeyGen render
    estimated_time = 150  # seconds
    
    return ProcessVideoResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Video generation started. Use /job/{job_id} to check progress.",
        estimated_time_seconds=estimated_time
    )


@app.post("/api/generate-script", response_model=ScriptOnlyResponse)
async def generate_script(request: ScriptOnlyRequest):
    """
    Generate script only (without video rendering)
    
    Useful for previewing the Groq-enhanced script before committing to video
    """
    
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
    
    try:
        groq = get_groq_service()
        script = await asyncio.to_thread(
            groq.generate_script,
            text=request.text,
            style=request.style.value,
            duration_hint=request.duration_hint
        )
        
        # Estimate duration: ~150 words per minute
        word_count = len(script.split())
        estimated_duration = int((word_count / 150) * 60)
        
        return ScriptOnlyResponse(
            original_text=request.text,
            script=script,
            style=request.style.value,
            word_count=word_count,
            estimated_duration_seconds=estimated_duration
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script generation failed: {e}")


@app.get("/job/{job_id}/progress", response_model=JobProgress)
async def get_job_progress(job_id: str):
    """Get job progress"""
    
    progress = job_manager.get_job_progress(job_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return progress


@app.get("/job/{job_id}/result", response_model=VideoResult)
async def get_job_result(job_id: str):
    """Get job final result (video URL)"""
    
    result = job_manager.get_job_result(job_id)
    
    if not result:
        # Check if job is still processing
        progress = job_manager.get_job_progress(job_id)
        if progress and progress.status != JobStatus.COMPLETED:
            raise HTTPException(status_code=202, detail="Job still processing")
        
        raise HTTPException(status_code=404, detail="Job not found")
    
    return result


@app.websocket("/ws/job/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates
    """
    
    # Check if job exists
    progress = job_manager.get_job_progress(job_id)
    if not progress:
        await websocket.close(code=1008, reason="Job not found")
        return
    
    # Connect the client
    await job_manager.connection_manager.connect(websocket, job_id)
    
    try:
        # Send initial progress
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "status": progress.status.value,
            "progress_percent": progress.progress_percent,
            "current_step": progress.current_step,
            "message": progress.message
        })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        job_manager.connection_manager.disconnect(websocket)


@app.get("/api/avatars", response_model=AvailableAvatarsResponse)
async def list_avatars():
    """Get list of available HeyGen avatars"""
    
    if not settings.HEYGEN_API_KEY:
        raise HTTPException(status_code=500, detail="HEYGEN_API_KEY not configured")
    
    try:
        heygen = get_heygen_service()
        avatars_data = await heygen.list_avatars()
        
        avatars = [
            AvatarInfo(
                avatar_id=a.get("avatar_id", ""),
                name=a.get("avatar_name", "Unknown"),
                preview_url=a.get("preview_image_url")
            )
            for a in avatars_data
        ]
        
        return AvailableAvatarsResponse(avatars=avatars)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list avatars: {e}")


@app.get("/api/voices", response_model=AvailableVoicesResponse)
async def list_voices():
    """Get list of available HeyGen voices"""
    
    if not settings.HEYGEN_API_KEY:
        raise HTTPException(status_code=500, detail="HEYGEN_API_KEY not configured")
    
    try:
        heygen = get_heygen_service()
        voices_data = await heygen.list_voices()
        
        voices = [
            VoiceInfo(
                voice_id=v.get("voice_id", ""),
                name=v.get("name", "Unknown"),
                language=v.get("language"),
                gender=v.get("gender")
            )
            for v in voices_data
        ]
        
        return AvailableVoicesResponse(voices=voices)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list voices: {e}")


if __name__ == "__main__":
    print(f"""
==============================================================
    Strang Video Generation Backend v3.0
    Groq (FREE) + HeyGen Pipeline
==============================================================

Config:
  - AI Provider: Groq API (FREE and FAST!)
  - Groq Model: {settings.GROQ_MODEL}
  - Video Provider: HeyGen
  - HeyGen Avatar: {settings.HEYGEN_AVATAR_ID}
  - Output: {settings.OUTPUT_DIR}
  - Port: {settings.PORT}

Starting server...
""")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
