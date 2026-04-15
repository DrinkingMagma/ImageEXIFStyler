import configparser
from pathlib import Path

from core import CONFIG_PATH, PROJECT_ROOT

fonts_dir = PROJECT_ROOT / "config" / "fonts"
logos_dir = PROJECT_ROOT / "config" / "logos"
templates_dir = PROJECT_ROOT / "config" / "templates"

def load_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding='utf-8')
    return config


def save_config(config: configparser.ConfigParser) -> None:
    config_path = Path(CONFIG_PATH)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open('w', encoding='utf-8') as f:
        config.write(f)
