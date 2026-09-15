# Promo Causal Impact Analysis

**Does a promotional campaign actually drive incremental revenue — and who should we target?**

## TL;DR

A naive before/after comparison says the promo increased conversions by 0.116 percentage points. Two independent causal estimators (a causal forest and a doubly-robust learner) confirm that number is real, not confounded — but the causal forest analysis reveals the *average* effect hides massive heterogeneity: a small ~5.8% segment of customers actually converts *less* when promoted. Excluding that segment and targeting only the remaining 94.2% would more than double net incremental conversions (963.7 → 2,172.7) while reducing spend by 5.8% — an estimated $48K → $109K swing in incremental revenue at an illustrative $50 AOV.

## Business question

Companies run promotions constantly, but most only ask "did conversions go up," which conflates people who would have converted anyway with people the promo actually persuaded. This project answers the harder question: *who did this promo actually cause to convert, and should we keep targeting them?*

## Data

[Criteo Uplift Modeling Dataset](https://ailab.criteo.com/criteo-uplift-prediction-dataset/) — a real ad-treatment RCT with ~14M rows, `treatment`/`control` assignment (85/15 split by design), `conversion`/`visit` outcomes, and 12 anonymized covariates (`f0`–`f11`). Analysis uses a stratified 7% subsample (~979K rows) for local tractability — an explicit, documented tradeoff, not a hidden shortcut.

## Approach

1. **Validate the experiment before trusting it.** Sample Ratio Mismatch check against Criteo's documented 85/15 design (passed, p=1.0), and a covariate balance check across all 12 features — all 12 were statistically "significant" at this sample size (an artifact of 14M rows), but 0/12 showed practical imbalance (standardized mean difference < 0.1), confirming randomization held.
2. **Power analysis.** At the actual 85/15 allocation and control-arm size, the subsample can reliably detect a relative lift of ~18.5% at 80% power — smaller effects would need the full 14M-row dataset.
3. **Naive vs. causal ATE.** Naive diff-in-means (0.00116) vs. a 1,000-iteration bootstrapped ATE (0.00116, 95% CI [0.00091, 0.00142]) — they match almost exactly, as expected for a genuine RCT where randomization already removes confounding.
4. **Causal DAG and assumptions.** See `docs/dag_diagram.png`. Because `treatment` was randomly assigned in this experiment, there is no backdoor path from unmeasured confounders to `conversion` — the pre-treatment covariates (f0–f11) may still explain who responds more or less, but they aren't confounders in the causal-inference sense, since randomization already severs any covariate → treatment dependency. This is why the naive difference-in-means matches the bootstrapped ATE almost exactly: there's no bias to correct. The causal forest's role here isn't to remove confounding — it's purely to explain heterogeneity in the treatment effect across covariates. In an observational (non-randomized) version of this problem, you would instead need propensity-score weighting or a doubly-robust estimator to adjust for the backdoor path opened by confounders — which is exactly the robustness pattern demonstrated by the doubly-robust cross-check below, even though it isn't strictly required by this RCT's design.
5. **Heterogeneous effects (causal forest).** `CausalForestDML` (EconML, 500 trees) estimates individual-level treatment effects (CATE). ATE = 0.00101, closely matching the bootstrapped baseline — but individual predicted uplift ranges from **-0.185 to +0.235**, revealing that most customers are barely affected while a minority drive most of the effect (positively or negatively).
6. **Doubly-robust cross-check.** `LinearDRLearner` (EconML) gives ATE = 0.00110 — a second, structurally different estimator confirming the same result.
7. **SHAP on the CATE model.** Explains what drives *treatment-effect* heterogeneity (not outcome). Two features (`f2`, `f8`) dominate — together roughly double the influence of the next tier. See `docs/shap_summary.png`.
8. **Qini curve + optimal targeting.** Reveals that net incremental conversions peak at 94.2% of the population, not 100% — the bottom ~5.8% are "sleeping dogs" who respond negatively to the promo. See `docs/qini_curve.png`.

## The naive-vs-causal hook

| Estimator | ATE |
|---|---|
| Naive diff-in-means | 0.00116 |
| Bootstrapped (95% CI) | 0.00116 [0.00091, 0.00142] |
| Causal forest (DML) | 0.00101 |
| Doubly-robust (DR) | 0.00110 |

All four land within a ~15% band of each other. They agree *because* this is a genuine RCT — randomization already removes confounding, so there's no bias for a causal estimator to correct. In an observational (non-randomized) setting, these numbers would likely diverge, and the doubly-robust estimator would matter far more.

## Key finding: the segment insight

The causal forest's real value isn't the ATE — it's uncovering who the average hides. Sorting customers by predicted uplift and tracing cumulative incremental conversions:

- Blanket rollout (100% targeted): **963.7** incremental conversions.
- Optimal targeting (top 94.2% by predicted uplift): **2,172.7** incremental conversions — a **+125.5%** increase, using **5.8% less spend**.

This is a "sleeping dogs" effect: a small subgroup converts *less* when promoted, and blanket rollout has been quietly wasting budget on them.

## Recommendation

**Exclude the bottom ~5.8% of customers (ranked by predicted uplift) from future promo targeting.** At an assumed $50 average order value (illustrative, not a real AOV — replace with actual figures in a production setting), this shifts estimated incremental revenue from ~$48,183 (blanket rollout) to ~$108,634 (optimal targeting).

## Limitations & future work

- Features are anonymized (`f0`–`f11`), limiting business interpretability of *which* customer traits drive the segment split.
- Individual-level uplift estimates in the extreme tails are the noisiest part of any CATE model, especially with a rare (~0.3%) conversion outcome — the 5.8% cutoff is directionally credible but not precise to the percentage point without further validation (e.g., cross-validated ranking stability).
- A real deployment would need online monitoring for novelty/decay effects — uplift patterns can shift over time.
- Sensitivity analysis (e.g., E-values) for unmeasured confounding would be the natural next step if this were observational rather than randomized data.
- Analysis uses a 7% stratified subsample; results should be validated against the full 14M-row dataset before any real targeting decision.

## Live demo

[Streamlit dashboard](LIVE_DEMO_URL) — *link added after deployment*

## Tech stack

Python · pandas · EconML (`CausalForestDML`, `LinearDRLearner`) · SHAP · statsmodels · scikit-learn · Streamlit · AWS S3

## Repository structure

```
07-promo-causal-impact/
├── README.md
├── requirements.txt
├── data/               # sample data (not committed — see .gitignore)
├── notebooks/
├── src/
│   ├── data_prep.py       # SRM, covariate balance, stratified subsample
│   ├── power_analysis.py  # MDE / power analysis
│   ├── causal_model.py    # naive/bootstrap ATE, causal forest, doubly-robust
│   ├── shap_analysis.py   # SHAP on the CATE model
│   ├── evaluation.py      # Qini curve, decile table, business translation
│   └── dag_diagram.py     # causal DAG figure
├── app.py                 # Streamlit dashboard
├── tests/
│   └── test_causal_model.py
└── docs/
    ├── dag_diagram.png
    ├── qini_curve.png
    └── shap_summary.png
```

## Setup

```bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
```

Run the pipeline in order:

```bash
python src\data_prep.py       # SRM, covariate balance, stratified subsample
python src\power_analysis.py  # MDE / power analysis
python src\dag_diagram.py     # causal DAG figure
python src\causal_model.py    # naive/bootstrap ATE, causal forest (~14 min)
python -m src.robustness_check  # doubly-robust cross-check
python src\shap_analysis.py   # SHAP on the CATE model
python src\evaluation.py      # Qini curve, decile table, business translation
streamlit run app.py          # launch the dashboard
```