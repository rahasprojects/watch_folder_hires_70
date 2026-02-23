@echo off
echo ========================================
echo Watch Folder Hires 70 - Pipeline Copy
echo Fase 1: 12 → 70
echo ========================================
echo.

:: Aktifkan virtual environment
call .venv\Scripts\activate.bat

:: Jalankan aplikasi
python main.py

:: Jika error, pause
if errorlevel 1 (
    echo.
    echo Application exited with error.
    pause
)