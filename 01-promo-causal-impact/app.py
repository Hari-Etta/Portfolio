"""
app.py — Streamlit dashboard for the Promo Causal Impact project.
Reuses functions from src/evaluation.py and src/causal_model.py so the
dashboard always reflects the same logic as the analysis scripts.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
from PIL import Image

from src.evaluation import qini_curve, qini_coefficient, decile_table, find_optimal_cutoff, ASSUMED_AOV

DATA_PATH = "data/criteo_sample_with_uplift.csv"
QINI_IMG_PATH = "docs/qini_curve.png"
SHAP_IMG_PATH = "docs/shap_summary.png"

st.set_page_config(page_title="Promo Causal Impact", layout="wide")


@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)


@st.cache_data
def compute_qini_analysis(df):
    df_sorted = qini_curve(df)
    qini_coef, total_incremental = qini_coefficient(df_sorted)
    decile_df = decile_table(df_sorted)
    peak_frac, peak_value = find_optimal_cutoff(df_sorted)
    return df_sorted, qini_coef, total_incremental, decile_df, peak_frac, peak_value


# --- Header / TL;DR ---
st.title("Promo Causal Impact Analysis")
st.markdown(
    "**Business question:** Does a promotional campaign actually drive incremental "
    "conversions, and if so, who should we target?\n\n"
    "**Key finding:** Blanket rollout produces a real but modest ATE — but a subset "
    "of customers respond *negatively* to the promo ('sleeping dogs'). Excluding them "
    "more than doubles net incremental conversions while spending less."
)

df = load_data()
df_sorted, qini_coef, total_incremental, decile_df, peak_frac, peak_value = compute_qini_analysis(df)

# --- Naive vs Causal ATE comparison ---
st.header("1. Naive vs. Causal ATE — the hook")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Naive diff-in-means", "0.00116")
col2.metric("Bootstrapped ATE", "0.00116", help="95% CI: [0.00091, 0.00142]")
col3.metric("Causal forest ATE", "0.00101")
col4.metric("Doubly-robust ATE", "0.00110")
st.caption(
    "All four estimators agree closely — expected, since this is a genuine RCT "
    "(Criteo's ad-treatment experiment). Randomization already removes confounding, "
    "so the naive number was already unbiased here. The causal forest's real value "
    "is uncovering *heterogeneity*, shown below."
)

# --- Qini curve ---
st.header("2. Segment insight — who actually responds")
qcol1, qcol2 = st.columns([2, 1])
with qcol1:
    if os.path.exists(QINI_IMG_PATH):
        st.image(Image.open(QINI_IMG_PATH), use_container_width=True)
    else:
        st.warning("Qini curve image not found — run src/evaluation.py first.")
with qcol2:
    st.metric("Qini coefficient", f"{qini_coef:.5f}")
    st.metric("Optimal targeting cutoff", f"{peak_frac:.1%} of population")
    st.metric("Incremental conversions (optimal)", f"{peak_value:.1f}",
              delta=f"{peak_value - total_incremental:.1f} vs. blanket rollout")

st.subheader("Decile targeting table")
st.dataframe(
    decile_df.style.format({
        "pct_of_spend": "{:.0%}",
        "cumulative_incremental_conversions": "{:.1f}",
        "pct_of_incremental_captured": "{:.1%}",
        "efficiency_ratio": "{:.2f}x",
    }),
    use_container_width=True,
)

# --- SHAP ---
st.header("3. What drives who responds (SHAP on the CATE model)")
if os.path.exists(SHAP_IMG_PATH):
    st.image(Image.open(SHAP_IMG_PATH), use_container_width=False, width=700)
    st.caption(
        "Features are anonymized (f0-f11), so business interpretation of *which* "
        "customer traits matter is limited — a real deployment would need "
        "non-anonymized features to translate this into actionable segments."
    )
else:
    st.warning("SHAP summary image not found — run src/shap_analysis.py first.")

# --- Business recommendation ---
st.header("4. Business recommendation")
excluded_frac = 1 - peak_frac
gain_pct = (peak_value - total_incremental) / total_incremental
dollar_optimal = peak_value * ASSUMED_AOV
dollar_blanket = total_incremental * ASSUMED_AOV

st.success(
    f"**Exclude the bottom {excluded_frac:.1%} of customers** (predicted to respond "
    f"negatively to the promo) from targeting.\n\n"
    f"- Net incremental conversions rise from **{total_incremental:.1f}** (blanket rollout) "
    f"to **{peak_value:.1f}** (optimal targeting) — a **{gain_pct:.1%} increase**\n"
    f"- Simultaneously reduces spend by **{excluded_frac:.1%}**\n"
    f"- At an assumed \\${ASSUMED_AOV:.0f} average order value, that's an estimated "
    f"**\\${dollar_optimal:,.0f}** in incremental revenue vs. \\${dollar_blanket:,.0f} "
    f"under blanket rollout — illustrative, not a precise revenue forecast."
)


st.caption(
    "Limitations: anonymized features limit interpretability of *which* customer "
    "traits drive this; individual-level uplift estimates in the extreme tails are "
    "the noisiest part of any CATE model, especially with a rare (~0.3%) conversion "
    "outcome — this cutoff is directionally credible but not precise to the percentage "
    "point without further validation (e.g. cross-validated ranking stability)."
)