# -*- coding: utf-8 -*-
"""
Settings panel untuk konfigurasi aplikasi
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional, List
from ..models.settings import Settings
from ..utils.config_manager import ConfigManager
from ..utils.validators import validate_path, validate_extension
from ..constants.settings import DEFAULT_EXTENSIONS

class SettingsPanel(ttk.LabelFrame):
    """
    Panel untuk mengatur konfigurasi aplikasi
    """
    
    def __init__(self, parent, config_manager: ConfigManager, 
                 on_settings_changed: Optional[Callable] = None):
        """
        Inisialisasi SettingsPanel
        
        Args:
            parent: Parent widget
            config_manager: ConfigManager instance
            on_settings_changed: Callback saat settings berubah
        """
        super().__init__(parent, text="⚙️ Settings", padding=10)
        
        self.config_manager = config_manager
        self.settings = config_manager.get_settings()
        self.on_settings_changed = on_settings_changed
        
        # Variables
        self.max_download_var = tk.IntVar(value=self.settings.max_download)
        self.max_retry_var = tk.IntVar(value=self.settings.max_retry)
        
        self._create_widgets()
        self._load_settings()
    
    def _create_widgets(self):
        """Buat semua widget"""
        
        # === SOURCE FOLDERS ===
        source_frame = ttk.LabelFrame(self, text="📂 Source Folders (12)", padding=5)
        source_frame.pack(fill='x', pady=5)
        
        # Listbox dengan scrollbar
        list_frame = ttk.Frame(source_frame)
        list_frame.pack(fill='both', expand=True)
        
        self.source_listbox = tk.Listbox(list_frame, height=4, selectmode=tk.SINGLE)
        self.source_listbox.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.source_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.source_listbox.config(yscrollcommand=scrollbar.set)
        
        # Buttons
        btn_frame = ttk.Frame(source_frame)
        btn_frame.pack(fill='x', pady=5)
        
        ttk.Button(btn_frame, text="➕ Add", command=self._add_source_folder).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="➖ Remove", command=self._remove_source_folder).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="📁 Browse", command=self._browse_source_folder).pack(side='left', padx=2)
        
        # === DESTINATION FOLDER ===
        dest_frame = ttk.LabelFrame(self, text="💾 Destination Folder (70)", padding=5)
        dest_frame.pack(fill='x', pady=5)
        
        dest_entry_frame = ttk.Frame(dest_frame)
        dest_entry_frame.pack(fill='x')
        
        self.dest_var = tk.StringVar()
        self.dest_entry = ttk.Entry(dest_entry_frame, textvariable=self.dest_var)
        self.dest_entry.pack(side='left', fill='x', expand=True, padx=2)
        
        ttk.Button(dest_entry_frame, text="📁 Browse", command=self._browse_dest_folder).pack(side='right', padx=2)
        
        # === EXTENSIONS ===
        ext_frame = ttk.LabelFrame(self, text="🎬 File Extensions", padding=5)
        ext_frame.pack(fill='x', pady=5)
        
        # Listbox dengan scrollbar
        ext_list_frame = ttk.Frame(ext_frame)
        ext_list_frame.pack(fill='both', expand=True)
        
        self.ext_listbox = tk.Listbox(ext_list_frame, height=5, selectmode=tk.SINGLE)
        self.ext_listbox.pack(side='left', fill='both', expand=True)
        
        ext_scrollbar = ttk.Scrollbar(ext_list_frame, orient='vertical', command=self.ext_listbox.yview)
        ext_scrollbar.pack(side='right', fill='y')
        self.ext_listbox.config(yscrollcommand=ext_scrollbar.set)
        
        # Buttons
        ext_btn_frame = ttk.Frame(ext_frame)
        ext_btn_frame.pack(fill='x', pady=5)
        
        ttk.Button(ext_btn_frame, text="➕ Add", command=self._add_extension).pack(side='left', padx=2)
        ttk.Button(ext_btn_frame, text="➖ Remove", command=self._remove_extension).pack(side='left', padx=2)
        ttk.Button(ext_btn_frame, text="🔄 Reset Default", command=self._reset_extensions).pack(side='left', padx=2)
        
        # === CONCURRENCY SETTINGS ===
        concurrent_frame = ttk.LabelFrame(self, text="⚡ Concurrency Settings", padding=5)
        concurrent_frame.pack(fill='x', pady=5)
        
        # Max Download
        dl_frame = ttk.Frame(concurrent_frame)
        dl_frame.pack(fill='x', pady=2)
        
        ttk.Label(dl_frame, text="Max Download Paralel:").pack(side='left')
        ttk.Scale(dl_frame, from_=1, to=10, orient='horizontal', 
                 variable=self.max_download_var, command=self._on_max_download_change).pack(side='left', fill='x', expand=True, padx=5)
        self.dl_label = ttk.Label(dl_frame, text=str(self.max_download_var.get()))
        self.dl_label.pack(side='right', padx=5)
        
        # Max Retry
        retry_frame = ttk.Frame(concurrent_frame)
        retry_frame.pack(fill='x', pady=2)
        
        ttk.Label(retry_frame, text="Max Retry:").pack(side='left')
        ttk.Scale(retry_frame, from_=0, to=5, orient='horizontal',
                 variable=self.max_retry_var, command=self._on_max_retry_change).pack(side='left', fill='x', expand=True, padx=5)
        self.retry_label = ttk.Label(retry_frame, text=str(self.max_retry_var.get()))
        self.retry_label.pack(side='right', padx=5)
        
        # === BUTTONS ===
        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="💾 Save Settings", command=self._save_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🔄 Load Settings", command=self._load_settings).pack(side='left', padx=5)
        ttk.Button(button_frame, text="📋 Validate", command=self._validate_settings).pack(side='left', padx=5)
    
    def _load_settings(self):
        """Load settings dari config manager"""
        self.settings = self.config_manager.load()
        
        # Update UI
        self._update_source_listbox()
        self.dest_var.set(self.settings.destination_folder)
        self._update_ext_listbox()
        self.max_download_var.set(self.settings.max_download)
        self.max_retry_var.set(self.settings.max_retry)
        
        self.dl_label.config(text=str(self.settings.max_download))
        self.retry_label.config(text=str(self.settings.max_retry))
    
    def _save_settings(self):
        """Save settings ke config manager"""
        # Update settings dari UI
        self.settings.source_folders = list(self.source_listbox.get(0, tk.END))
        self.settings.destination_folder = self.dest_var.get().strip()
        self.settings.extensions = list(self.ext_listbox.get(0, tk.END))
        self.settings.max_download = self.max_download_var.get()
        self.settings.max_retry = self.max_retry_var.get()
        
        # Validasi
        valid, msg = self.settings.validate()
        if not valid:
            messagebox.showerror("Invalid Settings", msg)
            return
        
        # Save
        if self.config_manager.save(self.settings):
            messagebox.showinfo("Success", "Settings saved successfully")
            if self.on_settings_changed:
                self.on_settings_changed()
        else:
            messagebox.showerror("Error", "Failed to save settings")
    
    def _validate_settings(self):
        """Validasi settings"""
        valid, msg = self.settings.validate()
        if valid:
            messagebox.showinfo("Validation", "✅ Settings are valid")
        else:
            messagebox.showerror("Validation", f"❌ {msg}")
    
    def _update_source_listbox(self):
        """Update source listbox dari settings"""
        self.source_listbox.delete(0, tk.END)
        for folder in self.settings.source_folders:
            self.source_listbox.insert(tk.END, folder)
    
    def _update_ext_listbox(self):
        """Update extension listbox dari settings"""
        self.ext_listbox.delete(0, tk.END)
        for ext in self.settings.extensions:
            self.ext_listbox.insert(tk.END, ext)
    
    def _add_source_folder(self):
        """Tambah source folder manual"""
        dialog = tk.Toplevel(self)
        dialog.title("Add Source Folder")
        dialog.geometry("400x120")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Enter folder path:").pack(pady=5)
        
        var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=var, width=50)
        entry.pack(pady=5)
        
        def on_ok():
            folder = var.get().strip()
            if folder:
                valid, msg = validate_path(folder, must_exist=False)
                if valid:
                    self.source_listbox.insert(tk.END, folder)
                    dialog.destroy()
                else:
                    messagebox.showerror("Invalid Path", msg)
            else:
                dialog.destroy()
        
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=5)
        entry.focus()
    
    def _remove_source_folder(self):
        """Hapus source folder terpilih"""
        selection = self.source_listbox.curselection()
        if selection:
            self.source_listbox.delete(selection[0])
    
    def _browse_source_folder(self):
        """Browse dan tambah source folder"""
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_listbox.insert(tk.END, folder)
    
    def _browse_dest_folder(self):
        """Browse destination folder"""
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.dest_var.set(folder)
    
    def _add_extension(self):
        """Tambah ekstensi baru"""
        dialog = tk.Toplevel(self)
        dialog.title("Add Extension")
        dialog.geometry("300x120")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Enter extension (e.g., .mp4 or mp4):").pack(pady=5)
        
        var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=var, width=30)
        entry.pack(pady=5)
        
        def on_ok():
            ext = var.get().strip()
            if ext:
                valid, normalized = validate_extension(ext)
                if valid:
                    self.ext_listbox.insert(tk.END, normalized)
                    dialog.destroy()
                else:
                    messagebox.showerror("Invalid Extension", normalized)
            else:
                dialog.destroy()
        
        ttk.Button(dialog, text="OK", command=on_ok).pack(pady=5)
        entry.focus()
    
    def _remove_extension(self):
        """Hapus ekstensi terpilih"""
        selection = self.ext_listbox.curselection()
        if selection:
            self.ext_listbox.delete(selection[0])
    
    def _reset_extensions(self):
        """Reset extensions ke default"""
        self.ext_listbox.delete(0, tk.END)
        for ext in DEFAULT_EXTENSIONS:
            self.ext_listbox.insert(tk.END, ext)
    
    def _on_max_download_change(self, value):
        """Handler saat max download berubah"""
        self.dl_label.config(text=str(int(float(value))))
    
    def _on_max_retry_change(self, value):
        """Handler saat max retry berubah"""
        self.retry_label.config(text=str(int(float(value))))
    
    def get_settings(self) -> Settings:
        """Dapatkan settings terbaru dari UI"""
        return Settings(
            source_folders=list(self.source_listbox.get(0, tk.END)),
            destination_folder=self.dest_var.get().strip(),
            extensions=list(self.ext_listbox.get(0, tk.END)),
            max_download=self.max_download_var.get(),
            max_retry=self.max_retry_var.get()
        )