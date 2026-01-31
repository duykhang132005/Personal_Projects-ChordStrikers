@echo off
echo Setting up ChordStrikers Environment...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment found.
)

REM Activate virtual environment and install dependencies
echo Installing dependencies...
call venv\Scripts\activate
pip install -r requirements.txt

echo Setup complete!
pause
