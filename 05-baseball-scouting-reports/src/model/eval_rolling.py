"""Rolling (walk-forward) evaluation of the whiff model across the season.
For each test month: train on everything before it (minus the last 14 days), use those 14 days for early
stopping, then score the test month. Mimics predicting the future at that point in the season.
Uses the same LGB_PARAMS / fit_model as train_whiff.py. The --features option lets experiments compare
feature sets on identical folds."""
import argparse
import json

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, roc_auc_score

from src.model.train_whiff import FEATURES, OUT, TARGET, calibration_error, fit_model, load

TEST_MONTHS = ["2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01"]
VALID_DAYS = 14


def run(df: pd.DataFrame, features: list[str], label: str) -> pd.DataFrame:
    rows = []
    starts = [pd.Timestamp(s) for s in TEST_MONTHS]
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else df.game_date.max() + pd.Timedelta(days=1)
        valid_start = start - pd.Timedelta(days=VALID_DAYS)
        train = df[df.game_date < valid_start]
        valid = df[(df.game_date >= valid_start) & (df.game_date < start)]
        test = df[(df.game_date >= start) & (df.game_date < end)]

        model = fit_model(train, valid, features)
        p = model.predict_proba(test[features])[:, 1]
        base_rate = float(train[TARGET].mean())
        ll = log_loss(test[TARGET], p)
        base_ll = log_loss(test[TARGET], np.full(len(test), base_rate))
        rows.append({
            "features": label,
            "test_month": start.strftime("%Y-%m"),
            "train_n": len(train),
            "test_n": len(test),
            "log_loss": round(ll, 4),
            "baseline": round(base_ll, 4),
            "improvement_pct": round(100 * (base_ll - ll) / base_ll, 1),
            "auc": round(roc_auc_score(test[TARGET], p), 4),
            "calib_error": round(calibration_error(test[TARGET], p), 4),
            "best_iter": model.best_iteration_,
        })
        print(f"  {label}: test {rows[-1]['test_month']} done")
    return pd.DataFrame(rows)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--label", default="baseline_features")
    a = p.parse_args()

    df = load()
    res = run(df, FEATURES, a.label)
    print("\n=== rolling evaluation ===")
    print(res.to_string(index=False))
    print("\n=== average across folds ===")
    print(res[["log_loss", "baseline", "improvement_pct", "auc", "calib_error"]].mean().round(4).to_string())

    (OUT / f"rolling_{a.label}.json").write_text(json.dumps(res.to_dict(orient="records"), indent=2))
    print(f"\nsaved to {OUT / f'rolling_{a.label}.json'}")


if __name__ == "__main__":
    main()
