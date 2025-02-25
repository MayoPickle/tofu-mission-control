import json

class ConfigLoader:
    def __init__(self, config_path="config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def get_config(self):
        return self.config
