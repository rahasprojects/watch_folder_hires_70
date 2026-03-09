# -*- coding: utf-8 -*-
"""
File monitor untuk mendeteksi file baru di folder 12 menggunakan SMB
Dengan rename test untuk deteksi file siap
"""

import os
import time
import threading
import logging
from typing import List, Optional, Callable, Dict
from datetime import datetime
from ..models.file_job import FileJob
from ..core.queue_manager import QueueManager
from ..utils.validators import is_video_file
from ..constants.settings import SMB_POLLING_INTERVAL

logger = logging.getLogger(__name__)

class FileMonitor:
    """
    Kelas untuk memonitor folder 12 dan mendeteksi file baru
    """
    
    def __init__(self, 
                 source_folders: List[str],
                 extensions: List[str],
                 queue_manager: QueueManager,
                 polling_interval: int = SMB_POLLING_INTERVAL):
        """
        Inisialisasi FileMonitor
        
        Args:
            source_folders: Daftar folder sumber (12) yang dimonitor
            extensions: Daftar ekstensi file yang diproses
            queue_manager: QueueManager instance
            polling_interval: Interval polling dalam detik (fallback)
        """
        self.source_folders = source_folders
        self.extensions = extensions
        self.queue_manager = queue_manager
        self.polling_interval = polling_interval
        
        # State untuk file yang sudah pernah dilihat
        self.seen_files: Dict[str, set] = {}  # {folder: set of files}
        
        # State untuk file yang sedang dalam proses stabilisasi
        self.stable_files: Dict[str, dict] = {}  # {file_path: info}
        
        # State untuk file yang sedang aktif di-copy (tracking progress)
        self.active_copies: Dict[str, dict] = {}  # {file_path: info}
        
        self.running = False
        self.monitor_thread = None
        
        # Callbacks
        self.detection_callbacks = []
        
        logger.info(f"FileMonitor initialized with {len(source_folders)} folders")
        for folder in source_folders:
            logger.info(f"  - Monitoring: {folder}")
        logger.info(f"  - Extensions: {extensions}")
    
    def start(self):
        """Start monitoring"""
        if self.running:
            logger.warning("FileMonitor already running")
            return
        
        self.running = True
        
        # Initialize seen files
        for folder in self.source_folders:
            self.seen_files[folder] = set()
            self._scan_folder(folder, initial=True)
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("FileMonitor started")
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("FileMonitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info(f"Monitor loop started (interval: {self.polling_interval}s)")
        
        while self.running:
            try:
                # Scan folder untuk file baru
                for folder in self.source_folders:
                    self._scan_folder(folder)
                
                # Cek kestabilan file (metode lama - untuk kompatibilitas)
                self._check_stable_files()
                
                # Update progress untuk file yang sedang di-copy (metode baru)
                self._update_copy_progress()
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            # Sleep
            for _ in range(self.polling_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _scan_folder(self, folder: str, initial: bool = False):
        """
        Scan folder untuk mencari file baru
        
        Args:
            folder: Path folder
            initial: True jika scan pertama kali
        """
        try:
            if not os.path.exists(folder):
                logger.warning(f"Folder not found: {folder}")
                return
            
            # Dapatkan semua file
            try:
                all_items = os.listdir(folder)
            except PermissionError:
                logger.error(f"Permission denied accessing folder: {folder}")
                return
            except Exception as e:
                logger.error(f"Error listing folder {folder}: {e}")
                return
            
            current_files = set()
            
            for item in all_items:
                item_path = os.path.join(folder, item)
                
                # Skip folder
                if os.path.isdir(item_path):
                    continue
                
                # Cek ekstensi
                if not is_video_file(item, self.extensions):
                    continue
                
                current_files.add(item)
                
                # Cek file baru (belum pernah dilihat)
                if folder not in self.seen_files:
                    self.seen_files[folder] = set()
                
                if not initial and item not in self.seen_files[folder]:
                    # File baru terdeteksi
                    try:
                        file_size = os.path.getsize(item_path)
                        logger.info(f"📂 New file detected: {item} ({file_size/(1024**3):.2f}GB) in {folder}")
                        
                        # Masukkan ke active_copies untuk tracking dengan rename test
                        self.active_copies[item_path] = {
                            'filename': item,
                            'first_seen': time.time(),
                            'last_size': file_size,
                            'last_active': time.time(),
                            'folder': folder,
                            'status': 'copying'
                        }
                        
                    except Exception as e:
                        logger.error(f"Error getting size for new file {item}: {e}")
            
            # Update seen files
            self.seen_files[folder] = current_files
            
        except Exception as e:
            logger.error(f"Error scanning folder {folder}: {e}")
    
    def _check_stable_files(self):
        """
        Cek file yang sudah stabil (tidak berubah ukurannya) - METODE LAMA
        Untuk kompatibilitas ke belakang
        """
        to_remove = []
        
        for file_path, info in self.stable_files.items():
            try:
                if not os.path.exists(file_path):
                    logger.debug(f"File removed before stabilization: {info['filename']}")
                    to_remove.append(file_path)
                    continue
                
                current_size = os.path.getsize(file_path)
                time_since_first = time.time() - info['first_seen']
                info['checked_count'] = info.get('checked_count', 0) + 1
                
                logger.debug(f"Checking {info['filename']}: size={current_size}, last_size={info['last_size']}, time={time_since_first:.1f}s")
                
                if current_size == info['last_size'] and time_since_first >= 5:
                    logger.info(f"File stable: {info['filename']} ({current_size/(1024**3):.2f}GB) after {time_since_first:.1f}s")
                    
                    # Buat job
                    job = FileJob(
                        name=info['filename'],
                        source_path=file_path,
                        dest_path="",
                        size_bytes=current_size
                    )
                    
                    logger.info(f"Created job for {info['filename']}")
                    
                    # Tambah ke queue
                    position = self.queue_manager.add_job(job)
                    logger.info(f"Job added to queue at position {position}")
                    
                    self._notify_callbacks(job)
                    to_remove.append(file_path)
                    
                elif current_size != info['last_size']:
                    logger.debug(f"File {info['filename']} still changing: {info['last_size']} -> {current_size}")
                    info['last_size'] = current_size
                    
                elif time_since_first > 30:
                    logger.info(f"File {info['filename']} still changing after 30s, current size: {current_size/(1024**3):.2f}GB")
                    
            except Exception as e:
                logger.error(f"Error checking stable file {file_path}: {e}")
                to_remove.append(file_path)
        
        for file_path in to_remove:
            if file_path in self.stable_files:
                del self.stable_files[file_path]
    
    def is_file_active(self, file_path: str, check_interval: int = 2) -> bool:
        """
        Cek apakah file sedang aktif ditulis (ukuran bertambah)
        
        Args:
            file_path: Path file yang dicek
            check_interval: Interval pengecekan dalam detik
        
        Returns:
            True jika ukuran bertambah, False jika stabil
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Baca ukuran pertama
            size1 = os.path.getsize(file_path)
            
            # Tunggu sebentar
            time.sleep(check_interval)
            
            # Baca ukuran kedua
            size2 = os.path.getsize(file_path)
            
            # Jika bertambah, file masih aktif
            if size2 > size1:
                logger.debug(f"📈 File aktif: {os.path.basename(file_path)} bertambah {size2-size1} bytes")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking file activity: {e}")
            return False
    
    def is_file_ready(self, file_path: str) -> bool:
        """
        Cek apakah file sudah siap diproses dengan mencoba rename
        
        Args:
            file_path: Path file yang dicek
            
        Returns:
            True jika file tidak terkunci, False jika masih terkunci
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Coba rename ke nama sementara
            temp_path = file_path + ".tmp_check"
            os.rename(file_path, temp_path)
            
            # Jika berhasil, rename kembali
            os.rename(temp_path, file_path)
            
            logger.debug(f"✅ File siap: {os.path.basename(file_path)}")
            return True
            
        except OSError as e:
            # File masih terkunci oleh proses lain
            logger.debug(f"🔒 File masih terkunci: {os.path.basename(file_path)}")
            return False
        except Exception as e:
            logger.error(f"Error checking file readiness: {e}")
            return False
    
    def _update_copy_progress(self):
        """Update progress untuk file yang sedang di-copy menggunakan rename test"""
        to_remove = []
        
        for file_path, info in list(self.active_copies.items()):
            try:
                if not os.path.exists(file_path):
                    logger.debug(f"File removed: {info['filename']}")
                    to_remove.append(file_path)
                    continue
                
                # ===== CEK AKTIVITAS =====
                if self.is_file_active(file_path):
                    # File masih aktif ditulis
                    info['last_active'] = time.time()
                    logger.debug(f"⏳ {info['filename']} masih aktif")
                    continue  # Langsung skip ke file berikutnya
                # ==========================
                
                # ===== CEK SIAP DENGAN RENAME TEST =====
                if self.is_file_ready(file_path):
                    # File sudah selesai dan tidak terkunci
                    size_gb = os.path.getsize(file_path) / (1024**3)
                    logger.info(f"✅ File READY for processing: {info['filename']} ({size_gb:.2f}GB)")
                    
                    # Buat job
                    job = FileJob(
                        name=info['filename'],
                        source_path=file_path,
                        dest_path="",  # Akan diisi download_worker
                        size_bytes=os.path.getsize(file_path)
                    )
                    
                    position = self.queue_manager.add_job(job)
                    logger.info(f"   → Job added to queue at position {position}")
                    
                    self._notify_callbacks('ready', job)
                    to_remove.append(file_path)
                    continue
                # =======================================
                
                # Jika sampai sini, file stabil tapi masih terkunci
                logger.debug(f"⏸️  {info['filename']} stabil tapi terkunci")
                
            except Exception as e:
                logger.error(f"Error in _update_copy_progress: {e}")
                to_remove.append(file_path)
        
        # Hapus file yang sudah diproses
        for file_path in to_remove:
            if file_path in self.active_copies:
                del self.active_copies[file_path]
    
    def add_source_folder(self, folder: str):
        """Tambah folder sumber baru"""
        if folder not in self.source_folders:
            self.source_folders.append(folder)
            self.seen_files[folder] = set()
            logger.info(f"Added source folder: {folder}")
    
    def remove_source_folder(self, folder: str):
        """Hapus folder sumber"""
        if folder in self.source_folders:
            self.source_folders.remove(folder)
            if folder in self.seen_files:
                del self.seen_files[folder]
            logger.info(f"Removed source folder: {folder}")
    
    def update_extensions(self, extensions: List[str]):
        """Update daftar ekstensi"""
        self.extensions = extensions
        logger.info(f"Extensions updated: {extensions}")
    
    def register_callback(self, callback: Callable):
        """Register callback untuk notifikasi file baru"""
        self.detection_callbacks.append(callback)
    
    def _notify_callbacks(self, event: str, *args, **kwargs):
        """Notifikasi ke semua callback"""
        for callback in self.detection_callbacks:
            try:
                callback(event, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def get_stats(self) -> dict:
        """Dapatkan statistik monitoring"""
        total_files_seen = 0
        for files in self.seen_files.values():
            total_files_seen += len(files)
            
        return {
            'folders_monitored': len(self.source_folders),
            'files_seen': total_files_seen,
            'active_copies': len(self.active_copies),
            'extensions': self.extensions,
            'running': self.running
        }
    
    def force_scan(self):
        """Force scan semua folder"""
        logger.info("Forcing scan...")
        for folder in self.source_folders:
            self._scan_folder(folder)
        self._check_stable_files()
        self._update_copy_progress()


# Test sederhana
if __name__ == "__main__":
    from ..utils.logger import setup_logging
    setup_logging()
    
    # Buat queue manager dummy
    class DummyQueue:
        def add_job(self, job):
            print(f"Job added: {job.name}")
            return 1
    
    # Buat file monitor
    monitor = FileMonitor(
        source_folders=["D:/Test watch folder/source"],
        extensions=['.mp4', '.mxf', '.mov'],
        queue_manager=DummyQueue()
    )
    
    print("FileMonitor class ready with rename test")
    print(f"Monitoring: {monitor.source_folders}")
    print(f"Extensions: {monitor.extensions}")
    print("Features:")
    print("  - Active copy tracking with rename test")
    print("  - File activity detection")
    print("  - Ready check via rename test")