# -*- coding: utf-8 -*-
"""
History panel untuk menampilkan riwayat file yang sudah diproses
"""

import tkinter as tk
from tkinter import ttk
import os
from ..utils.history import HistoryLogger
from ..constants.settings import REFRESH_INTERVAL

class HistoryPanel(ttk.LabelFrame):
    """
    Panel untuk menampilkan history file yang sudah dicopy/dihapus
    """
    
    def __init__(self, parent, history_logger):
        """
        Inisialisasi HistoryPanel
        
        Args:
            parent: Parent widget
            history_logger: HistoryLogger instance
        """
        super().__init__(parent, text="📜 Copy History", padding=5)
        
        self.history_logger = history_logger
        self.after_id = None
        
        self._create_widgets()
        self._refresh_display()
    
    def _create_widgets(self):
        """Buat semua widget"""
        
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill='x', pady=(0, 5))
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self._refresh_display, width=10).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📂 Open File", command=self._open_history_file, width=10).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📊 Stats", command=self._show_stats, width=8).pack(side='left', padx=2)
        
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(toolbar, textvariable=self.filter_var, 
                                    values=["All", "Success", "Failed"], width=10)
        filter_combo.pack(side='right', padx=2)
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_display())
        
        # Treeview untuk history
        columns = ('timestamp', 'filename', 'size', 'status', 'duration', 'retry')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', height=10)
        
        # Define headings
        self.tree.heading('timestamp', text='Timestamp')
        self.tree.heading('filename', text='Filename')
        self.tree.heading('size', text='Size')
        self.tree.heading('status', text='Status')
        self.tree.heading('duration', text='Duration')
        self.tree.heading('retry', text='Retry')
        
        # Define columns
        self.tree.column('timestamp', width=140, anchor='center')
        self.tree.column('filename', width=300, anchor='w')
        self.tree.column('size', width=80, anchor='center')
        self.tree.column('status', width=80, anchor='center')
        self.tree.column('duration', width=70, anchor='center')
        self.tree.column('retry', width=50, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Status bar
        self.status_label = ttk.Label(self, text="", font=('Arial', 8, 'italic'))
        self.status_label.pack(fill='x', pady=5)
    
    def _refresh_display(self):
        """Refresh tampilan history"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Baca history dari file
        try:
            entries = self._parse_history_file()
            
            # Filter berdasarkan status
            filter_by = self.filter_var.get()
            if filter_by != "All":
                entries = [e for e in entries if e['status'] == filter_by.upper()]
            
            # Insert entries
            for entry in entries[-100:]:  # Last 100 entries
                self.tree.insert('', 'end', values=(
                    entry['timestamp'],
                    entry['filename'],
                    entry['size'],
                    entry['status'],
                    entry['duration'],
                    entry['retry']
                ))
            
            # Update status
            total = len(entries)
            success = len([e for e in entries if e['status'] == 'SUCCESS'])
            failed = len([e for e in entries if e['status'] == 'FAILED'])
            total_gb = sum([self._parse_size(e['size']) for e in entries if e['status'] == 'SUCCESS'])
            
            self.status_label.config(
                text=f"Total: {total} files | Success: {success} | Failed: {failed} | Total copied: {total_gb:.2f} GB"
            )
            
        except Exception as e:
            self.status_label.config(text=f"Error loading history: {e}")
        
        # Refresh lagi nanti
        self.after_id = self.after(REFRESH_INTERVAL * 5, self._refresh_display)
    
    def _parse_history_file(self) -> list:
        """
        Parse file history
        
        Returns:
            List of history entries
        """
        entries = []
        
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            history_path = os.path.join(root_dir, 'copy_history.txt')
            
            if not os.path.exists(history_path):
                return []
            
            with open(history_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Skip header (first 5 lines)
            for line in lines[5:]:
                line = line.strip()
                if not line:
                    continue
                
                # Parse line format:
                # 2026-02-23 21:36:31  test 1.mxf                             1.84 GB SUCCESS    00:45:41   1
                parts = line.split()
                if len(parts) >= 7:
                    timestamp = f"{parts[0]} {parts[1]}"
                    
                    # Filename bisa mengandung spasi, ambil sisanya sampai ketemu size
                    idx = 2
                    filename_parts = []
                    while idx < len(parts) and not parts[idx].replace('.','').isdigit():
                        filename_parts.append(parts[idx])
                        idx += 1
                    filename = ' '.join(filename_parts)
                    
                    size = f"{parts[idx]} {parts[idx+1]}" if idx+1 < len(parts) else "-"
                    status = parts[idx+2] if idx+2 < len(parts) else "-"
                    duration = parts[idx+3] if idx+3 < len(parts) else "-"
                    retry = parts[idx+4] if idx+4 < len(parts) else "-"
                    
                    entries.append({
                        'timestamp': timestamp,
                        'filename': filename,
                        'size': size,
                        'status': status,
                        'duration': duration,
                        'retry': retry
                    })
            
            return entries[::-1]  # Balik urutan (terbaru di atas)
            
        except Exception as e:
            print(f"Error parsing history: {e}")
            return []
    
    def _parse_size(self, size_str: str) -> float:
        """Parse size string to GB"""
        try:
            parts = size_str.split()
            if len(parts) == 2:
                return float(parts[0])
            return 0
        except:
            return 0
    
    def _open_history_file(self):
        """Buka file history dengan default editor"""
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            history_path = os.path.join(root_dir, 'copy_history.txt')
            
            if os.path.exists(history_path):
                if os.name == 'nt':  # Windows
                    os.startfile(history_path)
                else:
                    import subprocess
                    subprocess.call(['xdg-open', history_path])
        except Exception as e:
            print(f"Error opening history file: {e}")
    
    def _show_stats(self):
        """Tampilkan statistik dalam dialog"""
        stats = self.history_logger.get_stats()
        
        dialog = tk.Toplevel(self)
        dialog.title("History Statistics")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill='both', expand=True)
        
        ttk.Label(main_frame, text="📊 COPY STATISTICS", font=('Arial', 12, 'bold')).pack(pady=10)
        
        stats_text = f"""
Total Files: {stats['total_files']}
Success: {stats['success_count']}
Failed: {stats['failed_count']}
Total Size: {stats['total_size_gb']:.2f} GB
Total Duration: {stats['total_duration_seconds']/3600:.2f} hours
        """
        
        ttk.Label(main_frame, text=stats_text, font=('Arial', 10)).pack(pady=10)
        
        ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=10)
    
    def destroy(self):
        """Cleanup saat panel di-destroy"""
        if self.after_id:
            self.after_cancel(self.after_id)
        super().destroy()