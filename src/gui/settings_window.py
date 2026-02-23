# -*- coding: utf-8 -*-
"""
Settings window terpisah dengan layout kiri-kanan
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable
from ..models.settings import Settings
from ..utils.config_manager import ConfigManager
from ..utils.validators import validate_extension
from ..constants.settings import DEFAULT_EXTENSIONS

class SettingsWindow:
    """
    Window terpisah untuk settings dengan layout kiri-kanan
    """
    
    def __init__(self, parent, config_manager: ConfigManager, 
                 on_settings_saved: Optional[Callable] = None):
        """
        Inisialisasi SettingsWindow
        
        Args:
            parent: Parent window
            config_manager: ConfigManager instance
            on_settings_saved: Callback saat settings disimpan
        """
        self.parent = parent
        self.config_manager = config_manager
        self.settings = config_manager.get_settings()
        self.on_settings_saved = on_settings_saved
        
        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title("⚙️ Settings - Watch Folder Hires 70")
        self.window.geometry("900x550")
        self.window.minsize(800, 500)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - self.window.winfo_width()) // 2
        y = (self.window.winfo_screenheight() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
        
        # Variables
        self.current_tab = "source"
        self.source_folders = self.settings.source_folders.copy()
        self.destination_folder = self.settings.destination_folder
        self.extensions = self.settings.extensions.copy()
        self.max_download = self.settings.max_download
        self.max_retry = self.settings.max_retry
        
        # Create UI
        self._create_widgets()
        self._show_tab("source")
        
        # Bind close event
        self.window.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _create_widgets(self):
        """Buat semua widget"""
        
        # Main container
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill='both', expand=True)
        
        # ========== LEFT PANEL (MENU) ==========
        left_frame = ttk.Frame(main_frame, width=200, relief='ridge', padding=5)
        left_frame.pack(side='left', fill='y', padx=(0, 10))
        left_frame.pack_propagate(False)
        
        ttk.Label(left_frame, text="SETTINGS", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Menu items
        self.menu_buttons = {}
        
        menu_items = [
            ("source", "📂 Source Folders"),
            ("destination", "💾 Destination"),
            ("extensions", "🎬 File Extensions"),
            ("concurrency", "⚡ Concurrency"),
            ("advanced", "🔧 Advanced"),
            ("about", "ℹ️ About")
        ]
        
        for tab_id, tab_label in menu_items:
            btn = tk.Button(left_frame, text=tab_label, anchor='w', padx=10,
                          bg='#f0f0f0', bd=1, relief='raised',
                          command=lambda t=tab_id: self._show_tab(t))
            btn.pack(fill='x', pady=2)
            self.menu_buttons[tab_id] = btn
        
        # ========== RIGHT PANEL (CONTENT) ==========
        self.right_frame = ttk.Frame(main_frame, relief='sunken', padding=10)
        self.right_frame.pack(side='right', fill='both', expand=True)
        
        # ========== BOTTOM BUTTONS (GLOBAL) ==========
        bottom_frame = ttk.Frame(self.window, padding=10)
        bottom_frame.pack(side='bottom', fill='x')
        
        ttk.Button(bottom_frame, text="💾 SAVE SETTINGS", 
                  command=self._on_save, width=15).pack(side='left', padx=2)
        ttk.Button(bottom_frame, text="📂 LOAD SETTINGS", 
                  command=self._on_load, width=15).pack(side='left', padx=2)
        ttk.Button(bottom_frame, text="🔄 RESET", 
                  command=self._on_reset, width=10).pack(side='left', padx=2)
        
        ttk.Button(bottom_frame, text="✖ CANCEL", 
                  command=self._on_cancel, width=10).pack(side='right', padx=2)
    
    def _show_tab(self, tab_id: str):
        """
        Tampilkan tab tertentu
        
        Args:
            tab_id: ID tab yang akan ditampilkan
        """
        # Update button styles
        for tid, btn in self.menu_buttons.items():
            if tid == tab_id:
                btn.config(bg='#0078d4', fg='white', relief='sunken')
            else:
                btn.config(bg='#f0f0f0', fg='black', relief='raised')
        
        self.current_tab = tab_id
        
        # Clear right frame
        for widget in self.right_frame.winfo_children():
            widget.destroy()
        
        # Show selected tab
        if tab_id == "source":
            self._show_source_tab()
        elif tab_id == "destination":
            self._show_destination_tab()
        elif tab_id == "extensions":
            self._show_extensions_tab()
        elif tab_id == "concurrency":
            self._show_concurrency_tab()
        elif tab_id == "advanced":
            self._show_advanced_tab()
        elif tab_id == "about":
            self._show_about_tab()
    
    # ========== SOURCE FOLDERS TAB ==========
    def _show_source_tab(self):
        """Tampilkan tab source folders"""
        # Header
        header = ttk.Label(self.right_frame, text="📂 SOURCE FOLDERS (12)", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 10))
        
        # Listbox frame
        list_frame = ttk.Frame(self.right_frame)
        list_frame.pack(fill='both', expand=True, pady=5)
        
        # Listbox dengan scrollbar
        self.source_listbox = tk.Listbox(list_frame, height=8, selectmode=tk.SINGLE)
        self.source_listbox.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.source_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.source_listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate listbox
        for folder in self.source_folders:
            self.source_listbox.insert(tk.END, folder)
        
        # Button frame
        btn_frame = ttk.Frame(self.right_frame)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="➕ ADD", command=self._add_source_folder).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="➖ REMOVE", command=self._remove_source_folder).pack(side='left', padx=2)
    
    def _add_source_folder(self):
        """Tambah source folder via browse dialog"""
        folder = filedialog.askdirectory(
            title="Select Source Folder",
            parent=self.window
        )
        
        if folder:
            # Cek duplikasi
            if folder in self.source_folders:
                messagebox.showwarning("Duplicate", "Folder already in list")
                return
            
            self.source_folders.append(folder)
            self.source_listbox.insert(tk.END, folder)
    
    def _remove_source_folder(self):
        """Hapus source folder yang dipilih"""
        selection = self.source_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Please select a folder to remove")
            return
        
        folder = self.source_listbox.get(selection[0])
        
        # Konfirmasi
        if messagebox.askyesno("Confirm Remove", f"Remove folder:\n{folder}?"):
            self.source_folders.remove(folder)
            self.source_listbox.delete(selection[0])
    
    # ========== DESTINATION TAB ==========
    def _show_destination_tab(self):
        """Tampilkan tab destination"""
        # Header
        header = ttk.Label(self.right_frame, text="💾 DESTINATION FOLDER (70)", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 20))
        
        # Frame untuk destination
        dest_frame = ttk.Frame(self.right_frame)
        dest_frame.pack(fill='x', pady=10)
        
        ttk.Label(dest_frame, text="Folder Path:").pack(anchor='w')
        
        # Entry dengan button browse
        entry_frame = ttk.Frame(dest_frame)
        entry_frame.pack(fill='x', pady=5)
        
        self.dest_var = tk.StringVar(value=self.destination_folder)
        self.dest_entry = ttk.Entry(entry_frame, textvariable=self.dest_var, width=50)
        self.dest_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(entry_frame, text="📁 BROWSE", command=self._browse_destination).pack(side='right')
    
    def _browse_destination(self):
        """Browse destination folder"""
        folder = filedialog.askdirectory(
            title="Select Destination Folder",
            parent=self.window
        )
        if folder:
            self.dest_var.set(folder)
            self.destination_folder = folder
    
    # ========== EXTENSIONS TAB ==========
    def _show_extensions_tab(self):
        """Tampilkan tab extensions"""
        # Header
        header = ttk.Label(self.right_frame, text="🎬 FILE EXTENSIONS", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 10))
        
        # Listbox frame
        list_frame = ttk.Frame(self.right_frame)
        list_frame.pack(fill='both', expand=True, pady=5)
        
        self.ext_listbox = tk.Listbox(list_frame, height=8, selectmode=tk.SINGLE)
        self.ext_listbox.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.ext_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.ext_listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate listbox
        for ext in self.extensions:
            self.ext_listbox.insert(tk.END, ext)
        
        # Button frame
        btn_frame = ttk.Frame(self.right_frame)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="➕ ADD", command=self._add_extension).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="➖ REMOVE", command=self._remove_extension).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="🔄 RESET DEFAULT", command=self._reset_extensions).pack(side='left', padx=2)
    
    def _add_extension(self):
        """Tambah extension via dialog"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Add Extension")
        dialog.geometry("300x150")
        dialog.transient(self.window)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Enter extension (e.g., .mp4 or mp4):").pack(pady=10)
        
        var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=var, width=30)
        entry.pack(pady=5)
        entry.focus()
        
        def on_ok():
            ext = var.get().strip()
            if ext:
                valid, result = validate_extension(ext)
                if valid:
                    if result in self.extensions:
                        messagebox.showwarning("Duplicate", "Extension already in list")
                    else:
                        self.extensions.append(result)
                        self.ext_listbox.insert(tk.END, result)
                    dialog.destroy()
                else:
                    messagebox.showerror("Invalid Extension", result)
            else:
                dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
    
    def _remove_extension(self):
        """Hapus extension yang dipilih"""
        selection = self.ext_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Please select an extension to remove")
            return
        
        ext = self.ext_listbox.get(selection[0])
        
        if messagebox.askyesno("Confirm Remove", f"Remove extension: {ext}?"):
            self.extensions.remove(ext)
            self.ext_listbox.delete(selection[0])
    
    def _reset_extensions(self):
        """Reset extensions ke default"""
        if messagebox.askyesno("Confirm Reset", "Reset extensions to defaults?"):
            self.extensions = DEFAULT_EXTENSIONS.copy()
            self.ext_listbox.delete(0, tk.END)
            for ext in self.extensions:
                self.ext_listbox.insert(tk.END, ext)
    
    # ========== CONCURRENCY TAB ==========
    def _show_concurrency_tab(self):
        """Tampilkan tab concurrency"""
        # Header
        header = ttk.Label(self.right_frame, text="⚡ CONCURRENCY SETTINGS", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 20))
        
        # Max Download
        dl_frame = ttk.Frame(self.right_frame)
        dl_frame.pack(fill='x', pady=10)
        
        ttk.Label(dl_frame, text="Max Download Paralel:", font=('Arial', 10)).pack(anchor='w')
        
        slider_frame = ttk.Frame(dl_frame)
        slider_frame.pack(fill='x', pady=5)
        
        self.download_var = tk.IntVar(value=self.max_download)
        scale = ttk.Scale(slider_frame, from_=1, to=10, orient='horizontal',
                         variable=self.download_var, command=self._on_download_change)
        scale.pack(side='left', fill='x', expand=True)
        
        self.download_label = ttk.Label(slider_frame, text=str(self.max_download), width=3)
        self.download_label.pack(side='right', padx=5)
        
        # Max Retry
        retry_frame = ttk.Frame(self.right_frame)
        retry_frame.pack(fill='x', pady=10)
        
        ttk.Label(retry_frame, text="Max Retry:", font=('Arial', 10)).pack(anchor='w')
        
        retry_slider_frame = ttk.Frame(retry_frame)
        retry_slider_frame.pack(fill='x', pady=5)
        
        self.retry_var = tk.IntVar(value=self.max_retry)
        retry_scale = ttk.Scale(retry_slider_frame, from_=0, to=5, orient='horizontal',
                               variable=self.retry_var, command=self._on_retry_change)
        retry_scale.pack(side='left', fill='x', expand=True)
        
        self.retry_label = ttk.Label(retry_slider_frame, text=str(self.max_retry), width=3)
        self.retry_label.pack(side='right', padx=5)
    
    def _on_download_change(self, value):
        """Handler slider download berubah"""
        val = int(float(value))
        self.download_var.set(val)
        self.download_label.config(text=str(val))
        self.max_download = val
    
    def _on_retry_change(self, value):
        """Handler slider retry berubah"""
        val = int(float(value))
        self.retry_var.set(val)
        self.retry_label.config(text=str(val))
        self.max_retry = val
    
    # ========== ADVANCED TAB ==========
    def _show_advanced_tab(self):
        """Tampilkan tab advanced (placeholder)"""
        # Header
        header = ttk.Label(self.right_frame, text="🔧 ADVANCED SETTINGS", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 20))
        
        # Placeholder
        ttk.Label(self.right_frame, text="Advanced settings coming soon...",
                 font=('Arial', 10, 'italic')).pack(pady=50)
    
    # ========== ABOUT TAB ==========
    def _show_about_tab(self):
        """Tampilkan tab about"""
        # Header
        header = ttk.Label(self.right_frame, text="ℹ️ ABOUT", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 20))
        
        # Info
        info_frame = ttk.Frame(self.right_frame)
        info_frame.pack(fill='both', expand=True)
        
        ttk.Label(info_frame, text="🎬 Watch Folder Hires 70",
                 font=('Arial', 14, 'bold')).pack(pady=5)
        
        ttk.Label(info_frame, text="Pipeline Copy - Fase 1 (12 → 70)",
                 font=('Arial', 11)).pack(pady=2)
        
        ttk.Label(info_frame, text="Version: 1.0.0").pack(pady=2)
        ttk.Label(info_frame, text="Created: 2026").pack(pady=2)
        ttk.Label(info_frame, text="").pack(pady=5)
        
        ttk.Label(info_frame, text="Fitur:").pack(anchor='w', pady=(10,2))
        ttk.Label(info_frame, text="• Monitor folder 12 via SMB").pack(anchor='w')
        ttk.Label(info_frame, text="• FIFO queue tanpa prioritas").pack(anchor='w')
        ttk.Label(info_frame, text="• Resume capability (checkpoint 10%)").pack(anchor='w')
        ttk.Label(info_frame, text="• Max parallel download configurable").pack(anchor='w')
        ttk.Label(info_frame, text="• Filter file extensions").pack(anchor='w')
        ttk.Label(info_frame, text="• Real-time progress monitoring").pack(anchor='w')
    
    # ========== GLOBAL BUTTON HANDLERS ==========
    def _on_save(self):
        """Save all settings"""
        # Update settings object
        self.settings.source_folders = self.source_folders
        self.settings.destination_folder = self.destination_folder
        self.settings.extensions = self.extensions
        self.settings.max_download = self.max_download
        self.settings.max_retry = self.max_retry
        
        # Validate
        valid, msg = self.settings.validate()
        if not valid:
            messagebox.showerror("Invalid Settings", msg)
            return
        
        # Save
        if self.config_manager.save(self.settings):
            messagebox.showinfo("Success", "Settings saved successfully")
            if self.on_settings_saved:
                self.on_settings_saved()
            self.window.destroy()
        else:
            messagebox.showerror("Error", "Failed to save settings")
    
    def _on_load(self):
        """Load all settings"""
        if messagebox.askyesno("Confirm Load", "Load settings from file? (Unsaved changes will be lost)"):
            self.settings = self.config_manager.load()
            
            # Update variables
            self.source_folders = self.settings.source_folders.copy()
            self.destination_folder = self.settings.destination_folder
            self.extensions = self.settings.extensions.copy()
            self.max_download = self.settings.max_download
            self.max_retry = self.settings.max_retry
            
            # Refresh current tab
            self._show_tab(self.current_tab)
            
            messagebox.showinfo("Success", "Settings loaded successfully")
    
    def _on_reset(self):
        """Reset all settings to default"""
        if messagebox.askyesno("Confirm Reset", "Reset all settings to defaults?"):
            self.settings = Settings()
            
            # Update variables
            self.source_folders = self.settings.source_folders.copy()
            self.destination_folder = self.settings.destination_folder
            self.extensions = self.settings.extensions.copy()
            self.max_download = self.settings.max_download
            self.max_retry = self.settings.max_retry
            
            # Refresh current tab
            self._show_tab(self.current_tab)
    
    def _on_cancel(self):
        """Cancel and close window"""
        self.window.destroy()
    
    def show(self):
        """Tampilkan window"""
        self.window.wait_window()