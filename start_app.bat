@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start "" .venv\Scripts\streamlit.exe run app.py
timeout /t 5 /nobreak >nul
start http://localhost:8501
