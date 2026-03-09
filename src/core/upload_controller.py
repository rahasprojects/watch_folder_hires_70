# -*- coding: utf-8 -*-
"""
Controller untuk menghubungkan download selesai dengan upload
Dipanggil saat download selesai untuk memulai upload ke 51 dan 40
"""

import logging
import os
from typing import Optional
from ..models.file_job import FileJob
from ..models.upload_job import UploadJob
from ..core.upload_manager import UploadManager
from ..core.upload_queue_manager import UploadQueueManager
from ..utils.config_manager import ConfigManager
from ..utils.history import HistoryLogger
from ..constants.settings import UPLOAD_PRIORITY_51, UPLOAD_PRIORITY_40

logger = logging.getLogger(__name__)

class UploadController:
    """
    Controller yang menghubungkan download selesai dengan upload
    
    Saat download selesai, controller ini akan:
    1. Membuat 2 UploadJob (untuk 51 dan 40)
    2. Menambahkan ke queue manager
    3. Memulai proses upload
    """
    
    def __init__(self, 
                 upload_manager: UploadManager,
                 queue_manager: UploadQueueManager,
                 config_manager: Optional[ConfigManager] = None,
                 history_logger: Optional[HistoryLogger] = None):
        """
        Inisialisasi UploadController
        
        Args:
            upload_manager: UploadManager instance
            queue_manager: UploadQueueManager instance
            config_manager: ConfigManager instance (optional)
            history_logger: HistoryLogger instance (optional)
        """
        self.upload_manager = upload_manager
        self.queue_manager = queue_manager
        self.config_manager = config_manager or ConfigManager()
        self.history_logger = history_logger or HistoryLogger()
        
        # Cache settings
        self._settings = None
        
        logger.info("UploadController initialized")
    
    @property
    def settings(self):
        """Lazy loading of settings"""
        if self._settings is None:
            self._settings = self.config_manager.load()
            logger.debug(f"Settings loaded: dest_51='{self._settings.destination_51}', dest_40='{self._settings.destination_40}'")
        return self._settings
    
    def on_download_complete(self, download_job: FileJob):
        """
        Dipanggil saat download selesai
        
        Args:
            download_job: FileJob yang selesai di-download
        """
        logger.info(f"=== UPLOAD CONTROLLER ===")
        logger.info(f"📥 Download completed: {download_job.name}")
        logger.info(f"📁 Source file in 70: {download_job.dest_path}")
        
        # ===== DEBUG: CEK SETTINGS =====
        logger.info("🔍 Checking settings...")
        if not self._validate_settings():
            logger.error("❌ Cannot create upload jobs: settings not configured")
            logger.error(f"   destination_51: '{self.settings.destination_51}'")
            logger.error(f"   destination_40: '{self.settings.destination_40}'")
            return
        
        logger.info(f"✅ Settings valid:")
        logger.info(f"   - destination_51: {self.settings.destination_51}")
        logger.info(f"   - destination_40: {self.settings.destination_40}")
        
        # ===== CEK FOLDER DESTINATION =====
        logger.info("🔍 Checking destination folders...")
        
        # Cek folder 51
        if not os.path.exists(self.settings.destination_51):
            logger.error(f"❌ Destination 51 folder does not exist: {self.settings.destination_51}")
            logger.info("   Will attempt to create folder...")
            try:
                os.makedirs(self.settings.destination_51, exist_ok=True)
                logger.info(f"✅ Created destination 51 folder: {self.settings.destination_51}")
            except Exception as e:
                logger.error(f"❌ Cannot create destination 51 folder: {e}")
                return
        else:
            logger.info(f"✅ Destination 51 folder exists: {self.settings.destination_51}")
            
            # Cek write permission
            if not os.access(self.settings.destination_51, os.W_OK):
                logger.error(f"❌ No write permission to destination 51 folder: {self.settings.destination_51}")
                return
            else:
                logger.info(f"✅ Write permission OK for destination 51")
        
        # Cek folder 40
        if not os.path.exists(self.settings.destination_40):
            logger.error(f"❌ Destination 40 folder does not exist: {self.settings.destination_40}")
            logger.info("   Will attempt to create folder...")
            try:
                os.makedirs(self.settings.destination_40, exist_ok=True)
                logger.info(f"✅ Created destination 40 folder: {self.settings.destination_40}")
            except Exception as e:
                logger.error(f"❌ Cannot create destination 40 folder: {e}")
                return
        else:
            logger.info(f"✅ Destination 40 folder exists: {self.settings.destination_40}")
            
            # Cek write permission
            if not os.access(self.settings.destination_40, os.W_OK):
                logger.error(f"❌ No write permission to destination 40 folder: {self.settings.destination_40}")
                return
            else:
                logger.info(f"✅ Write permission OK for destination 40")
        
        # Buat upload job untuk 51 (HIRES)
        logger.info(f"🔍 Creating upload job for 51 (HIRES)...")
        job_51 = self._create_upload_job(
            download_job=download_job,
            destination=51,
            priority=UPLOAD_PRIORITY_51
        )
        
        # Buat upload job untuk 40 (LOWRES)
        logger.info(f"🔍 Creating upload job for 40 (LOWRES)...")
        job_40 = self._create_upload_job(
            download_job=download_job,
            destination=40,
            priority=UPLOAD_PRIORITY_40
        )
        
        # Tambahkan ke queue manager
        if job_51:
            logger.info(f"✅ Upload job 51 created successfully")
            position_51 = self.queue_manager.add_job(job_51)
            logger.info(f"[51-HIGH] Added to queue at position {position_51}")
            logger.info(f"   Source: {job_51.source_path}")
            logger.info(f"   Dest: {job_51.dest_path}")
        else:
            logger.error(f"❌ Failed to create upload job for 51: {download_job.name}")
        
        if job_40:
            logger.info(f"✅ Upload job 40 created successfully")
            position_40 = self.queue_manager.add_job(job_40)
            logger.info(f"[40-NORMAL] Added to queue at position {position_40}")
            logger.info(f"   Source: {job_40.source_path}")
            logger.info(f"   Dest: {job_40.dest_path}")
        else:
            logger.error(f"❌ Failed to create upload job for 40: {download_job.name}")
        
        # Refresh settings cache (in case of changes)
        self._settings = None
    
    def _create_upload_job(self, download_job: FileJob, destination: int, priority: str) -> Optional[UploadJob]:
        """
        Buat UploadJob untuk destination tertentu
        
        Args:
            download_job: FileJob yang selesai di-download
            destination: 51 atau 40
            priority: HIGH atau NORMAL
            
        Returns:
            UploadJob object atau None jika gagal
        """
        try:
            # Tentukan destination path berdasarkan settings
            if destination == 51:
                dest_folder = self.settings.destination_51
                dest_name = "51-HIRES"
            else:  # destination == 40
                dest_folder = self.settings.destination_40
                dest_name = "40-LOWRES"
            
            logger.debug(f"Creating job for {dest_name} with folder: {dest_folder}")
            
            if not dest_folder:
                logger.error(f"❌ Destination folder for {dest_name} is empty!")
                return None
            
            if not os.path.exists(dest_folder):
                logger.error(f"❌ Destination folder for {dest_name} does not exist: {dest_folder}")
                return None
            
            # Buat destination path
            dest_path = os.path.join(dest_folder, download_job.name)
            logger.debug(f"Destination path: {dest_path}")
            
            # Buat UploadJob
            upload_job = UploadJob(
                source_path=download_job.dest_path,  # File di 70
                dest_path=dest_path,
                destination=destination,
                priority=priority,
                file_size=download_job.size_bytes,
                file_name=download_job.name,
                max_retry=download_job.max_retry,
                original_download_job=download_job
            )
            
            logger.info(f"✅ Created upload job for {dest_name}: {download_job.name}")
            logger.debug(f"  Source: {upload_job.source_path}")
            logger.debug(f"  Dest: {upload_job.dest_path}")
            logger.debug(f"  Priority: {priority}")
            
            return upload_job
            
        except Exception as e:
            logger.error(f"❌ Error creating upload job for {destination}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _validate_settings(self) -> bool:
        """
        Validasi settings untuk upload
        
        Returns:
            True jika settings valid, False jika tidak
        """
        settings = self.settings
        valid = True
        
        # Cek destination 51
        if not settings.destination_51:
            logger.warning("❌ Destination 51 (HIRES) is not configured")
            valid = False
        elif not isinstance(settings.destination_51, str):
            logger.warning(f"❌ Destination 51 is not a string: {type(settings.destination_51)}")
            valid = False
        
        # Cek destination 40
        if not settings.destination_40:
            logger.warning("❌ Destination 40 (LOWRES) is not configured")
            valid = False
        elif not isinstance(settings.destination_40, str):
            logger.warning(f"❌ Destination 40 is not a string: {type(settings.destination_40)}")
            valid = False
        
        return valid
    
    def on_settings_changed(self):
        """Dipanggil saat settings berubah"""
        # Refresh cache
        self._settings = None
        logger.info("UploadController settings cache refreshed")
    
    def get_pending_uploads(self, source_path: str) -> dict:
        """
        Dapatkan status upload untuk file tertentu
        
        Args:
            source_path: Path file di 70
            
        Returns:
            Dictionary status upload untuk file tersebut
        """
        jobs = self.queue_manager.get_job_by_source(source_path)
        
        result = {
            '51': {'status': 'not_found', 'job': None},
            '40': {'status': 'not_found', 'job': None}
        }
        
        for job in jobs:
            if job.destination == 51:
                result['51'] = {
                    'status': job.status,
                    'progress': job.progress,
                    'job': job
                }
            elif job.destination == 40:
                result['40'] = {
                    'status': job.status,
                    'progress': job.progress,
                    'job': job
                }
        
        return result
    
    def retry_failed_uploads(self, source_path: str):
        """
        Manual retry untuk upload yang gagal
        
        Args:
            source_path: Path file di 70
        """
        jobs = self.queue_manager.get_job_by_source(source_path)
        
        for job in jobs:
            if job.status == 'failed' and job.retry_count < job.max_retry:
                logger.info(f"Manual retry for {job.file_name} to {job.destination}")
                self.queue_manager.fail_job(job, "Manual retry", retry=True)


# Test sederhana
if __name__ == "__main__":
    from ..utils.logger import setup_logging
    setup_logging()
    
    print("UploadController class ready with DEBUG logging")
    print("- Will show detailed logs for debugging upload issues")