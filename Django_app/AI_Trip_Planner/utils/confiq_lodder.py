import yaml
import os

def load_config(config_path: str = None) -> dict:
    if config_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "..", "Confiq", "config.yaml")
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config