@echo off
title Auto Clip - AI Video Editor
echo Setting up Auto Clip...
echo.

:: 1. Try default python command
python -c "import moviepy, whisper, imageio_ffmpeg, google.antigravity" >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto RUN
)

:: 2. Try Python Launcher (standard on Windows)
py -3 -c "import moviepy, whisper, imageio_ffmpeg, google.antigravity" >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3
    goto RUN
)

:: 3. Try fallback to standard Windows Python installation path
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -c "import moviepy, whisper, imageio_ffmpeg, google.antigravity" >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto RUN
)

:: If none found, show error
echo [!] ERROR: Required Python packages are missing or Python is not configured correctly.
echo Please run the following command in your terminal first:
echo pip install -r requirements.txt
echo.
pause
exit /b

:RUN
echo [*] Environment verified. Launching application...
%PYTHON_CMD% autoclip.py
pause
