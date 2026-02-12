"""
Strang Backend API - Groq (Script) + OpenAI Sora (Video) + EdgeTTS (Audio)
Clean, efficient pipeline rebuilt for Cinematic AI Video Generation
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json

from config import settings
from models import (
    ProcessVideoRequest,
    ProcessVideoResponse,
    JobProgress,
    VideoResult,
    JobStatus,
    ScriptOnlyRequest,
    ScriptOnlyResponse,
    AvailableVoicesResponse,
    VoiceInfo
)
from utils.job_manager import job_manager
from services.groq_service import GroqService
from services.openai_service import OpenAIService
from services.tts_service import TTSService
from services.video_composer import VideoComposer

# Configure logging
log_dir = Path(settings.TEMP_DIR) / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"strang_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Strang Cinematic Video API",
    description="Groq + Sora + EdgeTTS Video Generator",
    version="4.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated videos
app.mount("/outputs", StaticFiles(directory=str(settings.OUTPUT_DIR)), name="outputs")

# Initialize services
_groq_service: Optional[GroqService] = None
_openai_service: Optional[OpenAIService] = None
_tts_service: Optional[TTSService] = None
_composer_service: Optional[VideoComposer] = None


def get_groq_service() -> GroqService:
    global _groq_service
    if _groq_service is None:
        _groq_service = GroqService()
    return _groq_service

def get_openai_service() -> OpenAIService:
    global _openai_service
    if _openai_service is None:
        _openai_service = OpenAIService()
    return _openai_service

def get_tts_service() -> TTSService:
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service

def get_composer_service() -> VideoComposer:
    global _composer_service
    if _composer_service is None:
        _composer_service = VideoComposer()
    return _composer_service


async def process_video_generation(job_id: str, request: ProcessVideoRequest) -> dict:
    """
    Main video generation pipeline:
    1. Groq generates Script JSON (Scenes: Narration + Visual Prompt)
    2. Parallel Generation:
       - EdgeTTS generates Audio for each scene
       - Sora generates Video for each scene
    3. MoviePy stitches them together
    """
    
    try:
        # ============================================
        # Stage 1: Scripting (0-20%)
        # ============================================
        job_manager.update_progress(job_id, JobStatus.SCRIPTING, 10, "scripting", "Groq AI is writing your screenplay...")
        
        groq = get_groq_service()
        scenes = await asyncio.to_thread(
            groq.generate_script_json,
            text=request.text,
            style=request.style.value
        )
        
        if not scenes:
            raise RuntimeError("Failed to generate valid scenes from text")
            
        print(f"[{job_id}] Generated {len(scenes)} scenes")
        job_manager.update_progress(job_id, JobStatus.PROCESSING, 20, "processing", f"Generated {len(scenes)} scenes. Starting production...")
        
        # ============================================
        # Stage 2: Production (Audio & Video) (20-80%)
        # ============================================
        openai = get_openai_service()
        tts = get_tts_service()
        
        generated_scenes = []
        total_scenes = len(scenes)
        
        # Process scenes sequentially or in parallel?
        # Parallel is faster but might hit rate limits. Let's do semi-parallel or sequential for safety first.
        # We'll do sequential scenes, but parallel Audio/Video within a scene.
        
        for i, scene in enumerate(scenes):
            scene_num = i + 1
            narration = scene.get("narration", "")
            video_prompt = scene.get("video_prompt", "")
            
            job_manager.update_progress(
                job_id, 
                JobStatus.PROCESSING, 
                20 + int((i / total_scenes) * 60), 
                "production", 
                f"Producing Scene {scene_num}/{total_scenes}..."
            )
            
            # Generate Audio & Video validation
            if not narration or not video_prompt:
                continue
                
            # Create tasks
            audio_task = tts.generate_audio(
                text=narration,
                voice=request.voice_id or "en-US-GuyNeural",
                file_name=f"{job_id}_scene_{scene_num}.mp3"
            )
            
            video_task = openai.generate_scene_video(
                scene_prompt=video_prompt
            )
            
            # Run parallel
            print(f"[{job_id}] Starting Scene {scene_num} generation...")
            audio_path, video_url = await asyncio.gather(audio_task, video_task)
            
            generated_scenes.append({
                "audio_path": audio_path,
                "video_path": video_url, # Composer needs to handle URL downloading or we do it here
                "narration": narration
            })
            
            print(f"[{job_id}] Finished Scene {scene_num}")
            
        if not generated_scenes:
            raise RuntimeError("Production failed: No scenes were successfully generated")

        # ============================================
        # Stage 3: Post-Production (Composition) (80-100%)
        # ============================================
        job_manager.update_progress(job_id, JobStatus.RENDERING, 80, "rendering", "Stitching video clips...")
        
        composer = get_composer_service()
        
        # We need to make sure video_path is local for MoviePy usually
        # The VideoComposer might need update to handle URLs, or we download here.
        # Check VideoComposer... it takes video_path.
        # Let's download video URLs here to temp dir.
        
        import httpx
        async with httpx.AsyncClient() as client:
            for i, scene in enumerate(generated_scenes):
                url = scene["video_path"]
                if url.startswith("http"):
                    local_filename = f"{job_id}_scene_{i+1}.mp4"
                    local_path = settings.TEMP_DIR / local_filename
                    
                    job_manager.update_progress(
                        job_id, 
                        JobStatus.RENDERING, 
                        80 + int((i / len(generated_scenes)) * 10), 
                        "rendering", 
                        f"Downloading clip {i+1}..."
                    )
                    
                    print(f"[{job_id}] Downloading {url} to {local_path}...")
                    resp = await client.get(url, timeout=60.0)
                    if resp.status_code == 200:
                        with open(local_path, "wb") as f:
                            f.write(resp.content)
                        scene["video_path"] = str(local_path)
                    else:
                        raise RuntimeError(f"Failed to download video clip for scene {i+1}")

        # Stitch
        final_video_url = await asyncio.to_thread(
            composer.compose_video,
            scenes=generated_scenes,
            job_id=job_id
        )
        
        # Validating output
        final_script = "\n\n".join([f"Scene {i+1}: {s['narration']}" for i, s in enumerate(generated_scenes)])
        
        job_manager.update_progress(job_id, JobStatus.COMPLETED, 100, "completed", "Video generation complete!")
        
        return {
            "video_url": final_video_url,
            "thumbnail_url": None, # Could extract later
            "duration": None, # Could calculate
            "script": final_script
        }
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job_manager.update_progress(job_id, JobStatus.FAILED, 0, "failed", f"Error: {str(e)}")
        raise


@app.get("/")
async def root():
    return {
        "service": "Strang Cinematic API",
        "version": "4.0.0",
        "pipeline": "Groq + Sora + EdgeTTS"
    }

@app.post("/api/process-video", response_model=ProcessVideoResponse)
async def process_video(request: ProcessVideoRequest):
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY missing")
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY missing")
        
    job_id = job_manager.create_job()
    job_manager.start_job_async(job_id, process_video_generation, request)
    
    return ProcessVideoResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Video production started.",
        estimated_time_seconds=120
    )

@app.get("/job/{job_id}/progress", response_model=JobProgress)
async def get_job_progress(job_id: str):
    progress = job_manager.get_job_progress(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Job not found")
    return progress

@app.get("/job/{job_id}/result", response_model=VideoResult)
async def get_job_result(job_id: str):
    result = job_manager.get_job_result(job_id)
    if not result:
        progress = job_manager.get_job_progress(job_id)
        if progress and progress.status != JobStatus.COMPLETED:
            raise HTTPException(status_code=202, detail="Job processing")
        raise HTTPException(status_code=404, detail="Job not found")
    return result

@app.get("/api/voices", response_model=AvailableVoicesResponse)
async def list_voices():
    tts = get_tts_service()
    voices = tts.get_voices()
    return AvailableVoicesResponse(
        voices=[
            VoiceInfo(
                voice_id=v["id"],
                name=v["name"],
                gender=v["gender"],
                language="en-US"
            ) for v in voices
        ]
    )

@app.websocket("/ws/job/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    progress = job_manager.get_job_progress(job_id)
    if not progress:
        await websocket.close(code=1008, reason="Job not found")
        return
        
    await job_manager.connection_manager.connect(websocket, job_id)
    try:
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "status": progress.status.value,
            "progress_percent": progress.progress_percent,
            "message": progress.message
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        job_manager.connection_manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
