# -*- coding: utf-8 -*-
"""
Progress panel untuk menampilkan progress download aktif
"""

import tkinter as tk
from tkinter import ttk
import logging  # <-- TAMBAHKAN INI
from typing import Optional, List
from ..models.file_job import FileJob
from ..core.download_manager import DownloadManager
from ..constants.settings import REFRESH_INTERVAL

logger = logging.getLogger(__name__)

class ProgressPanel(ttk.Frame):  # <-- UBAH dari LabelFrame ke Frame biasa
    """
    Panel untuk menampilkan progress download aktif
    """
    
    def __init__(self, parent, download_manager: DownloadManager):
        """
        Inisialisasi ProgressPanel
        
        Args:
            parent: Parent widget
            download_manager: DownloadManager instance
        """
        super().__init__(parent)
        
        self.download_manager = download_manager
        self.after_id = None
        self.progress_bars = {}  # Dictionary untuk menyimpan widget per job
        
        self._create_widgets()
        self._refresh_display()
    
    def _create_widgets(self):
        """Buat container untuk progress bars"""
        # Canvas dengan scrollbar untuk mengakomodasi banyak progress
        self.canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind mousewheel untuk scroll
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _on_mousewheel(self, event):
        """Handler untuk mousewheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _refresh_display(self):
        """Refresh tampilan progress"""
        # Dapatkan active downloads
        active_jobs = self.download_manager.get_active_downloads()
        # logger.debug(f"Refreshing progress panel: {len(active_jobs)} active jobs")
        
        active_names = [job.name for job in active_jobs]
        
        # Hapus progress bar untuk job yang sudah selesai
        to_remove = []
        for name, widgets in self.progress_bars.items():
            if name not in active_names:
                self._destroy_job_widgets(name)
                to_remove.append(name)
        
        for name in to_remove:
            del self.progress_bars[name]
        
        # Update atau buat progress bar untuk active jobs
        for job in active_jobs:
            if job.name in self.progress_bars:
                # Update yang sudah ada
                self._update_job_progress(job)
            else:
                # Buat yang baru
                self._create_job_progress(job)
        
        # Schedule refresh berikutnya
        self.after_id = self.after(REFRESH_INTERVAL, self._refresh_display)
    
    def _create_job_progress(self, job: FileJob):
        """
        Buat widget progress untuk job baru
        
        Args:
            job: FileJob object
        """
        # Frame untuk satu job
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(fill='x', pady=5, padx=5)
        
        # Header dengan filename
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill='x')
        
        name_label = ttk.Label(header_frame, text=f"🎬 {job.name}", font=('Arial', 9, 'bold'))
        name_label.pack(side='left')
        
        speed_label = ttk.Label(header_frame, text="", font=('Arial', 8))
        speed_label.pack(side='right', padx=5)
        
        # Progress bar
        progress_var = tk.DoubleVar(value=job.progress)
        progress_bar = ttk.Progressbar(
            frame, 
            variable=progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        progress_bar.pack(fill='x', pady=2)
        
        # Info frame (size, progress, eta)
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill='x')
        
        size_label = ttk.Label(info_frame, text="", font=('Arial', 8))
        size_label.pack(side='left')
        
        eta_label = ttk.Label(info_frame, text="", font=('Arial', 8))
        eta_label.pack(side='right')
        
        # Simpan semua widget
        self.progress_bars[job.name] = {
            'frame': frame,
            'progress_var': progress_var,
            'speed_label': speed_label,
            'size_label': size_label,
            'eta_label': eta_label
        }
        
        # Initial update
        self._update_job_progress(job)
    
    def _update_job_progress(self, job: FileJob):
        """
        Update widget progress untuk job
        
        Args:
            job: FileJob object
        """
        widgets = self.progress_bars.get(job.name)
        if not widgets:
            return
        
        # Update progress bar
        widgets['progress_var'].set(job.progress)
        
        # Update speed
        if job.speed_mbps > 0:
            widgets['speed_label'].config(text=f"{job.speed_mbps:.1f} MB/s")
        else:
            widgets['speed_label'].config(text="")
        
        # Update size info
        size_text = f"{job.copied_gb:.2f} GB / {job.size_gb:.2f} GB ({job.progress:.1f}%)"
        widgets['size_label'].config(text=size_text)
        
        # Update ETA
        if job.eta_seconds > 0:
            widgets['eta_label'].config(text=f"ETA: {job.eta_formatted}")
        else:
            widgets['eta_label'].config(text="")
    
    def _destroy_job_widgets(self, job_name: str):
        """
        Hapus widget untuk job yang selesai
        
        Args:
            job_name: Nama job
        """
        widgets = self.progress_bars.get(job_name)
        if widgets:
            widgets['frame'].destroy()
    
    def destroy(self):
        """Cleanup saat panel di-destroy"""
        if self.after_id:
            self.after_cancel(self.after_id)
        self.canvas.unbind_all("<MouseWheel>")
        super().destroy()