# -*- coding: utf-8 -*-
"""
Upload panel untuk menampilkan upload ke LOWRES (40) - PRIORITAS NORMAL
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from ..models.upload_job import UploadJob
from ..core.upload_manager import UploadManager
from ..constants.settings import REFRESH_INTERVAL

class UploadPanel40(ttk.Frame):
    """
    Panel untuk menampilkan upload ke server 40 (LOWRES) - PRIORITAS NORMAL
    """
    
    def __init__(self, parent, upload_manager: UploadManager):
        """
        Inisialisasi UploadPanel40
        
        Args:
            parent: Parent widget
            upload_manager: UploadManager instance
        """
        super().__init__(parent)
        
        self.upload_manager = upload_manager
        self.after_id = None
        self.progress_bars = {}  # Dictionary untuk menyimpan widget per job
        
        self._create_widgets()
        self._refresh_display()
    
    def _create_widgets(self):
        """Buat semua widget"""
        
        # Title dengan priority
        title_frame = ttk.Frame(self)
        title_frame.pack(fill='x', pady=(0, 5))
        
        title_label = ttk.Label(
            title_frame, 
            text="📤 UPLOAD TO LOWRES (40) - PRIORITAS NORMAL", 
            font=('Arial', 11, 'bold')
        )
        title_label.pack(side='left')
        
        # Stats
        self.stats_label = ttk.Label(title_frame, text="Active: 0 | Waiting: 0", font=('Arial', 9))
        self.stats_label.pack(side='right')
        
        # Queue table
        self._create_queue_table()
        
        # Progress bars dengan scroll
        self._create_scrollable_progress()
    
    def _create_queue_table(self):
        """Buat tabel queue dengan kolom speed"""
        table_frame = ttk.Frame(self)
        table_frame.pack(fill='x', pady=(0, 10))
        
        # ===== TAMBAH KOLOM SPEED =====
        columns = ('pos', 'filename', 'size', 'status', 'progress', 'speed', 'eta')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=3)
        
        # Define headings
        self.tree.heading('pos', text='#')
        self.tree.heading('filename', text='Filename')
        self.tree.heading('size', text='Size')
        self.tree.heading('status', text='Status')
        self.tree.heading('progress', text='Progress')
        self.tree.heading('speed', text='Speed')  # <-- KOLOM BARU
        self.tree.heading('eta', text='ETA')
        
        # Define columns
        self.tree.column('pos', width=40, anchor='center')
        self.tree.column('filename', width=250, anchor='w')
        self.tree.column('size', width=80, anchor='center')
        self.tree.column('status', width=100, anchor='center')
        self.tree.column('progress', width=70, anchor='center')
        self.tree.column('speed', width=80, anchor='center')  # <-- KOLOM BARU
        self.tree.column('eta', width=80, anchor='center')
        
        # Scrollbar untuk table
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack table
        self.tree.pack(side='left', fill='x', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def _create_scrollable_progress(self):
        """Buat area progress bar dengan scroll vertical"""
        progress_container = ttk.Frame(self)
        progress_container.pack(fill='both', expand=True, pady=(5, 0))
        
        # Canvas untuk scroll
        self.canvas = tk.Canvas(progress_container, highlightthickness=0, height=100)
        self.scrollbar = ttk.Scrollbar(progress_container, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind mousewheel untuk scroll
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Pack canvas dan scrollbar
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')
        
        # Bind resize untuk mengatur lebar
        self.canvas.bind('<Configure>', self._on_canvas_configure)
    
    def _on_canvas_configure(self, event):
        """Handler saat canvas diresize"""
        self.canvas.itemconfig(1, width=event.width)
    
    def _on_mousewheel(self, event):
        """Handler untuk mousewheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _refresh_display(self):
        """Refresh tampilan panel"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Dapatkan jobs dari upload manager
        active_jobs = self.upload_manager.get_active_uploads_40()
        waiting_jobs = self.upload_manager.get_waiting_uploads_40()
        
        # Update stats
        self.stats_label.config(text=f"Active: {len(active_jobs)} | Waiting: {len(waiting_jobs)}")
        
        # ===== INSERT ACTIVE JOBS =====
        for job in active_jobs:
            self._insert_queue_row(job, 'active')
        
        # ===== INSERT WAITING JOBS =====
        for i, job in enumerate(waiting_jobs, 1):
            self._insert_queue_row(job, 'waiting', i)
        
        # Update progress bars
        self._update_progress_bars(active_jobs)
        
        # Schedule refresh berikutnya
        self.after_id = self.after(REFRESH_INTERVAL, self._refresh_display)
    
    # ===== METHOD UNTUK INSERT QUEUE ROW =====
    def _insert_queue_row(self, job: UploadJob, status_type: str, position: int = 0):
        """
        Insert row ke queue table
        
        Args:
            job: UploadJob object
            status_type: 'active' atau 'waiting'
            position: Posisi dalam antrian (untuk waiting)
        """
        # Format size
        size_str = f"{job.size_gb:.1f} GB"
        
        # Format progress, speed, ETA
        if status_type == 'active':
            progress_str = f"{job.progress:.1f}%"
            # ===== TAMPILKAN SPEED =====
            speed_str = f"{job.speed_mbps:.1f} MB/s" if job.speed_mbps > 0 else "-"
            eta_str = job.eta_formatted
            status_text = "⬆️ ACTIVE"
            pos_display = "▶"
        else:
            progress_str = "-"
            speed_str = "-"
            eta_str = "-"
            status_text = "⏳ WAITING"
            pos_display = str(position)
        
        # Insert row ke treeview
        item_id = self.tree.insert('', 'end', values=(
            pos_display,
            job.file_name,
            size_str,
            status_text,
            progress_str,
            speed_str,  # <-- KOLOM SPEED
            eta_str
        ))
        
        # Warna untuk active jobs
        if status_type == 'active':
            self.tree.tag_configure('active', background='#e8f5e9')  # Hijau muda
            self.tree.item(item_id, tags=('active',))
    
    def _update_progress_bars(self, active_jobs: list):
        """Update progress bars untuk active jobs"""
        active_names = [job.file_name for job in active_jobs]
        
        # Hapus progress bar untuk job yang sudah selesai
        to_remove = []
        for name, widgets in self.progress_bars.items():
            if name not in active_names:
                widgets['frame'].destroy()
                to_remove.append(name)
        
        for name in to_remove:
            del self.progress_bars[name]
        
        # Update atau buat progress bar untuk active jobs
        for job in active_jobs:
            if job.file_name in self.progress_bars:
                self._update_job_progress(job)
            else:
                self._create_job_progress(job)
        
        # Jika tidak ada active jobs, tampilkan pesan
        if not active_jobs:
            self._show_no_active_message()
        else:
            self._hide_no_active_message()
    
    def _create_job_progress(self, job: UploadJob):
        """
        Buat widget progress untuk job baru
        """
        # Frame untuk satu job
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(fill='x', pady=2, padx=5)
        
        # Header dengan filename
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill='x')
        
        name_label = ttk.Label(
            header_frame, 
            text=f"🎬 {job.file_name}", 
            font=('Arial', 9, 'bold')
        )
        name_label.pack(side='left')
        
        # ===== SPEED LABEL DI HEADER =====
        speed_label = ttk.Label(header_frame, text="", font=('Arial', 8), foreground='#27ae60')
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
        
        eta_label = ttk.Label(info_frame, text="", font=('Arial', 8), foreground='#27ae60')
        eta_label.pack(side='right')
        
        # Simpan semua widget
        self.progress_bars[job.file_name] = {
            'frame': frame,
            'progress_var': progress_var,
            'speed_label': speed_label,  # <-- SIMPAN SPEED LABEL
            'size_label': size_label,
            'eta_label': eta_label
        }
        
        # Initial update
        self._update_job_progress(job)
    
    def _update_job_progress(self, job: UploadJob):
        """
        Update widget progress untuk job
        """
        widgets = self.progress_bars.get(job.file_name)
        if not widgets:
            return
        
        # Update progress bar
        widgets['progress_var'].set(job.progress)
        
        # ===== UPDATE SPEED DENGAN ICON =====
        if job.speed_mbps > 0:
            speed_text = f"{job.speed_mbps:.1f} MB/s"
            # Icon berdasarkan kecepatan
            if job.speed_mbps > 30:
                widgets['speed_label'].config(text=f"⚡ {speed_text}", foreground='#27ae60')  # Hijau (cepat)
            elif job.speed_mbps > 10:
                widgets['speed_label'].config(text=f"📊 {speed_text}", foreground='#2980b9')  # Biru (sedang)
            else:
                widgets['speed_label'].config(text=f"🐢 {speed_text}", foreground='#e67e22')  # Oranye (lambat)
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
    
    def _show_no_active_message(self):
        """Tampilkan pesan ketika tidak ada active uploads"""
        if hasattr(self, 'no_active_label'):
            return
        
        self.no_active_label = ttk.Label(
            self.scrollable_frame, 
            text="✨ Tidak ada upload ke LOWRES (40) saat ini",
            font=('Arial', 9, 'italic'),
            foreground='#666666'
        )
        self.no_active_label.pack(pady=10)
    
    def _hide_no_active_message(self):
        """Sembunyikan pesan no active"""
        if hasattr(self, 'no_active_label'):
            self.no_active_label.destroy()
            delattr(self, 'no_active_label')
    
    def destroy(self):
        """Cleanup saat panel di-destroy"""
        if self.after_id:
            self.after_cancel(self.after_id)
        # Unbind mousewheel
        self.canvas.unbind_all("<MouseWheel>")
        super().destroy()


# Test sederhana
if __name__ == "__main__":
    print("UploadPanel40 class ready with SPEED display (NORMAL PRIORITY)")