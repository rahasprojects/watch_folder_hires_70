# -*- coding: utf-8 -*-
"""
Manager untuk mengatur upload workers ke server 51 dan 40
"""

import threading
import time
import logging
import os
from typing import List, Optional, Dict, Tuple
from ..models.upload_job import UploadJob
from ..core.upload_worker_51 import UploadWorker51
from ..core.upload_worker_40 import UploadWorker40
from ..core.upload_queue_manager import UploadQueueManager
from ..core.file_handler import FileHandler
from ..utils.state_manager import StateManager
from ..utils.history import HistoryLogger
from ..utils.config_manager import ConfigManager
from ..constants.settings import DEFAULT_MAX_UPLOAD_51, DEFAULT_MAX_UPLOAD_40

logger = logging.getLogger(__name__)

class UploadManager:
    """
    Kelas untuk mengelola upload workers ke server 51 dan 40
    - Mengelola workers untuk masing-masing destination
    - Tracking completion untuk file yang sama (51 dan 40)
    - Menghapus file dari 70 jika kedua upload selesai
    """
    
    def __init__(self, 
                 max_workers_51: int = DEFAULT_MAX_UPLOAD_51,
                 max_workers_40: int = DEFAULT_MAX_UPLOAD_40,
                 queue_manager: Optional[UploadQueueManager] = None,
                 file_handler: Optional[FileHandler] = None,
                 state_manager: Optional[StateManager] = None,
                 history_logger: Optional[HistoryLogger] = None):
        """
        Inisialisasi UploadManager
        
        Args:
            max_workers_51: Maksimal worker paralel untuk upload ke 51
            max_workers_40: Maksimal worker paralel untuk upload ke 40
            queue_manager: UploadQueueManager instance
            file_handler: FileHandler instance
            state_manager: StateManager instance
            history_logger: HistoryLogger instance
        """
        self.max_workers_51 = max_workers_51
        self.max_workers_40 = max_workers_40
        
        # Managers
        self.queue_manager = queue_manager or UploadQueueManager()
        self.file_handler = file_handler or FileHandler()
        self.state_manager = state_manager or StateManager()
        self.history_logger = history_logger or HistoryLogger()
        self.config_manager = ConfigManager()
        
        # Workers
        self.workers_51: List[UploadWorker51] = []
        self.workers_40: List[UploadWorker40] = []
        
        # Tracking completion per source file (file di 70)
        # Format: {source_path: {'51': bool, '40': bool, 'job_51': UploadJob, 'job_40': UploadJob}}
        self.completion_tracker: Dict[str, Dict] = {}
        
        # Control
        self.running = False
        self.lock = threading.Lock()
        
        # Callbacks untuk progress
        self.progress_callbacks = []
        
        logger.info(f"UploadManager initialized with max_workers_51={max_workers_51}, max_workers_40={max_workers_40}")
    
    def start(self):
        """Start semua workers"""
        if self.running:
            logger.warning("UploadManager already running")
            return
        
        self.running = True
        
        # Start workers untuk 51 (HIGH PRIORITY)
        for i in range(self.max_workers_51):
            worker = UploadWorker51(
                worker_id=i + 1,
                queue_manager=self.queue_manager,
                upload_manager=self,
                file_handler=self.file_handler,
                state_manager=self.state_manager,
                history_logger=self.history_logger
            )
            worker.start()
            self.workers_51.append(worker)
            logger.info(f"Started UploadWorker51-{i+1}")
        
        # Start workers untuk 40 (NORMAL PRIORITY)
        for i in range(self.max_workers_40):
            worker = UploadWorker40(
                worker_id=i + 1,
                queue_manager=self.queue_manager,
                upload_manager=self,
                file_handler=self.file_handler,
                state_manager=self.state_manager,
                history_logger=self.history_logger
            )
            worker.start()
            self.workers_40.append(worker)
            logger.info(f"Started UploadWorker40-{i+1}")
        
        logger.info(f"Total upload workers started: {self.max_workers_51 + self.max_workers_40}")
    
    def stop(self):
        """Stop semua workers"""
        logger.info("Stopping all upload workers...")
        self.running = False
        
        # Stop workers 51
        for worker in self.workers_51:
            worker.stop()
        
        # Stop workers 40
        for worker in self.workers_40:
            worker.stop()
        
        # Tunggu semua worker selesai
        for worker in self.workers_51 + self.workers_40:
            worker.join(timeout=5)
        
        logger.info("All upload workers stopped")
    
    def on_upload_complete(self, job: UploadJob):
        """
        Dipanggil saat satu upload job selesai
        
        Args:
            job: UploadJob yang selesai
        """
        with self.lock:
            source_path = job.source_path
            destination = job.destination
            
            # Inisialisasi tracker jika belum ada
            if source_path not in self.completion_tracker:
                self.completion_tracker[source_path] = {
                    '51': False,
                    '40': False,
                    'job_51': None,
                    'job_40': None,
                    'file_name': job.file_name,
                    'size': job.file_size
                }
            
            # Update status
            if destination == 51:
                self.completion_tracker[source_path]['51'] = True
                self.completion_tracker[source_path]['job_51'] = job
                logger.info(f"✅ Upload to 51 completed: {job.file_name}")
            else:  # destination == 40
                self.completion_tracker[source_path]['40'] = True
                self.completion_tracker[source_path]['job_40'] = job
                logger.info(f"✅ Upload to 40 completed: {job.file_name}")
            
            # Cek apakah kedua upload sudah selesai
            tracker = self.completion_tracker[source_path]
            if tracker['51'] and tracker['40']:
                self._handle_both_uploads_complete(source_path)
    
    def on_upload_failed(self, job: UploadJob):
        """
        Dipanggil saat upload job gagal permanen
        
        Args:
            job: UploadJob yang gagal
        """
        with self.lock:
            source_path = job.source_path
            destination = job.destination
            
            logger.warning(f"❌ Upload to {destination} failed permanently: {job.file_name}")
            
            # Tidak perlu hapus file dari 70 karena salah satu gagal
            # Tapi kita catat di tracker
            if source_path in self.completion_tracker:
                if destination == 51:
                    self.completion_tracker[source_path]['51'] = False
                else:
                    self.completion_tracker[source_path]['40'] = False
    
    def _handle_both_uploads_complete(self, source_path: str):
        """
        Handle ketika kedua upload (51 dan 40) sudah selesai
        
        Args:
            source_path: Path file di 70
        """
        tracker = self.completion_tracker[source_path]
        file_name = tracker['file_name']
        
        logger.info(f"🎉 Both uploads completed for: {file_name}")
        
        # ===== HAPUS FILE DARI 70 =====
        try:
            if os.path.exists(source_path):
                os.remove(source_path)
                logger.info(f"🗑️ Deleted source file from 70: {file_name}")
            else:
                logger.warning(f"File already deleted: {source_path}")
        except Exception as e:
            logger.error(f"Error deleting file from 70: {e}")
        
        # Catat ke history khusus (opsional)
        self.history_logger.log_success(
            filename=file_name,
            size_bytes=tracker['size'],
            duration_seconds=0,  # Total duration? Bisa dihitung nanti
            retry_count=0,
            destination="70_DELETED"
        )
        
        # Hapus dari tracker
        del self.completion_tracker[source_path]
    
    def update_progress(self, job: UploadJob):
        """
        Update progress upload
        
        Args:
            job: UploadJob object
        """
        # Notifikasi callbacks untuk GUI
        self._notify_progress(job)
    
    def _notify_progress(self, job: UploadJob):
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
        """Dapatkan statistik upload"""
        queue_stats = self.queue_manager.get_stats()
        
        # Hitung worker stats
        busy_51 = sum(1 for w in self.workers_51 if w.is_busy())
        busy_40 = sum(1 for w in self.workers_40 if w.is_busy())
        
        # Hitung total speed
        total_speed_51 = 0
        for worker in self.workers_51:
            job = worker.get_current_job()
            if job:
                total_speed_51 += job.speed_mbps
        
        total_speed_40 = 0
        for worker in self.workers_40:
            job = worker.get_current_job()
            if job:
                total_speed_40 += job.speed_mbps
        
        return {
            'queue': queue_stats,
            'workers_51': {
                'total': len(self.workers_51),
                'busy': busy_51,
                'idle': len(self.workers_51) - busy_51,
                'total_speed_mbps': total_speed_51
            },
            'workers_40': {
                'total': len(self.workers_40),
                'busy': busy_40,
                'idle': len(self.workers_40) - busy_40,
                'total_speed_mbps': total_speed_40
            },
            'completion_tracker': {
                'pending': len(self.completion_tracker),
                'completed': sum(1 for v in self.completion_tracker.values() if v['51'] and v['40'])
            },
            'max_workers_51': self.max_workers_51,
            'max_workers_40': self.max_workers_40,
            'running': self.running
        }
    
    def get_active_uploads_51(self) -> List[UploadJob]:
        """Dapatkan semua upload aktif ke 51"""
        return self.queue_manager.get_active_jobs_51()
    
    def get_active_uploads_40(self) -> List[UploadJob]:
        """Dapatkan semua upload aktif ke 40"""
        return self.queue_manager.get_active_jobs_40()
    
    def get_waiting_uploads_51(self) -> List[UploadJob]:
        """Dapatkan semua upload waiting ke 51"""
        return self.queue_manager.get_waiting_jobs_51()
    
    def get_waiting_uploads_40(self) -> List[UploadJob]:
        """Dapatkan semua upload waiting ke 40"""
        return self.queue_manager.get_waiting_jobs_40()
    
    def set_max_workers_51(self, new_max: int):
        """
        Ubah jumlah maksimal worker untuk upload ke 51
        
        Args:
            new_max: Jumlah worker baru
        """
        if new_max == self.max_workers_51:
            return
        
        if new_max > self.max_workers_51:
            # Tambah worker
            for i in range(self.max_workers_51, new_max):
                worker = UploadWorker51(
                    worker_id=i + 1,
                    queue_manager=self.queue_manager,
                    upload_manager=self
                )
                worker.start()
                self.workers_51.append(worker)
            logger.info(f"Added {new_max - self.max_workers_51} workers for 51")
        else:
            # Kurangi worker (stop yang idle)
            to_stop = []
            for worker in self.workers_51[new_max:]:
                if not worker.is_busy():
                    worker.stop()
                    to_stop.append(worker)
            
            for worker in to_stop:
                self.workers_51.remove(worker)
            logger.info(f"Removed {len(to_stop)} idle workers for 51")
        
        self.max_workers_51 = new_max
    
    def set_max_workers_40(self, new_max: int):
        """
        Ubah jumlah maksimal worker untuk upload ke 40
        
        Args:
            new_max: Jumlah worker baru
        """
        if new_max == self.max_workers_40:
            return
        
        if new_max > self.max_workers_40:
            # Tambah worker
            for i in range(self.max_workers_40, new_max):
                worker = UploadWorker40(
                    worker_id=i + 1,
                    queue_manager=self.queue_manager,
                    upload_manager=self
                )
                worker.start()
                self.workers_40.append(worker)
            logger.info(f"Added {new_max - self.max_workers_40} workers for 40")
        else:
            # Kurangi worker (stop yang idle)
            to_stop = []
            for worker in self.workers_40[new_max:]:
                if not worker.is_busy():
                    worker.stop()
                    to_stop.append(worker)
            
            for worker in to_stop:
                self.workers_40.remove(worker)
            logger.info(f"Removed {len(to_stop)} idle workers for 40")
        
        self.max_workers_40 = new_max


# Test sederhana
if __name__ == "__main__":
    from ..utils.logger import setup_logging
    setup_logging()
    
    print("UploadManager class ready")
    print("- Manages workers for 51 (HIGH) and 40 (NORMAL)")
    print("- Tracks completion for both uploads")
    print("- Deletes from 70 only when both are complete")