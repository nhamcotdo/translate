import customtkinter as ctk

from core.config_manager import ConfigManager
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.translate_tab import TranslateTab

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AI Subtitle Translator")
        self.geometry("900x700")
        
        self.config_manager = ConfigManager()
        
        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Create Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.tabview.add("Translate")
        self.tabview.add("Settings")
        
        # Instantiate tabs
        self.translate_tab = TranslateTab(self.tabview.tab("Translate"), self.config_manager)
        self.translate_tab.pack(expand=True, fill="both")
        
        self.settings_tab = SettingsTab(self.tabview.tab("Settings"), self.config_manager, providers_updated_callback=self.translate_tab.refresh_providers)
        self.settings_tab.pack(expand=True, fill="both")
