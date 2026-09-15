"""
shap_analysis.py — Step 8: SHAP on the CATE model, explaining what drives
treatment-effect heterogeneity (not outcome — treatment EFFECT).
"""
import joblib
import pandas as pd
import shap
import matplotlib.pyplot as plt

MODEL_PATH = "data/causal_forest_model.joblib"
DATA_PATH = "data/criteo_sample_with_uplift.csv"
FEATURE_COLS = [f"f{i}" for i in range(12)]
SHAP_SAMPLE_SIZE = 500  # SHAP on tree ensembles is expensive — subsample for speed

if __name__ == "__main__":
    print("Loading fitted causal forest model ...")
    cf = joblib.load(MODEL_PATH)

    df = pd.read_csv(DATA_PATH)
    df_shap = df.sample(n=SHAP_SAMPLE_SIZE, random_state=42)
    X_shap = df_shap[FEATURE_COLS].values

    print(f"Computing SHAP values on {SHAP_SAMPLE_SIZE:,} sampled rows ...")
    shap_values = cf.shap_values(X_shap)

    # econml's shap_values returns nested dict: {outcome: {treatment: Explanation}}
    # single outcome ('Y0') and single binary treatment ('T0') here
    explanation = shap_values["Y0"]["T0"]

    print("\n--- Mean absolute SHAP value per feature (feature importance for uplift) ---")
    mean_abs_shap = pd.Series(
        abs(explanation.values).mean(axis=0), index=FEATURE_COLS
    ).sort_values(ascending=False)
    print(mean_abs_shap)

    plt.figure()
    shap.summary_plot(explanation, X_shap, feature_names=FEATURE_COLS, show=False)
    plt.tight_layout()
    plt.savefig("docs/shap_summary.png", dpi=150, bbox_inches="tight")
    print("\nSaved SHAP summary plot to docs/shap_summary.png")