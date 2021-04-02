import json
import os


def get_maintenance_list():
    maintenance_path = os.environ.get("MAINTENANCE_PATH")
    with open(maintenance_path, "r") as f:
        maintenance_list = json.load(f)
    return maintenance_list
