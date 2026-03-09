#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
watch_folder_hires_70 - Aplikasi pipeline copy file
Fase 2: Download 12 → 70 dan Upload 70 → 40 & 51
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
        # ===== IMPORT UPLOAD MODULES =====
        from src.core.upload_queue_manager import UploadQueueManager
        from src.core.upload_manager import UploadManager
        from src.core.upload_controller import UploadController
        # ================================
        from src.gui.main_window import MainWindow
        import tkinter as tk
        import threading
        
        # Setup logging
        setup_logging()
        import logging
        logger = logging.getLogger(__name__)
        logger.info("="*50)
        logger.info("Memulai aplikasi watch_folder_hires_70 - FASE 2")
        logger.info("="*50)

        # Load konfigurasi
        config_mgr = ConfigManager()
        config = config_mgr.load()
        logger.info(f"Config loaded: max_download={config.max_download}, max_upload_51={config.max_upload_51}, max_upload_40={config.max_upload_40}")

        # Load state untuk resume
        state_mgr = StateManager()
        state = state_mgr.load()
        logger.info(f"State loaded: {len(state.get('jobs', {}))} jobs in state")

        # ===== INISIALISASI QUEUE MANAGER =====
        queue_mgr = QueueManager()  # Untuk download

        # ===== INISIALISASI UPLOAD COMPONENTS =====
        upload_queue_mgr = UploadQueueManager()  # Queue untuk upload
        upload_mgr = UploadManager(
            max_workers_51=config.max_upload_51,
            max_workers_40=config.max_upload_40,
            queue_manager=upload_queue_mgr,
            state_manager=state_mgr
        )
        upload_controller = UploadController(
            upload_manager=upload_mgr,
            queue_manager=upload_queue_mgr,
            config_manager=config_mgr,
            history_logger=None  # Akan pakai history logger dari main window
        )
        # ========================================

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
            upload_mgr=upload_mgr,              # BARU
            upload_controller=upload_controller, # BARU
            monitor=monitor
        )

        # ===== START MONITOR THREAD =====
        monitor_thread = threading.Thread(target=monitor.start, daemon=True)
        monitor_thread.start()
        logger.info("File monitor started")

        # ===== START DOWNLOAD MANAGER =====
        download_mgr.register_upload_controller(upload_controller)
        logger.info("Upload controller registered to download manager")
        download_mgr.start()
        logger.info("Download manager started")

        # ===== START UPLOAD MANAGER =====
        upload_mgr.start()
        logger.info("Upload manager started")

        # ===== HUBUNGKAN DOWNLOAD → UPLOAD =====
        # Kita perlu hook ke download manager untuk memanggil upload controller
        # saat download selesai. Ini bisa dilakukan dengan callback.
        
        def on_download_complete(job):
            """Callback saat download selesai"""
            logger.info(f"Download complete callback: {job.name}")
            upload_controller.on_download_complete(job)
        
        # Register callback ke download manager (perlu tambahan di download_manager.py)
        # Atau bisa juga di download_worker.py langsung panggil upload_controller
        # Untuk sementara, kita akan modifikasi download_worker.py nanti
        
        logger.info("Download→Upload hook registered")

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