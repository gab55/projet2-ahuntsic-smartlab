import yaml
from pathlib import Path

def get_config():
    config_path = Path(__file__).resolve().parent / "config.yaml"
    if not config_path.exists():
        raise ValueError("config.yaml not found")
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
        if config is None:
            raise ValueError("config.yaml is empty")
        return config

def abs_path(name, path=""):
    if path == "":
        return Path(__file__).resolve().parent / name
    else:
        return Path(__file__).resolve().parent / path / name