# -*- coding: utf-8 -*-
"""
Fungsi-fungsi validasi untuk path, file, extensions, dll
"""

import os
import re
import logging
from typing import List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

def validate_path(path: str, must_exist: bool = True) -> Tuple[bool, str]:
    """
    Validasi path folder
    
    Args:
        path: Path folder yang divalidasi
        must_exist: True jika folder harus ada, False jika boleh tidak ada
        
    Returns:
        (is_valid, error_message)
    """
    if not path or not path.strip():
        return False, "Path tidak boleh kosong"
    
    # Clean path
    path = path.strip()
    
    # Cek karakter invalid di Windows
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        if char in path:
            return False, f"Path mengandung karakter invalid: {char}"
    
    # Cek apakah path adalah network path (\\server\share)
    is_network = path.startswith('\\\\')
    
    # Cek apakah path adalah drive letter (X:)
    is_drive = re.match(r'^[a-zA-Z]:\\?$', path) is not None
    
    # Cek apakah path relatif
    is_relative = not (is_network or is_drive or path.startswith('/') or path.startswith('\\'))
    
    if must_exist:
        try:
            # Coba cek apakah folder ada
            if not os.path.exists(path):
                return False, f"Path tidak ditemukan: {path}"
            
            if not os.path.isdir(path):
                return False, f"Path bukan folder: {path}"
                
        except PermissionError:
            return False, f"Tidak punya akses ke path: {path}"
        except Exception as e:
            return False, f"Error accessing path: {e}"
    
    return True, "Path valid"

def validate_file_path(path: str, must_exist: bool = True) -> Tuple[bool, str]:
    """
    Validasi path file (bukan folder)
    
    Args:
        path: Path file yang divalidasi
        must_exist: True jika file harus ada
        
    Returns:
        (is_valid, error_message)
    """
    if not path or not path.strip():
        return False, "Path tidak boleh kosong"
    
    path = path.strip()
    
    if must_exist:
        try:
            if not os.path.exists(path):
                return False, f"File tidak ditemukan: {path}"
            
            if not os.path.isfile(path):
                return False, f"Path bukan file: {path}"
                
        except PermissionError:
            return False, f"Tidak punya akses ke file: {path}"
        except Exception as e:
            return False, f"Error accessing file: {e}"
    
    return True, "Path valid"

def validate_extension(ext: str) -> Tuple[bool, str]:
    """
    Validasi format ekstensi file
    
    Args:
        ext: Ekstensi (bisa dengan atau tanpa titik)
        
    Returns:
        (is_valid, error_message)
    """
    if not ext or not ext.strip():
        return False, "Ekstensi tidak boleh kosong"
    
    ext = ext.strip().lower()
    
    # Tambah titik jika belum ada
    if not ext.startswith('.'):
        ext = '.' + ext
    
    # Cek format (hanya huruf dan angka setelah titik)
    if not re.match(r'^\.[a-z0-9]+$', ext):
        return False, f"Format ekstensi tidak valid: {ext}"
    
    # Cek panjang (max 10 karakter setelah titik)
    if len(ext) > 11:  # titik + max 10 chars
        return False, f"Ekstensi terlalu panjang: {ext}"
    
    return True, ext  # Return normalized extension

def validate_size(size_bytes: int, max_size_gb: Optional[float] = None) -> Tuple[bool, str]:
    """
    Validasi ukuran file
    
    Args:
        size_bytes: Ukuran dalam bytes
        max_size_gb: Maksimum ukuran dalam GB (optional)
        
    Returns:
        (is_valid, error_message)
    """
    if size_bytes < 0:
        return False, "Ukuran file tidak boleh negatif"
    
    if max_size_gb is not None:
        max_bytes = max_size_gb * 1024**3
        if size_bytes > max_bytes:
            size_gb = size_bytes / 1024**3
            return False, f"Ukuran file terlalu besar: {size_gb:.2f}GB > {max_size_gb}GB"
    
    return True, "Ukuran valid"

def is_video_file(filename: str, extensions: List[str]) -> bool:
    """
    Cek apakah file termasuk video berdasarkan ekstensi
    
    Args:
        filename: Nama file
        extensions: Daftar ekstensi yang diizinkan
        
    Returns:
        True jika file video
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in extensions

def sanitize_filename(filename: str) -> str:
    """
    Bersihkan nama file dari karakter invalid
    
    Args:
        filename: Nama file asli
        
    Returns:
        Nama file yang sudah dibersihkan
    """
    # Ganti karakter invalid dengan underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Hapus karakter kontrol
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Trim
    filename = filename.strip()
    
    # Cegah nama file kosong
    if not filename:
        filename = "unnamed_file"
    
    return filename

def get_unique_filename(dest_dir: str, filename: str) -> str:
    """
    Dapatkan nama file unik (tambah nomor jika sudah ada)
    
    Args:
        dest_dir: Folder tujuan
        filename: Nama file yang diinginkan
        
    Returns:
        Nama file unik
    """
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    
    while os.path.exists(os.path.join(dest_dir, new_filename)):
        new_filename = f"{base}_{counter}{ext}"
        counter += 1
    
    return new_filename

def is_path_writable(path: str) -> Tuple[bool, str]:
    """
    Cek apakah path bisa ditulisi
    
    Args:
        path: Path folder yang dicek
        
    Returns:
        (is_writable, error_message)
    """
    try:
        # Buat folder jika belum ada
        os.makedirs(path, exist_ok=True)
        
        # Coba buat file test
        test_file = os.path.join(path, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        
        return True, "Path dapat ditulisi"
        
    except PermissionError:
        return False, f"Tidak punya akses write ke: {path}"
    except Exception as e:
        return False, f"Error writing to path: {e}"

def normalize_path(path: str) -> str:
    """
    Normalisasi path (ubah ke format standar)
    
    Args:
        path: Path yang akan dinormalisasi
        
    Returns:
        Path yang sudah dinormalisasi
    """
    if not path:
        return ""
    
    # Gunakan Path object dari pathlib
    try:
        p = Path(path)
        # Resolve kalau path relatif, tapi hati-hati dengan network path
        if not str(path).startswith('\\\\'):
            try:
                p = p.resolve()
            except:
                pass
        return str(p)
    except:
        # Fallback ke metode manual
        path = os.path.normpath(path)
        return path


# Test sederhana kalau dijalankan langsung
if __name__ == "__main__":
    # Test validators
    print("Testing validators...")
    
    # Test validate_path
    valid, msg = validate_path("C:\\Windows", must_exist=True)
    print(f"validate_path C:\\Windows: {valid} - {msg}")
    
    # Test validate_extension
    valid, msg = validate_extension("mp4")
    print(f"validate_extension mp4: {valid} - {msg}")
    
    # Test is_video_file
    is_video = is_video_file("movie.mxf", ['.mxf', '.mp4'])
    print(f"is_video_file movie.mxf: {is_video}")
    
    # Test get_unique_filename
    # (butuh folder test, skip dulu)
    
    print("Validators test done")