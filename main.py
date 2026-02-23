#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
watch_folder_hires_70 - Aplikasi pipeline copy file dari 12 ke 70
Fase 1: Download 12 → 70 dengan monitoring SMB, queue FIFO, resume capability.
"""

import sys
import os
import traceback

# Tambahkan path src ke sys.path agar bisa import modul
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main entry point aplikasi"""
    try:
        from src.utils.logger import setup_logging
        from src.utils.config_manager import ConfigManager
        from src.utils.state_manager import StateManager
        from src.core.file_monitor import FileMonitor
        from src.core.download_manager import DownloadManager
        from src.core.queue_manager import QueueManager
        from src.gui.main_window import MainWindow
        import tkinter as tk
        import threading
        
        # Setup logging
        setup_logging()
        import logging
        logger = logging.getLogger(__name__)
        logger.info("="*50)
        logger.info("Memulai aplikasi watch_folder_hires_70")
        logger.info("="*50)

        # Load konfigurasi
        config_mgr = ConfigManager()
        config = config_mgr.load()
        logger.info(f"Config loaded: max_download={config.max_download}")

        # Load state untuk resume
        state_mgr = StateManager()
        state = state_mgr.load()
        logger.info(f"State loaded: {len(state.get('jobs', {}))} jobs in state")

        # Inisialisasi queue manager (FIFO)
        queue_mgr = QueueManager()

        # Inisialisasi download manager
        download_mgr = DownloadManager(
            max_parallel=config.max_download,
            max_retry=config.max_retry,
            queue_manager=queue_mgr,
            state_manager=state_mgr
        )

        # Inisialisasi file monitor (SMB)
        monitor = FileMonitor(
            source_folders=config.source_folders,
            extensions=config.extensions,
            queue_manager=queue_mgr
        )

        # Inisialisasi GUI
        root = tk.Tk()
        app = MainWindow(
            root,
            config_mgr=config_mgr,
            state_mgr=state_mgr,
            queue_mgr=queue_mgr,
            download_mgr=download_mgr,
            monitor=monitor
        )

        # Start monitor di thread terpisah
        monitor_thread = threading.Thread(target=monitor.start, daemon=True)
        monitor_thread.start()
        logger.info("File monitor started")

        # Start download manager
        download_mgr.start()
        logger.info("Download manager started")

        # Jalankan GUI (blocking)
        logger.info("Starting GUI main loop")
        app.run()

    except KeyboardInterrupt:
        print("\n\nApplication stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()