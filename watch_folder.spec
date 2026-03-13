# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# ===== KOLEKSI SEMUA HIDDEN IMPORTS =====
hidden_imports = [
    'src.constants.settings',
    'src.models.file_job',
    'src.models.settings',
    'src.models.upload_job',
    'src.utils.logger',
    'src.utils.path_utils',
    'src.utils.config_manager',
    'src.utils.state_manager',
    'src.utils.history',
    'src.utils.validators',
    'src.core.file_handler',
    'src.core.queue_manager',
    'src.core.download_worker',
    'src.core.download_manager',
    'src.core.upload_worker_51',
    'src.core.upload_worker_40',
    'src.core.upload_queue_manager',
    'src.core.upload_manager',
    'src.core.upload_controller',
    'src.core.file_monitor',
    'src.gui.queue_panel',
    'src.gui.progress_panel',
    'src.gui.log_panel',
    'src.gui.history_panel',
    'src.gui.upload_panel_51',
    'src.gui.upload_panel_40',
    'src.gui.settings_window',
    'src.gui.main_window',
]

a = Analysis(
    ['main.py'],
    pathex=['d:\\watch_folder_hires'],
    binaries=[],
    datas=[
        # Salin folder src ke dalam build
        ('src', 'src'),
        ('default_log.txt', 'data/pipeline.log'), 
        
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WatchFolderHires70',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # <-- NOCONSOLE
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'              # <-- ICON
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WatchFolderHires70'    # <-- ONE FOLDER
)