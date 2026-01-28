"""
Job manager for async video generation with progress tracking
"""
import asyncio
from typing import Dict, Optional, Callable
from datetime import datetime
import uuid
from models import JobStatus, JobProgress, VideoResult
from pathlib import Path


class JobManager:
    """Manage async video generation jobs"""
    
    def __init__(self):
        self.jobs: Dict[str, JobProgress] = {}
        self.results: Dict[str, VideoResult] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
    
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
        """Update job progress"""
        if job_id in self.jobs:
            self.jobs[job_id].status = status
            self.jobs[job_id].progress_percent = progress_percent
            self.jobs[job_id].current_step = current_step
            self.jobs[job_id].message = message
            
            print(f"[{job_id[:8]}] {progress_percent}% - {message}")
    
    def set_result(
        self,
        job_id: str,
        video_url: Optional[str] = None,
        srt_content: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration: Optional[float] = None,
        metadata: Optional[dict] = None,
        error: Optional[str] = None
    ):
        """Set final job result"""
        status = JobStatus.COMPLETED if not error else JobStatus.FAILED
        
        self.results[job_id] = VideoResult(
            job_id=job_id,
            status=status,
            video_url=video_url,
            srt_content=srt_content,
            thumbnail_url=thumbnail_url,
            duration=duration,
            metadata=metadata,
            error=error
        )
        
        # Update progress to completed/failed
        if job_id in self.jobs:
            self.jobs[job_id].status = status
            self.jobs[job_id].progress_percent = 100 if not error else 0
            if error:
                self.jobs[job_id].error = error
    
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
        task = asyncio.create_task(self.run_job(job_id, job_func, *args, **kwargs))
        self.tasks[job_id] = task
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove old jobs from memory"""
        # In production, store in Redis or database
        # For now, just keep everything in memory
        pass


# Global job manager instance
job_manager = JobManager()
