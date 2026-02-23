# -*- coding: utf-8 -*-
"""
File handler untuk operasi copy file dengan progress, delete, retry, dan auto-rename
"""

import os
import time
import logging
from typing import Callable, Optional
from ..models.file_job import FileJob
from ..constants.settings import CHUNK_SIZE, CHECKPOINT_PERCENT

logger = logging.getLogger(__name__)

class FileHandler:
    """
    Kelas untuk menangani operasi file (copy, delete, retry) dengan auto-rename untuk duplikat
    """
    
    def __init__(self, chunk_size: int = CHUNK_SIZE):
        """
        Inisialisasi FileHandler
        
        Args:
            chunk_size: Ukuran chunk untuk copy (default 256MB)
        """
        self.chunk_size = chunk_size
        logger.debug(f"FileHandler initialized with chunk_size={chunk_size/(1024**2):.0f}MB")
    
    def get_unique_dest_path(self, dest_folder: str, filename: str) -> str:
        """
        Dapatkan path destination unik dengan menambahkan nomor jika file sudah ada
        
        Args:
            dest_folder: Folder tujuan
            filename: Nama file asli
            
        Returns:
            Path destination yang unik
        """
        # Split nama file dan ekstensi
        base, ext = os.path.splitext(filename)
        
        # Path lengkap
        dest_path = os.path.join(dest_folder, filename)
        
        # Jika file belum ada, return path asli
        if not os.path.exists(dest_path):
            return dest_path
        
        # File sudah ada, cari nomor yang tersedia
        counter = 1
        while True:
            # Format: nama (1).ext, nama (2).ext, dst
            new_filename = f"{base} ({counter}){ext}"
            new_path = os.path.join(dest_folder, new_filename)
            
            if not os.path.exists(new_path):
                logger.info(f"File already exists, using: {new_filename}")
                return new_path
            
            counter += 1
    
    def copy_with_progress(self, job: FileJob, 
                           progress_callback: Optional[Callable[[int, float], None]] = None,
                           checkpoint_callback: Optional[Callable[[FileJob], None]] = None) -> bool:
        """
        Copy file dengan progress monitoring dan retry untuk permission denied
        
        Args:
            job: FileJob object
            progress_callback: Callback untuk update progress (bytes_copied, percent)
            checkpoint_callback: Callback untuk checkpoint (setiap 10%)
            
        Returns:
            True jika sukses, False jika gagal
        """
        start_time = time.time()
        max_retries = 5  # Maksimal 5 kali percobaan untuk permission denied
        base_delay = 1   # Delay awal 1 detik
        
        for attempt in range(max_retries):
            try:
                # Buat folder tujuan jika belum ada
                os.makedirs(os.path.dirname(job.dest_path), exist_ok=True)
                
                logger.info(f"Copying to: {job.dest_path}")
                
                # Buka file sumber dan tujuan
                with open(job.source_path, 'rb') as src_file:
                    with open(job.dest_path, 'wb') as dst_file:
                        
                        # Jika resume, seek ke posisi terakhir
                        if job.copied_bytes > 0:
                            src_file.seek(job.copied_bytes)
                            dst_file.seek(job.copied_bytes)
                            logger.info(f"Resuming {job.name} from {job.copied_bytes/(1024**2):.2f}MB")
                        
                        total_bytes = job.size_bytes
                        copied_bytes = job.copied_bytes
                        last_checkpoint = job.last_checkpoint
                        last_log_percent = 0
                        
                        while copied_bytes < total_bytes:
                            # Baca chunk
                            chunk = src_file.read(self.chunk_size)
                            if not chunk:
                                break
                            
                            # Tulis chunk
                            dst_file.write(chunk)
                            copied_bytes += len(chunk)
                            
                            # Update progress
                            percent = (copied_bytes / total_bytes) * 100
                            
                            if progress_callback:
                                progress_callback(copied_bytes, percent)
                            
                            # Log progress setiap 10%
                            if int(percent) >= last_log_percent + 10:
                                last_log_percent = int(percent)
                                logger.info(f"{job.name}: {percent:.1f}% ({copied_bytes/(1024**3):.2f}GB/{job.size_gb:.2f}GB)")
                            
                            # Cek checkpoint (setiap 10%)
                            current_checkpoint = int(percent // CHECKPOINT_PERCENT) * CHECKPOINT_PERCENT
                            if current_checkpoint > last_checkpoint and checkpoint_callback:
                                job.copied_bytes = copied_bytes
                                job.progress = percent
                                job.last_checkpoint = current_checkpoint
                                checkpoint_callback(job)
                                last_checkpoint = current_checkpoint
                                logger.debug(f"Checkpoint {job.name}: {current_checkpoint}%")
                
                # Jika sampai sini, copy berhasil
                duration = time.time() - start_time
                actual_filename = os.path.basename(job.dest_path)
                logger.info(f"Copy completed: {actual_filename} ({job.size_gb:.2f}GB) in {duration:.2f}s")
                
                # Update job
                job.copied_bytes = total_bytes
                job.progress = 100
                job.end_time = time.time()
                
                return True
                
            except PermissionError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff: 1, 2, 4, 8, 16 detik
                    logger.warning(f"Permission denied for {job.name}, file mungkin masih digunakan. "
                                 f"Retry dalam {delay} detik... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    logger.error(f"Permission denied for {job.name} after {max_retries} attempts: {e}")
                    job.last_error = f"Permission denied after {max_retries} attempts"
                    return False
                    
            except FileNotFoundError as e:
                logger.error(f"File not found: {job.source_path} - {e}")
                job.last_error = f"Source file not found: {job.source_path}"
                return False
                
            except IOError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"IO Error for {job.name}: {e}. Retry dalam {delay} detik...")
                    time.sleep(delay)
                else:
                    logger.error(f"IO Error for {job.name} after {max_retries} attempts: {e}")
                    job.last_error = f"IO Error: {e}"
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected error copying {job.name}: {e}")
                job.last_error = str(e)
                return False
        
        return False
    
    def safe_copy(self, job: FileJob, 
                  progress_callback: Optional[Callable] = None,
                  checkpoint_callback: Optional[Callable] = None) -> bool:
        """
        Safe copy dengan verifikasi ukuran file dan auto-rename untuk duplikat
        
        Args:
            job: FileJob object
            progress_callback: Callback progress
            checkpoint_callback: Callback checkpoint
            
        Returns:
            True jika sukses
        """
        # Validasi awal
        if not os.path.exists(job.source_path):
            logger.error(f"Source file does not exist: {job.source_path}")
            job.last_error = "Source file does not exist"
            return False
        
        # Cek ukuran file sumber
        actual_size = os.path.getsize(job.source_path)
        if actual_size != job.size_bytes:
            logger.warning(f"Source file size changed: expected {job.size_bytes}, got {actual_size}")
            job.size_bytes = actual_size  # Update ukuran
        
        # ===== AUTO-RENAME UNTUK FILE DUPLIKAT =====
        dest_folder = os.path.dirname(job.dest_path)
        original_filename = os.path.basename(job.dest_path)
        
        # Dapatkan path unik (dengan nomor jika sudah ada)
        unique_dest_path = self.get_unique_dest_path(dest_folder, original_filename)
        
        # Jika berbeda dengan path asli, update job
        renamed = False
        if unique_dest_path != job.dest_path:
            old_filename = os.path.basename(job.dest_path)
            new_filename = os.path.basename(unique_dest_path)
            job.dest_path = unique_dest_path
            renamed = True
            logger.info(f"Destination renamed to avoid conflict: {old_filename} → {new_filename}")
        
        # Copy dengan progress
        success = self.copy_with_progress(job, progress_callback, checkpoint_callback)
        
        if not success:
            return False
        
        # Verifikasi ukuran file hasil copy
        if os.path.exists(job.dest_path):
            dest_size = os.path.getsize(job.dest_path)
            if dest_size != job.size_bytes:
                logger.error(f"Verification failed: {job.name} - destination size {dest_size} != source size {job.size_bytes}")
                job.last_error = "Size mismatch after copy"
                return False
            else:
                # Gunakan nama file yang sebenarnya (mungkin sudah di-rename)
                actual_filename = os.path.basename(job.dest_path)
                logger.info(f"Verification passed: {actual_filename} ({job.size_gb:.2f}GB)")
                if renamed:
                    logger.info(f"File saved as: {actual_filename}")
        else:
            logger.error(f"Destination file not found after copy: {job.dest_path}")
            job.last_error = "Destination file missing after copy"
            return False
        
        return True
    
    def delete_file(self, path: str, max_retries: int = 3) -> bool:
        """
        Hapus file dengan retry
        
        Args:
            path: Path file yang akan dihapus
            max_retries: Maksimal percobaan
            
        Returns:
            True jika sukses, False jika gagal
        """
        if not os.path.exists(path):
            logger.warning(f"File not found for deletion: {path}")
            return True
        
        for attempt in range(max_retries):
            try:
                os.remove(path)
                logger.info(f"Deleted: {path}")
                return True
                
            except PermissionError:
                logger.warning(f"Permission error deleting {path}, file mungkin masih digunakan. "
                             f"Attempt {attempt+1}/{max_retries}")
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Error deleting {path}: {e}")
                time.sleep(1)
        
        logger.error(f"Failed to delete {path} after {max_retries} attempts")
        return False
    
    def verify_file(self, job: FileJob) -> bool:
        """
        Verifikasi file setelah copy
        
        Args:
            job: FileJob object
            
        Returns:
            True jika valid
        """
        try:
            # Cek apakah file tujuan ada
            if not os.path.exists(job.dest_path):
                logger.error(f"Destination file not found: {job.dest_path}")
                return False
            
            # Cek ukuran
            actual_size = os.path.getsize(job.dest_path)
            if actual_size != job.size_bytes:
                logger.error(f"Size mismatch: {job.name} - expected {job.size_bytes}, got {actual_size}")
                return False
            
            actual_filename = os.path.basename(job.dest_path)
            logger.debug(f"File verified: {actual_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying {job.name}: {e}")
            return False
    
    def get_file_info(self, path: str) -> Optional[dict]:
        """
        Dapatkan informasi file
        
        Args:
            path: Path file
            
        Returns:
            Dictionary info file atau None jika error
        """
        try:
            if not os.path.exists(path):
                return None
            
            stat = os.stat(path)
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'is_file': os.path.isfile(path),
                'is_dir': os.path.isdir(path)
            }
            
        except Exception as e:
            logger.error(f"Error getting file info for {path}: {e}")
            return None


# Test sederhana
if __name__ == "__main__":
    # Setup logging
    from ..utils.logger import setup_logging
    setup_logging()
    
    # Test FileHandler
    handler = FileHandler()
    print(f"FileHandler created with chunk_size={handler.chunk_size/(1024**2):.0f}MB")
    
    # Test auto-rename function
    test_folder = "C:/test"
    test_file = "test.mxf"
    
    unique_path = handler.get_unique_dest_path(test_folder, test_file)
    print(f"Auto-rename test: {unique_path}")
    
    print("FileHandler ready with auto-rename feature")