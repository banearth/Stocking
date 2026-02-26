@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [INFO] Checking environment...

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python first.
    pause
    exit /b
)

:: Check venv
if not exist .venv (
    echo [INFO] Virtual environment not found. Creating one...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
    
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
    
    echo [INFO] Upgrading pip...
    python -m pip install --upgrade pip
    
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b
    )
) else (
    echo [INFO] Virtual environment found. Activating...
    call .venv\Scripts\activate.bat
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to activate virtual environment.
        echo Try deleting the .venv folder and running this script again.
        pause
        exit /b
    )
)

:: Start App
echo [INFO] Starting Streamlit app...
start "Stocking App" cmd /k "python -m streamlit run app.py"

:: Open Browser
timeout /t 3 /nobreak >nul
start http://localhost:8501

echo [INFO] App launched! You can close this window if the app is running.
:: pause
