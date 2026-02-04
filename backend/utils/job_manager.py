"""
Job manager for async video generation with progress tracking
"""
import asyncio
from typing import Dict, Optional, Callable, Set
from datetime import datetime
import uuid
from models import JobStatus, JobProgress, VideoResult
from pathlib import Path
from fastapi import WebSocket


class ConnectionManager:
    """Manage WebSocket connections for real-time progress updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}  # job_id -> set of websockets
        self.connection_jobs: Dict[WebSocket, str] = {}  # websocket -> job_id
    
    async def connect(self, websocket: WebSocket, job_id: str):
        """Connect a client to a specific job's updates"""
        await websocket.accept()
        
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        
        self.active_connections[job_id].add(websocket)
        self.connection_jobs[websocket] = job_id
        
        print(f"[WebSocket] Client connected to job {job_id[:8]}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a client"""
        if websocket in self.connection_jobs:
            job_id = self.connection_jobs[websocket]
            
            if job_id in self.active_connections:
                self.active_connections[job_id].discard(websocket)
                
                # Clean up empty sets
                if not self.active_connections[job_id]:
                    del self.active_connections[job_id]
            
            del self.connection_jobs[websocket]
            print(f"[WebSocket] Client disconnected from job {job_id[:8]}")
    
    async def broadcast_to_job(self, job_id: str, message: dict):
        """Broadcast a message to all clients watching a specific job"""
        if job_id not in self.active_connections:
            return
        
        disconnected = set()
        
        for connection in self.active_connections[job_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"[WebSocket] Error sending to client: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


class JobManager:
    """Manage async video generation jobs"""
    
    def __init__(self):
        self.jobs: Dict[str, JobProgress] = {}
        self.results: Dict[str, VideoResult] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.connection_manager = ConnectionManager()
    
    def create_job(self) -> str:
        """Create a new job and return its ID"""
        job_id = str(uuid.uuid4())
        
        self.jobs[job_id] = JobProgress(
            job_id=job_id,
            status=JobStatus.QUEUED,
            progress_percent=0,
            current_step="queued",
            message="Job created, waiting to start..."
        )
        
        return job_id
    
    def get_job_progress(self, job_id: str) -> Optional[JobProgress]:
        """Get current job progress"""
        return self.jobs.get(job_id)
    
    def get_job_result(self, job_id: str) -> Optional[VideoResult]:
        """Get final job result (if completed)"""
        return self.results.get(job_id)
    
    def update_progress(
        self,
        job_id: str,
        status: JobStatus,
        progress_percent: int,
        current_step: str,
        message: str
    ):
        """Update job progress and broadcast to WebSocket clients"""
        print(f"[DEBUG] update_progress called for {job_id[:8]}, job exists: {job_id in self.jobs}", flush=True)
        if job_id in self.jobs:
            self.jobs[job_id].status = status
            self.jobs[job_id].progress_percent = progress_percent
            self.jobs[job_id].current_step = current_step
            self.jobs[job_id].message = message
            
            print(f"[{job_id[:8]}] {progress_percent}% - {message}", flush=True)
            
            # Broadcast to WebSocket clients
            asyncio.create_task(
                self.connection_manager.broadcast_to_job(
                    job_id,
                    {
                        "type": "progress",
                        "job_id": job_id,
                        "status": status.value,
                        "progress_percent": progress_percent,
                        "current_step": current_step,
                        "message": message
                    }
                )
            )
    
    def set_result(
        self,
        job_id: str,
        video_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration: Optional[float] = None,
        script: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Set final job result and broadcast to WebSocket clients"""
        status = JobStatus.COMPLETED if not error else JobStatus.FAILED
        
        self.results[job_id] = VideoResult(
            job_id=job_id,
            status=status,
            video_url=video_url,
            thumbnail_url=thumbnail_url,
            duration=duration,
            script=script,
            error=error
        )
        
        # Update progress to completed/failed
        if job_id in self.jobs:
            self.jobs[job_id].status = status
            self.jobs[job_id].progress_percent = 100 if not error else 0
            if error:
                self.jobs[job_id].error = error
        
        # Broadcast completion to WebSocket clients
        asyncio.create_task(
            self.connection_manager.broadcast_to_job(
                job_id,
                {
                    "type": "complete" if not error else "error",
                    "job_id": job_id,
                    "status": status.value,
                    "video_url": video_url,
                    "thumbnail_url": thumbnail_url,
                    "duration": duration,
                    "script": script,
                    "error": error
                }
            )
        )
    
    async def run_job(
        self,
        job_id: str,
        job_func: Callable,
        *args,
        **kwargs
    ):
        """
        Run a job function asynchronously
        
        Args:
            job_id: Job identifier
            job_func: The actual processing function (can be sync or async)
            *args, **kwargs: Arguments for job_func
        """
        print(f"[JobManager] run_job started for {job_id[:8]}", flush=True)
        
        try:
            self.update_progress(
                job_id,
                JobStatus.PROCESSING,
                5,
                "starting",
                "Starting video generation..."
            )
            
            # Run the job function
            if asyncio.iscoroutinefunction(job_func):
                result = await job_func(job_id, *args, **kwargs)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, job_func, job_id, *args, **kwargs)
            
            # Job succeeded
            self.set_result(job_id, **result)
            
        except Exception as e:
            # Job failed
            error_msg = f"Job failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            self.set_result(job_id, error=error_msg)
            self.update_progress(
                job_id,
                JobStatus.FAILED,
                0,
                "failed",
                error_msg
            )
    
    def start_job_async(
        self,
        job_id: str,
        job_func: Callable,
        *args,
        **kwargs
    ):
        """Start a job in the background"""
        print(f"[JobManager] Starting async job {job_id[:8]}...", flush=True)
        try:
            task = asyncio.create_task(self.run_job(job_id, job_func, *args, **kwargs))
            self.tasks[job_id] = task
            print(f"[JobManager] Task created for job {job_id[:8]}", flush=True)
        except Exception as e:
            print(f"[JobManager] ERROR creating task: {e}", flush=True)
            raise
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove old jobs from memory"""
        # In production, store in Redis or database
        # For now, just keep everything in memory
        pass


# Global job manager instance
job_manager = JobManager()
