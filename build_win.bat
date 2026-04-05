@echo off
echo ===================================
echo Windows Build Script for Subtitle Translator
echo ===================================

REM Check for python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH!
    pause
    exit /b
)

REM Setup virtual env if missing
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Cleaning previous builds...
rmdir /s /q build dist 2>nul
del /q *.spec 2>nul

echo.
echo Building executable with PyInstaller...
REM Note: Windows uses semicolon (;) for --add-data separator
pyinstaller --noconfirm --onedir --windowed --name "SubtitleTranslator" --add-data "core;core" --add-data "ui;ui" main.py

echo.
echo Build complete! Check the 'dist\SubtitleTranslator' folder.
echo (You can run SubtitleTranslator.exe from there)
pause
