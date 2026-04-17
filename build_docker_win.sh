#!/bin/bash
# Cross-compiling Windows exe via Docker
echo "====================================="
echo "Building Windows App via Docker..."
echo "====================================="
echo ""
echo "Note: This will download a lightweight Windows/Wine container, install dependencies, and build the exe."

docker run --rm -v "$(pwd):/src/" -w /src/ --platform linux/amd64 tobix/pywine:3.10 bash -c "
echo '=> Installing Python dependencies for Windows...' && \
wine pip install -r requirements.txt && \
echo '=> Running PyInstaller (Windows Build)...' && \
wine pyinstaller --noconfirm --onedir --windowed --name 'SubtitleTranslator' --add-data 'core;core' --add-data 'ui;ui' --add-data 'theme.json;.' --add-data 'settings.json;.' --collect-all imageio_ffmpeg main.py
"

if [ $? -eq 0 ]; then
    echo "====================================="
    echo "Done! 🎉 Check the 'dist/SubtitleTranslator' directory."
else
    echo "Build failed. Ensure Docker is running."
fi
