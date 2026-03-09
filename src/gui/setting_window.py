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
        self.window.geometry("900x650")  # Diperbesar untuk 3 destination
        self.window.minsize(800, 600)
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
        self.destination_70 = self.settings.destination_70
        # ===== VARIABEL BARU =====
        self.destination_51 = self.settings.destination_51
        self.destination_40 = self.settings.destination_40
        # ========================
        self.extensions = self.settings.extensions.copy()
        self.max_download = self.settings.max_download
        # ===== VARIABEL BARU =====
        self.max_upload_51 = self.settings.max_upload_51
        self.max_upload_40 = self.settings.max_upload_40
        # ========================
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
            ("destination", "💾 Destinations"),  # Berubah jadi plural
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
        
        # Tombol dengan style baru (panjang, bold, icon di tengah)
        button_style = {'width': 20, 'font': ('Arial', 10, 'bold')}
        
        ttk.Button(bottom_frame, text="💾 SAVE ALL", 
                  command=self._on_save, **button_style).pack(side='left', padx=2)
        ttk.Button(bottom_frame, text="📂 OPEN SETTINGS", 
                  command=self._on_load, **button_style).pack(side='left', padx=2)
        ttk.Button(bottom_frame, text="🔄 RESET", 
                  command=self._on_reset, **button_style).pack(side='left', padx=2)
        
        ttk.Button(bottom_frame, text="✖ CANCEL", 
                  command=self._on_cancel, **button_style).pack(side='right', padx=2)
    
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
            self._show_destination_tab()  # Sekarang untuk 3 destination
        elif tab_id == "extensions":
            self._show_extensions_tab()
        elif tab_id == "concurrency":
            self._show_concurrency_tab()  # Sekarang dengan 3 slider
        elif tab_id == "advanced":
            self._show_advanced_tab()
        elif tab_id == "about":
            self._show_about_tab()
    
    # ========== SOURCE FOLDERS TAB (TIDAK BERUBAH) ==========
    def _show_source_tab(self):
        """Tampilkan tab source folders"""
        # Header
        header = ttk.Label(self.right_frame, text="📂 SOURCE FOLDERS (12)", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 10))
        
        # Listbox frame
        list_frame = ttk.Frame(self.right_frame)
        list_frame.pack(fill='both', expand=True, pady=5)
        
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
    
    # ========== DESTINATION TAB (BARU - UNTUK 3 DESTINATION) ==========
    def _show_destination_tab(self):
        """Tampilkan tab destination untuk 70, 51, dan 40"""
        # Header
        header = ttk.Label(self.right_frame, text="💾 DESTINATION FOLDERS", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 20))
        
        # ===== DESTINATION 70 (DOWNLOAD) =====
        dest70_frame = ttk.LabelFrame(self.right_frame, text="📥 Destination 70 (Download)", padding=5)
        dest70_frame.pack(fill='x', pady=5)
        
        frame70 = ttk.Frame(dest70_frame)
        frame70.pack(fill='x', pady=5)
        
        ttk.Label(frame70, text="Folder Path:").pack(anchor='w')
        
        entry_frame70 = ttk.Frame(frame70)
        entry_frame70.pack(fill='x', pady=5)
        
        self.dest70_var = tk.StringVar(value=self.destination_70)
        self.dest70_entry = ttk.Entry(entry_frame70, textvariable=self.dest70_var, width=50)
        self.dest70_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(entry_frame70, text="📁 BROWSE", command=self._browse_dest70).pack(side='right')
        
        # ===== DESTINATION 51 (HIRES) =====
        dest51_frame = ttk.LabelFrame(self.right_frame, text="📤 Destination 51 (HIRES) - ⭐ HIGH PRIORITY", padding=5)
        dest51_frame.pack(fill='x', pady=5)
        
        frame51 = ttk.Frame(dest51_frame)
        frame51.pack(fill='x', pady=5)
        
        ttk.Label(frame51, text="Folder Path:").pack(anchor='w')
        
        entry_frame51 = ttk.Frame(frame51)
        entry_frame51.pack(fill='x', pady=5)
        
        self.dest51_var = tk.StringVar(value=self.destination_51)
        self.dest51_entry = ttk.Entry(entry_frame51, textvariable=self.dest51_var, width=50)
        self.dest51_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(entry_frame51, text="📁 BROWSE", command=self._browse_dest51).pack(side='right')
        
        # ===== DESTINATION 40 (LOWRES) =====
        dest40_frame = ttk.LabelFrame(self.right_frame, text="📤 Destination 40 (LOWRES) - NORMAL PRIORITY", padding=5)
        dest40_frame.pack(fill='x', pady=5)
        
        frame40 = ttk.Frame(dest40_frame)
        frame40.pack(fill='x', pady=5)
        
        ttk.Label(frame40, text="Folder Path:").pack(anchor='w')
        
        entry_frame40 = ttk.Frame(frame40)
        entry_frame40.pack(fill='x', pady=5)
        
        self.dest40_var = tk.StringVar(value=self.destination_40)
        self.dest40_entry = ttk.Entry(entry_frame40, textvariable=self.dest40_var, width=50)
        self.dest40_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(entry_frame40, text="📁 BROWSE", command=self._browse_dest40).pack(side='right')
    
    # ========== BROWSE METHODS ==========
    def _browse_dest70(self):
        """Browse destination 70"""
        folder = filedialog.askdirectory(title="Select Destination 70 Folder")
        if folder:
            self.dest70_var.set(folder)
            self.destination_70 = folder
    
    def _browse_dest51(self):
        """Browse destination 51"""
        folder = filedialog.askdirectory(title="Select Destination 51 (HIRES) Folder")
        if folder:
            self.dest51_var.set(folder)
            self.destination_51 = folder
    
    def _browse_dest40(self):
        """Browse destination 40"""
        folder = filedialog.askdirectory(title="Select Destination 40 (LOWRES) Folder")
        if folder:
            self.dest40_var.set(folder)
            self.destination_40 = folder
    
    # ========== EXTENSIONS TAB (TIDAK BERUBAH) ==========
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
    
    # ========== CONCURRENCY TAB (BARU - DENGAN 3 SLIDER) ==========
    def _show_concurrency_tab(self):
        """Tampilkan tab concurrency dengan 3 slider"""
        # Header
        header = ttk.Label(self.right_frame, text="⚡ CONCURRENCY SETTINGS", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 20))
        
        # ===== MAX DOWNLOAD (TETAP) =====
        dl_frame = ttk.LabelFrame(self.right_frame, text="Download (12 → 70)", padding=5)
        dl_frame.pack(fill='x', pady=5)
        
        dl_slider_frame = ttk.Frame(dl_frame)
        dl_slider_frame.pack(fill='x', pady=5)
        
        ttk.Label(dl_slider_frame, text="Max Download Paralel:").pack(side='left')
        self.download_var = tk.IntVar(value=self.max_download)
        scale_dl = ttk.Scale(dl_slider_frame, from_=1, to=10, orient='horizontal',
                            variable=self.download_var, command=self._on_download_change)
        scale_dl.pack(side='left', fill='x', expand=True, padx=5)
        self.download_label = ttk.Label(dl_slider_frame, text=str(self.max_download), width=3)
        self.download_label.pack(side='right', padx=5)
        
        # ===== MAX UPLOAD 51 (BARU) =====
        ul51_frame = ttk.LabelFrame(self.right_frame, text="Upload to HIRES (51) - ⭐ HIGH PRIORITY", padding=5)
        ul51_frame.pack(fill='x', pady=5)
        
        ul51_slider_frame = ttk.Frame(ul51_frame)
        ul51_slider_frame.pack(fill='x', pady=5)
        
        ttk.Label(ul51_slider_frame, text="Max Upload 51 Paralel:").pack(side='left')
        self.upload51_var = tk.IntVar(value=self.max_upload_51)
        scale_ul51 = ttk.Scale(ul51_slider_frame, from_=1, to=5, orient='horizontal',
                              variable=self.upload51_var, command=self._on_upload51_change)
        scale_ul51.pack(side='left', fill='x', expand=True, padx=5)
        self.upload51_label = ttk.Label(ul51_slider_frame, text=str(self.max_upload_51), width=3)
        self.upload51_label.pack(side='right', padx=5)
        
        # ===== MAX UPLOAD 40 (BARU) =====
        ul40_frame = ttk.LabelFrame(self.right_frame, text="Upload to LOWRES (40) - NORMAL PRIORITY", padding=5)
        ul40_frame.pack(fill='x', pady=5)
        
        ul40_slider_frame = ttk.Frame(ul40_frame)
        ul40_slider_frame.pack(fill='x', pady=5)
        
        ttk.Label(ul40_slider_frame, text="Max Upload 40 Paralel:").pack(side='left')
        self.upload40_var = tk.IntVar(value=self.max_upload_40)
        scale_ul40 = ttk.Scale(ul40_slider_frame, from_=1, to=5, orient='horizontal',
                              variable=self.upload40_var, command=self._on_upload40_change)
        scale_ul40.pack(side='left', fill='x', expand=True, padx=5)
        self.upload40_label = ttk.Label(ul40_slider_frame, text=str(self.max_upload_40), width=3)
        self.upload40_label.pack(side='right', padx=5)
        
        # ===== MAX RETRY (TETAP) =====
        retry_frame = ttk.LabelFrame(self.right_frame, text="Retry Settings", padding=5)
        retry_frame.pack(fill='x', pady=5)
        
        retry_slider_frame = ttk.Frame(retry_frame)
        retry_slider_frame.pack(fill='x', pady=5)
        
        ttk.Label(retry_slider_frame, text="Max Retry:").pack(side='left')
        self.retry_var = tk.IntVar(value=self.max_retry)
        scale_retry = ttk.Scale(retry_slider_frame, from_=0, to=5, orient='horizontal',
                               variable=self.retry_var, command=self._on_retry_change)
        scale_retry.pack(side='left', fill='x', expand=True, padx=5)
        self.retry_label = ttk.Label(retry_slider_frame, text=str(self.max_retry), width=3)
        self.retry_label.pack(side='right', padx=5)
    
    # ========== SLIDER HANDLERS (BARU) ==========
    def _on_download_change(self, value):
        val = int(float(value))
        self.download_var.set(val)
        self.download_label.config(text=str(val))
        self.max_download = val
    
    def _on_upload51_change(self, value):
        val = int(float(value))
        self.upload51_var.set(val)
        self.upload51_label.config(text=str(val))
        self.max_upload_51 = val
    
    def _on_upload40_change(self, value):
        val = int(float(value))
        self.upload40_var.set(val)
        self.upload40_label.config(text=str(val))
        self.max_upload_40 = val
    
    def _on_retry_change(self, value):
        val = int(float(value))
        self.retry_var.set(val)
        self.retry_label.config(text=str(val))
        self.max_retry = val
    
    # ========== ADVANCED TAB (TIDAK BERUBAH) ==========
    def _show_advanced_tab(self):
        """Tampilkan tab advanced (placeholder)"""
        header = ttk.Label(self.right_frame, text="🔧 ADVANCED SETTINGS", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 20))
        
        ttk.Label(self.right_frame, text="Advanced settings coming soon...",
                 font=('Arial', 10, 'italic')).pack(pady=50)
    
    # ========== ABOUT TAB (TIDAK BERUBAH) ==========
    def _show_about_tab(self):
        """Tampilkan tab about"""
        header = ttk.Label(self.right_frame, text="ℹ️ ABOUT", 
                          font=('Arial', 12, 'bold'))
        header.pack(anchor='w', pady=(0, 20))
        
        info_frame = ttk.Frame(self.right_frame)
        info_frame.pack(fill='both', expand=True)
        
        ttk.Label(info_frame, text="🎬 Watch Folder Hires 70",
                 font=('Arial', 14, 'bold')).pack(pady=5)
        
        ttk.Label(info_frame, text="Pipeline Copy - Fase 2 (70 → 40 & 51)",
                 font=('Arial', 11)).pack(pady=2)
        
        ttk.Label(info_frame, text="Version: 2.0.0").pack(pady=2)
        ttk.Label(info_frame, text="Created: 2026").pack(pady=2)
        ttk.Label(info_frame, text="").pack(pady=5)
        
        ttk.Label(info_frame, text="Fitur:").pack(anchor='w', pady=(10,2))
        ttk.Label(info_frame, text="• Monitor folder 12 via SMB").pack(anchor='w')
        ttk.Label(info_frame, text="• Download 12 → 70").pack(anchor='w')
        ttk.Label(info_frame, text="• Upload 70 → 51 (HIRES) ⭐ HIGH PRIORITY").pack(anchor='w')
        ttk.Label(info_frame, text="• Upload 70 → 40 (LOWRES) NORMAL PRIORITY").pack(anchor='w')
        ttk.Label(info_frame, text="• Auto-delete from 70 after both uploads").pack(anchor='w')
    
    # ========== METHOD YANG SUDAH ADA (TIDAK BERUBAH) ==========
    def _add_source_folder(self):
        """Tambah source folder via browse dialog"""
        folder = filedialog.askdirectory(
            title="Select Source Folder",
            parent=self.window
        )
        
        if folder:
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
        
        if messagebox.askyesno("Confirm Remove", f"Remove folder:\n{folder}?"):
            self.source_folders.remove(folder)
            self.source_listbox.delete(selection[0])
    
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
    
    # ========== GLOBAL BUTTON HANDLERS (UPDATE) ==========
    def _on_save(self):
        """Save all settings"""
        # Update settings object
        self.settings.source_folders = self.source_folders
        self.settings.destination_70 = self.destination_70
        self.settings.destination_51 = self.destination_51
        self.settings.destination_40 = self.destination_40
        self.settings.extensions = self.extensions
        self.settings.max_download = self.max_download
        self.settings.max_upload_51 = self.max_upload_51
        self.settings.max_upload_40 = self.max_upload_40
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
            self.destination_70 = self.settings.destination_70
            self.destination_51 = self.settings.destination_51
            self.destination_40 = self.settings.destination_40
            self.extensions = self.settings.extensions.copy()
            self.max_download = self.settings.max_download
            self.max_upload_51 = self.settings.max_upload_51
            self.max_upload_40 = self.settings.max_upload_40
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
            self.destination_70 = self.settings.destination_70
            self.destination_51 = self.settings.destination_51
            self.destination_40 = self.settings.destination_40
            self.extensions = self.settings.extensions.copy()
            self.max_download = self.settings.max_download
            self.max_upload_51 = self.settings.max_upload_51
            self.max_upload_40 = self.settings.max_upload_40
            self.max_retry = self.settings.max_retry
            
            # Refresh current tab
            self._show_tab(self.current_tab)
    
    def _on_cancel(self):
        """Cancel and close window"""
        self.window.destroy()
    
    def show(self):
        """Tampilkan window"""
        self.window.wait_window()