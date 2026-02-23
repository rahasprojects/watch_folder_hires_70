# -*- coding: utf-8 -*-
"""
Model untuk merepresentasikan satu file yang akan diproses
"""

import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List
from ..constants.settings import STATUS_WAITING

@dataclass
class FileJob:
    """
    Kelas untuk merepresentasikan satu file dalam pipeline
    """
    # Identitas file
    name: str
    source_path: str
    dest_path: str
    size_bytes: int
    
    # Status dan progress
    status: str = STATUS_WAITING
    progress: float = 0.0  # 0-100
    copied_bytes: int = 0
    
    # Timestamps
    detected_time: datetime = field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Queue info
    queue_position: Optional[int] = None
    priority: int = 2  # Default priority (1 tertinggi, 3 terendah) - tapi tidak dipakai
    
    # Retry
    retry_count: int = 0
    max_retry: int = 3
    last_error: Optional[str] = None
    
    # Resume
    last_checkpoint: int = 0  # bytes yang sudah di-copy saat checkpoint terakhir
    checkpoints: List[int] = field(default_factory=list)  # daftar checkpoint yang sudah dicapai
    
    def __post_init__(self):
        """Validasi setelah inisialisasi"""
        if not self.name:
            self.name = os.path.basename(self.source_path)
    
    @property
    def size_gb(self) -> float:
        """Ukuran file dalam GB"""
        return self.size_bytes / (1024**3)
    
    @property
    def copied_gb(self) -> float:
        """Jumlah yang sudah di-copy dalam GB"""
        return self.copied_bytes / (1024**3)
    
    @property
    def progress_percent(self) -> float:
        """Progress dalam persen (0-100)"""
        if self.size_bytes == 0:
            return 0
        return (self.copied_bytes / self.size_bytes) * 100
    
    @property
    def elapsed_seconds(self) -> float:
        """Detik yang sudah berlalu sejak mulai"""
        if not self.start_time:
            return 0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
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
        remaining_bytes = self.size_bytes - self.copied_bytes
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
    
    def update_progress(self, copied_bytes: int):
        """Update progress dan cek checkpoint"""
        self.copied_bytes = copied_bytes
        self.progress = self.progress_percent
        
        # Cek checkpoint (setiap 10%)
        checkpoint = int(self.progress // 10) * 10
        if checkpoint > self.last_checkpoint and checkpoint not in self.checkpoints:
            self.checkpoints.append(checkpoint)
            self.last_checkpoint = checkpoint
            return True  # Ada checkpoint baru
        return False
    
    def to_dict(self) -> dict:
        """Konversi ke dictionary untuk disimpan ke JSON"""
        return {
            'name': self.name,
            'source_path': self.source_path,
            'dest_path': self.dest_path,
            'size_bytes': self.size_bytes,
            'status': self.status,
            'progress': self.progress,
            'copied_bytes': self.copied_bytes,
            'detected_time': self.detected_time.isoformat() if self.detected_time else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'queue_position': self.queue_position,
            'priority': self.priority,
            'retry_count': self.retry_count,
            'max_retry': self.max_retry,
            'last_error': self.last_error,
            'last_checkpoint': self.last_checkpoint,
            'checkpoints': self.checkpoints
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FileJob':
        """Buat FileJob dari dictionary"""
        # Parse datetime
        detected_time = None
        if data.get('detected_time'):
            try:
                detected_time = datetime.fromisoformat(data['detected_time'])
            except:
                detected_time = datetime.now()
        
        start_time = None
        if data.get('start_time'):
            try:
                start_time = datetime.fromisoformat(data['start_time'])
            except:
                pass
        
        end_time = None
        if data.get('end_time'):
            try:
                end_time = datetime.fromisoformat(data['end_time'])
            except:
                pass
        
        return cls(
            name=data['name'],
            source_path=data['source_path'],
            dest_path=data['dest_path'],
            size_bytes=data['size_bytes'],
            status=data.get('status', STATUS_WAITING),
            progress=data.get('progress', 0),
            copied_bytes=data.get('copied_bytes', 0),
            detected_time=detected_time,
            start_time=start_time,
            end_time=end_time,
            queue_position=data.get('queue_position'),
            priority=data.get('priority', 2),
            retry_count=data.get('retry_count', 0),
            max_retry=data.get('max_retry', 3),
            last_error=data.get('last_error'),
            last_checkpoint=data.get('last_checkpoint', 0),
            checkpoints=data.get('checkpoints', [])
        )