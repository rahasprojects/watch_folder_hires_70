# -*- coding: utf-8 -*-
"""
Log panel untuk menampilkan activity log
"""

import tkinter as tk
from tkinter import ttk
import logging
import os
import time
import re
from datetime import datetime
from ..utils.logger import get_logger
from ..constants.settings import REFRESH_INTERVAL, LOG_FILE

logger = get_logger(__name__)

class LogPanel(ttk.LabelFrame):
    """
    Panel untuk menampilkan activity log
    """
    
    def __init__(self, parent):
        """
        Inisialisasi LogPanel
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent, text="📝 Activity Log", padding=5)
        
        self.after_id = None
        self.log_lines = []
        self.max_lines = 1000  # Maksimal baris yang ditampilkan
        self.auto_scroll = True
        self.last_clear_time = time.time()  # <-- INI KUNCINYA!
        
        self._create_widgets()
        self._refresh_display()
    
    def _create_widgets(self):
        """Buat semua widget"""
        
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill='x', pady=(0, 5))
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self._force_refresh, width=10).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🧹 Clear", command=self._clear_log, width=8).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📂 Open Log File", command=self._open_log_file, width=12).pack(side='left', padx=2)
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Auto-scroll", variable=self.auto_scroll_var).pack(side='left', padx=10)
        
        # Info kapan terakhir clear
        self.clear_info_label = ttk.Label(toolbar, text="", font=('Arial', 8, 'italic'))
        self.clear_info_label.pack(side='right', padx=5)
        
        self.status_label = ttk.Label(toolbar, text="", font=('Arial', 8))
        self.status_label.pack(side='right', padx=5)
        
        # Frame untuk text dan scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill='both', expand=True)
        
        # Text widget untuk menampilkan log
        self.text_widget = tk.Text(
            text_frame,
            wrap='word',
            height=12,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            insertbackground='white'
        )
        self.text_widget.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self._on_scroll)
        scrollbar.pack(side='right', fill='y')
        self.text_widget.config(yscrollcommand=scrollbar.set)
        
        # Disable editing
        self.text_widget.config(state='disabled')
        
        # Configure tags untuk warna
        self.text_widget.tag_configure('INFO', foreground='#6a9955')
        self.text_widget.tag_configure('WARNING', foreground='#dcdcaa')
        self.text_widget.tag_configure('ERROR', foreground='#f48771', font=('Consolas', 9, 'bold'))
        self.text_widget.tag_configure('DEBUG', foreground='#569cd6')
        self.text_widget.tag_configure('CRITICAL', foreground='#f44747', background='#2d2d2d')
        self.text_widget.tag_configure('TIMESTAMP', foreground='#808080')
        self.text_widget.tag_configure('DEFAULT', foreground='#d4d4d4')
    
    def _on_scroll(self, *args):
        """Handler saat scroll"""
        self.text_widget.yview(*args)
        # Cek apakah user scroll ke bawah
        if self.text_widget.yview()[1] >= 0.99:
            self.auto_scroll_var.set(True)
        else:
            self.auto_scroll_var.set(False)
    
    def _refresh_display(self):
        """Refresh tampilan log"""
        try:
            # Baca file log dengan filter waktu
            new_lines = self._read_log_file()
            
            if new_lines != self.log_lines:
                self.log_lines = new_lines
                self._update_display()
            
            # Update status
            self.status_label.config(text=f"Lines: {len(self.log_lines)}")
            
            # Update info clear
            if self.last_clear_time > 0:
                from datetime import datetime
                clear_time_str = datetime.fromtimestamp(self.last_clear_time).strftime("%H:%M:%S")
                self.clear_info_label.config(text=f"Clear sejak: {clear_time_str}")
            else:
                self.clear_info_label.config(text="")
            
        except Exception as e:
            logger.error(f"Error refreshing log: {e}")
        
        # Schedule refresh berikutnya
        self.after_id = self.after(REFRESH_INTERVAL, self._refresh_display)
    
    def _force_refresh(self):
        """Force refresh log"""
        self._refresh_display()
    
    def _read_log_file(self) -> list:
        """
        Baca file log, hanya ambil log setelah last_clear_time
        
        Returns:
            List of log lines
        """
        try:
            # Cari file log di root folder
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            log_path = os.path.join(root_dir, LOG_FILE)
            
            if not os.path.exists(log_path):
                return ["Log file not found. Waiting for logs..."]
            
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filter hanya log setelah last_clear_time
            filtered_lines = []
            for line in lines[-self.max_lines:]:
                line = line.strip()
                if not line:
                    continue
                
                # Parse timestamp (format: YYYY-MM-DD HH:MM:SS)
                timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    try:
                        log_time_str = timestamp_match.group(1)
                        log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S").timestamp()
                        
                        # Hanya tampilkan log yang lebih baru dari last_clear_time
                        if log_time > self.last_clear_time:
                            filtered_lines.append(line)
                    except:
                        # Jika gagal parse timestamp, tampilkan saja
                        filtered_lines.append(line)
                else:
                    # Baris tanpa timestamp (mungkin header), tampilkan saja
                    filtered_lines.append(line)
            
            return filtered_lines
            
        except Exception as e:
            return [f"Error reading log: {e}"]
    
    def _update_display(self):
        """Update text widget dengan log terbaru"""
        # Enable editing
        self.text_widget.config(state='normal')
        
        # Clear
        self.text_widget.delete('1.0', tk.END)
        
        # Insert lines with colors
        for line in self.log_lines:
            self._insert_colored_line(line)
        
        # Auto-scroll ke bawah jika diaktifkan
        if self.auto_scroll_var.get():
            self.text_widget.see(tk.END)
        
        # Disable editing
        self.text_widget.config(state='disabled')
    
    def _insert_colored_line(self, line: str):
        """
        Insert satu line dengan warna berdasarkan level
        
        Args:
            line: Log line
        """
        if not line:
            return
        
        # Parse timestamp (format: YYYY-MM-DD HH:MM:SS)
        timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            rest = line[len(timestamp):].strip()
            
            # Insert timestamp
            self.text_widget.insert(tk.END, timestamp + ' ', 'TIMESTAMP')
            
            # Cari level log
            level_match = re.search(r'\[(INFO|WARNING|ERROR|DEBUG|CRITICAL)\]', rest)
            if level_match:
                level = level_match.group(1)
                level_part = f"[{level}]"
                
                # Insert level dengan warna
                self.text_widget.insert(tk.END, f"[{level}] ", level)
                
                # Insert sisanya (setelah level)
                rest_after_level = rest[len(level_part):].strip()
                self.text_widget.insert(tk.END, rest_after_level + '\n', 'DEFAULT')
            else:
                self.text_widget.insert(tk.END, rest + '\n', 'DEFAULT')
        else:
            self.text_widget.insert(tk.END, line + '\n', 'DEFAULT')
    
    def _clear_log(self):
        """Clear tampilan log - log lama hilang, log baru tetap masuk"""
        # Set waktu clear ke sekarang
        self.last_clear_time = time.time()
        
        # Refresh display
        self._refresh_display()
        
        # Tambah pesan clear di log (tapi tidak akan tampil karena disaring)
        # Tapi kita bisa tambahkan secara manual
        self.add_message("Log display cleared", "INFO")
    
    def _open_log_file(self):
        """Buka file log dengan default editor"""
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            log_path = os.path.join(root_dir, LOG_FILE)
            
            if os.path.exists(log_path):
                if os.name == 'nt':  # Windows
                    os.startfile(log_path)
                else:  # Linux/Mac
                    import subprocess
                    subprocess.call(['xdg-open', log_path])
            else:
                logger.error(f"Log file not found: {log_path}")
                
        except Exception as e:
            logger.error(f"Error opening log file: {e}")
    
    def add_message(self, message: str, level: str = 'INFO'):
        """
        Tambah message ke log secara manual
        
        Args:
            message: Pesan
            level: Level log (INFO, WARNING, ERROR)
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"{timestamp} [{level}] {message}"
        
        self.log_lines.append(log_line)
        if len(self.log_lines) > self.max_lines:
            self.log_lines = self.log_lines[-self.max_lines:]
        
        self._update_display()
    
    def destroy(self):
        """Cleanup saat panel di-destroy"""
        if self.after_id:
            self.after_cancel(self.after_id)
        super().destroy()