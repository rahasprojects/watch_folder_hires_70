# -*- coding: utf-8 -*-
"""
Konstanta dan default settings untuk aplikasi
"""

# Default settings
DEFAULT_MAX_DOWNLOAD = 4
DEFAULT_MAX_RETRY = 3
DEFAULT_CHUNK_SIZE = 256 * 1024 * 1024  # 8MB
CHECKPOINT_PERCENT = 10  # Resume setiap 10%

# ===== KONSTANTA UNTUK UPLOAD =====
DEFAULT_MAX_UPLOAD_51 = 2
DEFAULT_MAX_UPLOAD_40 = 2
UPLOAD_PRIORITY_51 = "HIGH"
UPLOAD_PRIORITY_40 = "NORMAL"

# CHUNK_SIZE untuk kompatibilitas
CHUNK_SIZE = DEFAULT_CHUNK_SIZE

# Default extensions untuk file video
DEFAULT_EXTENSIONS = [
    '.mxf', '.mov', '.mp4',
]

# Status values
STATUS_WAITING = "waiting"
STATUS_DOWNLOADING = "downloading"
STATUS_UPLOADING = "uploading"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_PAUSED = "paused"

# Log formats
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ===== FILE NAMES (TANPA PATH) =====
CONFIG_FILE = "config.json"
STATE_FILE = "pipeline_state.json"
HISTORY_FILE = "copy_history.txt"
LOG_FILE = "pipeline.log"
DATA_FOLDER = "data"  # <-- FOLDER DATA

# SMB settings
SMB_POLLING_INTERVAL = 5  # detik, untuk fallback
SMB_CHANGE_TIMEOUT = 30   # detik

# UI settings
REFRESH_INTERVAL = 1000  # ms (1 detik) untuk refresh GUI