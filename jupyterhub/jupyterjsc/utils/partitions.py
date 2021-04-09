import json
import os


def get_default_partitions():
    default_partitions_path = os.environ.get("DEFAULT_PARTITIONS_PATH")
    with open(default_partitions_path, "r") as f:
        default_partitions = json.load(f)
    return default_partitions
