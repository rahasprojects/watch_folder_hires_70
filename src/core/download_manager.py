# -*- coding: utf-8 -*-
"""
Manager untuk mengatur download workers
"""

import threading
import time
import logging
from typing import List, Optional, Dict
from ..models.file_job import FileJob
from ..core.download_worker import DownloadWorker
from ..core.file_handler import FileHandler
from ..core.queue_manager import QueueManager
from ..utils.state_manager import StateManager
from ..utils.history import HistoryLogger
from ..constants.settings import DEFAULT_MAX_DOWNLOAD, DEFAULT_MAX_RETRY

logger = logging.getLogger(__name__)

class DownloadManager:
    """
    Kelas untuk mengelola download workers
    """
    
    def __init__(self, 
                 max_parallel: int = DEFAULT_MAX_DOWNLOAD,
                 max_retry: int = DEFAULT_MAX_RETRY,
                 queue_manager: Optional[QueueManager] = None,
                 file_handler: Optional[FileHandler] = None,
                 state_manager: Optional[StateManager] = None,
                 history_logger: Optional[HistoryLogger] = None):
        """
        Inisialisasi DownloadManager
        
        Args:
            max_parallel: Maksimal worker paralel
            max_retry: Maksimal retry per file
            queue_manager: QueueManager instance
            file_handler: FileHandler instance
            state_manager: StateManager instance
            history_logger: HistoryLogger instance
        """
        self.max_parallel = max_parallel
        self.max_retry = max_retry
        
        # Managers
        self.queue_manager = queue_manager or QueueManager()
        self.file_handler = file_handler or FileHandler()
        self.state_manager = state_manager or StateManager()
        self.history_logger = history_logger or HistoryLogger()
        
        # Workers
        self.workers: List[DownloadWorker] = []
        self.worker_status: Dict[int, dict] = {}
        
        # Control
        self.running = False
        self.lock = threading.Lock()
        
        # Callbacks
        self.progress_callbacks = []
        
        logger.info(f"DownloadManager initialized with max_parallel={max_parallel}")
    
    def start(self):
        """Start semua workers"""
        if self.running:
            logger.warning("DownloadManager already running")
            return
        
        self.running = True
        
        # Load state untuk resume
        self._load_resume_state()
        
        # Start workers
        for i in range(self.max_parallel):
            worker = DownloadWorker(
                worker_id=i + 1,
                queue_manager=self.queue_manager,
                download_manager=self,
                file_handler=self.file_handler,
                state_manager=self.state_manager,
                history_logger=self.history_logger
            )
            worker.start()
            self.workers.append(worker)
            
            # Status awal
            self.worker_status[i + 1] = {
                'busy': False,
                'current_job': None,
                'start_time': None
            }
        
        logger.info(f"Started {len(self.workers)} download workers")
    
    def stop(self):
        """Stop semua workers"""
        logger.info("Stopping all workers...")
        self.running = False
        
        for worker in self.workers:
            worker.stop()
        
        # Tunggu workers selesai
        for worker in self.workers:
            worker.join(timeout=5)
        
        # Save state terakhir
        self._save_state()
        
        logger.info("All workers stopped")
    
    def _load_resume_state(self):
        """Load state untuk resume file yang belum selesai"""
        try:
            state = self.state_manager.load()
            resumable_jobs = self.state_manager.get_resumable_jobs()
            
            if resumable_jobs:
                logger.info(f"Found {len(resumable_jobs)} resumable jobs")
                
                for job_data in resumable_jobs:
                    # Buat FileJob dari data
                    job = FileJob.from_dict(job_data)
                    
                    # Tambah ke queue
                    self.queue_manager.add_job(job)
                    
                    logger.info(f"Resumed job: {job.name} ({job.progress:.1f}%)")
            
            # Clear completed dari state
            self.state_manager.clear_completed()
            
        except Exception as e:
            logger.error(f"Error loading resume state: {e}")
    
    def _save_state(self):
        """Save state semua jobs"""
        try:
            jobs = self.queue_manager.get_all_jobs()
            self.state_manager.save(jobs)
            # logger.debug("State saved")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def update_progress(self, job: FileJob):
        """
        Update progress job
        
        Args:
            job: FileJob object
        """
        # Update worker status
        for worker in self.workers:
            if worker.get_current_job() == job:
                self.worker_status[worker.worker_id] = {
                    'busy': True,
                    'current_job': job,
                    'progress': job.progress,
                    'speed': job.speed_mbps,
                    'eta': job.eta_formatted
                }
                break
        
        # Notifikasi callbacks
        self._notify_progress(job)
        
        # Save state setiap update (bisa di-throttle kalau perlu)
        if int(job.progress) % 10 == 0:  # Setiap 10%
            self._save_state()
    
    def _notify_progress(self, job: FileJob):
        """Notifikasi progress ke semua callback"""
        for callback in self.progress_callbacks:
            try:
                callback(job)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def register_progress_callback(self, callback):
        """Register callback untuk update progress"""
        self.progress_callbacks.append(callback)
    
    def get_stats(self) -> dict:
        """Dapatkan statistik download"""
        with self.lock:
            queue_stats = self.queue_manager.get_stats()
            
            # Hitung worker stats
            busy_workers = sum(1 for w in self.workers if w.is_busy())
            total_speed = 0
            for worker in self.workers:
                job = worker.get_current_job()
                if job:
                    total_speed += job.speed_mbps
            
            return {
                'queue': queue_stats,
                'workers': {
                    'total': len(self.workers),
                    'busy': busy_workers,
                    'idle': len(self.workers) - busy_workers,
                    'total_speed_mbps': total_speed
                },
                'max_parallel': self.max_parallel,
                'running': self.running
            }
    
    def get_active_downloads(self) -> List[FileJob]:
        active = []
        for worker in self.workers:
            job = worker.get_current_job()
            if job:
                active.append(job)
                # Optional: biarkan satu log saja kalau mau
                # logger.debug(f"Active download: {job.name} - {job.progress:.1f}%")
        return active
        
    def set_max_parallel(self, new_max: int):
        """
        Ubah jumlah maksimal worker paralel
        
        Args:
            new_max: Jumlah worker baru
        """
        if new_max == self.max_parallel:
            return
        
        if new_max > self.max_parallel:
            # Tambah worker
            for i in range(self.max_parallel, new_max):
                worker = DownloadWorker(
                    worker_id=i + 1,
                    queue_manager=self.queue_manager,
                    download_manager=self
                )
                worker.start()
                self.workers.append(worker)
                
            logger.info(f"Added {new_max - self.max_parallel} workers")
            
        else:
            # Kurangi worker (stop yang idle)
            to_stop = []
            for worker in self.workers[new_max:]:
                if not worker.is_busy():
                    worker.stop()
                    to_stop.append(worker)
            
            # Hapus dari list
            for worker in to_stop:
                self.workers.remove(worker)
            
            logger.info(f"Removed {len(to_stop)} idle workers")
        
        self.max_parallel = new_max
        logger.info(f"Max parallel changed to {new_max}")


# Test sederhana
if __name__ == "__main__":
    from ..utils.logger import setup_logging
    setup_logging()
    
    # Buat download manager
    dm = DownloadManager(max_parallel=2)
    
    # Start
    dm.start()
    
    # Jalankan sebentar
    time.sleep(2)
    
    # Stop
    dm.stop()
    
    print("DownloadManager test done")