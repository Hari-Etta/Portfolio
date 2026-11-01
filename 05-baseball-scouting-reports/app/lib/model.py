"""Loads the whiff model from S3 (read-only key) and builds planner features the same way training did."""
import json

import lightgbm as lgb
import numpy as np
import pandas as pd
import streamlit as st

from lib.data import _connection

FASTBALLS = {"FF", "SI", "FC", "FA"}
GROUPS = {**{t: "fastball" for t in FASTBALLS},
          **{t: "breaking" for t in ["SL", "ST", "CU", "KC", "SV", "CS"]},
          **{t: "offspeed" for t in ["CH", "FS", "FO", "SC"]}}
ZONE_HALF_WIDTH = 0.828   # half plate + ball radius (ft), same as int_pitches
TYPICAL_ZONE_HEIGHT = 1.8 # ft; gold tables don't store each batter's zone size


@st.cache_resource(show_spinner="Loading whiff model...")
def load_model() -> tuple[lgb.Booster, dict]:
    con, bucket = _connection(), st.secrets["aws"]["bucket"]
    model_txt = con.execute(f"SELECT content FROM read_text('s3://{bucket}/ml/whiff_model/model.txt')").fetchone()[0]
    meta_txt = con.execute(f"SELECT content FROM read_text('s3://{bucket}/ml/whiff_model/model_meta.json')").fetchone()[0]
    return lgb.Booster(model_str=model_txt), json.loads(meta_txt)


def attack_zone(x_away: np.ndarray, z_norm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """zone_ratio and attack zone, matching int_pitches (with a typical zone height)."""
    half_h = TYPICAL_ZONE_HEIGHT / 2 + 0.12
    ratio = np.maximum(np.abs(x_away) / ZONE_HALF_WIDTH, np.abs(z_norm - 0.5) * TYPICAL_ZONE_HEIGHT / half_h)
    zone = np.select([ratio < 0.67, ratio < 1.33, ratio < 2.0], ["heart", "shadow", "chase"], default="waste")
    return ratio, zone


def predict(booster: lgb.Booster, meta: dict, rows: pd.DataFrame) -> np.ndarray:
    X = rows[meta["features"]].copy()
    for col, cats in meta["categories"].items():
        X[col] = pd.Categorical(X[col].astype("string"), categories=cats)
    X["same_side"] = X["same_side"].astype("float")
    return booster.predict(X)
