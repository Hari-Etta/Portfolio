"""Trains the whiff-per-swing model (Phase 3).
Time-based split, never random: train = Mar-Jul, validation = Aug (early stopping only),
test = Sep (untouched until final evaluation). Reports log-loss, AUC and Brier against a
constant baseline (the training whiff rate), plus a calibration table and plot on the test month.
LGB_PARAMS and fit_model are shared with eval_rolling.py so every evaluation uses the same model."""
import json
import os
from pathlib import Path

import duckdb
import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

load_dotenv()
OUT = Path("artifacts/whiff_model")
OUT.mkdir(parents=True, exist_ok=True)

CATEGORICAL = ["pitch_type", "pitch_group", "attack_zone", "p_throws", "stand"]
NUMERIC = [
    "release_speed", "spin_rate", "arm_angle", "ivb_in", "arm_side_break_in",
    "plate_x_away", "plate_z_norm", "zone_ratio",
    "velo_diff_fb", "ivb_diff_fb", "hb_diff_fb",
    "balls", "strikes", "same_side",
    "bat_prior_swings", "bat_prior_whiff_rate", "bat_grp_prior_swings", "bat_grp_prior_whiff_rate",
    "pit_prior_swings", "pit_prior_whiff_rate", "pit_type_prior_swings", "pit_type_prior_whiff_rate",
]
FEATURES = CATEGORICAL + NUMERIC
TARGET = "is_whiff"
TRAIN_END = pd.Timestamp("2026-07-31")
VALID_END = pd.Timestamp("2026-08-31")

LGB_PARAMS = dict(
    objective="binary",
    n_estimators=3000,
    learning_rate=0.03,
    num_leaves=63,
    min_child_samples=200,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    verbose=-1,
)


def load() -> pd.DataFrame:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""
        CREATE SECRET s3_secret (
            TYPE S3,
            KEY_ID '{os.environ["AWS_ACCESS_KEY_ID"]}',
            SECRET '{os.environ["AWS_SECRET_ACCESS_KEY"]}',
            REGION '{os.environ.get("AWS_REGION", "us-east-2")}'
        );
    """)
    df = con.execute(
        f"SELECT * FROM read_parquet('s3://{os.environ['S3_BUCKET']}/ml/whiff_features.parquet')"
    ).df()
    df["game_date"] = pd.to_datetime(df["game_date"])
    df["same_side"] = df["same_side"].astype("float")
    for c in CATEGORICAL:
        df[c] = df[c].astype("category")  # categories fixed on the full data, so all splits share them
    return df


def fit_model(train: pd.DataFrame, valid: pd.DataFrame, features: list[str]) -> lgb.LGBMClassifier:
    """Fits LightGBM with early stopping on the validation set (validation is never used for scoring)."""
    model = lgb.LGBMClassifier(**LGB_PARAMS)
    model.fit(
        train[features], train[TARGET],
        eval_X=valid[features],
        eval_y=valid[TARGET],
        eval_metric="binary_logloss",
        callbacks=[lgb.early_stopping(100, verbose=False)],
    )
    return model


def calibration_error(y: pd.Series, p: np.ndarray, bins: int = 10) -> float:
    """Average |predicted - actual| across equal-size bins (0.01 = about 1 point off on average)."""
    frac_pos, mean_pred = calibration_curve(y, p, n_bins=bins, strategy="quantile")
    return float(np.mean(np.abs(frac_pos - mean_pred)))


def evaluate(y: pd.Series, p: np.ndarray, base_rate: float, name: str) -> dict:
    return {
        "split": name,
        "n": int(len(y)),
        "whiff_rate": round(float(y.mean()), 4),
        "log_loss": round(float(log_loss(y, p)), 4),
        "baseline_log_loss": round(float(log_loss(y, np.full(len(y), base_rate))), 4),
        "auc": round(float(roc_auc_score(y, p)), 4),
        "brier": round(float(brier_score_loss(y, p)), 4),
    }


def main() -> None:
    df = load()
    train = df[df.game_date <= TRAIN_END]
    valid = df[(df.game_date > TRAIN_END) & (df.game_date <= VALID_END)]
    test = df[df.game_date > VALID_END]
    print(f"train {len(train):,} | valid {len(valid):,} | test {len(test):,}")

    base_rate = float(train[TARGET].mean())
    model = fit_model(train, valid, FEATURES)
    print(f"best iteration: {model.best_iteration_}")

    results = []
    for name, part in [("train", train), ("valid", valid), ("test", test)]:
        p = model.predict_proba(part[FEATURES])[:, 1]
        results.append(evaluate(part[TARGET], p, base_rate, name))
    print("\n=== metrics ===")
    print(pd.DataFrame(results).to_string(index=False))

    p_test = model.predict_proba(test[FEATURES])[:, 1]
    frac_pos, mean_pred = calibration_curve(test[TARGET], p_test, n_bins=10, strategy="quantile")
    calib = pd.DataFrame({"predicted": mean_pred, "actual": frac_pos})
    print("\n=== calibration (test, 10 equal-size bins) ===")
    print(calib.round(3).to_string(index=False))

    plt.figure(figsize=(5, 5))
    plt.plot([0, 1], [0, 1], "--", color="gray", label="perfect")
    plt.plot(mean_pred, frac_pos, "o-", label="model")
    plt.xlabel("predicted whiff probability")
    plt.ylabel("actual whiff rate")
    plt.title("Calibration: September (unseen)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "calibration_test.png", dpi=120)

    imp = pd.Series(model.booster_.feature_importance("gain"), index=FEATURES)
    imp = (100 * imp / imp.sum()).sort_values(ascending=False)
    print("\n=== feature importance (% of total gain, top 12) ===")
    print(imp.head(12).round(1).to_string())

    model.booster_.save_model(str(OUT / "model.txt"), num_iteration=model.best_iteration_)
    (OUT / "metrics.json").write_text(json.dumps({
        "metrics": results,
        "calibration_test": calib.round(4).to_dict(orient="records"),
        "best_iteration": model.best_iteration_,
        "train_end": str(TRAIN_END.date()),
        "valid_end": str(VALID_END.date()),
        "features": FEATURES,
    }, indent=2))
    print(f"\nsaved model, metrics and calibration plot to {OUT}")


if __name__ == "__main__":
    main()
