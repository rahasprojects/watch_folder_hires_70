# -*- coding: utf-8 -*-
"""
Konstanta dan default settings untuk aplikasi
"""

# Default settings
DEFAULT_MAX_DOWNLOAD = 4
DEFAULT_MAX_RETRY = 3
DEFAULT_CHUNK_SIZE = 256 * 1024 * 1024  # 256MB
CHECKPOINT_PERCENT = 10  # Resume setiap 10%

# CHUNK_SIZE untuk kompatibilitas (sama dengan DEFAULT_CHUNK_SIZE)
CHUNK_SIZE = DEFAULT_CHUNK_SIZE

# Default extensions untuk file video
DEFAULT_EXTENSIONS = [
    '.mxf', '.mov', '.mp4', '.avi', '.mkv', 
    '.m4v', '.mpg', '.mpeg', '.wmv', '.flv',
    '.mts', '.m2ts', '.vob', '.3gp', '.webm'
]

# Status values
STATUS_WAITING = "waiting"
STATUS_DOWNLOADING = "downloading"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_PAUSED = "paused"

# Log formats
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# File names
CONFIG_FILE = "config.json"
STATE_FILE = "pipeline_state.json"
HISTORY_FILE = "copy_history.txt"
LOG_FILE = "pipeline.log"

# SMB settings
SMB_POLLING_INTERVAL = 5  # detik, untuk fallback
SMB_CHANGE_TIMEOUT = 30   # detik

# UI settings
REFRESH_INTERVAL = 1000  # ms (1 detik) untuk refresh GUI