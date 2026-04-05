#!/bin/bash
# Cross-compiling Windows exe via Docker
echo "====================================="
echo "Building Windows App via Docker..."
echo "====================================="
echo ""
echo "Note: This will download a lightweight Windows/Wine container, install dependencies, and build the exe."

docker run --rm -v "$(pwd):/src/" cdrx/pyinstaller-windows:python3 -c "
echo '=> Installing Python dependencies for Windows...' && \
pip install -r requirements.txt && \
echo '=> Running PyInstaller (Windows Build)...' && \
pyinstaller --noconfirm --onedir --windowed --name 'SubtitleTranslator' --add-data 'core;core' --add-data 'ui;ui' main.py
"

if [ $? -eq 0 ]; then
    echo "====================================="
    echo "Done! 🎉 Check the 'dist/SubtitleTranslator' directory."
else
    echo "Build failed. Ensure Docker is running."
fi
