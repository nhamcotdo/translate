import customtkinter as ctk
import sys
import os

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")

# Load custom theme
current_dir = os.path.dirname(os.path.abspath(__file__))
theme_path = os.path.join(current_dir, "theme.json")
if os.path.exists(theme_path):
    ctk.set_default_color_theme(theme_path)
else:
    ctk.set_default_color_theme("blue")

# Ensure imports work from the script directory
sys.path.insert(0, current_dir)

from ui.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
