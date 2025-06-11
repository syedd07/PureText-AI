from typing import Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

# Unified job storage
jobs = {}

class JobStore:
    """Unified job storage for all background processing tasks"""
    
    @staticmethod
    def create_job(job_id: str, status: str = "processing", **kwargs) -> Dict[str, Any]:
        """Create a new job with initial status and data"""
        jobs[job_id] = {
            "status": status,
            "created_at": time.time(),
            "updated_at": time.time(),
            "progress": 0,
            **kwargs
        }
        return jobs[job_id]
    
    @staticmethod
    def get_job(job_id: str) -> Dict[str, Any]:
        """Get job by ID"""
        return jobs.get(job_id)
        
    @staticmethod
    def update_job(job_id: str, **kwargs) -> Dict[str, Any]:
        """Update job with new attributes"""
        if job_id not in jobs:
            logger.warning(f"Trying to update non-existent job: {job_id}")
            return None
            
        jobs[job_id].update(kwargs)
        jobs[job_id]["updated_at"] = time.time()
        return jobs[job_id]
    
    @staticmethod
    def set_job_status(job_id: str, status: str, progress: int = None) -> None:
        """Update job status and optionally progress"""
        if job_id not in jobs:
            logger.warning(f"Trying to update status of non-existent job: {job_id}")
            return
            
        jobs[job_id]["status"] = status
        jobs[job_id]["updated_at"] = time.time()
        if progress is not None:
            jobs[job_id]["progress"] = progress
            
    @staticmethod
    def set_job_completed(job_id: str, result: Dict[str, Any]) -> None:
        """Mark job as completed with results"""
        if job_id not in jobs:
            logger.warning(f"Trying to complete non-existent job: {job_id}")
            return
            
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = result
        jobs[job_id]["progress"] = 100
        jobs[job_id]["updated_at"] = time.time()
    
    @staticmethod
    def set_job_failed(job_id: str, error: str) -> None:
        """Mark job as failed with error"""
        if job_id not in jobs:
            logger.warning(f"Trying to fail non-existent job: {job_id}")
            return
            
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = error
        jobs[job_id]["updated_at"] = time.time()
        
    @staticmethod
    def cleanup_old_jobs(max_age_hours: int = 24) -> None:
        """Remove old jobs to prevent memory leaks"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 60 * 60
        
        to_remove = []
        for job_id, job in jobs.items():
            if current_time - job.get("updated_at", 0) > max_age_seconds:
                to_remove.append(job_id)
                
        for job_id in to_remove:
            del jobs[job_id]
            
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old jobs")

# Singleton instance
job_store = JobStore()