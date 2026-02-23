# -*- coding: utf-8 -*-
"""
Main window aplikasi watch_folder_hires_70
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from ..utils.logger import get_logger
from ..utils.config_manager import ConfigManager
from ..utils.state_manager import StateManager
from ..utils.history import HistoryLogger
from ..core.queue_manager import QueueManager
from ..core.download_manager import DownloadManager
from ..core.file_monitor import FileMonitor
from ..gui.queue_panel import QueuePanel
from ..gui.progress_panel import ProgressPanel
from ..gui.log_panel import LogPanel
from ..gui.settings_window import SettingsWindow
from ..constants.settings import REFRESH_INTERVAL

logger = get_logger(__name__)

class MainWindow:
    """
    Main window aplikasi
    """
    
    def __init__(self, root, config_mgr: ConfigManager, state_mgr: StateManager,
                 queue_mgr: QueueManager, download_mgr: DownloadManager,
                 monitor: FileMonitor):
        """
        Inisialisasi MainWindow
        
        Args:
            root: Tk root window
            config_mgr: ConfigManager instance
            state_mgr: StateManager instance
            queue_mgr: QueueManager instance
            download_mgr: DownloadManager instance
            monitor: FileMonitor instance
        """
        self.root = root
        self.config_mgr = config_mgr
        self.state_mgr = state_mgr
        self.queue_mgr = queue_mgr
        self.download_mgr = download_mgr
        self.monitor = monitor
        self.history_logger = HistoryLogger()  # Tambahkan history logger
        
        # Window properties
        self.root.title("🎬 Watch Folder Hires 70 - Pipeline Copy (Fase 1: 12→70)")
        self.root.geometry("1300x800")
        self.root.minsize(1100, 600)
        
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
        
        logger.info("Main window initialized")
    
    def _create_menu(self):
        """Buat menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self._open_settings, accelerator="Ctrl+,")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Open Settings", command=self._open_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Save Settings", command=self._save_settings)
        settings_menu.add_command(label="Load Settings", command=self._load_settings)
        settings_menu.add_command(label="Reset to Defaults", command=self._reset_settings)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh All", command=self._refresh_all, accelerator="F5")
        view_menu.add_separator()
        view_menu.add_command(label="Clear Log", command=self._clear_log)
        view_menu.add_command(label="Clear History", command=self._clear_history)
        
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
        """Buat semua widget utama"""
        
        # Main container
        main_container = ttk.Frame(self.root, padding=5)
        main_container.pack(fill='both', expand=True)
        
        # Notebook untuk panels
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill='both', expand=True, pady=5)
        
        # Queue panel (Tab 1)
        queue_frame = ttk.Frame(notebook)
        notebook.add(queue_frame, text="📋 Queue")
        self.queue_panel = QueuePanel(queue_frame, self.queue_mgr)
        self.queue_panel.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Progress panel (Tab 2)
        progress_frame = ttk.Frame(notebook)
        notebook.add(progress_frame, text="⬇️ Active Downloads")
        self.progress_panel = ProgressPanel(progress_frame, self.download_mgr)
        self.progress_panel.pack(fill='both', expand=True, padx=5, pady=5)
        
        # History panel (Tab 3 - BARU!)
        try:
            from ..gui.history_panel import HistoryPanel
            history_frame = ttk.Frame(notebook)
            notebook.add(history_frame, text="📜 History")
            self.history_panel = HistoryPanel(history_frame, self.history_logger)
            self.history_panel.pack(fill='both', expand=True, padx=5, pady=5)
        except Exception as e:
            logger.error(f"Could not load HistoryPanel: {e}")
            # Buat placeholder jika gagal
            history_frame = ttk.Frame(notebook)
            notebook.add(history_frame, text="📜 History")
            ttk.Label(history_frame, text=f"History panel failed to load: {e}").pack(pady=20)
        
        # Log panel (Tab 4)
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="📝 Activity Log")
        self.log_panel = LogPanel(log_frame)
        self.log_panel.pack(fill='both', expand=True, padx=5, pady=5)
    
    def _create_statusbar(self):
        """Buat status bar"""
        status_frame = ttk.Frame(self.root, relief='sunken', padding=2)
        status_frame.pack(side='bottom', fill='x')
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor='w', width=30)
        status_label.pack(side='left', padx=5)
        
        stats_label = ttk.Label(status_frame, textvariable=self.stats_var, anchor='e')
        stats_label.pack(side='right', padx=5)
        
        # Progress bar kecil untuk aktivitas
        self.activity_bar = ttk.Progressbar(status_frame, mode='indeterminate', length=100)
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
        if hasattr(self, 'queue_panel'):
            self.queue_panel._refresh_display()
        if hasattr(self, 'progress_panel'):
            self.progress_panel._refresh_display()
        if hasattr(self, 'history_panel'):
            self.history_panel._refresh_display()
        self.log_panel.add_message("Manual refresh requested", "DEBUG")
    
    def _clear_log(self):
        """Clear log panel"""
        if hasattr(self, 'log_panel'):
            self.log_panel._clear_log()
    
    def _clear_history(self):
        """Clear history display (not the file)"""
        if hasattr(self, 'history_panel'):
            if messagebox.askyesno("Confirm", "Clear history display? (File will not be deleted)"):
                # History panel clear functionality
                pass
    
    def _open_log_file(self):
        """Open log file"""
        if hasattr(self, 'log_panel'):
            self.log_panel._open_log_file()
    
    def _open_history_file(self):
        """Open history file"""
        try:
            import os
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
        """Update status bar"""
        try:
            # Get stats
            download_stats = self.download_mgr.get_stats()
            
            # Update status
            if self.monitor.running:
                status = "🟢 Monitoring"
            else:
                status = "🔴 Monitoring stopped"
            
            self.status_var.set(status)
            
            # Update stats
            stats = f"Active: {download_stats['workers']['busy']}/{download_stats['max_parallel']} | "
            stats += f"Queue: {download_stats['queue']['waiting']} | "
            stats += f"Speed: {download_stats['workers']['total_speed_mbps']:.1f} MB/s"
            self.stats_var.set(stats)
            
            # Activity bar
            if download_stats['workers']['busy'] > 0:
                self.activity_bar.start(10)
            else:
                self.activity_bar.stop()
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
        
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
        
        self.log_panel.add_message("Settings applied", "INFO")
    
    def _show_about(self):
        """Show about dialog"""
        about_text = """
🎬 Watch Folder Hires 70
Pipeline Copy - Fase 1 (12 → 70)

Version: 1.0.0
Created: 2026

Fitur:
✅ Monitor folder 12 via SMB
✅ FIFO queue tanpa prioritas
✅ Resume capability (checkpoint 10%)
✅ Max parallel download configurable
✅ Filter file extensions
✅ Real-time progress
✅ Copy history dengan detail
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
    print("MainWindow class ready with History Panel")