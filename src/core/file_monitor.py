# -*- coding: utf-8 -*-
"""
File monitor untuk mendeteksi file baru di folder 12 menggunakan SMB
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
        
        # State
        self.seen_files: Dict[str, set] = {}  # {folder: set of files}
        self.stable_files: Dict[str, dict] = {}  # {file_path: info}
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
                for folder in self.source_folders:
                    self._scan_folder(folder)
                    
                # Cek kestabilan file
                self._check_stable_files()
                
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
                        logger.info(f"New file detected: {item} ({file_size/(1024**3):.2f}GB) in {folder}")
                        
                        # Masukkan ke daftar file yang perlu dicek kestabilannya
                        self.stable_files[item_path] = {
                            'first_seen': time.time(),
                            'last_size': file_size,
                            'folder': folder,
                            'filename': item,
                            'checked_count': 0
                        }
                    except Exception as e:
                        logger.error(f"Error getting size for new file {item}: {e}")
            
            # Update seen files
            self.seen_files[folder] = current_files
            
        except Exception as e:
            logger.error(f"Error scanning folder {folder}: {e}")
    
    def _check_stable_files(self):
        """
        Cek file yang sudah stabil (tidak berubah ukurannya)
        """
        to_remove = []
        
        for file_path, info in self.stable_files.items():
            try:
                if not os.path.exists(file_path):
                    # File sudah dihapus
                    logger.debug(f"File removed before stabilization: {info['filename']}")
                    to_remove.append(file_path)
                    continue
                
                current_size = os.path.getsize(file_path)
                time_since_first = time.time() - info['first_seen']
                info['checked_count'] = info.get('checked_count', 0) + 1
                
                logger.debug(f"Checking {info['filename']}: size={current_size}, last_size={info['last_size']}, time={time_since_first:.1f}s")
                
                if current_size == info['last_size'] and time_since_first >= 5:
                    # File stabil (ukuran tidak berubah selama 3 detik)
                    logger.info(f"File stable: {info['filename']} ({current_size/(1024**3):.2f}GB) after {time_since_first:.1f}s")
                    
                    # Buat job (dest_path akan diisi kosong dulu)
                    job = FileJob(
                        name=info['filename'],
                        source_path=file_path,
                        dest_path="",  # Akan diisi oleh settings/download_worker
                        size_bytes=current_size
                    )
                    
                    logger.info(f"Created job for {info['filename']} with source: {file_path}")
                    
                    # Tambah ke queue
                    position = self.queue_manager.add_job(job)
                    logger.info(f"Job added to queue at position {position}")
                    
                    # Notifikasi
                    self._notify_callbacks(job)
                    
                    to_remove.append(file_path)
                    
                elif current_size != info['last_size']:
                    # Ukuran berubah, update
                    logger.debug(f"File {info['filename']} still changing: {info['last_size']} -> {current_size}")
                    info['last_size'] = current_size
                    
                elif time_since_first > 30:
                    # Sudah 30 detik tapi masih berubah? mungkin file besar
                    logger.info(f"File {info['filename']} still changing after 30s, current size: {current_size/(1024**3):.2f}GB")
                    # Tetap pertahankan, jangan hapus
                    
            except Exception as e:
                logger.error(f"Error checking stable file {file_path}: {e}")
                to_remove.append(file_path)
        
        # Hapus yang sudah diproses
        for file_path in to_remove:
            if file_path in self.stable_files:
                del self.stable_files[file_path]
        
        if to_remove:
            logger.debug(f"Removed {len(to_remove)} files from stabilization queue")
    
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
    
    def _notify_callbacks(self, job: FileJob):
        """Notifikasi ke semua callback"""
        for callback in self.detection_callbacks:
            try:
                callback(job)
            except Exception as e:
                logger.error(f"Error in detection callback: {e}")
    
    def get_stats(self) -> dict:
        """Dapatkan statistik monitoring"""
        total_files_seen = 0
        for files in self.seen_files.values():
            total_files_seen += len(files)
            
        return {
            'folders_monitored': len(self.source_folders),
            'files_seen': total_files_seen,
            'files_stabilizing': len(self.stable_files),
            'extensions': self.extensions,
            'running': self.running
        }
    
    def force_scan(self):
        """Force scan semua folder"""
        logger.info("Forcing scan...")
        for folder in self.source_folders:
            self._scan_folder(folder)
        self._check_stable_files()


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
    
    print("FileMonitor class ready with full debug")
    print(f"Monitoring: {monitor.source_folders}")
    print(f"Extensions: {monitor.extensions}")