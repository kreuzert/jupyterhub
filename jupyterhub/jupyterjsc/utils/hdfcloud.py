import json
import os


def get_hdfcloud():
    hdf_cloud_path = os.environ.get("HDF_CLOUD_PATH")
    with open(hdf_cloud_path, "r") as f:
        hdf_cloud = json.load(f)
    return hdf_cloud
