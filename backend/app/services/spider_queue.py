import asyncio
import time
import logging
from typing import Dict, Any, Callable, Awaitable, List, Optional
import uuid

logger = logging.getLogger(__name__)

class SpiderQueue:
    """Queue system for managing spider tasks to prevent conflicts"""
    
    def __init__(self, max_concurrent: int = 1):
        self.queue = asyncio.Queue()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.results: Dict[str, Any] = {}
        self._running = False
        self._worker_task = None
    
    async def start(self):
        """Start the queue worker"""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Spider queue worker started")
    
    async def stop(self):
        """Stop the queue worker"""
        if self._running:
            self._running = False
            await self.queue.put(None)  # Signal to stop
            if self._worker_task:
                await self._worker_task
            logger.info("Spider queue worker stopped")
    
    async def _worker(self):
        """Worker to process tasks"""
        while self._running:
            try:
                # Get next task from queue
                task_item = await self.queue.get()
                
                # Check for stop signal
                if task_item is None:
                    break
                
                # Unpack task
                task_id, func, args, kwargs = task_item
                
                # Execute with semaphore
                async with self.semaphore:
                    try:
                        # Add delay for rate limiting
                        await asyncio.sleep(1)
                        
                        # Execute the function
                        self.results[task_id] = {
                            "status": "running",
                            "start_time": time.time()
                        }
                        
                        result = await func(*args, **kwargs)
                        
                        # Store the result
                        self.results[task_id] = {
                            "status": "completed",
                            "end_time": time.time(),
                            "result": result
                        }
                    except Exception as e:
                        # Store the error
                        logger.error(f"Error executing spider task {task_id}: {str(e)}")
                        self.results[task_id] = {
                            "status": "failed",
                            "end_time": time.time(),
                            "error": str(e)
                        }
                    finally:
                        # Mark task as done
                        self.queue.task_done()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in spider queue worker: {str(e)}")
    
    async def add_task(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> str:
        """Add a new task to the queue"""
        task_id = str(uuid.uuid4())
        await self.queue.put((task_id, func, args, kwargs))
        return task_id
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a task by ID"""
        return self.results.get(task_id)
    
    def cleanup_old_results(self, max_age_hours: int = 24):
        """Clean up old results to prevent memory leaks"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 60 * 60
        to_remove = []
        
        for task_id, result in self.results.items():
            if result.get("status") == "completed" or result.get("status") == "failed":
                if current_time - result.get("end_time", 0) > max_age_seconds:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.results[task_id]

# Singleton instance
spider_queue = SpiderQueue()

# Function to initialize the queue on startup
async def init_spider_queue():
    await spider_queue.start()