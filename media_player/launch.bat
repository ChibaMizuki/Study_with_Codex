@echo off
cd /d "%~dp0"
if exist "dist\MediaPlayer\MediaPlayer.exe" (
    start "" "dist\MediaPlayer\MediaPlayer.exe"
) else (
    uv run python main.py
)
