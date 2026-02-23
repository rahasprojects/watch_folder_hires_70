# -*- coding: utf-8 -*-
"""
Manager untuk load/save konfigurasi
"""

import json
import os
import logging
from typing import Optional
from ..models.settings import Settings
from ..constants.settings import CONFIG_FILE

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Kelas untuk mengelola konfigurasi aplikasi
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inisialisasi ConfigManager
        
        Args:
            config_path: Path ke file konfigurasi (optional)
        """
        if config_path:
            self.config_path = config_path
        else:
            # Default: config.json di folder utama
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.config_path = os.path.join(root_dir, CONFIG_FILE)
        
        self.settings = Settings()
        logger.debug(f"ConfigManager initialized with path: {self.config_path}")
    
    def load(self) -> Settings:
        """
        Load konfigurasi dari file
        
        Returns:
            Settings object
        """
        if not os.path.exists(self.config_path):
            logger.info(f"Config file not found: {self.config_path}, using defaults")
            return self.settings
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.settings = Settings.from_dict(data)
            logger.info(f"Config loaded from: {self.config_path}")
            return self.settings
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.settings
    
    def save(self, settings: Optional[Settings] = None) -> bool:
        """
        Save konfigurasi ke file
        
        Args:
            settings: Settings object (optional, jika None pakai self.settings)
            
        Returns:
            True jika berhasil, False jika gagal
        """
        if settings:
            self.settings = settings
        
        try:
            # Buat folder jika belum ada
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings.to_dict(), f, indent=4, ensure_ascii=False)
            
            logger.info(f"Config saved to: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def get_settings(self) -> Settings:
        """Dapatkan settings object"""
        return self.settings
    
    def update_settings(self, **kwargs):
        """
        Update settings dengan keyword arguments
        
        Args:
            **kwargs: Field yang akan diupdate
        """
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
                logger.debug(f"Settings updated: {key} = {value}")
            else:
                logger.warning(f"Unknown settings field: {key}")
        
        return self.settings
    
    def reset_to_defaults(self):
        """Reset settings ke default"""
        self.settings = Settings()
        logger.info("Settings reset to defaults")
        return self.settings


# Test sederhana kalau dijalankan langsung
if __name__ == "__main__":
    # Setup logging dulu
    from .logger import setup_logging
    setup_logging()
    
    # Test ConfigManager
    mgr = ConfigManager()
    
    # Load config
    settings = mgr.load()
    print(f"Loaded settings: {settings.to_dict()}")
    
    # Update settings
    mgr.update_settings(max_download=5, max_retry=2)
    
    # Save config
    mgr.save()
    print(f"Saved settings to {mgr.config_path}")