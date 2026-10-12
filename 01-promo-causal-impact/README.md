# Promo Causal Impact Analysis

> Every promo report says conversions went up. This one asks who actually needed the discount to buy — and finds a segment the promo was quietly paying to *not* convert.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![EconML](https://img.shields.io/badge/EconML-CausalForestDML%20%2B%20DRLearner-4B8BBE?logo=python&logoColor=white)
![SHAP](https://img.shields.io/badge/SHAP-explainability-8A2BE2)
![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-FF4B4B?logo=streamlit&logoColor=white)
![AWS S3](https://img.shields.io/badge/AWS%20S3-data%20storage-FF9900?logo=amazons3&logoColor=white)
![Status](https://img.shields.io/badge/status-analysis%20complete-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

Companies run promotions constantly, but most only ask "did conversions go up" — a question that conflates customers who'd have bought anyway with customers the promo actually persuaded. This project answers the harder question, on a real ad-treatment RCT (~1M rows): *who did this promo actually cause to convert, and should we keep targeting them?* The naive number says yes, blanket rollout is working. Two independent causal estimators confirm that number is real — but a causal forest shows the average is hiding a ~5.8% segment that converts *less* when promoted, and excluding them more than doubles net incremental conversions while cutting spend.

**[Live Demo](LIVE_DEMO_URL)** · **[GitHub](https://github.com/Hari-Etta/Portfolio/tree/main/07-promo-causal-impact)** · **[Portfolio Site](#)**
*(live demo link goes live once Streamlit Community Cloud deployment is finalized — see [Status](#status))*

---

## Table of Contents
- [Status](#status)
- [Why This Exists](#why-this-exists)
- [Data](#data)
- [Architecture / Approach](#architecture--approach)
- [Project Structure](#project-structure)
- [Validating the Experiment First](#validating-the-experiment-first)
- [The Naive-vs-Causal Hook](#the-naive-vs-causal-hook)
- [Key Finding: The Segment Insight](#key-finding-the-segment-insight)
- [Business Recommendation](#business-recommendation)
- [Limitations & Future Work](#limitations--future-work)
- [Dashboard](#dashboard)
- [Running This Yourself](#running-this-yourself)
- [Accounts Used](#accounts-used)
- [License](#license)

---

## Status

| Step | Description | Status |
|---|---|---|
| 1 | Data & setup (Criteo download, stratified 7% subsample) | ✅ Done |
| 2 | Experiment validation (SRM check, covariate balance, power analysis) | ✅ Done — SRM passed, 0/12 features practically imbalanced |
| 3 | Naive vs. bootstrapped ATE (the hook) | ✅ Done — estimators agree within a ~15% band |
| 4 | Causal DAG + assumptions writeup | ✅ Done |
| 5 | Heterogeneous effects — causal forest (`CausalForestDML`) | ✅ Done — 500 trees, ~14 min fit |
| 6 | Doubly-robust cross-check (`LinearDRLearner`) | ✅ Done — confirms causal forest result |
| 7 | SHAP on the CATE model | ✅ Done — 2 features dominate heterogeneity |
| 8 | Qini curve + optimal targeting / business translation | ✅ Done — 125.5% incremental-conversion gain found |
| 9 | Streamlit dashboard | ✅ Done — ATE comparison, Qini curve, SHAP, recommendation panel |
| 10 | Unit tests (pytest) | ✅ Done — 6/6 passing |
| 11 | AWS S3 (raw/processed data round-trip) | 🔧 Deferred — not required for the analysis, needed before Streamlit Cloud deployment can serve data |
| 12 | Deployment (GitHub + Streamlit Community Cloud) | 🔧 In progress |

---

## Why This Exists

1. **The naive hook, shown honestly — not hidden.** Most causal-inference portfolio projects jump straight to the "sophisticated" model. This one shows the naive, uncorrected number first, exactly as a junior analyst would report it, then validates it two independent ways before trusting it.
2. **The segment insight is the actual differentiator.** The average treatment effect (0.00101–0.00116 across four estimators) is small and easy to dismiss. The causal forest reveals that average is hiding individual effects ranging from **-0.185 to +0.235** — a "sleeping dogs" segment that responds *negatively* to the promo, invisible to any analysis that stops at the ATE.
3. **The business translation is a dollar number, not a model metric.** "Qini coefficient = 0.00169" means nothing to a hiring manager. "Excluding the bottom 5.8% of customers increases net incremental conversions by 125.5% while cutting spend by 5.8%" does.

---

## Data

[Criteo Uplift Modeling Dataset](https://ailab.criteo.com/criteo-uplift-prediction-dataset/) — a real ad-treatment RCT with ~14M rows, `treatment`/`control` assignment (85/15 split by design), `conversion`/`visit` outcomes, and 12 anonymized covariates (`f0`–`f11`). Downloaded via a Hugging Face mirror after Criteo's own S3 bucket returned a 403. Analysis uses a stratified 7% subsample (~979K rows) for local tractability — an explicit, documented tradeoff, not a hidden shortcut.

---

## Architecture / Approach

```
┌──────────────────┐     ┌───────────────────────┐     ┌──────────────────────────┐
│  Criteo raw CSV    │     │  Experiment validation  │     │  Naive vs. causal ATE      │
│  ~14M rows,         │────▶│  SRM check (85/15)      │────▶│  naive diff-in-means       │
│  stratified 7%      │     │  covariate balance      │     │  vs. 1,000-iter bootstrap  │
│  subsample (~979K)  │     │  power analysis (MDE)   │     │  → agree within ~15%       │
└──────────────────┘     └───────────────────────┘     └────────────┬─────────────┘
                                                                        │
                          ┌─────────────────────────────────────────────┘
                          ▼
             ┌──────────────────────────┐     ┌──────────────────────────┐
             │  Causal forest (CATE)      │────▶│  SHAP on the CATE model    │
             │  CausalForestDML, 500      │     │  which features drive      │
             │  trees → predicted_uplift  │     │  heterogeneity (f2, f8      │
             │  per customer, -0.185 to   │     │  dominate)                 │
             │  +0.235                    │     └──────────────────────────┘
             └────────────┬─────────────┘
                          │
                          ▼
             ┌──────────────────────────┐     ┌──────────────────────────┐
             │  Doubly-robust cross-      │     │  Qini curve + optimal       │
             │  check (LinearDRLearner)   │     │  targeting cutoff           │
             │  confirms causal forest    │────▶│  → exclude bottom 5.8%      │
             │  ATE independently         │     │  → +125.5% incremental      │
             └──────────────────────────┘     │  conversions                │
                                                └────────────┬─────────────┘
                                                             │
                                                             ▼
                                                ┌──────────────────────────┐
                                                │  Streamlit dashboard       │
                                                │  ATE comparison, Qini       │
                                                │  curve, SHAP summary,       │
                                                │  business recommendation    │
                                                └──────────────────────────┘
```

**Tech stack:** Python · pandas · EconML (`CausalForestDML`, `LinearDRLearner`) · scikit-learn · SHAP · statsmodels · scipy · Streamlit · pytest · joblib · AWS S3 (planned)

---

## Project Structure

```
07-promo-causal-impact/
├── README.md
├── requirements.txt
├── data/                   # sample data + model binary (gitignored — see Data Quality note below)
├── notebooks/
│   └── 01_eda_and_causal_analysis.ipynb
├── src/
│   ├── data_prep.py        # SRM check, covariate balance, stratified subsample
│   ├── power_analysis.py   # MDE / power analysis
│   ├── dag_diagram.py      # causal DAG figure
│   ├── causal_model.py     # naive/bootstrap ATE, causal forest
│   ├── robustness_check.py # doubly-robust (LinearDRLearner) cross-check
│   ├── shap_analysis.py    # SHAP on the CATE model
│   └── evaluation.py       # Qini curve, decile table, business translation
├── app.py                  # Streamlit dashboard
├── tests/
│   └── test_causal_model.py  # 6 sanity checks: ATE sign, CI width, Qini/ATE consistency, etc.
└── docs/
    ├── dag_diagram.png
    ├── qini_curve.png
    └── shap_summary.png
```

---

## Validating the Experiment First

Before trusting any causal estimate, the experiment itself has to check out — most "I ran a t-test" tutorials skip straight past this.

**Sample Ratio Mismatch (SRM) check.** Criteo's documented design is an intentional 85/15 treatment/control split, not 50/50. Checked against that documented ratio (not a naive 50/50 assumption): **passed, chi²=0.000, p=1.0000**.

**Covariate balance.** All 12 anonymized features (`f0`–`f11`) were statistically "significant" between treatment and control groups (Bonferroni-corrected) — but that's a known artifact of testing at ~979K rows, not evidence of a real imbalance. Checking standardized mean difference (the practical-significance measure) instead: **0 of 12 features showed |SMD| > 0.1** — randomization held cleanly.

**Power analysis.** At the actual 85/15 allocation and resulting control-arm size, the subsample can reliably detect a relative lift of **~18.5%** at 80% power — smaller effects would need the full 14M-row dataset, a limitation stated explicitly rather than glossed over.

---

## The Naive-vs-Causal Hook

| Estimator | ATE |
|---|---|
| Naive diff-in-means | 0.00116 |
| Bootstrapped (1,000 iterations, 95% CI) | 0.00116 [0.00091, 0.00142] |
| Causal forest (`CausalForestDML`, 500 trees) | 0.00101 |
| Doubly-robust (`LinearDRLearner`) | 0.00110 |

All four estimators land within a ~15% band of each other. They agree *because* this is a genuine RCT — randomization already removes confounding, so there's no bias for a causal estimator to correct. (See `docs/dag_diagram.png`: no backdoor path from the anonymized covariates to `conversion` exists once `treatment` is randomized — the covariates explain heterogeneity, not bias. In an observational, non-randomized version of this problem, these four numbers would likely diverge, and the doubly-robust estimator would matter far more.)

---

## Key Finding: The Segment Insight

The causal forest's real value isn't the ATE — it's uncovering who the average hides. Individual-level predicted uplift ranges from **-0.185 to +0.235** around a mean of 0.00101: most customers are barely affected, while a minority drive nearly all of the effect, in both directions. SHAP on the CATE model shows two features (`f2`, `f8`) dominate that heterogeneity — together roughly double the influence of the next tier (features are anonymized, limiting business interpretability of *which* customer traits these represent — see Limitations).

Sorting customers by predicted uplift and tracing cumulative incremental conversions:

- **Blanket rollout (100% targeted): 963.7 incremental conversions.**
- **Optimal targeting (top 94.2% by predicted uplift): 2,172.7 incremental conversions** — a **+125.5%** increase, using **5.8% less spend.**

This is a "sleeping dogs" effect: a small subgroup converts *less* when promoted, and blanket rollout has been quietly wasting budget on them. Qini coefficient: 0.00169.

---

## Business Recommendation

**Exclude the bottom ~5.8% of customers (ranked by predicted uplift) from future promo targeting.** At an assumed $50 average order value (illustrative, not a real AOV — replace with actual figures in a production setting):

| Scenario | Incremental conversions | Estimated incremental revenue |
|---|---|---|
| Blanket rollout (100%) | 963.7 | ~$48,183 |
| Optimal targeting (94.2%) | 2,172.7 | ~$108,634 |

---

## Limitations & Future Work

- Features are anonymized (`f0`–`f11`), limiting business interpretability of *which* customer traits drive the segment split.
- Individual-level uplift estimates in the extreme tails are the noisiest part of any CATE model, especially with a rare (~0.3%) conversion outcome — the 5.8% cutoff is directionally credible but not precise to the percentage point without further validation (e.g., cross-validated ranking stability).
- A real deployment would need online monitoring for novelty/decay effects — uplift patterns can shift over time.
- Sensitivity analysis (e.g., E-values) for unmeasured confounding would be the natural next step if this were observational rather than randomized data.
- Analysis uses a 7% stratified subsample; results should be validated against the full 14M-row dataset before any real targeting decision.

---

## Dashboard

`app.py` — a Streamlit dashboard reusing the same `src/evaluation.py` functions as the analysis scripts (no duplicated logic). Four panels: naive-vs-causal ATE comparison, the Qini curve with the decile targeting table, the SHAP summary plot, and a plain-language business recommendation panel with the dollar estimate.

---

## Running This Yourself

```bash
# 1. Clone and set up the environment
git clone https://github.com/Hari-Etta/Portfolio.git
cd Portfolio/07-promo-causal-impact
python -m venv venv && venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt

# 2. Run the pipeline in order
python src\data_prep.py          # SRM, covariate balance, stratified subsample
python src\power_analysis.py     # MDE / power analysis
python src\dag_diagram.py        # causal DAG figure
python src\causal_model.py       # naive/bootstrap ATE, causal forest (~14 min)
python -m src.robustness_check   # doubly-robust cross-check (~2-4 min)
python src\shap_analysis.py      # SHAP on the CATE model
python src\evaluation.py         # Qini curve, decile table, business translation

# 3. Run the tests
python -m pytest tests\test_causal_model.py -v

# 4. Launch the dashboard
streamlit run app.py
```

You'll need the raw Criteo dataset downloaded into `data/` (see [Data](#data) — a Hugging Face mirror works when Criteo's own S3 link doesn't) before step 2 will produce real output.

---

## Accounts Used

- Hugging Face Hub (dataset download — free, no account required for this dataset)
- AWS S3 (planned, not yet in active use — see [Status](#status))
- Streamlit Community Cloud (dashboard hosting, deployment pending)
- GitHub (source control, portfolio hosting)

---

## License

MIT — see the [repository LICENSE](https://github.com/Hari-Etta/Portfolio/blob/main/LICENSE).