# -*- coding: utf-8 -*-
"""
Model untuk menyimpan konfigurasi aplikasi
"""

from dataclasses import dataclass, field
from typing import List
from ..constants.settings import (
    DEFAULT_MAX_DOWNLOAD, DEFAULT_MAX_RETRY, 
    DEFAULT_EXTENSIONS,
    DEFAULT_MAX_UPLOAD_51, DEFAULT_MAX_UPLOAD_40
)

@dataclass
class Settings:
    """
    Kelas untuk menyimpan semua konfigurasi aplikasi
    """
    # Source folders (12)
    source_folders: List[str] = field(default_factory=list)
    
    # Destination folders
    destination_70: str = ""
    destination_51: str = ""
    destination_40: str = ""
    
    # File extensions
    extensions: List[str] = field(default_factory=lambda: DEFAULT_EXTENSIONS.copy())
    
    # Concurrency settings
    max_download: int = DEFAULT_MAX_DOWNLOAD
    max_upload_51: int = DEFAULT_MAX_UPLOAD_51
    max_upload_40: int = DEFAULT_MAX_UPLOAD_40
    max_retry: int = DEFAULT_MAX_RETRY
    
    def validate(self) -> Tuple[bool, str]:
        """Validasi settings"""
        if not self.source_folders:
            return False, "Minimal satu source folder harus diisi"
        
        if not self.destination_70:
            return False, "Destination folder 70 harus diisi"
        
        if not self.destination_51:
            return False, "Destination folder 51 (HIRES) harus diisi"
        
        if not self.destination_40:
            return False, "Destination folder 40 (LOWRES) harus diisi"
        
        if not self.extensions:
            return False, "Minimal satu ekstensi file harus dipilih"
        
        if self.max_download < 1 or self.max_download > 10:
            return False, "Max download harus antara 1-10"
        
        if self.max_upload_51 < 1 or self.max_upload_51 > 5:
            return False, "Max upload 51 harus antara 1-5"
        
        if self.max_upload_40 < 1 or self.max_upload_40 > 5:
            return False, "Max upload 40 harus antara 1-5"
        
        if self.max_retry < 0 or self.max_retry > 5:
            return False, "Max retry harus antara 0-5"
        
        return True, "Settings valid"
    
    def to_dict(self) -> dict:
        """Konversi ke dictionary"""
        return {
            'source_folders': self.source_folders,
            'destination_70': self.destination_70,
            'destination_51': self.destination_51,
            'destination_40': self.destination_40,
            'extensions': self.extensions,
            'max_download': self.max_download,
            'max_upload_51': self.max_upload_51,
            'max_upload_40': self.max_upload_40,
            'max_retry': self.max_retry
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Settings':
        """Buat Settings dari dictionary"""
        return cls(
            source_folders=data.get('source_folders', []),
            destination_70=data.get('destination_70', data.get('destination_70', '')),
            destination_51=data.get('destination_51', ''),
            destination_40=data.get('destination_40', ''),
            extensions=data.get('extensions', DEFAULT_EXTENSIONS.copy()),
            max_download=data.get('max_download', DEFAULT_MAX_DOWNLOAD),
            max_upload_51=data.get('max_upload_51', DEFAULT_MAX_UPLOAD_51),
            max_upload_40=data.get('max_upload_40', DEFAULT_MAX_UPLOAD_40),
            max_retry=data.get('max_retry', DEFAULT_MAX_RETRY)
        )
    
    def add_source_folder(self, folder: str) -> bool:
        if folder and folder not in self.source_folders:
            self.source_folders.append(folder)
            return True
        return False
    
    def remove_source_folder(self, folder: str) -> bool:
        if folder in self.source_folders:
            self.source_folders.remove(folder)
            return True
        return False
    
    def add_extension(self, ext: str) -> bool:
        ext = ext.lower().strip()
        if not ext.startswith('.'):
            ext = '.' + ext
        if ext not in self.extensions:
            self.extensions.append(ext)
            return True
        return False
    
    def remove_extension(self, ext: str) -> bool:
        ext = ext.lower().strip()
        if ext in self.extensions:
            self.extensions.remove(ext)
            return True
        return False