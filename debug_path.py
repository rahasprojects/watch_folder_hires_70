# debug_path.py
import os
from src.models.file_job import FileJob
from src.core.file_handler import FileHandler
from src.utils.logger import setup_logging

setup_logging()

# Buat job manual
source = "D:/Test watch folder/source/SEKOLAH PONDOK DOMBA KALIJODOH Rev.mp4"
dest = "D:/Test watch folder/destination/SEKOLAH PONDOK DOMBA KALIJODOH Rev.mp4"

print(f"Source exists: {os.path.exists(source)}")
print(f"Source file: {source}")
print(f"Dest folder: {os.path.dirname(dest)}")
print(f"Dest folder exists: {os.path.exists(os.path.dirname(dest))}")

if os.path.exists(source):
    job = FileJob(
        name="test.mxf",
        source_path=source,
        dest_path=dest,
        size_bytes=os.path.getsize(source)
    )
    
    handler = FileHandler()
    success = handler.safe_copy(job)
    print(f"Copy success: {success}")
else:
    print("Source file not found!")