@echo off
setlocal

REM Set environment directory name
set "VENV_DIR=venv"

REM Check if virtual environment exists
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Install requirements
echo Installing required packages...
pip install --upgrade pip
pip install -r requirements.txt

REM Run the application
echo Starting AINA...
python main.py

endlocal
pause
