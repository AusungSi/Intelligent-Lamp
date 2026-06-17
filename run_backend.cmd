@echo off
cd /d "%~dp0"
call D:\miniconda3\condabin\conda.bat activate studypilot
python backend\run_local.py
