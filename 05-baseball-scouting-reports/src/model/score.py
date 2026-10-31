"""Loads the whiff model from S3 and scores swings with the EXACT category codes used in training.
Shared by batch scoring and the Streamlit app, so every caller prepares features the same way."""
import json
import os
import tempfile

import lightgbm as lgb
import pandas as pd

from src.ingest.s3_utils import BUCKET, _s3

S3_PREFIX = "ml/whiff_model"


def load_model() -> tuple[lgb.Booster, dict]:
    tmp = tempfile.mkdtemp()
    model_path = os.path.join(tmp, "model.txt")
    meta_path = os.path.join(tmp, "model_meta.json")
    _s3.download_file(BUCKET, f"{S3_PREFIX}/model.txt", model_path)
    _s3.download_file(BUCKET, f"{S3_PREFIX}/model_meta.json", meta_path)
    with open(meta_path) as f:
        meta = json.load(f)
    return lgb.Booster(model_file=model_path), meta


def prepare(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    """Selects the model's features in training order and applies the saved category lists."""
    missing = [c for c in meta["features"] if c not in df.columns]
    if missing:
        raise ValueError(f"missing feature columns: {missing}")
    X = df[meta["features"]].copy()
    for col, cats in meta["categories"].items():
        X[col] = pd.Categorical(X[col].astype("string"), categories=cats)
    X["same_side"] = X["same_side"].astype("float")
    return X


def predict(booster: lgb.Booster, meta: dict, df: pd.DataFrame):
    return booster.predict(prepare(df, meta))
