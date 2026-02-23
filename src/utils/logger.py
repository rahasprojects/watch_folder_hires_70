# -*- coding: utf-8 -*-
"""
Setup logging untuk aplikasi
"""

import logging
import sys
import os
from datetime import datetime
from ..constants.settings import LOG_FILE, LOG_FORMAT, LOG_DATE_FORMAT

def setup_logging():
    """
    Setup logging ke file dan console
    """
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Hapus handler yang sudah ada (kalau ada)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Formatter
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    
    # File handler (DEBUG level)
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), LOG_FILE)
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (INFO level)
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