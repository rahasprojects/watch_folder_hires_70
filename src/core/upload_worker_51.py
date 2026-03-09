# -*- coding: utf-8 -*-
"""
Worker thread untuk upload file ke HIRES (51) - PRIORITAS TINGGI
"""

import threading
import time
import logging
import os
from typing import Optional
from ..models.upload_job import UploadJob
from ..core.file_handler import FileHandler
from ..utils.state_manager import StateManager
from ..utils.history import HistoryLogger
from ..utils.config_manager import ConfigManager
from ..constants.settings import STATUS_UPLOADING, STATUS_COMPLETED, STATUS_FAILED

logger = logging.getLogger(__name__)

class UploadWorker51(threading.Thread):
    """
    Worker thread untuk menangani upload satu file ke server 51 (HIRES)
    PRIORITAS: TINGGI (⭐)
    """
    
    def __init__(self, worker_id: int, queue_manager, upload_manager, 
                 file_handler: Optional[FileHandler] = None,
                 state_manager: Optional[StateManager] = None,
                 history_logger: Optional[HistoryLogger] = None):
        """
        Inisialisasi UploadWorker51
        
        Args:
            worker_id: ID worker (untuk logging)
            queue_manager: UploadQueueManager instance
            upload_manager: UploadManager instance
            file_handler: FileHandler instance (optional)
            state_manager: StateManager instance (optional)
            history_logger: HistoryLogger instance (optional)
        """
        super().__init__()
        self.worker_id = worker_id
        self.queue_manager = queue_manager
        self.upload_manager = upload_manager
        self.file_handler = file_handler or FileHandler()
        self.state_manager = state_manager or StateManager()
        self.history_logger = history_logger or HistoryLogger()
        self.config_manager = ConfigManager()
        
        self.daemon = True
        self.running = True
        self.current_job: Optional[UploadJob] = None
        
        logger.info(f"UploadWorker51-{worker_id} initialized (⭐ HIGH PRIORITY)")
    
    def run(self):
        """Main loop worker"""
        logger.info(f"UploadWorker51-{self.worker_id} started")
        
        while self.running:
            try:
                # Ambil job berikutnya dari queue 51 (HIGH PRIORITY)
                job = self.queue_manager.get_next_job_51()
                
                if job:
                    self.current_job = job
                    self._process_upload(job)
                    self.current_job = None
                else:
                    # Tidak ada job, sleep sebentar
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"UploadWorker51-{self.worker_id} error: {e}")
                time.sleep(5)
        
        logger.info(f"UploadWorker51-{self.worker_id} stopped")
    
    def _process_upload(self, job: UploadJob):
        """
        Proses satu job upload
        
        Args:
            job: UploadJob object
        """
        logger.info(f"Worker51-{self.worker_id} processing: {job.file_name} (⭐ HIGH PRIORITY)")
        logger.info(f"Source path: {job.source_path}")
        logger.info(f"Dest path: {job.dest_path}")
        logger.info(f"Size: {job.file_size} bytes")
        
        # ========== CEK SOURCE PATH ==========
        import os
        if not job.source_path or job.source_path == "":
            logger.error(f"Source path is EMPTY for {job.file_name}")
            self.queue_manager.fail_job(job, "Source path is empty", retry=False)
            return
            
        if not os.path.exists(job.source_path):
            logger.error(f"Source file does NOT exist: {job.source_path}")
            self.queue_manager.fail_job(job, f"Source file not found: {job.source_path}", retry=True)
            return
        else:
            logger.info(f"Source file exists, size: {os.path.getsize(job.source_path)} bytes")
        
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
        
        logger.info(f"All path checks passed for {job.file_name}")
        logger.info(f"Final source: {job.source_path}")
        logger.info(f"Final dest: {job.dest_path}")
        
        # Update status
        job.status = STATUS_UPLOADING
        job.start_time = job.start_time or time.time()
        
        # ===== MEMBUAT OBJEK YANG KOMPATIBEL DENGAN FILEHANDLER =====
        # FileHandler membutuhkan objek dengan atribut:
        # - source_path
        # - dest_path
        # - size_bytes
        # - copied_bytes
        # - last_checkpoint
        # - name (opsional)
        # - size_gb (property, tapi tidak masalah)
        
        class UploadTaskWrapper:
            """Wrapper untuk membuat UploadJob kompatibel dengan FileHandler"""
            def __init__(self, upload_job):
                self.upload_job = upload_job
                self.source_path = upload_job.source_path
                self.dest_path = upload_job.dest_path
                self.size_bytes = upload_job.file_size
                self.copied_bytes = upload_job.copied_bytes
                self.last_checkpoint = upload_job.last_checkpoint
                self.name = upload_job.file_name
            
            @property
            def size_gb(self):
                return self.upload_job.size_gb
            
            @property
            def speed_mbps(self):
                return self.upload_job.speed_mbps
            
            @property
            def eta_formatted(self):
                return self.upload_job.eta_formatted
        
        upload_task = UploadTaskWrapper(job)
        # ============================================================
        
        # Callback progress
        def progress_callback(copied_bytes: int, percent: float):
            job.copied_bytes = copied_bytes
            job.progress = percent
            self.upload_manager.update_progress(job)
        
        # Callback checkpoint
        def checkpoint_callback(task):
            # Update job dengan progress dari task
            job.copied_bytes = getattr(task, 'copied_bytes', job.copied_bytes)
            job.last_checkpoint = getattr(task, 'last_checkpoint', job.last_checkpoint)
            logger.debug(f"Checkpoint saved for {job.file_name}: {job.progress:.1f}%")
        
        # Start time
        start_time = time.time()
        
        try:
            # Lakukan upload menggunakan file_handler dengan wrapper
            logger.info(f"Starting upload for {job.file_name}")
            
            success = self.file_handler.safe_copy(
                job=upload_task,
                progress_callback=progress_callback,
                checkpoint_callback=checkpoint_callback
            )
            
            # Update job dengan progress terakhir
            job.copied_bytes = upload_task.copied_bytes
            job.last_checkpoint = upload_task.last_checkpoint
            
            duration = time.time() - start_time
            
            if success:
                # Sukses
                job.status = STATUS_COMPLETED
                job.end_time = time.time()
                
                # Catat history
                actual_filename = os.path.basename(job.dest_path)
                self.history_logger.log_success(
                    filename=actual_filename,
                    size_bytes=job.file_size,
                    duration_seconds=duration,
                    retry_count=job.retry_count,
                    destination=str(job.destination)
                )
                
                logger.info(f"Worker51-{self.worker_id} completed: {actual_filename} in {duration:.2f}s")
                
                # Notifikasi queue manager dan upload manager
                self.queue_manager.complete_job(job, success=True)
                self.upload_manager.on_upload_complete(job)
                
            else:
                # Gagal
                raise Exception("Upload failed (safe_copy returned False)")
                
        except Exception as e:
            logger.error(f"Worker51-{self.worker_id} failed: {job.file_name} - {e}")
            
            # Hitung durasi
            duration = time.time() - start_time
            
            # Catat history (gagal)
            self.history_logger.log_failed(
                filename=job.file_name,
                size_bytes=job.file_size,
                error_msg=str(e),
                retry_count=job.retry_count + 1,
                destination=str(job.destination)
            )
            
            # Handle retry
            if job.retry_count < job.max_retry - 1:
                # Masih ada kesempatan retry
                logger.info(f"Worker51-{self.worker_id} will retry {job.file_name} ({job.retry_count + 1}/{job.max_retry})")
                self.queue_manager.fail_job(job, str(e), retry=True)
            else:
                # Gagal permanen
                logger.error(f"Worker51-{self.worker_id} permanent failure: {job.file_name}")
                self.queue_manager.fail_job(job, str(e), retry=False)
                self.upload_manager.on_upload_failed(job)
    
    def stop(self):
        """Hentikan worker"""
        self.running = False
        logger.info(f"UploadWorker51-{self.worker_id} stopping...")
    
    def is_busy(self) -> bool:
        """Cek apakah worker sedang sibuk"""
        return self.current_job is not None
    
    def get_current_job(self) -> Optional[UploadJob]:
        """Dapatkan job yang sedang diproses"""
        return self.current_job


# Test sederhana
if __name__ == "__main__":
    from ..utils.logger import setup_logging
    setup_logging()
    
    print("UploadWorker51 class ready (⭐ HIGH PRIORITY)")
    print("- Using UploadTaskWrapper for FileHandler compatibility")