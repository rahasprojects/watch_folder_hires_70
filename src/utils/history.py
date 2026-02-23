# -*- coding: utf-8 -*-
"""
History logger untuk mencatat semua file yang pernah diproses
"""

import os
import logging
from datetime import datetime
from typing import Optional
from ..constants.settings import HISTORY_FILE

logger = logging.getLogger(__name__)

class HistoryLogger:
    """
    Kelas untuk mencatat history copy file
    """
    
    def __init__(self, history_path: Optional[str] = None):
        """
        Inisialisasi HistoryLogger
        
        Args:
            history_path: Path ke file history (optional)
        """
        if history_path:
            self.history_path = history_path
        else:
            # Default: copy_history.txt di folder utama
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.history_path = os.path.join(root_dir, HISTORY_FILE)
        
        # Buat header jika file belum ada
        if not os.path.exists(self.history_path):
            self._write_header()
        
        logger.debug(f"HistoryLogger initialized with path: {self.history_path}")
    
    def _write_header(self):
        """Tulis header ke file history"""
        try:
            with open(self.history_path, 'w', encoding='utf-8') as f:
                f.write("="*100 + "\n")
                f.write("HISTORY COPY FILE - watch_folder_hires_70\n")
                f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*100 + "\n")
                f.write(f"{'Timestamp':<20} {'Filename':<40} {'Size':>12} {'Status':<10} {'Duration':<10} {'Retry':<5}\n")
                f.write("-"*100 + "\n")
        except Exception as e:
            logger.error(f"Error writing history header: {e}")
    
    def log_success(self, filename: str, size_bytes: int, duration_seconds: float, retry_count: int = 0):
        """
        Catat file yang sukses di-copy
        
        Args:
            filename: Nama file
            size_bytes: Ukuran file dalam bytes
            duration_seconds: Durasi copy dalam detik
            retry_count: Jumlah retry
        """
        self._log_entry(filename, size_bytes, "SUCCESS", duration_seconds, retry_count)
    
    def log_failed(self, filename: str, size_bytes: int, error_msg: str, retry_count: int = 3):
        """
        Catat file yang gagal di-copy
        
        Args:
            filename: Nama file
            size_bytes: Ukuran file dalam bytes
            error_msg: Pesan error
            retry_count: Jumlah retry
        """
        self._log_entry(filename, size_bytes, f"FAILED", 0, retry_count, error_msg)
    
    def _log_entry(self, filename: str, size_bytes: int, status: str, 
                   duration_seconds: float = 0, retry_count: int = 0, 
                   error_msg: Optional[str] = None):
        """
        Internal method untuk menulis entry ke history
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            size_gb = size_bytes / (1024**3)
            
            # Format durasi
            if duration_seconds > 0:
                hours = int(duration_seconds // 3600)
                minutes = int((duration_seconds % 3600) // 60)
                seconds = int(duration_seconds % 60)
                duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = "-"
            
            # Potong filename jika terlalu panjang
            display_filename = filename if len(filename) <= 38 else filename[:35] + "..."
            
            # Format line
            line = f"{timestamp:<20} {display_filename:<40} {size_gb:>11.2f} GB {status:<10} {duration_str:<10} {retry_count:<5}\n"
            
            # Tambah error message jika ada
            if error_msg:
                line += f"{' ':<20} {'ERROR:':<40} {error_msg}\n"
            
            # Tulis ke file
            with open(self.history_path, 'a', encoding='utf-8') as f:
                f.write(line)
            
            logger.debug(f"History logged: {filename} - {status}")
            
        except Exception as e:
            logger.error(f"Error writing to history: {e}")
    
    def get_recent(self, limit: int = 10) -> list:
        """
        Ambil history terbaru
        
        Args:
            limit: Jumlah entry terakhir yang diambil
            
        Returns:
            List of history entries
        """
        entries = []
        try:
            if not os.path.exists(self.history_path):
                return entries
            
            with open(self.history_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Skip header (5 baris pertama)
            data_lines = lines[5:]
            
            # Ambil limit terakhir
            for line in data_lines[-limit:]:
                if line.strip() and not line.startswith(' '):
                    entries.append(line.strip())
            
        except Exception as e:
            logger.error(f"Error reading history: {e}")
        
        return entries
    
    def get_stats(self) -> dict:
        """
        Dapatkan statistik dari history
        
        Returns:
            Dictionary statistik
        """
        stats = {
            'total_files': 0,
            'total_size_gb': 0,
            'success_count': 0,
            'failed_count': 0,
            'total_duration_seconds': 0
        }
        
        try:
            if not os.path.exists(self.history_path):
                return stats
            
            with open(self.history_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Skip header (5 baris pertama)
            data_lines = lines[5:]
            
            for line in data_lines:
                if line.strip() and not line.startswith(' '):
                    parts = line.split()
                    if len(parts) >= 6:
                        stats['total_files'] += 1
                        
                        # Parse size (kolom ke-4 dan 5: "XX.XX GB")
                        try:
                            size = float(parts[3])
                            stats['total_size_gb'] += size
                        except:
                            pass
                        
                        # Parse status (kolom ke-6)
                        status = parts[5]
                        if status == 'SUCCESS':
                            stats['success_count'] += 1
                        elif status == 'FAILED':
                            stats['failed_count'] += 1
                        
                        # Parse duration (kolom ke-7)
                        if len(parts) > 6 and parts[6] != '-':
                            try:
                                time_parts = parts[6].split(':')
                                if len(time_parts) == 3:
                                    hours = int(time_parts[0])
                                    minutes = int(time_parts[1])
                                    seconds = int(time_parts[2])
                                    stats['total_duration_seconds'] += hours*3600 + minutes*60 + seconds
                            except:
                                pass
            
        except Exception as e:
            logger.error(f"Error calculating history stats: {e}")
        
        return stats


# Test sederhana kalau dijalankan langsung
if __name__ == "__main__":
    # Setup logging dulu
    from .logger import setup_logging
    setup_logging()
    
    # Test HistoryLogger
    history = HistoryLogger()
    
    # Log beberapa entry
    history.log_success("movie1.mxf", 21474836480, 3600, 0)  # 20GB, 1 jam
    history.log_success("movie2.mp4", 32212254720, 5400, 1)  # 30GB, 1.5 jam
    history.log_failed("corrupt.mov", 10737418240, "Connection timeout", 3)  # 10GB
    
    # Tampilkan recent
    print("\nRecent history:")
    for entry in history.get_recent(5):
        print(f"  {entry}")
    
    # Tampilkan stats
    stats = history.get_stats()
    print(f"\nStats: {stats}")