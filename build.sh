#!/bin/bash
# MacOS/Linux build script

# Setup virtual env if missing
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "Cleaning previous builds..."
rm -rf build dist *.spec

echo "Building executable with PyInstaller..."
pyinstaller --noconfirm --onedir --windowed --name "SubtitleTranslator" --add-data "core:core" --add-data "ui:ui" main.py

echo "Build complete. Check the 'dist' folder."
