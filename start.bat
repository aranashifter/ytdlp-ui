@echo off
cd /d "%~dp0"
title yt-dlp Web UI

if not exist yt-dlp.exe goto setup
if not exist ffmpeg.exe goto setup
if not exist deno.exe goto setup
goto run

:setup
echo Prothombar chalachhen. Dorkari tool gulo download hochhe, 2-5 minute lagte pare...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 2 goto end
if errorlevel 1 goto end

:run
where py >nul 2>nul
if %errorlevel%==0 (
  py ytdlp_ui.py
  goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
  python ytdlp_ui.py
  goto end
)
echo Python paoa jay nai. start.bat abar chalan.
:end
pause
