# -*- coding: utf-8 -*-
"""
Queue manager untuk upload ke server 51 dan 40
Mengelola 2 queue terpisah dengan prioritas berbeda
"""

import queue
import threading
import logging
from typing import List, Optional, Dict
from datetime import datetime
from ..models.upload_job import UploadJob
from ..constants.settings import STATUS_WAITING, STATUS_UPLOADING, STATUS_COMPLETED, STATUS_FAILED

logger = logging.getLogger(__name__)

class UploadQueueManager:
    """
    Kelas untuk mengelola antrian upload ke 51 dan 40
    Memiliki 2 queue terpisah:
    - queue_51: HIGH priority (untuk HIRES)
    - queue_40: NORMAL priority (untuk LOWRES)
    """
    
    def __init__(self):
        """Inisialisasi UploadQueueManager"""
        # Queue terpisah untuk masing-masing destination
        self.queue_51 = queue.Queue()  # HIGH PRIORITY
        self.queue_40 = queue.Queue()  # NORMAL PRIORITY
        
        # Dictionary semua jobs: {job_id: UploadJob}
        self.jobs: Dict[str, UploadJob] = {}
        
        # Tracking jobs per destination
        self.active_jobs_51: List[str] = []
        self.active_jobs_40: List[str] = []
        self.waiting_jobs_51: List[str] = []
        self.waiting_jobs_40: List[str] = []
        self.completed_jobs: List[str] = []
        self.failed_jobs: List[str] = []
        
        self.lock = threading.Lock()
        self.callbacks = []  # Untuk notifikasi perubahan
        
        logger.info("UploadQueueManager initialized with separate queues for 51 and 40")
    
    def add_job(self, job: UploadJob) -> int:
        """
        Tambah job ke antrian sesuai destination
        
        Args:
            job: UploadJob object
            
        Returns:
            Posisi dalam antrian (untuk destination masing-masing)
        """
        with self.lock:
            # Buat ID unik untuk job
            job_id = f"{job.destination}_{job.file_name}_{datetime.now().timestamp()}"
            
            # Set status dan timestamp
            job.status = STATUS_WAITING
            job.created_time = job.created_time or datetime.now()
            
            # Simpan job
            self.jobs[job_id] = job
            
            # Masukkan ke queue sesuai destination
            if job.destination == 51:
                self.queue_51.put(job)
                self.waiting_jobs_51.append(job_id)
                queue_name = "51-HIGH"
                position = len(self.waiting_jobs_51)
            else:  # destination == 40
                self.queue_40.put(job)
                self.waiting_jobs_40.append(job_id)
                queue_name = "40-NORMAL"
                position = len(self.waiting_jobs_40)
            
            logger.info(f"[{queue_name}] Job added to queue: {job.file_name} (size: {job.size_gb:.2f}GB)")
            self._notify_callbacks('added', job)
            
            return position
    
    def get_next_job_51(self) -> Optional[UploadJob]:
        """
        Ambil job berikutnya dari queue 51 (HIGH PRIORITY)
        
        Returns:
            UploadJob object atau None jika queue kosong
        """
        try:
            job = self.queue_51.get(timeout=1)
            
            with self.lock:
                # Cari job_id berdasarkan job
                job_id = self._find_job_id(job)
                if job_id and job_id in self.waiting_jobs_51:
                    job.status = STATUS_UPLOADING
                    self.active_jobs_51.append(job_id)
                    self.waiting_jobs_51.remove(job_id)
                    
                    logger.info(f"[51-HIGH] Job started: {job.file_name}")
                    self._notify_callbacks('started', job)
                    
                    return job
                else:
                    logger.warning(f"[51-HIGH] Job {job.file_name} not found in waiting list")
                    return None
                    
        except queue.Empty:
            return None
    
    def get_next_job_40(self) -> Optional[UploadJob]:
        """
        Ambil job berikutnya dari queue 40 (NORMAL PRIORITY)
        
        Returns:
            UploadJob object atau None jika queue kosong
        """
        try:
            job = self.queue_40.get(timeout=1)
            
            with self.lock:
                # Cari job_id berdasarkan job
                job_id = self._find_job_id(job)
                if job_id and job_id in self.waiting_jobs_40:
                    job.status = STATUS_UPLOADING
                    self.active_jobs_40.append(job_id)
                    self.waiting_jobs_40.remove(job_id)
                    
                    logger.info(f"[40-NORMAL] Job started: {job.file_name}")
                    self._notify_callbacks('started', job)
                    
                    return job
                else:
                    logger.warning(f"[40-NORMAL] Job {job.file_name} not found in waiting list")
                    return None
                    
        except queue.Empty:
            return None
    
    def complete_job(self, job: UploadJob, success: bool = True):
        """
        Tandai job sebagai selesai
        
        Args:
            job: UploadJob object
            success: True jika sukses, False jika gagal
        """
        with self.lock:
            job_id = self._find_job_id(job)
            if not job_id:
                logger.warning(f"Job {job.file_name} not found")
                return
            
            # Update status
            if success:
                job.status = STATUS_COMPLETED
                self.completed_jobs.append(job_id)
                log_msg = f"[{job.destination}-{'HIGH' if job.destination==51 else 'NORMAL'}] Job completed: {job.file_name}"
                logger.info(log_msg)
            else:
                job.status = STATUS_FAILED
                self.failed_jobs.append(job_id)
                log_msg = f"[{job.destination}-{'HIGH' if job.destination==51 else 'NORMAL'}] Job failed: {job.file_name}"
                logger.warning(log_msg)
            
            # Hapus dari active list
            if job.destination == 51 and job_id in self.active_jobs_51:
                self.active_jobs_51.remove(job_id)
            elif job.destination == 40 and job_id in self.active_jobs_40:
                self.active_jobs_40.remove(job_id)
            
            # Mark as done di queue
            if job.destination == 51:
                self.queue_51.task_done()
            else:
                self.queue_40.task_done()
            
            self._notify_callbacks('completed' if success else 'failed', job)
    
    def fail_job(self, job: UploadJob, error: str, retry: bool = True):
        """
        Tandai job sebagai gagal (dengan opsi retry)
        
        Args:
            job: UploadJob object
            error: Pesan error
            retry: True jika boleh retry
        """
        with self.lock:
            job.retry_count += 1
            job.last_error = error
            
            if retry and job.retry_count < job.max_retry:
                # Kembalikan ke antrian untuk retry
                job.status = STATUS_WAITING
                
                if job.destination == 51:
                    self.waiting_jobs_51.append(self._find_job_id(job))
                    self.queue_51.put(job)
                else:
                    self.waiting_jobs_40.append(self._find_job_id(job))
                    self.queue_40.put(job)
                
                logger.warning(f"[{job.destination}] Job {job.file_name} will retry ({job.retry_count}/{job.max_retry})")
            else:
                # Gagal permanen
                job.status = STATUS_FAILED
                self.failed_jobs.append(self._find_job_id(job))
                logger.error(f"[{job.destination}] Job failed permanently: {job.file_name} - {error}")
            
            # Hapus dari active list
            if job.destination == 51 and self._find_job_id(job) in self.active_jobs_51:
                self.active_jobs_51.remove(self._find_job_id(job))
            elif job.destination == 40 and self._find_job_id(job) in self.active_jobs_40:
                self.active_jobs_40.remove(self._find_job_id(job))
            
            self._notify_callbacks('failed', job)
    
    def _find_job_id(self, job: UploadJob) -> Optional[str]:
        """Cari job_id berdasarkan job object"""
        for job_id, stored_job in self.jobs.items():
            if stored_job is job:
                return job_id
        return None
    
    def get_job_by_source(self, source_path: str) -> List[UploadJob]:
        """
        Dapatkan semua job yang berasal dari source file yang sama
        
        Args:
            source_path: Path file di 70
            
        Returns:
            List of UploadJob
        """
        result = []
        for job in self.jobs.values():
            if job.source_path == source_path:
                result.append(job)
        return result
    
    def get_active_jobs_51(self) -> List[UploadJob]:
        """Dapatkan jobs yang sedang aktif di queue 51"""
        with self.lock:
            return [self.jobs[job_id] for job_id in self.active_jobs_51 if job_id in self.jobs]
    
    def get_active_jobs_40(self) -> List[UploadJob]:
        """Dapatkan jobs yang sedang aktif di queue 40"""
        with self.lock:
            return [self.jobs[job_id] for job_id in self.active_jobs_40 if job_id in self.jobs]
    
    def get_waiting_jobs_51(self) -> List[UploadJob]:
        """Dapatkan jobs yang menunggu di queue 51"""
        with self.lock:
            return [self.jobs[job_id] for job_id in self.waiting_jobs_51 if job_id in self.jobs]
    
    def get_waiting_jobs_40(self) -> List[UploadJob]:
        """Dapatkan jobs yang menunggu di queue 40"""
        with self.lock:
            return [self.jobs[job_id] for job_id in self.waiting_jobs_40 if job_id in self.jobs]
    
    def queue_size_51(self) -> int:
        """Jumlah job dalam antrian 51 (waiting)"""
        return len(self.waiting_jobs_51)
    
    def queue_size_40(self) -> int:
        """Jumlah job dalam antrian 40 (waiting)"""
        return len(self.waiting_jobs_40)
    
    def active_count_51(self) -> int:
        """Jumlah job aktif di queue 51"""
        return len(self.active_jobs_51)
    
    def active_count_40(self) -> int:
        """Jumlah job aktif di queue 40"""
        return len(self.active_jobs_40)
    
    def get_stats(self) -> dict:
        """Dapatkan statistik queue"""
        with self.lock:
            return {
                '51': {
                    'waiting': len(self.waiting_jobs_51),
                    'active': len(self.active_jobs_51),
                    'total': len(self.waiting_jobs_51) + len(self.active_jobs_51)
                },
                '40': {
                    'waiting': len(self.waiting_jobs_40),
                    'active': len(self.active_jobs_40),
                    'total': len(self.waiting_jobs_40) + len(self.active_jobs_40)
                },
                'completed': len(self.completed_jobs),
                'failed': len(self.failed_jobs),
                'total_jobs': len(self.jobs)
            }
    
    def register_callback(self, callback):
        """Register callback untuk notifikasi perubahan"""
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, event: str, job: UploadJob):
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
            for job_id in self.completed_jobs + self.failed_jobs:
                if job_id in self.jobs:
                    del self.jobs[job_id]
            
            # Clear lists
            self.completed_jobs.clear()
            self.failed_jobs.clear()
            
            logger.info("Cleared completed/failed upload jobs from memory")


# Test sederhana
if __name__ == "__main__":
    from ..utils.logger import setup_logging
    setup_logging()
    
    print("UploadQueueManager class ready")
    print("- Manages separate queues for 51 (HIGH) and 40 (NORMAL)")