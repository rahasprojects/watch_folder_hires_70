# -*- coding: utf-8 -*-
"""
GUI modules for watch_folder_hires_70
"""

from .queue_panel import QueuePanel
from .progress_panel import ProgressPanel
from .log_panel import LogPanel
from .history_panel import HistoryPanel
from .settings_window import SettingsWindow
from .main_window import MainWindow

# ===== EKSPOR PANEL UPLOAD BARU =====
from .upload_panel_51 import UploadPanel51
from .upload_panel_40 import UploadPanel40
# ====================================

__all__ = [
    'QueuePanel',
    'ProgressPanel',
    'LogPanel',
    'HistoryPanel',
    'SettingsWindow',
    'MainWindow',
    # ===== BARU =====
    'UploadPanel51',
    'UploadPanel40'
]