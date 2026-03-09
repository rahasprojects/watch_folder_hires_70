# -*- coding: utf-8 -*-
"""
History panel untuk menampilkan riwayat file yang sudah diproses
Dengan layout 2 kolom: kiri untuk history, kanan untuk stats + storage
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
import time
import re
import shutil
from datetime import datetime
from ..utils.history import HistoryLogger
from ..constants.settings import REFRESH_INTERVAL

logger = logging.getLogger(__name__)

class HistoryPanel(ttk.Frame):
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
        super().__init__(parent)
        
        self.history_logger = history_logger
        self.after_id = None
        self.last_clear_time = time.time()
        self.all_entries = []
        self.filtered_entries = []
        
        # Path untuk disk usage
        self.dest_70_path = r"D:/Test watch folder/destination 70"
        self.dest_51_path = r"D:/Test watch folder/destionation 51"
        self.dest_40_path = r"D:/Test watch folder/destination 40"
        
        self._create_widgets()
        self._refresh_display()
    
    def _get_disk_usage(self, path):
        """Mendapatkan info disk usage dalam GB"""
        try:
            total, used, free = shutil.disk_usage(path)
            return {
                'total': total / (1024**3),
                'used': used / (1024**3),
                'free': free / (1024**3),
                'percent': (used / total) * 100
            }
        except:
            return None
    
    def _create_widgets(self):
        """Buat semua widget dengan layout 2 kolom"""
        
        # Main container dengan 2 kolom
        main_container = ttk.Frame(self)
        main_container.pack(fill='both', expand=True)
        
        # Configure grid untuk 2 kolom (70% - 30%)
        main_container.grid_columnconfigure(0, weight=7)  # Kolom kiri 70%
        main_container.grid_columnconfigure(1, weight=3)  # Kolom kanan 30%
        main_container.grid_rowconfigure(0, weight=1)
        
        # ===== KOLOM KIRI: HISTORY TABLE =====
        left_frame = ttk.Frame(main_container)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Toolbar
        toolbar = ttk.Frame(left_frame)
        toolbar.pack(fill='x', pady=(0, 5))
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self._refresh_display, width=10).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🧹 Clear Display", command=self._clear_display, width=12).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📂 Open File", command=self._open_history_file, width=10).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📊 Stats", command=self._show_stats, width=8).pack(side='left', padx=2)
        
        # Filter Status
        ttk.Label(toolbar, text="Status:").pack(side='left', padx=(10, 2))
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(toolbar, textvariable=self.filter_var, 
                                    values=["All", "SUCCESS", "FAILED"], width=8, state='readonly')
        filter_combo.pack(side='left', padx=2)
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_display())
        
        # Filter Destination
        ttk.Label(toolbar, text="Dest:").pack(side='left', padx=(10, 2))
        self.dest_filter_var = tk.StringVar(value="All")
        dest_filter_combo = ttk.Combobox(toolbar, textvariable=self.dest_filter_var,
                                        values=["All", "70", "51", "40"], width=5, state='readonly')
        dest_filter_combo.pack(side='left', padx=2)
        dest_filter_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_display())
        
        # Info clear
        self.clear_info_label = ttk.Label(toolbar, text="", font=('Arial', 8, 'italic'))
        self.clear_info_label.pack(side='right', padx=5)
        
        # Treeview untuk history
        columns = ('timestamp', 'filename', 'size', 'status', 'duration', 'retry', 'dest')
        self.tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.tree.heading('timestamp', text='Timestamp')
        self.tree.heading('filename', text='Filename')
        self.tree.heading('size', text='Size')
        self.tree.heading('status', text='Status')
        self.tree.heading('duration', text='Duration')
        self.tree.heading('retry', text='Retry')
        self.tree.heading('dest', text='Dest')
        
        # Define columns
        self.tree.column('timestamp', width=140, anchor='center')
        self.tree.column('filename', width=300, anchor='w')
        self.tree.column('size', width=80, anchor='center')
        self.tree.column('status', width=80, anchor='center')
        self.tree.column('duration', width=70, anchor='center')
        self.tree.column('retry', width=50, anchor='center')
        self.tree.column('dest', width=50, anchor='center')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Configure tags untuk warna baris
        self.tree.tag_configure('success_row', foreground='#27ae60')  # Hijau
        self.tree.tag_configure('failed_row', foreground='#c0392b')   # Merah
        
        # ===== KOLOM KANAN: STATS + STORAGE =====
        right_frame = ttk.Frame(main_container)
        right_frame.grid(row=0, column=1, sticky='nsew')
        
        # Frame untuk STATISTICS
        stats_frame = ttk.LabelFrame(right_frame, text="📊 STATISTICS", padding=10)
        stats_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        self.stats_text = tk.Text(stats_frame, wrap='word', height=12, width=30,
                                  font=('Consolas', 9, 'bold'), bd=0, bg='#f5f5f5')
        self.stats_text.pack(fill='both', expand=True)
        self.stats_text.config(state='disabled')
        
        # Frame untuk STORAGE INFORMATION
        storage_frame = ttk.LabelFrame(right_frame, text="💾 STORAGE INFORMATION", padding=10)
        storage_frame.pack(fill='both', expand=True, pady=(5, 0))
        
        self.storage_text = tk.Text(storage_frame, wrap='word', height=12, width=30,
                                    font=('Consolas', 9), bd=0, bg='#f5f5f5')
        self.storage_text.pack(fill='both', expand=True)
        self.storage_text.config(state='disabled')
    
    def _refresh_display(self):
        """Refresh tampilan history"""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Baca history dari file
        self.all_entries = self._parse_history_file()
        
        # Filter berdasarkan status
        filter_by = self.filter_var.get()
        if filter_by != "All":
            self.filtered_entries = [e for e in self.all_entries if e['status'] == filter_by]
        else:
            self.filtered_entries = self.all_entries.copy()
        
        # Filter berdasarkan destination
        dest_filter = self.dest_filter_var.get()
        if dest_filter != "All":
            self.filtered_entries = [e for e in self.filtered_entries if e.get('dest', '') == dest_filter]
        
        # Filter berdasarkan waktu (hanya yang setelah last_clear_time)
        display_entries = []
        for entry in self.filtered_entries:
            try:
                entry_time = datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S").timestamp()
                if entry_time > self.last_clear_time:
                    display_entries.append(entry)
            except:
                display_entries.append(entry)
        
        # Insert entries ke treeview dengan warna sesuai status
        for entry in display_entries[-100:]:
            # Tentukan tag berdasarkan status
            if entry['status'] == 'SUCCESS':
                tags = ('success_row',)
            elif entry['status'] == 'FAILED':
                tags = ('failed_row',)
            else:
                tags = ()
            
            self.tree.insert('', 'end', values=(
                entry['timestamp'],
                entry['filename'],
                entry['size'],
                entry['status'],
                entry['duration'],
                entry['retry'],
                entry.get('dest', '-')
            ), tags=tags)
        
        # Update stats display
        self._update_stats_display()
        
        # Update storage display
        self._update_storage_display()
        
        # Update info clear
        if self.last_clear_time > 0:
            clear_time_str = datetime.fromtimestamp(self.last_clear_time).strftime("%Y-%m-%d %H:%M:%S")
            self.clear_info_label.config(text=f"Clear sejak: {clear_time_str}")
        else:
            self.clear_info_label.config(text="")
        
        # Refresh lagi nanti
        self.after_id = self.after(REFRESH_INTERVAL * 5, self._refresh_display)
    
    def _update_stats_display(self):
        """Update panel statistik dengan format vertikal"""
        # Hitung statistik
        total = len(self.all_entries)
        displayed = len([e for e in self.filtered_entries 
                        if self._is_after_clear(e)])
        
        success = len([e for e in self.all_entries if e['status'] == 'SUCCESS'])
        failed = len([e for e in self.all_entries if e['status'] == 'FAILED'])
        
        to_70 = len([e for e in self.all_entries if e.get('dest') == '70'])
        to_51 = len([e for e in self.all_entries if e.get('dest') == '51'])
        to_40 = len([e for e in self.all_entries if e.get('dest') == '40'])
        
        total_gb = sum(self._parse_size(e['size']) for e in self.all_entries if e['status'] == 'SUCCESS')
        
        # Format teks vertikal
        stats_text = f"""
