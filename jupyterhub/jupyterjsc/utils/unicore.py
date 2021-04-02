import json
import os


def get_unicore_config():
    unicore_config_path = os.environ.get("UNICORE_CONFIG_PATH")
    with open(unicore_config_path, "r") as f:
        unicore_config = json.load(f)
    return unicore_config
