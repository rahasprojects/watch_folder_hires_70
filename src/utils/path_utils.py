# src/utils/path_utils.py
import os
import sys
from ..constants.settings import DATA_FOLDER

def get_base_path() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def get_data_path(filename: str = "") -> str:
    base_path = get_base_path()
    data_path = os.path.join(base_path, DATA_FOLDER)
    
    # ===== PASTIKAN FOLDER DATA ADA =====
    if not os.path.exists(data_path):
        try:
            os.makedirs(data_path, exist_ok=True)
            print(f"📁 Folder data dibuat: {data_path}")
        except Exception as e:
            print(f"❌ Gagal membuat folder data: {e}")
    
    if filename:
        return os.path.join(data_path, filename)
    return data_path

def ensure_data_folder():
    """Memastikan folder data ada"""
    data_path = get_data_path()
    os.makedirs(data_path, exist_ok=True)
    return data_path