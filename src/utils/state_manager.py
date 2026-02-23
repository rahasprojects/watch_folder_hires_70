# -*- coding: utf-8 -*-
"""
Manager untuk menyimpan state aplikasi (resume capability)
"""

import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from ..models.file_job import FileJob
from ..constants.settings import STATE_FILE

logger = logging.getLogger(__name__)

class StateManager:
    """
    Kelas untuk mengelola state aplikasi agar bisa resume setelah restart
    """
    
    def __init__(self, state_path: Optional[str] = None):
        """
        Inisialisasi StateManager
        
        Args:
            state_path: Path ke file state (optional)
        """
        if state_path:
            self.state_path = state_path
        else:
            # Default: pipeline_state.json di folder utama
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.state_path = os.path.join(root_dir, STATE_FILE)
        
        self.state = {
            'version': '1.0',
            'last_update': None,
            'jobs': {},
            'active_downloads': [],
            'queue': []
        }
        logger.debug(f"StateManager initialized with path: {self.state_path}")
    
    def load(self) -> Dict:
        """
        Load state dari file
        
        Returns:
            Dictionary state
        """
        if not os.path.exists(self.state_path):
            logger.info(f"State file not found: {self.state_path}, using empty state")
            return self.state
        
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update state dengan data yang diload
            self.state.update(data)
            logger.info(f"State loaded from: {self.state_path}")
            return self.state
            
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return self.state
    
    def save(self, jobs: List[FileJob] = None) -> bool:
        """
        Save state ke file
        
        Args:
            jobs: List of FileJob objects (optional)
            
        Returns:
            True jika berhasil, False jika gagal
        """
        try:
            # Update timestamp
            self.state['last_update'] = datetime.now().isoformat()
            
            # Update jobs jika diberikan
            if jobs is not None:
                jobs_dict = {}
                active = []
                queue = []
                
                for i, job in enumerate(jobs):
                    jobs_dict[job.name] = job.to_dict()
                    if job.status in ['downloading', 'waiting']:
                        if job.status == 'downloading':
                            active.append(job.name)
                        else:
                            queue.append(job.name)
                
                self.state['jobs'] = jobs_dict
                self.state['active_downloads'] = active
                self.state['queue'] = queue
            
            # Buat folder jika belum ada
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            
            # Simpan ke file
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=4, ensure_ascii=False)
            
            logger.info(f"State saved to: {self.state_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            return False
    
    def update_job(self, job: FileJob) -> bool:
        """
        Update satu job dalam state
        
        Args:
            job: FileJob object
            
        Returns:
            True jika berhasil
        """
        try:
            # Update jobs dictionary
            self.state['jobs'][job.name] = job.to_dict()
            
            # Update active_downloads jika status berubah
            if job.status == 'downloading':
                if job.name not in self.state['active_downloads']:
                    self.state['active_downloads'].append(job.name)
            else:
                if job.name in self.state['active_downloads']:
                    self.state['active_downloads'].remove(job.name)
            
            # Update queue
            if job.status == 'waiting':
                if job.name not in self.state['queue']:
                    self.state['queue'].append(job.name)
            else:
                if job.name in self.state['queue']:
                    self.state['queue'].remove(job.name)
            
            self.state['last_update'] = datetime.now().isoformat()
            return True
            
        except Exception as e:
            logger.error(f"Error updating job in state: {e}")
            return False
    
    def remove_job(self, job_name: str) -> bool:
        """
        Hapus job dari state (misal sudah selesai)
        
        Args:
            job_name: Nama file
            
        Returns:
            True jika berhasil
        """
        try:
            if job_name in self.state['jobs']:
                del self.state['jobs'][job_name]
            
            if job_name in self.state['active_downloads']:
                self.state['active_downloads'].remove(job_name)
            
            if job_name in self.state['queue']:
                self.state['queue'].remove(job_name)
            
            self.state['last_update'] = datetime.now().isoformat()
            logger.debug(f"Job removed from state: {job_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing job from state: {e}")
            return False
    
    def get_resumable_jobs(self) -> List[Dict]:
        """
        Dapatkan daftar job yang bisa di-resume (belum selesai)
        
        Returns:
            List of job dictionaries
        """
        resumable = []
        for job_name, job_data in self.state['jobs'].items():
            if job_data.get('status') in ['downloading', 'waiting']:
                resumable.append(job_data)
        return resumable
    
    def clear_completed(self) -> int:
        """
        Hapus job yang sudah completed/failed dari state
        
        Returns:
            Jumlah job yang dihapus
        """
        to_remove = []
        for job_name, job_data in self.state['jobs'].items():
            if job_data.get('status') in ['completed', 'failed']:
                to_remove.append(job_name)
        
        for job_name in to_remove:
            self.remove_job(job_name)
        
        if to_remove:
            logger.info(f"Cleared {len(to_remove)} completed/failed jobs from state")
        
        return len(to_remove)


# Test sederhana kalau dijalankan langsung
if __name__ == "__main__":
    # Setup logging dulu
    from .logger import setup_logging
    setup_logging()
    
    # Test StateManager
    mgr = StateManager()
    
    # Load state
    state = mgr.load()
    print(f"Loaded state: {state['version']}")
    
    # Buat dummy job untuk test
    from ..models.file_job import FileJob
    job = FileJob(
        name="test.mxf",
        source_path=r"\\server\path\test.mxf",
        dest_path=r"C:\local\test.mxf",
        size_bytes=10737418240
    )
    
    # Update job
    mgr.update_job(job)
    print(f"Job added to state")
    
    # Save state
    mgr.save([job])
    print(f"State saved to {mgr.state_path}")