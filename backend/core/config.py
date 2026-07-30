import os
import json

class ConfigManager:
    """
    Centralized configuration management.
    Reads from environment variables and JSON configs.
    """
    def __init__(self):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
        os.makedirs(self.config_dir, exist_ok=True)
        self._cache = {}

    def get_config(self, module: str) -> dict:
        if module in self._cache:
            return self._cache[module]
            
        file_path = os.path.join(self.config_dir, f"{module}.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
                self._cache[module] = data
                return data
        
        # Default empty config
        return {}
        
config = ConfigManager()
