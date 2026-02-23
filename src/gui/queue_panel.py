# -*- coding: utf-8 -*-
"""
Queue panel untuk menampilkan antrian download
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from ..models.file_job import FileJob
from ..core.queue_manager import QueueManager
from ..constants.settings import REFRESH_INTERVAL

class QueuePanel(ttk.LabelFrame):
    """
    Panel untuk menampilkan antrian download
    """
    
    def __init__(self, parent, queue_manager: QueueManager):
        """
        Inisialisasi QueuePanel
        
        Args:
            parent: Parent widget
            queue_manager: QueueManager instance
        """
        super().__init__(parent, text="📋 Download Queue", padding=5)
        
        self.queue_manager = queue_manager
        self.after_id = None
        
        self._create_widgets()
        self._refresh_display()
    
    def _create_widgets(self):
        """Buat semua widget"""
        
        # Treeview untuk menampilkan queue
        columns = ('priority', 'filename', 'size', 'status', 'progress', 'eta')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', height=8)
        
        # Define headings
        self.tree.heading('priority', text='#')
        self.tree.heading('filename', text='Filename')
        self.tree.heading('size', text='Size')
        self.tree.heading('status', text='Status')
        self.tree.heading('progress', text='Progress')
        self.tree.heading('eta', text='ETA')
        
        # Define columns
        self.tree.column('priority', width=40, anchor='center')
        self.tree.column('filename', width=300, anchor='w')
        self.tree.column('size', width=80, anchor='center')
        self.tree.column('status', width=100, anchor='center')
        self.tree.column('progress', width=100, anchor='center')
        self.tree.column('eta', width=80, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Info bar
        info_frame = ttk.Frame(self)
        info_frame.pack(fill='x', pady=5)
        
        self.info_label = ttk.Label(info_frame, text="", font=('Arial', 9, 'italic'))
        self.info_label.pack(side='left')
        
        # Bind double-click untuk detail
        self.tree.bind('<Double-Button-1>', self._show_job_details)
    
    def _refresh_display(self):
        """Refresh tampilan queue"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get jobs dari queue manager
        waiting_jobs = self.queue_manager.get_waiting_jobs()
        active_jobs = self.queue_manager.get_active_jobs()
        
        # Hitung statistik
        total_waiting = len(waiting_jobs)
        total_active = len(active_jobs)
        total_size = sum(job.size_gb for job in waiting_jobs + active_jobs)
        
        # Update info label
        self.info_label.config(
            text=f"📊 Active: {total_active} | Waiting: {total_waiting} | Total: {total_size:.1f} GB"
        )
        
        # Tampilkan active jobs dulu (dengan warna hijau)
        for job in active_jobs:
            self._insert_job_row(job, 'active')
        
        # Tampilkan waiting jobs
        for job in waiting_jobs:
            self._insert_job_row(job, 'waiting')
        
        # Schedule refresh berikutnya
        self.after_id = self.after(REFRESH_INTERVAL, self._refresh_display)
    
    def _insert_job_row(self, job: FileJob, status_type: str):
        """
        Insert satu row ke treeview
        
        Args:
            job: FileJob object
            status_type: 'active' atau 'waiting'
        """
        # Format size
        size_str = f"{job.size_gb:.1f} GB"
        
        # Format progress
        if status_type == 'active':
            progress_str = f"{job.progress:.1f}%"
            eta_str = job.eta_formatted
        else:
            progress_str = "-"
            eta_str = "-"
        
        # Status text
        status_text = "⬇️ Downloading" if status_type == 'active' else "⏳ Waiting"
        
        # Priority/position
        if status_type == 'active':
            priority = "▶"
        else:
            pos = job.queue_position or 0
            priority = str(pos)
        
        # Insert row
        item_id = self.tree.insert('', 'end', values=(
            priority,
            job.name,
            size_str,
            status_text,
            progress_str,
            eta_str
        ))
        
        # Warna untuk active jobs
        if status_type == 'active':
            self.tree.tag_configure('active', background='#e8f5e9')  # Hijau muda
            self.tree.item(item_id, tags=('active',))
    
    def _show_job_details(self, event):
        """Show detail job saat double-click"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item, 'values')
        if not values:
            return
        
        filename = values[1]  # Kolom filename
        
        # Cari job
        job = self.queue_manager.get_job(filename)
        if not job:
            return
        
        # Show detail dialog
        self._show_detail_dialog(job)
    
    def _show_detail_dialog(self, job: FileJob):
        """
        Tampilkan dialog detail job
        
        Args:
            job: FileJob object
        """
        dialog = tk.Toplevel(self)
        dialog.title(f"Job Details: {job.name}")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        # Frame untuk details
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill='both', expand=True)
        
        # Details
        details = [
            ("Filename:", job.name),
            ("Source:", job.source_path),
            ("Destination:", job.dest_path),
            ("Size:", f"{job.size_gb:.2f} GB ({job.size_bytes} bytes)"),
            ("Status:", job.status),
            ("Progress:", f"{job.progress:.1f}%"),
            ("Copied:", f"{job.copied_gb:.2f} GB"),
            ("Speed:", f"{job.speed_mbps:.2f} MB/s" if job.speed_mbps > 0 else "-"),
            ("ETA:", job.eta_formatted),
            ("Retry:", f"{job.retry_count}/{job.max_retry}"),
            ("Detected:", job.detected_time.strftime("%Y-%m-%d %H:%M:%S") if job.detected_time else "-"),
            ("Started:", job.start_time.strftime("%Y-%m-%d %H:%M:%S") if job.start_time else "-"),
            ("Last Error:", job.last_error or "-")
        ]
        
        for i, (label, value) in enumerate(details):
            ttk.Label(main_frame, text=label, font=('Arial', 9, 'bold')).grid(row=i, column=0, sticky='w', pady=2)
            ttk.Label(main_frame, text=str(value), font=('Arial', 9)).grid(row=i, column=1, sticky='w', pady=2, padx=5)
        
        # Close button
        ttk.Button(main_frame, text="Close", command=dialog.destroy).grid(row=len(details), column=0, columnspan=2, pady=10)
    
    def destroy(self):
        """Cleanup saat panel di-destroy"""
        if self.after_id:
            self.after_cancel(self.after_id)
        super().destroy()


# Test sederhana
if __name__ == "__main__":
    from ..utils.logger import setup_logging
    setup_logging()
    
    print("QueuePanel class ready")