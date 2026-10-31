"""Smoke test: score every swing with the model downloaded from S3 and check the results make sense.
(In-sample, so predictions should track actual whiff rates closely; this checks plumbing, not quality.)"""
import pandas as pd

from src.model.score import load_model, predict
from src.model.train_whiff import load


def main() -> None:
    booster, meta = load_model()
    df = load()
    df["p_whiff"] = predict(booster, meta, df)
    print(f"model: {meta['model']} | trees: {meta['n_trees']} | trained on {meta['train_rows']:,} swings")
    print(f"\naverage predicted whiff: {df.p_whiff.mean():.4f} | actual whiff rate: {df.is_whiff.mean():.4f}")

    print("\n=== predicted vs actual by attack zone ===")
    order = {"heart": 1, "shadow": 2, "chase": 3, "waste": 4}
    by_zone = (df.groupby("attack_zone", observed=True)
                 .agg(swings=("is_whiff", "size"), predicted=("p_whiff", "mean"), actual=("is_whiff", "mean"))
                 .reset_index())
    by_zone = by_zone.sort_values("attack_zone", key=lambda s: s.astype(str).map(order))
    print(by_zone.round(3).to_string(index=False))

    print("\n=== predicted vs actual by strikes ===")
    by_strikes = df.groupby("strikes").agg(predicted=("p_whiff", "mean"), actual=("is_whiff", "mean")).round(3)
    print(by_strikes.to_string())


if __name__ == "__main__":
    main()
