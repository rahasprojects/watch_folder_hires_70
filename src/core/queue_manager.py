# -*- coding: utf-8 -*-
"""
Queue manager untuk antrian FIFO
"""

import queue
import threading
import logging
from typing import List, Optional, Callable
from datetime import datetime
from ..models.file_job import FileJob
from ..constants.settings import STATUS_WAITING, STATUS_DOWNLOADING, STATUS_COMPLETED, STATUS_FAILED

logger = logging.getLogger(__name__)

class QueueManager:
    """
    Kelas untuk mengelola antrian FIFO
    """
    
    def __init__(self):
        """Inisialisasi QueueManager"""
        self.queue = queue.Queue()  # FIFO queue
        self.jobs = {}  # Dictionary semua jobs: {filename: FileJob}
        self.active_jobs = []  # List jobs yang sedang diproses
        self.waiting_jobs = []  # List jobs yang menunggu
        self.completed_jobs = []  # List jobs yang selesai
        self.failed_jobs = []  # List jobs yang gagal
        
        self.lock = threading.Lock()
        self.callbacks = []  # Untuk notifikasi perubahan
        
        logger.info("QueueManager initialized")
    
    def add_job(self, job: FileJob) -> int:
        """
        Tambah job ke antrian
        
        Args:
            job: FileJob object
            
        Returns:
            Posisi dalam antrian
        """
        with self.lock:
            # Cek apakah sudah ada
            # if job.name in self.jobs:
            #     logger.warning(f"Job {job.name} already exists in queue")
            #     return self.get_position(job.name)
            
            # Set status dan timestamp
            job.status = STATUS_WAITING
            job.detected_time = job.detected_time or datetime.now()
            
            # Simpan job
            self.jobs[job.name] = job
            self.waiting_jobs.append(job.name)
            
            # Masukkan ke queue
            self.queue.put(job)
            
            # Update posisi
            self._update_positions()
            
            logger.info(f"Job added to queue: {job.name} (size: {job.size_gb:.2f}GB)")
            self._notify_callbacks('added', job)
            
            return self.get_position(job.name)
    
    def get_next_job(self) -> Optional[FileJob]:
        """
        Ambil job berikutnya dari antrian (blocking)
        
        Returns:
            FileJob object atau None jika queue kosong
        """
        try:
            job = self.queue.get(timeout=1)
            
            with self.lock:
                if job.name in self.jobs:
                    job.status = STATUS_DOWNLOADING
                    self.active_jobs.append(job.name)
                    if job.name in self.waiting_jobs:
                        self.waiting_jobs.remove(job.name)
                    
                    logger.info(f"Job started: {job.name}")
                    self._notify_callbacks('started', job)
                    
                    return job
                else:
                    logger.warning(f"Job {job.name} not found in jobs dict")
                    return None
                    
        except queue.Empty:
            return None
    
    def complete_job(self, job: FileJob, success: bool = True):
        """
        Tandai job sebagai selesai
        
        Args:
            job: FileJob object
            success: True jika sukses, False jika gagal
        """
        with self.lock:
            if job.name not in self.jobs:
                logger.warning(f"Job {job.name} not found")
                return
            
            # Update status
            if success:
                job.status = STATUS_COMPLETED
                self.completed_jobs.append(job.name)
                logger.info(f"Job completed: {job.name}")
            else:
                job.status = STATUS_FAILED
                self.failed_jobs.append(job.name)
                logger.warning(f"Job failed: {job.name}")
            
            # Hapus dari active
            if job.name in self.active_jobs:
                self.active_jobs.remove(job.name)
            
            # Update posisi
            self._update_positions()
            
            # Mark as done di queue
            self.queue.task_done()
            
            self._notify_callbacks('completed' if success else 'failed', job)
    
    def fail_job(self, job: FileJob, error: str, retry: bool = True):
        """
        Tandai job sebagai gagal (dengan opsi retry)
        
        Args:
            job: FileJob object
            error: Pesan error
            retry: True jika boleh retry
        """
        with self.lock:
            job.retry_count += 1
            job.last_error = error
            
            if retry and job.retry_count < job.max_retry:
                # Kembalikan ke antrian untuk retry
                job.status = STATUS_WAITING
                self.waiting_jobs.append(job.name)
                self.queue.put(job)
                logger.warning(f"Job {job.name} will retry ({job.retry_count}/{job.max_retry})")
            else:
                # Gagal permanen
                job.status = STATUS_FAILED
                self.failed_jobs.append(job.name)
                logger.error(f"Job failed permanently: {job.name} - {error}")
            
            # Hapus dari active
            if job.name in self.active_jobs:
                self.active_jobs.remove(job.name)
            
            self._update_positions()
            self._notify_callbacks('failed', job)
    
    def get_job(self, filename: str) -> Optional[FileJob]:
        """Dapatkan job berdasarkan nama file"""
        return self.jobs.get(filename)
    
    def get_all_jobs(self) -> List[FileJob]:
        """Dapatkan semua jobs"""
        with self.lock:
            return list(self.jobs.values())
    
    def get_active_jobs(self) -> List[FileJob]:
        """Dapatkan jobs yang sedang aktif"""
        with self.lock:
            return [self.jobs[name] for name in self.active_jobs if name in self.jobs]
    
    def get_waiting_jobs(self) -> List[FileJob]:
        """Dapatkan jobs yang menunggu"""
        with self.lock:
            return [self.jobs[name] for name in self.waiting_jobs if name in self.jobs]
    
    def get_position(self, filename: str) -> int:
        """Dapatkan posisi job dalam antrian (tanpa lock)"""
        # Tanpa lock dulu untuk testing
        if filename in self.waiting_jobs:
            return self.waiting_jobs.index(filename) + 1
        return 0
        
    def queue_size(self) -> int:
        """Jumlah job dalam antrian (waiting)"""
        return len(self.waiting_jobs)
    
    def active_count(self) -> int:
        """Jumlah job aktif"""
        return len(self.active_jobs)
    
    def _update_positions(self):
        """Update posisi semua job dalam antrian"""
        for i, name in enumerate(self.waiting_jobs):
            if name in self.jobs:
                self.jobs[name].queue_position = i + 1
    
    def register_callback(self, callback: Callable):
        """Register callback untuk notifikasi perubahan"""
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, event: str, job: FileJob):
        """Notifikasi ke semua callback"""
        for callback in self.callbacks:
            try:
                callback(event, job)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def clear_completed(self):
        """Hapus jobs yang sudah completed/failed dari memory"""
        with self.lock:
            # Hapus dari jobs dict
            for name in self.completed_jobs + self.failed_jobs:
                if name in self.jobs:
                    del self.jobs[name]
            
            # Clear lists
            self.completed_jobs.clear()
            self.failed_jobs.clear()
            
            logger.info("Cleared completed/failed jobs from memory")
    
    def get_stats(self) -> dict:
        """Dapatkan statistik queue"""
        with self.lock:
            return {
                'waiting': len(self.waiting_jobs),
                'active': len(self.active_jobs),
                'completed': len(self.completed_jobs),
                'failed': len(self.failed_jobs),
                'total': len(self.jobs)
            }