# -*- coding: utf-8 -*-
"""
Worker thread untuk download file dari 12 ke 70
"""

import threading
import time
import logging
import os
from typing import Optional
from ..models.file_job import FileJob
from ..core.file_handler import FileHandler
from ..utils.state_manager import StateManager
from ..utils.history import HistoryLogger
from ..utils.config_manager import ConfigManager
from ..constants.settings import STATUS_DOWNLOADING, STATUS_COMPLETED, STATUS_FAILED

logger = logging.getLogger(__name__)

class DownloadWorker(threading.Thread):
    """
    Worker thread untuk menangani download satu file
    """
    
    def __init__(self, worker_id: int, queue_manager, download_manager, 
                 file_handler: Optional[FileHandler] = None,
                 state_manager: Optional[StateManager] = None,
                 history_logger: Optional[HistoryLogger] = None):
        """
        Inisialisasi DownloadWorker
        
        Args:
            worker_id: ID worker (untuk logging)
            queue_manager: QueueManager instance
            download_manager: DownloadManager instance
            file_handler: FileHandler instance (optional)
            state_manager: StateManager instance (optional)
            history_logger: HistoryLogger instance (optional)
        """
        super().__init__()
        self.worker_id = worker_id
        self.queue_manager = queue_manager
        self.download_manager = download_manager
        self.file_handler = file_handler or FileHandler()
        self.state_manager = state_manager or StateManager()
        self.history_logger = history_logger or HistoryLogger()
        self.config_manager = ConfigManager()
        
        self.daemon = True
        self.running = True
        self.current_job: Optional[FileJob] = None
        
        logger.info(f"DownloadWorker-{worker_id} initialized")
    
    def run(self):
        """Main loop worker"""
        logger.info(f"DownloadWorker-{self.worker_id} started")
        
        while self.running:
            try:
                # Ambil job berikutnya dari queue
                job = self.queue_manager.get_next_job()
                
                if job:
                    self.current_job = job
                    self._process_job(job)
                    self.current_job = None
                else:
                    # Tidak ada job, sleep sebentar
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"DownloadWorker-{self.worker_id} error: {e}")
                time.sleep(5)
        
        logger.info(f"DownloadWorker-{self.worker_id} stopped")
    
    def _process_job(self, job: FileJob):
        """
        Proses satu job download
        
        Args:
            job: FileJob object
        """

        # ========== DEBUG: CEK PATH ==========
        logger.info(f"Worker-{self.worker_id} processing: {job.name}")
        logger.info(f"Source path from job: {job.source_path}")
        logger.info(f"Dest path from job: {job.dest_path}")
        logger.info(f"Size: {job.size_bytes} bytes")
        
        # ========== CEK SOURCE PATH ==========
        import os
        if not job.source_path or job.source_path == "":
            logger.error(f"Source path is EMPTY for {job.name}")
            self.queue_manager.fail_job(job, "Source path is empty", retry=False)
            return
            
        if not os.path.exists(job.source_path):
            logger.error(f"Source file does NOT exist: {job.source_path}")
            self.queue_manager.fail_job(job, f"Source file not found: {job.source_path}", retry=True)
            return
        else:
            logger.info(f"Source file exists, size: {os.path.getsize(job.source_path)} bytes")
        
        # ========== CEK DESTINATION PATH ==========
        if not job.dest_path or job.dest_path == "":
            logger.warning(f"Destination path is EMPTY for {job.name}, trying to set from config")
            
            # Load config untuk dapat destination folder
            config = self.config_manager.load()
            if config.destination_folder and config.destination_folder != "":
                import os
                job.dest_path = os.path.join(config.destination_folder, job.name)
                logger.info(f"Set destination path from config: {job.dest_path}")
            else:
                logger.error(f"Cannot set destination path: destination_folder is empty in config")
                self.queue_manager.fail_job(job, "Destination folder not configured", retry=False)
                return
        
        # ========== CEK FOLDER DESTINATION ==========
        dest_folder = os.path.dirname(job.dest_path)
        if not os.path.exists(dest_folder):
            logger.warning(f"Destination folder does not exist: {dest_folder}")
            try:
                os.makedirs(dest_folder, exist_ok=True)
                logger.info(f"Created destination folder: {dest_folder}")
            except Exception as e:
                logger.error(f"Cannot create destination folder: {e}")
                self.queue_manager.fail_job(job, f"Cannot create destination folder: {e}", retry=False)
                return
        
        # ========== CEK WRITE PERMISSION ==========
        if not os.access(dest_folder, os.W_OK):
            logger.error(f"No write permission to destination folder: {dest_folder}")
            self.queue_manager.fail_job(job, f"No write permission to {dest_folder}", retry=False)
            return
        
        logger.info(f"All path checks passed for {job.name}")
        logger.info(f"Final source: {job.source_path}")
        logger.info(f"Final dest: {job.dest_path}")
        
        # Update state
        job.status = STATUS_DOWNLOADING
        self.state_manager.update_job(job)
        
        # Callback progress
        def progress_callback(copied_bytes: int, percent: float):
            job.copied_bytes = copied_bytes
            job.progress = percent
            self.download_manager.update_progress(job)
        
        # Callback checkpoint
        def checkpoint_callback(job: FileJob):
            self.state_manager.update_job(job)
            logger.debug(f"Checkpoint saved for {job.name}: {job.progress:.1f}%")
        
        # Start time
        start_time = time.time()
        
        try:
            # Lakukan copy
            logger.info(f"Starting copy for {job.name}")
            success = self.file_handler.safe_copy(
                job=job,
                progress_callback=progress_callback,
                checkpoint_callback=checkpoint_callback
            )
            
            duration = time.time() - start_time
            
            if success:
                # Sukses
                job.status = STATUS_COMPLETED
                job.end_time = time.time()
                
                # Catat history
                self.history_logger.log_success(
                    filename=job.name,
                    size_bytes=job.size_bytes,
                    duration_seconds=duration,
                    retry_count=job.retry_count
                )
                
                # Update state
                self.state_manager.update_job(job)
                
                # Hapus file sumber dari 12
                logger.info(f"Deleting source file: {job.source_path}")
                self.file_handler.delete_file(job.source_path)
                
                logger.info(f"Worker-{self.worker_id} completed: {job.name} in {duration:.2f}s")
                
                # Notifikasi queue manager
                self.queue_manager.complete_job(job, success=True)
                
            else:
                # Gagal
                raise Exception("Copy failed (safe_copy returned False)")
                
        except Exception as e:
            logger.error(f"Worker-{self.worker_id} failed: {job.name} - {e}")
            
            # Hitung durasi
            duration = time.time() - start_time
            
            # Catat history (gagal)
            self.history_logger.log_failed(
                filename=job.name,
                size_bytes=job.size_bytes,
                error_msg=str(e),
                retry_count=job.retry_count + 1
            )
            
            # Handle retry
            if job.retry_count < job.max_retry - 1:
                # Masih ada kesempatan retry
                logger.info(f"Worker-{self.worker_id} will retry {job.name} ({job.retry_count + 1}/{job.max_retry})")
                self.queue_manager.fail_job(job, str(e), retry=True)
            else:
                # Gagal permanen
                logger.error(f"Worker-{self.worker_id} permanent failure: {job.name}")
                self.queue_manager.fail_job(job, str(e), retry=False)
    
    def stop(self):
        """Hentikan worker"""
        self.running = False
        logger.info(f"DownloadWorker-{self.worker_id} stopping...")
    
    def is_busy(self) -> bool:
        """Cek apakah worker sedang sibuk"""
        return self.current_job is not None
    
    def get_current_job(self) -> Optional[FileJob]:
        """Dapatkan job yang sedang diproses"""
        return self.current_job


# Test sederhana
if __name__ == "__main__":
    from ..utils.logger import setup_logging
    setup_logging()
    
    print("DownloadWorker class ready with full debug")