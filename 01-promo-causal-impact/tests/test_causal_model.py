"""
test_causal_model.py — light sanity checks on the causal analysis pipeline.
Loads already-saved data/model artifacts rather than refitting anything.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import joblib
import pandas as pd
import pytest

from src.causal_model import naive_diff, bootstrap_ate
from src.evaluation import qini_curve

DATA_PATH = "data/criteo_sample_with_uplift.csv"
MODEL_PATH = "data/causal_forest_model.joblib"


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(DATA_PATH)


def test_naive_ate_sign_positive(df):
    """The promo should show a positive naive effect on conversion —
    if this flips sign, something upstream broke (e.g. treatment/control swapped)."""
    diff = naive_diff(df, outcome="conversion")
    assert diff > 0, f"Expected positive naive ATE, got {diff}"


def test_bootstrap_ci_has_positive_width(df):
    """A degenerate (zero-width) CI usually means the bootstrap loop is broken,
    not that the estimate is unusually precise."""
    ate, (ci_low, ci_high), _ = bootstrap_ate(df, outcome="conversion", n_boot=200)
    assert ci_high > ci_low, "Bootstrap CI has zero or negative width"
    assert ci_low <= ate <= ci_high, "Point estimate falls outside its own CI"


def test_bootstrap_ci_excludes_zero(df):
    """Given the sample size and known effect, the 95% CI should exclude zero —
    if this starts failing, the underlying effect may have genuinely vanished."""
    ate, (ci_low, ci_high), _ = bootstrap_ate(df, outcome="conversion", n_boot=200)
    assert ci_low > 0, f"CI lower bound {ci_low} does not exclude zero — effect no longer significant"


def test_predicted_uplift_column_exists_and_bounded(df):
    """predicted_uplift should exist and stay within a plausible probability-delta range."""
    assert "predicted_uplift" in df.columns
    assert df["predicted_uplift"].between(-1, 1).all(), "predicted_uplift has values outside [-1, 1]"


def test_causal_forest_model_loads_and_predicts(df):
    """The saved model should load and produce an effect() array matching the row count."""
    cf = joblib.load(MODEL_PATH)
    feature_cols = [f"f{i}" for i in range(12)]
    X_sample = df[feature_cols].head(100).values
    effects = cf.effect(X_sample)
    assert len(effects) == 100, "cf.effect() output length doesn't match input rows"


def test_qini_total_matches_naive_ate_order_of_magnitude(df):
    """Sanity check: the Qini curve's final cumulative value (100% population)
    should be in the same ballpark as naive_diff * N — not exact (different
    formulas), but should agree within a generous tolerance."""
    df_sorted = qini_curve(df)
    qini_total = df_sorted["qini"].iloc[-1]
    expected_order_of_magnitude = naive_diff(df, outcome="conversion") * len(df)
    ratio = qini_total / expected_order_of_magnitude
    assert 0.5 < ratio < 2.0, (
        f"Qini total ({qini_total:.1f}) is more than 2x off from naive-ATE-implied "
        f"total ({expected_order_of_magnitude:.1f}) — investigate formula or data mismatch"
    )