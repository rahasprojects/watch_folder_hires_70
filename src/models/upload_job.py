# -*- coding: utf-8 -*-
"""
Model untuk merepresentasikan satu job upload
"""

import os
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List

from ..constants.settings import STATUS_WAITING, UPLOAD_PRIORITY_51, UPLOAD_PRIORITY_40

logger = logging.getLogger(__name__)

@dataclass
class UploadJob:
    """
    Kelas untuk merepresentasikan satu job upload ke server tujuan
    """
    # Identitas file
    source_path: str          # File di 70
    dest_path: str            # Tujuan (51 atau 40)
    destination: int          # 51 atau 40
    priority: str             # "HIGH" atau "NORMAL"
    file_size: int            # Ukuran file dalam bytes
    file_name: str = ""       # Nama file (diisi otomatis dari source_path)
    
    # Status dan progress
    status: str = STATUS_WAITING
    progress: float = 0.0     # 0-100
    copied_bytes: int = 0
    
    # Timestamps
    created_time: datetime = field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Retry
    retry_count: int = 0
    max_retry: int = 3
    last_error: Optional[str] = None
    
    # Resume untuk upload (checkpoint)
    last_checkpoint: int = 0
    checkpoints: List[int] = field(default_factory=list)
    
    # Relasi ke download job asli (optional)
    original_download_job: Optional[object] = None
    
    def __post_init__(self):
        """Validasi setelah inisialisasi"""
        if not self.file_name:
            self.file_name = os.path.basename(self.source_path)
        
        # Validasi destination
        if self.destination not in [51, 40]:
            raise ValueError(f"Invalid destination: {self.destination}. Must be 51 or 40")
        
        # Set priority berdasarkan destination jika tidak ditentukan
        if not self.priority:
            self.priority = UPLOAD_PRIORITY_51 if self.destination == 51 else UPLOAD_PRIORITY_40
    
    @property
    def size_gb(self) -> float:
        """Ukuran file dalam GB"""
        return self.file_size / (1024**3)
    
    @property
    def copied_gb(self) -> float:
        """Jumlah yang sudah di-upload dalam GB"""
        return self.copied_bytes / (1024**3)
    
    @property
    def progress_percent(self) -> float:
        """Progress dalam persen (0-100)"""
        if self.file_size == 0:
            return 0
        return (self.copied_bytes / self.file_size) * 100
    
    @property
    def elapsed_seconds(self) -> float:
        """Detik yang sudah berlalu sejak mulai"""
        if not self.start_time:
            return 0
        
        # ===== FIX: Konversi ke datetime jika masih berupa float (timestamp) =====
        if isinstance(self.start_time, (int, float)):
            start = datetime.fromtimestamp(self.start_time)
        else:
            start = self.start_time
        
        # Konversi end_time jika ada
        if self.end_time:
            if isinstance(self.end_time, (int, float)):
                end = datetime.fromtimestamp(self.end_time)
            else:
                end = self.end_time
        else:
            end = datetime.now()
        
        # Pastikan keduanya datetime
        if not isinstance(start, datetime) or not isinstance(end, datetime):
            logger.error(f"Invalid types in elapsed_seconds: start={type(start)}, end={type(end)}")
            return 0
        
        return (end - start).total_seconds()
        # =========================================================================
    
    @property
    def speed_mbps(self) -> float:
        """Kecepatan transfer dalam MB/s"""
        if self.elapsed_seconds == 0 or self.copied_bytes == 0:
            return 0
        return (self.copied_bytes / (1024*1024)) / self.elapsed_seconds
    
    @property
    def eta_seconds(self) -> float:
        """Estimasi waktu selesai dalam detik"""
        if self.speed_mbps == 0 or self.progress_percent >= 100:
            return 0
        remaining_bytes = self.file_size - self.copied_bytes
        return (remaining_bytes / (1024*1024)) / self.speed_mbps
    
    @property
    def eta_formatted(self) -> str:
        """Estimasi waktu selesai dalam format HH:MM:SS"""
        eta = self.eta_seconds
        if eta <= 0:
            return "-"
        hours = int(eta // 3600)
        minutes = int((eta % 3600) // 60)
        seconds = int(eta % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def priority_display(self) -> str:
        """Display priority dengan icon"""
        if self.priority == "HIGH":
            return "⭐ HIGH"
        else:
            return "NORMAL"
    
    def update_progress(self, copied_bytes: int):
        """Update progress dan cek checkpoint"""
        self.copied_bytes = copied_bytes
        self.progress = self.progress_percent
        
        # Cek checkpoint (setiap 10%)
        checkpoint = int(self.progress // 10) * 10
        if checkpoint > self.last_checkpoint and checkpoint not in self.checkpoints:
            self.checkpoints.append(checkpoint)
            self.last_checkpoint = checkpoint
            return True
        return False
    
    def to_dict(self) -> dict:
        """Konversi ke dictionary untuk disimpan ke JSON"""
        # ===== FIX: Format datetime dengan aman =====
        created_time_str = None
        if self.created_time:
            if isinstance(self.created_time, datetime):
                created_time_str = self.created_time.isoformat()
            elif isinstance(self.created_time, (int, float)):
                # Jika berupa timestamp, konversi ke datetime dulu
                try:
                    dt = datetime.fromtimestamp(self.created_time)
                    created_time_str = dt.isoformat()
                except:
                    created_time_str = str(self.created_time)
            else:
                created_time_str = str(self.created_time)
        
        start_time_str = None
        if self.start_time:
            if isinstance(self.start_time, datetime):
                start_time_str = self.start_time.isoformat()
            elif isinstance(self.start_time, (int, float)):
                try:
                    dt = datetime.fromtimestamp(self.start_time)
                    start_time_str = dt.isoformat()
                except:
                    start_time_str = str(self.start_time)
            else:
                start_time_str = str(self.start_time)
        
        end_time_str = None
        if self.end_time:
            if isinstance(self.end_time, datetime):
                end_time_str = self.end_time.isoformat()
            elif isinstance(self.end_time, (int, float)):
                try:
                    dt = datetime.fromtimestamp(self.end_time)
                    end_time_str = dt.isoformat()
                except:
                    end_time_str = str(self.end_time)
            else:
                end_time_str = str(self.end_time)
        # =============================================
        
        return {
            'file_name': self.file_name,
            'source_path': self.source_path,
            'dest_path': self.dest_path,
            'destination': self.destination,
            'priority': self.priority,
            'file_size': self.file_size,
            'status': self.status,
            'progress': self.progress,
            'copied_bytes': self.copied_bytes,
            'created_time': created_time_str,
            'start_time': start_time_str,
            'end_time': end_time_str,
            'retry_count': self.retry_count,
            'max_retry': self.max_retry,
            'last_error': self.last_error,
            'last_checkpoint': self.last_checkpoint,
            'checkpoints': self.checkpoints
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UploadJob':
        """Buat UploadJob dari dictionary"""
        # ===== FIX: Parse datetime dengan handle berbagai format =====
        created_time = None
        if data.get('created_time'):
            try:
                # Coba parse sebagai ISO format string
                created_time = datetime.fromisoformat(data['created_time'])
            except (ValueError, TypeError):
                try:
                    # Coba parse sebagai float (timestamp)
                    created_time = datetime.fromtimestamp(float(data['created_time']))
                except (ValueError, TypeError):
                    try:
                        # Coba parse sebagai string format lain
                        created_time = datetime.strptime(data['created_time'], "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        # Jika semua gagal, gunakan waktu sekarang
                        logger.warning(f"Failed to parse created_time: {data.get('created_time')}, using now")
                        created_time = datetime.now()
        
        start_time = None
        if data.get('start_time'):
            try:
                start_time = datetime.fromisoformat(data['start_time'])
            except (ValueError, TypeError):
                try:
                    start_time = datetime.fromtimestamp(float(data['start_time']))
                except (ValueError, TypeError):
                    try:
                        start_time = datetime.strptime(data['start_time'], "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        # Jika gagal parse, biarkan None
                        pass
        
        end_time = None
        if data.get('end_time'):
            try:
                end_time = datetime.fromisoformat(data['end_time'])
            except (ValueError, TypeError):
                try:
                    end_time = datetime.fromtimestamp(float(data['end_time']))
                except (ValueError, TypeError):
                    try:
                        end_time = datetime.strptime(data['end_time'], "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        pass
        # ==============================================================
        
        return cls(
            file_name=data.get('file_name', ''),
            source_path=data['source_path'],
            dest_path=data['dest_path'],
            destination=data['destination'],
            priority=data.get('priority', ''),
            file_size=data['file_size'],
            status=data.get('status', STATUS_WAITING),
            progress=data.get('progress', 0),
            copied_bytes=data.get('copied_bytes', 0),
            created_time=created_time,
            start_time=start_time,
            end_time=end_time,
            retry_count=data.get('retry_count', 0),
            max_retry=data.get('max_retry', 3),
            last_error=data.get('last_error'),
            last_checkpoint=data.get('last_checkpoint', 0),
            checkpoints=data.get('checkpoints', [])
        )


# Test sederhana
if __name__ == "__main__":
    from ..utils.logger import setup_logging
    setup_logging()
    
    print("UploadJob class ready with datetime fixes")
    
    # Test dengan berbagai tipe datetime
    job = UploadJob(
        source_path=r"D:\70\test.mxf",
        dest_path=r"\\server\51\test.mxf",
        destination=51,
        priority="HIGH",
        file_size=1073741824,
        file_name="test.mxf"
    )
    
    # Test konversi
    job_dict = job.to_dict()
    print(f"Job dict: {job_dict['created_time']}")
    
    job2 = UploadJob.from_dict(job_dict)
    print(f"Job2 created_time: {job2.created_time}")
    
    print("✅ Fix applied - elapsed_seconds will work with both datetime and float")