import customtkinter as ctk
import sys
import os
import logging

# Ensure imports work from the script directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Ensure ffmpeg from imageio-ffmpeg is in the PATH so Whisper can find it
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_exe)
except ImportError:
    pass

# Set up logging for production and dev
if getattr(sys, 'frozen', False):
    log_dir = os.path.dirname(sys.executable)
else:
    log_dir = current_dir

log_path = os.path.join(log_dir, "app.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.info(f"Application started. Logging to {log_path}")

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")

# Load custom theme
theme_path = os.path.join(current_dir, "theme.json")
if os.path.exists(theme_path):
    ctk.set_default_color_theme(theme_path)
else:
    ctk.set_default_color_theme("blue")

from ui.app import App

if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        logging.exception("Unhandled exception occurred")
        raise
