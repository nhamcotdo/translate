import json
import os
import sys
from typing import Dict, List, Any

CONFIG_FILE = "settings.json"


def _get_config_path() -> str:
    """Resolve config path for both dev and PyInstaller-bundled mode.
    
    In bundled mode, settings.json is initially inside _MEIPASS (read-only).
    We store the writable copy next to the actual .exe so user changes persist.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        exe_dir = os.path.dirname(sys.executable)
        user_config = os.path.join(exe_dir, CONFIG_FILE)
        if not os.path.exists(user_config):
            # Copy default from bundle on first run
            bundled = os.path.join(sys._MEIPASS, CONFIG_FILE)
            if os.path.exists(bundled):
                import shutil
                shutil.copy2(bundled, user_config)
        return user_config
    else:
        # Dev mode — file next to the script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', CONFIG_FILE)


class ConfigManager:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or _get_config_path()
        self.config = self._load_config()

    def _get_default_config(self) -> Dict[str, Any]:
        return {
            "keys": {
                "openai": [],
                "gemini": [],
                "nvidia": []
            },
            "custom_providers": {},
            "default_provider": "openai",
            "default_model": "gpt-4o-mini",
            "key_selection_mode": "auto" # or "specific"
        }

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return self._get_default_config()
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Ensure shape
            default_conf = self._get_default_config()
            for k, v in default_conf.items():
                if k not in data:
                    data[k] = v
            if "custom_providers" not in data:
                data["custom_providers"] = {}
                
            return data
        except Exception:
            return self._get_default_config()

    def save_config(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    # Key management for default providers
    def get_keys(self, provider: str) -> List[str]:
        if provider in ["openai", "gemini", "nvidia"]:
            return self.config["keys"].get(provider, [])
        # For custom providers
        if provider in self.config["custom_providers"]:
            return self.config["custom_providers"][provider].get("keys", [])
        return []

    def set_keys(self, provider: str, keys: List[str]):
        if provider in ["openai", "gemini", "nvidia"]:
            self.config["keys"][provider] = keys
        elif provider in self.config["custom_providers"]:
            self.config["custom_providers"][provider]["keys"] = keys
        self.save_config()

    # Custom providers management
    def get_custom_providers(self) -> Dict[str, Any]:
        return self.config.get("custom_providers", {})

    def add_custom_provider(self, provider_id: str, payload: Dict[str, Any]):
        if "custom_providers" not in self.config:
            self.config["custom_providers"] = {}
        self.config["custom_providers"][provider_id] = payload
        self.save_config()

    def delete_custom_provider(self, provider_id: str):
        if provider_id in self.config.get("custom_providers", {}):
            del self.config["custom_providers"][provider_id]
            self.save_config()
            
    # Generic property access
    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)
        
    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save_config()
