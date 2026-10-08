@echo off
rem SEGGER SystemView <-> ST-Link koprusunu baslatir (TCP 127.0.0.1:19111).
rem SystemView: Target > Recorder Configuration > IP, 127.0.0.1, 19111 > Start Recording
chcp 65001 >nul
cd /d "%~dp0.."

if not exist "tools\.venv\Scripts\python.exe" (
    echo [kurulum] tools\.venv olusturuluyor ve pyOCD kuruluyor...
    python -m venv tools\.venv || goto :err
    tools\.venv\Scripts\python -m pip install -q -r tools\requirements.txt || goto :err
)

set PYTHONIOENCODING=utf-8
tools\.venv\Scripts\python tools\sysview_stlink.py %*
pause
exit /b 0

:err
echo Kurulum basarisiz. Python 3 PATH'te mi?
pause
exit /b 1
