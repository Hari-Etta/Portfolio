"""Pulls the Olist Brazilian E-Commerce dataset from Kaggle via API straight into data/raw/.
Requires a Kaggle API token at ~/.kaggle/kaggle.json (see README for setup)."""
import os
from kaggle.api.kaggle_api_extended import KaggleApi

DATASET = "olistbr/brazilian-ecommerce"
DEST_DIR = "data/raw"

def download_olist_dataset(dest_dir: str = DEST_DIR):
    os.makedirs(dest_dir, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    print(f"Downloading {DATASET} to {dest_dir}/ ...")
    api.dataset_download_files(DATASET, path=dest_dir, unzip=True)
    print("Done. Files in data/raw/:")
    for f in os.listdir(dest_dir):
        print(f"  {f}")

if __name__ == "__main__":
    download_olist_dataset()