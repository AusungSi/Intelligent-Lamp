@echo off
cd /d "%~dp0"
call C:\Users\lyt\anaconda3\condabin\conda.bat activate smartled
python backend\run_local.py
