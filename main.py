import customtkinter as ctk
import sys
import os
import logging

# Ensure imports work from the script directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

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

# Ensure ffmpeg from imageio-ffmpeg is in the PATH so Whisper can find it
try:
    import imageio_ffmpeg
    import shutil
    import stat
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    
    # Whisper explicitly calls "ffmpeg". If the bundled binary is named differently
    # (e.g., ffmpeg-win32-v...exe), we need to create an exact 'ffmpeg.exe' copy.
    ffmpeg_alias = os.path.join(ffmpeg_dir, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if os.path.abspath(ffmpeg_exe) != os.path.abspath(ffmpeg_alias) and not os.path.exists(ffmpeg_alias):
        try:
            shutil.copyfile(ffmpeg_exe, ffmpeg_alias)
            st = os.stat(ffmpeg_alias)
            os.chmod(ffmpeg_alias, st.st_mode | stat.S_IEXEC)
        except Exception as e:
            logging.exception(f"Failed to create ffmpeg alias: {e}")
            
    os.environ["PATH"] += os.pathsep + ffmpeg_dir
    logging.info(f"Successfully added imageio-ffmpeg to PATH: {ffmpeg_dir}")
except Exception as e:
    logging.exception(f"Failed to configure imageio-ffmpeg: {e}")

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
