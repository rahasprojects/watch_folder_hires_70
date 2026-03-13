# -*- coding: utf-8 -*-
"""
Setup logging untuk aplikasi
"""

import logging
import sys
import os
from datetime import datetime
from ..constants.settings import LOG_FILE, LOG_FORMAT, LOG_DATE_FORMAT
from .path_utils import get_data_path

def setup_logging():
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Hapus handler yang sudah ada
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Formatter
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    
    # ===== PASTIKAN FOLDER DATA DIBUAT =====
    log_path = get_data_path(LOG_FILE)
    
    # Buat folder data jika belum ada
    os.makedirs(os.path.dirname(log_path), exist_ok=True)  # <-- PENTING!
    
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name):
    """
    Dapatkan logger dengan nama tertentu
    """
    return logging.getLogger(name)


# Test sederhana kalau dijalankan langsung
if __name__ == "__main__":
    setup_logging()
    logger = get_logger(__name__)
    logger.debug("Ini debug message")
    logger.info("Ini info message")
    logger.warning("Ini warning message")
    logger.error("Ini error message")