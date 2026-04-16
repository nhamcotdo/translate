import customtkinter as ctk

from core.config_manager import ConfigManager
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.translate_tab import TranslateTab
from ui.tabs.extract_tab import ExtractTab
from ui.tabs.summary_tab import SummaryTab


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Subtitle Translator")
        self.geometry("1000x720")
        self.minsize(800, 600)

        self.config_manager = ConfigManager()

        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        self.tabview.add("Translate")
        self.tabview.add("Extract Subtitles")
        self.tabview.add("Video Summary")
        self.tabview.add("Settings")

        # Instantiate tabs
        self.translate_tab = TranslateTab(self.tabview.tab("Translate"), self.config_manager)
        self.translate_tab.pack(expand=True, fill="both")

        self.extract_tab = ExtractTab(self.tabview.tab("Extract Subtitles"), self.config_manager)
        self.extract_tab.pack(expand=True, fill="both")
        self.extract_tab.set_translate_tab(self.translate_tab)

        self.summary_tab = SummaryTab(self.tabview.tab("Video Summary"), self.config_manager, self.translate_tab)
        self.summary_tab.pack(expand=True, fill="both")

        self.settings_tab = SettingsTab(
            self.tabview.tab("Settings"),
            self.config_manager,
            providers_updated_callback=self.translate_tab.refresh_providers,
        )
        self.settings_tab.pack(expand=True, fill="both")

        # MacOS Tkinter black screen workaround
        self.after(100, self._mac_redraw)

    def _mac_redraw(self):
        self.geometry("1001x720")
        self.after(50, lambda: self.geometry("1000x720"))
