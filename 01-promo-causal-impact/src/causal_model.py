"""
causal_model.py — naive vs. bootstrapped ATE (Phase 2 Step 4),
followed by CausalForestDML (Step 6).
"""
import time
import pandas as pd
import numpy as np
import joblib
from econml.dml import CausalForestDML
from sklearn.ensemble import RandomForestRegressor

SAMPLE_PATH = "data/criteo_sample.csv"
FEATURE_COLS = [f"f{i}" for i in range(12)]


def naive_diff(df, outcome="conversion"):
    """The naive, uncorrected treatment-vs-control difference — the number
    a junior analyst would report without any uncertainty quantification."""
    treat_rate = df[df.treatment == 1][outcome].mean()
    control_rate = df[df.treatment == 0][outcome].mean()
    diff = treat_rate - control_rate
    print(f"Naive: treatment rate={treat_rate:.5f}, control rate={control_rate:.5f}, diff={diff:.5f}")
    return diff


def bootstrap_ate(df, outcome="conversion", n_boot=1000, seed=42):
    """Bootstrapped ATE with a 95% CI — resamples the full dataset (not
    each arm separately) so arm sizes vary naturally across replicates,
    which is what makes this a valid CI for the difference-in-means."""
    rng = np.random.default_rng(seed)
    n = len(df)
    ates = np.empty(n_boot)
    treat_vals = df[outcome].values
    treatment_flags = df["treatment"].values

    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        t = treatment_flags[idx]
        y = treat_vals[idx]
        ates[i] = y[t == 1].mean() - y[t == 0].mean()

    ate = ates.mean()
    ci_low, ci_high = np.percentile(ates, [2.5, 97.5])
    print(f"Bootstrapped ATE: {ate:.5f}, 95% CI: [{ci_low:.5f}, {ci_high:.5f}] (n_boot={n_boot})")
    return ate, (ci_low, ci_high), ates


def naive_vs_causal_summary(df, outcome="conversion"):
    print(f"\n--- Naive vs. Bootstrapped ATE ({outcome}) ---")
    diff = naive_diff(df, outcome)
    ate, ci, _ = bootstrap_ate(df, outcome)

    print(f"\nNaive diff:        {diff:.5f}")
    print(f"Bootstrapped ATE:  {ate:.5f}  95% CI: [{ci[0]:.5f}, {ci[1]:.5f}]")
    ci_excludes_zero = ci[0] > 0 or ci[1] < 0
    print(f"CI excludes zero: {ci_excludes_zero}  -> {'statistically significant effect' if ci_excludes_zero else 'not distinguishable from zero'}")

    close = abs(diff - ate) < 0.0005
    print(f"\nNaive and bootstrapped estimates are {'close' if close else 'notably different'} — "
          f"{'expected, since Criteo is a genuine RCT: randomization already removes confounding, so the naive diff-in-means is already unbiased here.' if close else 'worth investigating why they diverge.'}")
    return diff, ate, ci


def fit_causal_forest(df, feature_cols=FEATURE_COLS, outcome="conversion",
                       n_estimators=100, min_samples_leaf=10, random_state=42):
    X = df[feature_cols].values
    T = df["treatment"].values
    Y = df[outcome].values

    print(f"Fitting CausalForestDML on {len(df):,} rows, {n_estimators} trees ...")
    cf = CausalForestDML(
        model_y=RandomForestRegressor(n_estimators=100, min_samples_leaf=10, n_jobs=-1),
        model_t=RandomForestRegressor(n_estimators=100, min_samples_leaf=10, n_jobs=-1),
        n_estimators=n_estimators, min_samples_leaf=min_samples_leaf,
        random_state=random_state, n_jobs=-1
    )
    cf.fit(Y, T, X=X)

    ate = cf.ate(X)
    print(f"Causal forest ATE: {ate:.5f}")
    return cf, X

from econml.dr import LinearDRLearner


from sklearn.ensemble import RandomForestClassifier

def fit_doubly_robust(df, feature_cols=FEATURE_COLS, outcome="conversion", random_state=42):
    X = df[feature_cols].values
    T = df["treatment"].values
    Y = df[outcome].values

    print(f"Fitting LinearDRLearner on {len(df):,} rows ...")
    dr = LinearDRLearner(
        model_propensity=RandomForestClassifier(n_estimators=100, min_samples_leaf=10, n_jobs=-1),
        model_regression=RandomForestRegressor(n_estimators=100, min_samples_leaf=10, n_jobs=-1),
        random_state=random_state
    )
    dr.fit(Y, T, X=X)
    dr_ate = dr.ate(X)
    print(f"Doubly-robust ATE: {dr_ate:.5f}")
    return dr, dr_ate

if __name__ == "__main__":
    df = pd.read_csv(SAMPLE_PATH)
    naive_vs_causal_summary(df, outcome="conversion")
    naive_vs_causal_summary(df, outcome="visit")

    # --- Smoke test (kept for reference/debugging — comment out once confirmed) ---
    # print("\n--- Causal forest smoke test (50k rows, 48 trees) ---")
    # df_small = df.sample(n=50_000, random_state=42)
    # start = time.time()
    # cf_test, X_test = fit_causal_forest(df_small, n_estimators=48)
    # elapsed = time.time() - start
    # print(f"Smoke test took {elapsed:.1f} seconds.")

    # --- Full run ---
    print(f"\n--- Causal forest FULL run ({len(df):,} rows, 500 trees) — this will take ~15-20 minutes ---")
    start = time.time()
    cf, X = fit_causal_forest(df, n_estimators=500)
    elapsed = time.time() - start
    joblib.dump(cf, "data/causal_forest_model.joblib")
    print("Saved fitted causal forest model to data/causal_forest_model.joblib")
    print(f"Full run took {elapsed/60:.1f} minutes.")

    df["predicted_uplift"] = cf.effect(X)
    print("\n--- Predicted uplift (CATE) distribution ---")
    print(df["predicted_uplift"].describe())

    ate_full = cf.ate(X)
    print(f"\nCausal forest ATE (full sample): {ate_full:.5f}")
    print(f"Bootstrapped ATE (for comparison): 0.00116")

    OUTPUT_PATH = "data/criteo_sample_with_uplift.csv"
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved sample with predicted_uplift column to {OUTPUT_PATH}")