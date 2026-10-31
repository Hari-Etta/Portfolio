"""Cross-fitted (leave-one-month-out) whiff expectations for every swing.
Each month is scored by a model trained on all OTHER months, so no swing is ever scored by a model that saw it.
For descriptive stats (whiffs over expected), not forecasting. March is grouped with April (few games).
Same features, params and tree count as the final model."""
import lightgbm as lgb
import pandas as pd
from sklearn.metrics import log_loss

from src.ingest.s3_utils import write_parquet
from src.model.score import load_model
from src.model.train_whiff import FEATURES, LGB_PARAMS, TARGET, calibration_error, load


def main() -> None:
    df = load()
    _, meta = load_model()
    n_trees = int(meta["n_trees"])
    df["fold"] = df.game_date.dt.month.clip(lower=4)

    parts = []
    for m in sorted(df.fold.unique()):
        train, test = df[df.fold != m], df[df.fold == m]
        model = lgb.LGBMClassifier(**{**LGB_PARAMS, "n_estimators": n_trees})
        model.fit(train[FEATURES], train[TARGET])
        p = model.predict_proba(test[FEATURES])[:, 1]
        parts.append(pd.DataFrame({"pitch_id": test.pitch_id.values, "xwhiff": p, "fold_month": int(m)}))
        print(f"  month {m}: scored {len(test):,} swings (trained on {len(train):,})")

    scores = pd.concat(parts, ignore_index=True)
    check = df[["pitch_id", TARGET]].merge(scores, on="pitch_id")
    print(f"\nscored {len(check):,} of {len(df):,} swings")
    print(f"average expected {check.xwhiff.mean():.4f} | actual {check[TARGET].mean():.4f}")
    print(f"log-loss {log_loss(check[TARGET], check.xwhiff):.4f} | "
          f"calibration error {calibration_error(check[TARGET], check.xwhiff):.4f}")
    write_parquet(scores, "ml/whiff_scores.parquet")


if __name__ == "__main__":
    main()