Total: {total} files

Displayed: {displayed}

Server 70: {to_70}
Server 51: {to_51}
Server 40: {to_40}

Success: {success}
Failed: {failed}

Total: {total_gb:.2f} GB
        """
        
        # Update text widget
        self.stats_text.config(state='normal')
        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert('1.0', stats_text)
        self.stats_text.config(state='disabled')
    
    def _update_storage_display(self):
        """Update panel storage information"""
        storage_text = "💾 DISK USAGE\n\n"
        
        # Download 70
        usage = self._get_disk_usage(self.dest_70_path)
        if usage:
            storage_text += f"📥 DOWNLOAD 70:\n"
            storage_text += f"  Used: {usage['used']:.1f}/{usage['total']:.0f} GB ({usage['percent']:.0f}%)\n"
            storage_text += f"  Free: {usage['free']:.1f} GB\n\n"
        else:
            storage_text += f"📥 DOWNLOAD 70:\n  (tidak tersedia)\n\n"
        
        # Upload 51
        usage = self._get_disk_usage(self.dest_51_path)
        if usage:
            storage_text += f"📤 UPLOAD 51:\n"
            storage_text += f"  Used: {usage['used']:.1f}/{usage['total']:.0f} GB ({usage['percent']:.0f}%)\n"
            storage_text += f"  Free: {usage['free']:.1f} GB\n\n"
        else:
            storage_text += f"📤 UPLOAD 51:\n  (tidak tersedia)\n\n"
        
        # Upload 40
        usage = self._get_disk_usage(self.dest_40_path)
        if usage:
            warning = " ⚠️" if usage['percent'] > 80 else ""
            storage_text += f"📤 UPLOAD 40:\n"
            storage_text += f"  Used: {usage['used']:.1f}/{usage['total']:.0f} GB ({usage['percent']:.0f}%){warning}\n"
            storage_text += f"  Free: {usage['free']:.1f} GB\n"
        else:
            storage_text += f"📤 UPLOAD 40:\n  (tidak tersedia)\n"
        
        # Update text widget
        self.storage_text.config(state='normal')
        self.storage_text.delete('1.0', tk.END)
        self.storage_text.insert('1.0', storage_text)
        self.storage_text.config(state='disabled')
    
    def _is_after_clear(self, entry):
        """Cek apakah entry setelah last_clear_time"""
        try:
            entry_time = datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S").timestamp()
            return entry_time > self.last_clear_time
        except:
            return True
    
    def _parse_history_file(self) -> list:
        """Parse file history (sama seperti sebelumnya)"""
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
                
                parts = line.split()
                
                # Format dengan destination
                if len(parts) >= 8:
                    timestamp = f"{parts[0]} {parts[1]}"
                    
                    idx = 2
                    filename_parts = []
                    while idx < len(parts) and not parts[idx].replace('.','').replace('(','').replace(')','').replace(',','').isdigit():
                        filename_parts.append(parts[idx])
                        idx += 1
                    filename = ' '.join(filename_parts)
                    
                    size = f"{parts[idx]} {parts[idx+1]}" if idx+1 < len(parts) else "-"
                    status = parts[idx+2] if idx+2 < len(parts) else "-"
                    duration = parts[idx+3] if idx+3 < len(parts) else "-"
                    retry = parts[idx+4] if idx+4 < len(parts) else "-"
                    dest = parts[idx+5] if idx+5 < len(parts) else "70"
                    
                    entries.append({
                        'timestamp': timestamp,
                        'filename': filename,
                        'size': size,
                        'status': status,
                        'duration': duration,
                        'retry': retry,
                        'dest': dest
                    })
                elif len(parts) >= 7:
                    # Format lama tanpa destination
                    timestamp = f"{parts[0]} {parts[1]}"
                    
                    idx = 2
                    filename_parts = []
                    while idx < len(parts) and not parts[idx].replace('.','').replace('(','').replace(')','').replace(',','').isdigit():
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
                        'retry': retry,
                        'dest': '70'
                    })
            
            return entries[::-1]  # Balik urutan
            
        except Exception as e:
            print(f"Error parsing history: {e}")
            return []
    
    def _parse_size(self, size_str: str) -> float:
        """Parse size string to GB"""
        try:
            parts = size_str.split()
            if len(parts) >= 1:
                return float(parts[0])
            return 0
        except:
            return 0
    
    def _clear_display(self):
        """Clear tampilan history"""
        self.last_clear_time = time.time()
        self._refresh_display()
        
        from ..utils.logger import get_logger
        log = get_logger(__name__)
        log.info("History display cleared")
    
    def _open_history_file(self):
        """Buka file history"""
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            history_path = os.path.join(root_dir, 'copy_history.txt')
            
            if os.path.exists(history_path):
                if os.name == 'nt':  # Windows
                    os.startfile(history_path)
                else:
                    import subprocess
                    subprocess.call(['xdg-open', history_path])
            else:
                messagebox.showinfo("Info", "History file not found yet")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening history file: {e}")
    
    def _show_stats(self):
        """Tampilkan statistik detail dalam dialog"""
        stats = self.history_logger.get_stats()
        
        dialog = tk.Toplevel(self)
        dialog.title("History Statistics")
        dialog.geometry("450x400")
        dialog.transient(self)
        dialog.grab_set()
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill='both', expand=True)
        
        ttk.Label(main_frame, text="📊 COPY STATISTICS", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Global stats
        global_frame = ttk.LabelFrame(main_frame, text="Global", padding=5)
        global_frame.pack(fill='x', pady=5)
        
        ttk.Label(global_frame, 
                 text=f"Total Files: {stats['total_files']}\n"
                      f"Success: {stats['success_count']}\n"
                      f"Failed: {stats['failed_count']}\n"
                      f"Total Size: {stats['total_size_gb']:.2f} GB\n"
                      f"Total Duration: {stats['total_duration_seconds']/3600:.2f} hours",
                 font=('Arial', 10)).pack(anchor='w', padx=10, pady=5)
        
        # Per destination stats
        dest_frame = ttk.LabelFrame(main_frame, text="Per Destination", padding=5)
        dest_frame.pack(fill='x', pady=5)
        
        dest_stats = stats.get('by_destination', {})
        
        text = ""
        for dest in ['70', '51', '40']:
            if dest in dest_stats:
                d = dest_stats[dest]
                text += f"Destination {dest}:\n"
                text += f"  Success: {d['success']}, Failed: {d['failed']}\n"
                text += f"  Size: {d['size']:.2f} GB\n\n"
        
        ttk.Label(dest_frame, text=text, font=('Arial', 10)).pack(anchor='w', padx=10, pady=5)
        
        ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=10)
    
    def destroy(self):
        """Cleanup saat panel di-destroy"""
        if self.after_id:
            self.after_cancel(self.after_id)
        super().destroy()