"""
robustness_check.py — Step 7: doubly-robust cross-check against the
already-fitted causal forest results (loads saved data, doesn't refit CF).
"""
import time
import pandas as pd
from src.causal_model import fit_doubly_robust, FEATURE_COLS

DATA_PATH = "data/criteo_sample_with_uplift.csv"

if __name__ == "__main__":
    df = pd.read_csv(DATA_PATH)

    start = time.time()
    dr, dr_ate = fit_doubly_robust(df, outcome="conversion")
    elapsed = time.time() - start
    print(f"\nDR fit took {elapsed/60:.1f} minutes.")

    print("\n--- Estimator comparison (conversion) ---")
    print(f"Naive diff:              0.00116")
    print(f"Bootstrapped ATE:        0.00116")
    print(f"Causal forest ATE:       0.00100")
    print(f"Doubly-robust ATE:       {dr_ate:.5f}")