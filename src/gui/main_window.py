# -*- coding: utf-8 -*-
"""
Main window aplikasi watch_folder_hires_70 dengan layout 3 tab
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
from ..utils.logger import get_logger
from ..utils.config_manager import ConfigManager
from ..utils.state_manager import StateManager
from ..utils.history import HistoryLogger
from ..core.queue_manager import QueueManager
from ..core.download_manager import DownloadManager
from ..core.upload_manager import UploadManager
from ..core.upload_queue_manager import UploadQueueManager
from ..core.upload_controller import UploadController
from ..core.file_monitor import FileMonitor
from ..gui.queue_panel import QueuePanel
from ..gui.progress_panel import ProgressPanel
from ..gui.log_panel import LogPanel
from ..gui.history_panel import HistoryPanel
from ..gui.upload_panel_51 import UploadPanel51
from ..gui.upload_panel_40 import UploadPanel40
from ..gui.settings_window import SettingsWindow
from ..constants.settings import REFRESH_INTERVAL

logger = get_logger(__name__)

class MainWindow:
    """
    Main window aplikasi dengan layout 3 tab
    - Tab 1: QUEUE (dengan 3 panel: Download, Upload 51, Upload 40)
    - Tab 2: HISTORY
    - Tab 3: ACTIVITY LOG
    """
    
    def __init__(self, root, config_mgr: ConfigManager, state_mgr: StateManager,
                 queue_mgr: QueueManager, download_mgr: DownloadManager,
                 upload_mgr: UploadManager, upload_controller: UploadController,
                 monitor: FileMonitor):
        """
        Inisialisasi MainWindow
        
        Args:
            root: Tk root window
            config_mgr: ConfigManager instance
            state_mgr: StateManager instance
            queue_mgr: QueueManager instance
            download_mgr: DownloadManager instance
            upload_mgr: UploadManager instance
            upload_controller: UploadController instance
            monitor: FileMonitor instance
        """
        self.root = root
        self.config_mgr = config_mgr
        self.state_mgr = state_mgr
        self.queue_mgr = queue_mgr
        self.download_mgr = download_mgr
        self.upload_mgr = upload_mgr
        self.upload_controller = upload_controller
        self.monitor = monitor
        self.history_logger = HistoryLogger()
        
        # Window properties
        self.root.title("🎬 Watch Folder Hires 70 - Pipeline Copy (Fase 2: 70 → 40 & 51)")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 750)
        
        # Variables
        self.status_var = tk.StringVar(value="Initializing...")
        self.stats_var = tk.StringVar(value="")
        self.after_id = None
        
        # Setup closing protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create GUI
        self._create_menu()
        self._create_widgets()
        self._create_statusbar()
        
        # Bind keyboard shortcuts
        self._bind_shortcuts()
        
        logger.info("Main window initialized with Upload panels")
    
    def _create_menu(self):
        """Buat menu bar (TIDAK BERUBAH)"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Settings", command=self._open_settings, accelerator="Ctrl+,")
        settings_menu.add_separator()
        settings_menu.add_command(label="Save Settings", command=self._save_settings)
        settings_menu.add_command(label="Load Settings", command=self._load_settings)
        settings_menu.add_command(label="Reset to Defaults", command=self._reset_settings)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh All", command=self._refresh_all, accelerator="F5")
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Open Log File", command=self._open_log_file)
        tools_menu.add_command(label="Open History File", command=self._open_history_file)
        tools_menu.add_separator()
        tools_menu.add_command(label="Show Statistics", command=self._show_statistics)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _create_widgets(self):
        """Buat semua widget utama dengan 3 tab"""
        
        # Main container
        main_container = ttk.Frame(self.root, padding=8)
        main_container.pack(fill='both', expand=True)
        
        # Create Notebook untuk 3 tab
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True)
        
        # ===== TAB 1: QUEUE (dengan 3 panel) =====
        self._create_queue_tab()
        
        # ===== TAB 2: HISTORY =====
        self._create_history_tab()
        
        # ===== TAB 3: ACTIVITY LOG =====
        self._create_log_tab()
    
    def _create_queue_tab(self):
        """Buat tab Queue dengan 3 panel vertikal"""
        queue_tab = ttk.Frame(self.notebook)
        self.notebook.add(queue_tab, text="📋 QUEUE")
        
       # Weight: download 1, upload 4, upload 4
        queue_tab.grid_rowconfigure(0, weight=1)  # Download (11%)
        queue_tab.grid_rowconfigure(1, weight=4)  # Upload 51 (44.5%)
        queue_tab.grid_rowconfigure(2, weight=4)  # Upload 40 (44.5%)
        queue_tab.grid_columnconfigure(0, weight=1)
        
        # ===== PANEL 1: DOWNLOAD (DENGAN PROGRESS BAR) =====
        download_frame = ttk.LabelFrame(queue_tab, text="📥 DOWNLOAD (12 → 70)", padding=5)
        download_frame.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
        
        # Gunakan grid di dalam download_frame
        download_frame.grid_rowconfigure(0, weight=0)  # Stats
        download_frame.grid_rowconfigure(1, weight=0)  # Queue (fixed)
        download_frame.grid_rowconfigure(2, weight=1)  # Progress (expandable)
        download_frame.grid_columnconfigure(0, weight=1)
        
        # Stats untuk download
        download_stats = ttk.Frame(download_frame)
        download_stats.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        
        self.dl_active_label = ttk.Label(download_stats, text="Active: 0", font=('Arial', 9, 'bold'))
        self.dl_active_label.pack(side='left', padx=5)
        
        self.dl_waiting_label = ttk.Label(download_stats, text="Waiting: 0", font=('Arial', 9, 'bold'))
        self.dl_waiting_label.pack(side='left', padx=5)
        
        self.dl_max_label = ttk.Label(download_stats, text=f"Max: {self.config_mgr.get_settings().max_download}", 
                                    font=('Arial', 9, 'bold'))
        self.dl_max_label.pack(side='left', padx=5)
        
        # Queue table untuk download (dengan QueuePanel yang sudah ada)
        self.download_queue = QueuePanel(download_frame, self.queue_mgr)
        self.download_queue.grid(row=1, column=0, sticky='ew', pady=(0, 5))
        
        # Progress bar dengan SCROLL untuk download (ProgressPanel yang sudah diupdate)
        self.download_progress = ProgressPanel(download_frame, self.download_mgr)
        self.download_progress.grid(row=2, column=0, sticky='nsew')
        
        # ===== PANEL 2: UPLOAD 51 (HIRES) - SUDAH BAIK =====
        upload51_frame = ttk.LabelFrame(queue_tab, text="📤 UPLOAD 51 (HIRES) - ⭐ HIGH PRIORITY", padding=5)
        upload51_frame.grid(row=1, column=0, sticky='nsew', padx=2, pady=2)
        
        # Gunakan grid di dalam upload51_frame
        upload51_frame.grid_rowconfigure(0, weight=0)  # Stats
        upload51_frame.grid_rowconfigure(1, weight=1)  # Upload panel
        upload51_frame.grid_columnconfigure(0, weight=1)
        
        # Stats untuk upload 51
        upload51_stats = ttk.Frame(upload51_frame)
        upload51_stats.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        
        self.ul51_active_label = ttk.Label(upload51_stats, text="Active: 0", font=('Arial', 9, 'bold'))
        self.ul51_active_label.pack(side='left', padx=5)
        
        self.ul51_waiting_label = ttk.Label(upload51_stats, text="Waiting: 0", font=('Arial', 9, 'bold'))
        self.ul51_waiting_label.pack(side='left', padx=5)
        
        self.ul51_max_label = ttk.Label(upload51_stats, text=f"Max: {self.config_mgr.get_settings().max_upload_51}", 
                                    font=('Arial', 9, 'bold'))
        self.ul51_max_label.pack(side='left', padx=5)
        
        # Upload 51 Panel (sudah include queue + progress dengan scroll)
        self.upload51_panel = UploadPanel51(upload51_frame, self.upload_mgr)
        self.upload51_panel.grid(row=1, column=0, sticky='nsew')
        
        # ===== PANEL 3: UPLOAD 40 (LOWRES) - SUDAH BAIK =====
        upload40_frame = ttk.LabelFrame(queue_tab, text="📤 UPLOAD 40 (LOWRES) - NORMAL PRIORITY", padding=5)
        upload40_frame.grid(row=2, column=0, sticky='nsew', padx=2, pady=2)
        
        # Gunakan grid di dalam upload40_frame
        upload40_frame.grid_rowconfigure(0, weight=0)  # Stats
        upload40_frame.grid_rowconfigure(1, weight=1)  # Upload panel
        upload40_frame.grid_columnconfigure(0, weight=1)
        
        # Stats untuk upload 40
        upload40_stats = ttk.Frame(upload40_frame)
        upload40_stats.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        
        self.ul40_active_label = ttk.Label(upload40_stats, text="Active: 0", font=('Arial', 9, 'bold'))
        self.ul40_active_label.pack(side='left', padx=5)
        
        self.ul40_waiting_label = ttk.Label(upload40_stats, text="Waiting: 0", font=('Arial', 9, 'bold'))
        self.ul40_waiting_label.pack(side='left', padx=5)
        
        self.ul40_max_label = ttk.Label(upload40_stats, text=f"Max: {self.config_mgr.get_settings().max_upload_40}", 
                                    font=('Arial', 9, 'bold'))
        self.ul40_max_label.pack(side='left', padx=5)
        
        # Upload 40 Panel (sudah include queue + progress dengan scroll)
        self.upload40_panel = UploadPanel40(upload40_frame, self.upload_mgr)
        self.upload40_panel.grid(row=1, column=0, sticky='nsew')
    
    def _create_history_tab(self):
        """Buat tab History (sama seperti Fase 1)"""
        history_tab = ttk.Frame(self.notebook)
        self.notebook.add(history_tab, text="📜 HISTORY")
        
        history_tab.grid_rowconfigure(0, weight=1)
        history_tab.grid_columnconfigure(0, weight=1)
        
        try:
            self.history_panel = HistoryPanel(history_tab, self.history_logger)
            self.history_panel.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        except Exception as e:
            logger.error(f"Could not load HistoryPanel: {e}")
            error_frame = ttk.Frame(history_tab)
            error_frame.pack(fill='both', expand=True)
            ttk.Label(error_frame, text=f"⚠️ History panel failed to load: {e}", 
                     foreground='red', font=('Arial', 12)).pack(pady=50)
    
    def _create_log_tab(self):
        """Buat tab Activity Log (sama seperti Fase 1)"""
        log_tab = ttk.Frame(self.notebook)
        self.notebook.add(log_tab, text="📝 ACTIVITY LOG")
        
        log_tab.grid_rowconfigure(0, weight=1)
        log_tab.grid_columnconfigure(0, weight=1)
        
        self.log_panel = LogPanel(log_tab)
        self.log_panel.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
    
    def _create_statusbar(self):
        """Buat status bar dengan info download dan upload"""
        status_frame = ttk.Frame(self.root, relief='sunken', padding=(5, 2))
        status_frame.pack(side='bottom', fill='x')
        
        # Left side - Monitoring status
        self.status_icon = ttk.Label(status_frame, text="🟢", font=('Arial', 10))
        self.status_icon.pack(side='left', padx=(2, 0))
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor='w')
        status_label.pack(side='left', padx=5)
        
        # Right side - Speed info
        self.speed_label = ttk.Label(status_frame, text="DL:0 | UL51:0 | UL40:0 MB/s", 
                                     anchor='e', font=('Arial', 8))
        self.speed_label.pack(side='right', padx=5)
        
        # Progress bar kecil untuk aktivitas
        self.activity_bar = ttk.Progressbar(status_frame, mode='indeterminate', length=60)
        self.activity_bar.pack(side='right', padx=5)
        
        self._update_status()
    
    def _bind_shortcuts(self):
        """Bind keyboard shortcuts"""
        self.root.bind('<Control-comma>', lambda e: self._open_settings())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<F5>', lambda e: self._refresh_all())
    
    def _open_settings(self):
        """Buka settings window"""
        try:
            SettingsWindow(self.root, self.config_mgr, on_settings_saved=self._on_settings_changed)
        except Exception as e:
            logger.error(f"Error opening settings window: {e}")
            messagebox.showerror("Error", f"Could not open settings window: {e}")
    
    def _save_settings(self):
        """Save settings"""
        if self.config_mgr.save():
            self.log_panel.add_message("Settings saved successfully", "INFO")
            messagebox.showinfo("Success", "Settings saved successfully")
        else:
            messagebox.showerror("Error", "Failed to save settings")
    
    def _load_settings(self):
        """Load settings"""
        self.config_mgr.load()
        self.log_panel.add_message("Settings loaded from file", "INFO")
        messagebox.showinfo("Success", "Settings loaded successfully")
    
    def _reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Confirm Reset", "Reset all settings to defaults?"):
            self.config_mgr.reset_to_defaults()
            self.log_panel.add_message("Settings reset to defaults", "WARNING")
            messagebox.showinfo("Success", "Settings reset to defaults")
    
    def _refresh_all(self):
        """Refresh semua panel"""
        if hasattr(self, 'download_panel'):
            self.download_panel._refresh_display()
        if hasattr(self, 'upload51_panel'):
            self.upload51_panel._refresh_display()
        if hasattr(self, 'upload40_panel'):
            self.upload40_panel._refresh_display()
        if hasattr(self, 'history_panel'):
            self.history_panel._refresh_display()
        self.log_panel.add_message("Manual refresh requested", "DEBUG")
    
    def _open_log_file(self):
        """Open log file"""
        if hasattr(self, 'log_panel'):
            self.log_panel._open_log_file()
    
    def _open_history_file(self):
        """Open history file"""
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            history_path = os.path.join(root_dir, 'copy_history.txt')
            if os.path.exists(history_path):
                os.startfile(history_path)
        except Exception as e:
            logger.error(f"Error opening history file: {e}")
    
    def _show_statistics(self):
        """Show statistics dialog"""
        if hasattr(self, 'history_panel'):
            self.history_panel._show_stats()
    
    def _update_status(self):
        """Update status bar dengan info download dan upload"""
        try:
            # Get stats
            download_stats = self.download_mgr.get_stats()
            upload_stats = self.upload_mgr.get_stats()
            queue_stats = self.queue_mgr.get_stats()
            
            # Update status icon
            if self.monitor.running:
                self.status_icon.config(text="🟢")
                status_text = "Monitoring"
            else:
                self.status_icon.config(text="🔴")
                status_text = "Stopped"
            
            # Get monitor stats
            monitor_stats = self.monitor.get_stats() if hasattr(self.monitor, 'get_stats') else {}
            folders = monitor_stats.get('folders_monitored', 0)
            
            self.status_var.set(f"{status_text} | Folders: {folders}")
            
            # Update speed - dengan error handling
            try:
                dl_speed = download_stats['workers']['total_speed_mbps']
            except:
                dl_speed = 0
                
            try:
                ul51_speed = upload_stats['workers_51']['total_speed_mbps']
            except:
                ul51_speed = 0
                
            try:
                ul40_speed = upload_stats['workers_40']['total_speed_mbps']
            except:
                ul40_speed = 0
            
            self.speed_label.config(
                text=f"DL:{dl_speed:.1f} | UL51:{ul51_speed:.1f} | UL40:{ul40_speed:.1f} MB/s"
            )
            
            # Update stats di panel
            if hasattr(self, 'dl_active_label'):
                try:
                    self.dl_active_label.config(text=f"Active: {download_stats['workers']['busy']}")
                    self.dl_waiting_label.config(text=f"Waiting: {queue_stats['waiting']}")
                    self.dl_total_label.config(text=f"Total: {queue_stats['total']}")
                except:
                    pass
            
            if hasattr(self, 'ul51_active_label'):
                try:
                    self.ul51_active_label.config(text=f"Active: {upload_stats['workers_51']['busy']}")
                    self.ul51_waiting_label.config(text=f"Waiting: {upload_stats['queue']['51']['waiting']}")
                    self.ul51_total_label.config(text=f"Max: {upload_stats['max_workers_51']}")
                except:
                    pass
            
            if hasattr(self, 'ul40_active_label'):
                try:
                    self.ul40_active_label.config(text=f"Active: {upload_stats['workers_40']['busy']}")
                    self.ul40_waiting_label.config(text=f"Waiting: {upload_stats['queue']['40']['waiting']}")
                    self.ul40_total_label.config(text=f"Max: {upload_stats['max_workers_40']}")
                except:
                    pass
            
            # Activity bar
            if download_stats['workers']['busy'] > 0 or upload_stats['workers_51']['busy'] > 0 or upload_stats['workers_40']['busy'] > 0:
                self.activity_bar.start(10)
            else:
                self.activity_bar.stop()
            
        except Exception as e:
            logger.debug(f"Non-critical error updating status: {e}")
            # Jangan sampai error ini mengganggu aplikasi
        
        # Schedule next update
        self.after_id = self.root.after(REFRESH_INTERVAL, self._update_status)
    
    def _on_settings_changed(self):
        """Handler saat settings berubah"""
        logger.info("Settings changed, updating components...")
        settings = self.config_mgr.get_settings()
        
        # Update monitor
        self.monitor.source_folders = settings.source_folders
        self.monitor.extensions = settings.extensions
        
        # Update download manager
        self.download_mgr.set_max_parallel(settings.max_download)
        
        # Update upload managers
        self.upload_mgr.set_max_workers_51(settings.max_upload_51)
        self.upload_mgr.set_max_workers_40(settings.max_upload_40)
        
        # Update upload controller cache
        self.upload_controller.on_settings_changed()
        
        self.log_panel.add_message("Settings applied", "INFO")
    
    def _show_about(self):
        """Show about dialog"""
        about_text = """
🎬 Watch Folder Hires 70
Pipeline Copy - Fase 2 (70 → 40 & 51)

Version: 2.0.0
Created: 2026

Fitur:
✅ Monitor folder 12 via SMB
✅ Download 12 → 70
✅ Upload 70 → 51 (HIRES) ⭐ HIGH PRIORITY
✅ Upload 70 → 40 (LOWRES) NORMAL PRIORITY
✅ Auto-delete from 70 after both uploads
✅ FIFO queue tanpa prioritas
✅ Resume capability (checkpoint 10%)
✅ Max parallel configurable
✅ Filter file extensions
✅ Real-time progress
✅ Auto-rename untuk file duplikat
✅ Copy history dengan detail destination
✅ Settings window terpisah

Untuk file video besar (20-60GB)
        """
        messagebox.showinfo("About", about_text)
    
    def on_closing(self):
        """Handler saat window ditutup"""
        logger.info("Closing application...")
        
        # Stop components
        self.monitor.stop()
        self.download_mgr.stop()
        self.upload_mgr.stop()
        
        # Cancel pending after events
        if self.after_id:
            self.root.after_cancel(self.after_id)
        
        # Save state
        self.state_mgr.save(self.queue_mgr.get_all_jobs())
        
        # Destroy window
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Run the application"""
        logger.info("Starting main loop")
        self.root.mainloop()


# Test sederhana
if __name__ == "__main__":
    print("MainWindow class ready with 3 panels in Queue tab")