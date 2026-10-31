"""Trains the FINAL whiff-per-swing model on the full season and uploads it to S3.
1) Early stopping on the last 14 days picks the number of trees.
2) Refit on ALL data with that tree count, so the final model learns from every month.
Quality comes from the rolling evaluation (saved as the model card), since a model trained on all data
can't be fairly tested on that same data. Category lists are saved so the app scores with identical codes."""
import json
import os
from datetime import datetime, timezone

import lightgbm as lgb
import pandas as pd

from src.ingest.s3_utils import BUCKET, _s3
from src.model.train_whiff import CATEGORICAL, FEATURES, LGB_PARAMS, OUT, TARGET, fit_model, load

S3_PREFIX = "ml/whiff_model"


def main() -> None:
    df = load()
    last = df.game_date.max()
    valid_start = last - pd.Timedelta(days=13)
    train = df[df.game_date < valid_start]
    valid = df[df.game_date >= valid_start]
    print(f"step 1: train {len(train):,} | early-stopping window {len(valid):,} ({valid_start.date()} to {last.date()})")

    probe = fit_model(train, valid, FEATURES)
    n_trees = probe.best_iteration_
    print(f"step 1: best number of trees = {n_trees}")

    params = {**LGB_PARAMS, "n_estimators": n_trees}
    final = lgb.LGBMClassifier(**params)
    final.fit(df[FEATURES], df[TARGET])
    print(f"step 2: refit on all {len(df):,} swings ({df.game_date.min().date()} to {last.date()})")

    model_path = OUT / "final_model.txt"
    final.booster_.save_model(str(model_path))

    rolling_path = OUT / "rolling_baseline.json"
    rolling = json.loads(rolling_path.read_text()) if rolling_path.exists() else []
    meta = {
        "model": "whiff_per_swing_lightgbm",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "train_dates": [str(df.game_date.min().date()), str(last.date())],
        "train_rows": int(len(df)),
        "base_whiff_rate": round(float(df[TARGET].mean()), 4),
        "n_trees": int(n_trees),
        "params": params,
        "features": FEATURES,
        "categories": {c: [str(x) for x in df[c].cat.categories] for c in CATEGORICAL},
        "evaluation": {
            "method": "rolling walk-forward (test months Jun-Sep), same features and params",
            "folds": rolling,
        },
    }
    meta_path = OUT / "final_model_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    _s3.upload_file(str(model_path), BUCKET, f"{S3_PREFIX}/model.txt")
    _s3.upload_file(str(meta_path), BUCKET, f"{S3_PREFIX}/model_meta.json")
    print(f"uploaded model and metadata to s3://{BUCKET}/{S3_PREFIX}/")


if __name__ == "__main__":
    main()
