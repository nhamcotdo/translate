import customtkinter as ctk
from tkinter import messagebox
import json
from typing import Callable
from ui.translations import get_tr

class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, providers_updated_callback: Callable, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_manager = config_manager
        self.providers_updated_callback = providers_updated_callback
        self.tr = get_tr(self.config_manager)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # --- Default Providers Card ---
        self.def_card = ctk.CTkFrame(self.main_container)
        self.def_card.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.def_card.grid_columnconfigure(1, weight=1)
        
        # --- App Settings ---
        self.app_settings_card = ctk.CTkFrame(self.main_container)
        self.app_settings_card.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.app_settings_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.app_settings_card, text=self.tr("Settings"), font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        ctk.CTkLabel(self.app_settings_card, text=self.tr("Language:")).grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        current_lang = "English" if self.config_manager.get("language", "en") == "en" else "Tiếng Việt"
        self.lang_var = ctk.StringVar(value=current_lang)
        self.lang_dropdown = ctk.CTkOptionMenu(self.app_settings_card, variable=self.lang_var, values=["English", "Tiếng Việt"], command=self.on_language_change, cursor="hand2")
        self.lang_dropdown.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="w")

        # --- Default Providers Card ---
        self.def_card = ctk.CTkFrame(self.main_container)
        self.def_card.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        self.def_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.def_card, text=self.tr("Built-in Providers"), font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")
        
        ctk.CTkLabel(self.def_card, text=self.tr("OpenAI Keys:")).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        self.openai_entry = ctk.CTkEntry(self.def_card, placeholder_text="sk-proj-..., sk-proj-...")
        self.openai_entry.grid(row=1, column=1, padx=20, pady=(0, 10), sticky="we")
        self.openai_entry.insert(0, ",".join(self.config_manager.get_keys("openai")))

        ctk.CTkLabel(self.def_card, text=self.tr("Gemini Keys:")).grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")
        self.gemini_entry = ctk.CTkEntry(self.def_card, placeholder_text="AIzaSy..., AIzaSy...")
        self.gemini_entry.grid(row=2, column=1, padx=20, pady=(0, 10), sticky="we")
        self.gemini_entry.insert(0, ",".join(self.config_manager.get_keys("gemini")))

        ctk.CTkLabel(self.def_card, text=self.tr("NVIDIA Keys:")).grid(row=3, column=0, padx=20, pady=(0, 15), sticky="w")
        self.nvidia_entry = ctk.CTkEntry(self.def_card, placeholder_text="nvapi-..., nvapi-...")
        self.nvidia_entry.grid(row=3, column=1, padx=20, pady=(0, 15), sticky="we")
        self.nvidia_entry.insert(0, ",".join(self.config_manager.get_keys("nvidia")))

        self.save_def_btn = ctk.CTkButton(self.def_card, text=self.tr("💾 Save Built-in Keys"), command=self.save_default_keys, cursor="hand2")
        self.save_def_btn.grid(row=4, column=1, padx=20, pady=(0, 20), sticky="e")

        # --- Custom Providers Card ---
        self.cust_card = ctk.CTkFrame(self.main_container)
        self.cust_card.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self.cust_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.cust_card, text=self.tr("Custom OpenAI-Compatible Providers"), font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 15), sticky="w")

        ctk.CTkLabel(self.cust_card, text=self.tr("Provider ID:")).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        self.cust_id_entry = ctk.CTkEntry(self.cust_card, placeholder_text="e.g. together, groq, deepseek")
        self.cust_id_entry.grid(row=1, column=1, padx=20, pady=(0, 10), sticky="we")

        ctk.CTkLabel(self.cust_card, text=self.tr("Display Name:")).grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")
        self.cust_name_entry = ctk.CTkEntry(self.cust_card, placeholder_text="e.g. Together AI")
        self.cust_name_entry.grid(row=2, column=1, padx=20, pady=(0, 10), sticky="we")

        ctk.CTkLabel(self.cust_card, text=self.tr("Base URL:")).grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")
        self.cust_url_entry = ctk.CTkEntry(self.cust_card, placeholder_text="e.g. https://api.together.xyz/v1")
        self.cust_url_entry.grid(row=3, column=1, padx=20, pady=(0, 10), sticky="we")

        ctk.CTkLabel(self.cust_card, text=self.tr("API Keys:")).grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")
        self.cust_keys_entry = ctk.CTkEntry(self.cust_card, placeholder_text="Comma-separated keys")
        self.cust_keys_entry.grid(row=4, column=1, padx=20, pady=(0, 10), sticky="we")

        ctk.CTkLabel(self.cust_card, text=self.tr("Models:")).grid(row=5, column=0, padx=20, pady=(0, 10), sticky="w")
        self.cust_models_entry = ctk.CTkEntry(self.cust_card, placeholder_text="meta-llama/Llama-3-70b-chat-hf, ...")
        self.cust_models_entry.grid(row=5, column=1, padx=20, pady=(0, 10), sticky="we")

        ctk.CTkLabel(self.cust_card, text=self.tr("Headers (JSON):")).grid(row=6, column=0, padx=20, pady=(0, 15), sticky="w")
        self.cust_headers_entry = ctk.CTkEntry(self.cust_card, placeholder_text='{"HTTP-Referer": "https://myapp.com"}')
        self.cust_headers_entry.grid(row=6, column=1, padx=20, pady=(0, 15), sticky="we")

        self.add_cust_btn = ctk.CTkButton(self.cust_card, text=self.tr("➕ Add / Update Custom Provider"), command=self.save_custom_provider, cursor="hand2")
        self.add_cust_btn.grid(row=7, column=1, padx=20, pady=(0, 20), sticky="e")

    def on_language_change(self, value):
        new_lang = "en" if value == "English" else "vi"
        if new_lang != self.config_manager.get("language"):
            self.config_manager.set("language", new_lang)
            messagebox.showinfo(self.tr("Restart Required"), self.tr("Please restart the application to apply language changes."))

    def save_default_keys(self):
        o_keys = [k.strip() for k in self.openai_entry.get().split(",") if k.strip()]
        g_keys = [k.strip() for k in self.gemini_entry.get().split(",") if k.strip()]
        n_keys = [k.strip() for k in self.nvidia_entry.get().split(",") if k.strip()]
        
        self.config_manager.set_keys("openai", o_keys)
        self.config_manager.set_keys("gemini", g_keys)
        self.config_manager.set_keys("nvidia", n_keys)
        messagebox.showinfo(self.tr("Success"), self.tr("Default keys saved successfully."))

    def save_custom_provider(self):
        p_id = self.cust_id_entry.get().strip()
        name = self.cust_name_entry.get().strip()
        url = self.cust_url_entry.get().strip()
        keys = [k.strip() for k in self.cust_keys_entry.get().split(",") if k.strip()]
        models = [m.strip() for m in self.cust_models_entry.get().split(",") if m.strip()]
        headers_str = self.cust_headers_entry.get().strip()
        
        if not p_id or not name or not url:
            messagebox.showerror(self.tr("Error"), self.tr("ID, Name, and Base URL are required."))
            return

        headers = {}
        if headers_str:
            try:
                headers = json.loads(headers_str)
            except Exception:
                messagebox.showerror(self.tr("Error"), self.tr("Invalid JSON format for headers."))
                return

        payload = {
            "name": name,
            "base_url": url,
            "keys": keys,
            "models": models,
            "headers": headers
        }
        self.config_manager.add_custom_provider(p_id, payload)
        messagebox.showinfo(self.tr("Success"), self.tr("Custom provider '{name}' saved successfully.", name=name))
        
        self.cust_id_entry.delete(0, 'end')
        self.cust_name_entry.delete(0, 'end')
        self.cust_url_entry.delete(0, 'end')
        self.cust_keys_entry.delete(0, 'end')
        self.cust_models_entry.delete(0, 'end')
        self.cust_headers_entry.delete(0, 'end')

        if self.providers_updated_callback:
            self.providers_updated_callback()
