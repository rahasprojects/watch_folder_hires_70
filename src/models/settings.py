# -*- coding: utf-8 -*-
"""
Model untuk menyimpan konfigurasi aplikasi
"""

from dataclasses import dataclass, field
from typing import List
from ..constants.settings import DEFAULT_MAX_DOWNLOAD, DEFAULT_MAX_RETRY, DEFAULT_EXTENSIONS

@dataclass
class Settings:
    """
    Kelas untuk menyimpan semua konfigurasi aplikasi
    """
    # Source folders (12)
    source_folders: List[str] = field(default_factory=list)
    
    # Destination folder (70)
    destination_folder: str = ""
    
    # File extensions yang diproses
    extensions: List[str] = field(default_factory=lambda: DEFAULT_EXTENSIONS.copy())
    
    # Concurrency settings
    max_download: int = DEFAULT_MAX_DOWNLOAD
    max_retry: int = DEFAULT_MAX_RETRY
    
    def validate(self) -> tuple[bool, str]:
        """
        Validasi settings
        Returns: (is_valid, error_message)
        """
        # Cek source folders
        if not self.source_folders:
            return False, "Minimal satu source folder harus diisi"
        
        # Cek destination folder
        if not self.destination_folder:
            return False, "Destination folder harus diisi"
        
        # Cek extensions
        if not self.extensions:
            return False, "Minimal satu ekstensi file harus dipilih"
        
        # Cek max_download (1-10)
        if self.max_download < 1 or self.max_download > 10:
            return False, "Max download harus antara 1-10"
        
        # Cek max_retry (0-5)
        if self.max_retry < 0 or self.max_retry > 5:
            return False, "Max retry harus antara 0-5"
        
        return True, "Settings valid"
    
    def to_dict(self) -> dict:
        """Konversi ke dictionary untuk disimpan ke JSON"""
        return {
            'source_folders': self.source_folders,
            'destination_folder': self.destination_folder,
            'extensions': self.extensions,
            'max_download': self.max_download,
            'max_retry': self.max_retry
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Settings':
        """Buat Settings dari dictionary"""
        return cls(
            source_folders=data.get('source_folders', []),
            destination_folder=data.get('destination_folder', ''),
            extensions=data.get('extensions', DEFAULT_EXTENSIONS.copy()),
            max_download=data.get('max_download', DEFAULT_MAX_DOWNLOAD),
            max_retry=data.get('max_retry', DEFAULT_MAX_RETRY)
        )
    
    def add_source_folder(self, folder: str) -> bool:
        """Tambah source folder baru"""
        if folder and folder not in self.source_folders:
            self.source_folders.append(folder)
            return True
        return False
    
    def remove_source_folder(self, folder: str) -> bool:
        """Hapus source folder"""
        if folder in self.source_folders:
            self.source_folders.remove(folder)
            return True
        return False
    
    def add_extension(self, ext: str) -> bool:
        """Tambah ekstensi file"""
        ext = ext.lower().strip()
        if not ext.startswith('.'):
            ext = '.' + ext
        if ext not in self.extensions:
            self.extensions.append(ext)
            return True
        return False
    
    def remove_extension(self, ext: str) -> bool:
        """Hapus ekstensi file"""
        ext = ext.lower().strip()
        if ext in self.extensions:
            self.extensions.remove(ext)
            return True
        return False