#!/bin/bash
# MacOS/Linux build script

# Setup virtual env if missing
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo "Cleaning previous builds..."
rm -rf build dist *.spec

echo "Building executable with PyInstaller..."
python -m PyInstaller --noconfirm --onedir --windowed --name "SubtitleTranslator" --add-data "core:core" --add-data "ui:ui" --add-data "theme.json:." --add-data "settings.json:." --collect-all imageio_ffmpeg main.py

echo "Build complete. Check the 'dist' folder."
