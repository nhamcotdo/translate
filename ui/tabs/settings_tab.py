import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Any

class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, providers_updated_callback: Callable, **kwargs):
        super().__init__(master, **kwargs)
        self.config_manager = config_manager
        self.providers_updated_callback = providers_updated_callback

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # 1. Default Providers (OpenAI, Gemini)
        self.label_def = ctk.CTkLabel(self, text="Default Providers Keys", font=ctk.CTkFont(size=16, weight="bold"))
        self.label_def.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="w")
        
        # OpenAI
        self.openai_label = ctk.CTkLabel(self, text="OpenAI Keys (comma separated):")
        self.openai_label.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        
        self.openai_entry = ctk.CTkEntry(self, width=400)
        self.openai_entry.grid(row=1, column=1, padx=20, pady=5, sticky="we")
        openai_keys = self.config_manager.get_keys("openai")
        self.openai_entry.insert(0, ",".join(openai_keys))

        # Gemini
        self.gemini_label = ctk.CTkLabel(self, text="Gemini Keys (comma separated):")
        self.gemini_label.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        
        self.gemini_entry = ctk.CTkEntry(self, width=400)
        self.gemini_entry.grid(row=2, column=1, padx=20, pady=5, sticky="we")
        gemini_keys = self.config_manager.get_keys("gemini")
        self.gemini_entry.insert(0, ",".join(gemini_keys))

        # NVIDIA
        self.nvidia_label = ctk.CTkLabel(self, text="NVIDIA Keys (comma separated):")
        self.nvidia_label.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        
        self.nvidia_entry = ctk.CTkEntry(self, width=400)
        self.nvidia_entry.grid(row=3, column=1, padx=20, pady=5, sticky="we")
        nvidia_keys = self.config_manager.get_keys("nvidia")
        self.nvidia_entry.insert(0, ",".join(nvidia_keys))

        self.save_def_btn = ctk.CTkButton(self, text="Save Default Keys", command=self.save_default_keys)
        self.save_def_btn.grid(row=4, column=1, padx=20, pady=10, sticky="e")

        # 2. Custom Providers
        self.label_cust = ctk.CTkLabel(self, text="Custom OpenAI-compatible Providers", font=ctk.CTkFont(size=16, weight="bold"))
        self.label_cust.grid(row=5, column=0, columnspan=2, padx=20, pady=(30, 10), sticky="w")

        # Form
        self.cust_id_label = ctk.CTkLabel(self, text="Provider ID:")
        self.cust_id_label.grid(row=6, column=0, padx=20, pady=5, sticky="w")
        self.cust_id_entry = ctk.CTkEntry(self)
        self.cust_id_entry.grid(row=6, column=1, padx=20, pady=5, sticky="we")

        self.cust_name_label = ctk.CTkLabel(self, text="Display Name:")
        self.cust_name_label.grid(row=7, column=0, padx=20, pady=5, sticky="w")
        self.cust_name_entry = ctk.CTkEntry(self)
        self.cust_name_entry.grid(row=7, column=1, padx=20, pady=5, sticky="we")

        self.cust_url_label = ctk.CTkLabel(self, text="Base URL:")
        self.cust_url_label.grid(row=8, column=0, padx=20, pady=5, sticky="w")
        self.cust_url_entry = ctk.CTkEntry(self)
        self.cust_url_entry.grid(row=8, column=1, padx=20, pady=5, sticky="we")

        self.cust_keys_label = ctk.CTkLabel(self, text="API Keys (comma separated):")
        self.cust_keys_label.grid(row=9, column=0, padx=20, pady=5, sticky="w")
        self.cust_keys_entry = ctk.CTkEntry(self)
        self.cust_keys_entry.grid(row=9, column=1, padx=20, pady=5, sticky="we")

        self.cust_models_label = ctk.CTkLabel(self, text="Models (comma separated, e.g. gpt-4o,claude-3):")
        self.cust_models_label.grid(row=10, column=0, padx=20, pady=5, sticky="w")
        self.cust_models_entry = ctk.CTkEntry(self)
        self.cust_models_entry.grid(row=10, column=1, padx=20, pady=5, sticky="we")

        self.cust_headers_label = ctk.CTkLabel(self, text="Headers (JSON, e.g. {\"X-Custom\": \"val\"}):")
        self.cust_headers_label.grid(row=11, column=0, padx=20, pady=5, sticky="w")
        self.cust_headers_entry = ctk.CTkEntry(self)
        self.cust_headers_entry.grid(row=11, column=1, padx=20, pady=5, sticky="we")

        self.add_cust_btn = ctk.CTkButton(self, text="Add / Update Custom Provider", command=self.save_custom_provider)
        self.add_cust_btn.grid(row=12, column=1, padx=20, pady=10, sticky="e")

    def save_default_keys(self):
        o_keys = [k.strip() for k in self.openai_entry.get().split(",") if k.strip()]
        g_keys = [k.strip() for k in self.gemini_entry.get().split(",") if k.strip()]
        n_keys = [k.strip() for k in self.nvidia_entry.get().split(",") if k.strip()]
        
        self.config_manager.set_keys("openai", o_keys)
        self.config_manager.set_keys("gemini", g_keys)
        self.config_manager.set_keys("nvidia", n_keys)
        messagebox.showinfo("Success", "Default keys saved successfully.")

    def save_custom_provider(self):
        p_id = self.cust_id_entry.get().strip()
        name = self.cust_name_entry.get().strip()
        url = self.cust_url_entry.get().strip()
        keys = [k.strip() for k in self.cust_keys_entry.get().split(",") if k.strip()]
        models = [m.strip() for m in self.cust_models_entry.get().split(",") if m.strip()]
        headers_str = self.cust_headers_entry.get().strip()
        
        if not p_id or not name or not url:
            messagebox.showerror("Error", "ID, Name, and Base URL are required.")
            return

        import json
        headers = {}
        if headers_str:
            try:
                headers = json.loads(headers_str)
            except Exception:
                messagebox.showerror("Error", "Invalid JSON format for headers.")
                return

        payload = {
            "name": name,
            "base_url": url,
            "keys": keys,
            "models": models,
            "headers": headers
        }
        self.config_manager.add_custom_provider(p_id, payload)
        messagebox.showinfo("Success", f"Custom provider '{name}' saved successfully.")
        
        # Clear fields
        self.cust_id_entry.delete(0, 'end')
        self.cust_name_entry.delete(0, 'end')
        self.cust_url_entry.delete(0, 'end')
        self.cust_keys_entry.delete(0, 'end')
        self.cust_models_entry.delete(0, 'end')
        self.cust_headers_entry.delete(0, 'end')

        if self.providers_updated_callback:
            self.providers_updated_callback()
