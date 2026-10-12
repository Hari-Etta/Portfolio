# Hari Etta — Data Science, AI & Data Engineering Portfolio

> End-to-end projects on real data that answer a business question, measure whether the answer holds up, and ship it as something a stakeholder can actually use.

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-4479A1?logo=postgresql&logoColor=white)
![Databricks](https://img.shields.io/badge/Databricks-FF3621?logo=databricks&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-FF694B?logo=dbt&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C)
![Claude API](https://img.shields.io/badge/Claude%20API-D4A27F?logo=anthropic&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-4285F4?logo=googlecloud&logoColor=white)
![EconML](https://img.shields.io/badge/EconML-4B8BBE)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Tableau](https://img.shields.io/badge/Tableau-E97627?logo=tableau&logoColor=white)

M.S. in Information Technology & Management (Data Science and Applied AI), Illinois Institute of Technology. Targeting **Data Scientist, Data Analyst, AI Engineer, ML Engineer, and Data Engineer** roles.

Every project here uses **real, public data**, documents what went wrong along the way, and reports honest results rather than a polished demo.

---

## Projects at a Glance

| Project | Business Question | Headline Result | Core Stack | Roles |
|---|---|---|---|---|
| [**Promo Causal Impact Analysis**](./07-promo-causal-impact) | Who did a promotion actually persuade, not just who converted? | Found a ~5.8% segment the promo pushed *away*; excluding them raised incremental conversions **+125.5%** with **5.8% less spend** | EconML, SHAP, statsmodels, Streamlit | DS · DA · ML |
| [**Complaint Investigation Agent**](./complaint-investigation-agent) | Why does every two-minute question wait days in an analyst's queue? | **23/23 (100%)** on a hand-verified eval set, **2.96s** avg latency, guardrail blocks 12/12 unsafe queries | LangGraph, Claude API, BigQuery, Streamlit | AI · DE · DA |
| [**E-Commerce Medallion Data Platform**](./03-e-commerce-medallion-platform) | Why do marketing, finance, and ops all report different revenue numbers? | One tested bronze → silver → gold pipeline, **14/14 dbt tests passing**, orchestrated daily | Databricks (PySpark), dbt, GitHub Actions, Tableau | DE · DA · DS |
| **Loan Default Risk Prediction** | Which borrowers are likely to default, and why? | Classical ML with explainability | XGBoost, SHAP | DS · ML |

---

## Featured Projects

### 📈 Promo Causal Impact Analysis
**[`07-promo-causal-impact`](./07-promo-causal-impact)** · Causal inference & experimentation

Most promo reports stop at "conversions went up." This one asks who the promo actually *caused* to convert, on a real ad-treatment RCT (Criteo, ~979K-row stratified subsample).

- **Validated the experiment first:** sample-ratio-mismatch check against the documented 85/15 split (passed), covariate balance via standardized mean difference (0/12 features imbalanced), and power analysis (MDE ~18.5%).
- **Naive vs. causal:** naive diff-in-means, bootstrapped ATE, causal forest, and doubly-robust estimates all agree within a ~15% band, as expected for a true RCT.
- **The real finding:** a causal forest showed individual uplift ranging from -0.185 to +0.235. A "sleeping dogs" segment converts *less* when promoted. Excluding the bottom ~5.8% by predicted uplift lifts net incremental conversions from 963.7 to 2,172.7.
- SHAP on the CATE model, Qini-curve targeting, a Streamlit dashboard, and 6/6 passing unit tests.

`Python` `EconML` `CausalForestDML` `LinearDRLearner` `SHAP` `statsmodels` `Streamlit` `pytest`

---

### 🤖 Complaint Investigation Agent
**[`complaint-investigation-agent`](./complaint-investigation-agent)** · Agentic AI

A self-serve agent that turns plain-English questions about the real CFPB Consumer Complaint Database into verified, source-grounded answers with a visible reasoning trail.

- **LangGraph plan → execute → synthesize** agent on `claude-haiku-4-5`, grounded in the real BigQuery schema and exact category values.
- **Guardrailed SQL tool:** blocks 10 destructive keywords, multi-statement injection, and non-`SELECT`/`WITH` queries, and caps results at 1,000 rows. Verified with automated tests and live prompt-injection attempts.
- **Evaluation harness:** 23 questions with hand-verified answers. Run 1 scored 22/23. The miss was a real data ambiguity (`consumer_disputed` is NULL for 69.2% of debt-collection rows), fixed by rewording the question rather than loosening the answer. Final: **23/23, 2.96s avg latency**.
- **Manual testing found 3 real bugs** (complaints vs. consumers, guessed category strings, "last year" vs. the dataset's real 2023 end date), each fixed at the schema-grounding root cause.

`Python` `LangGraph` `Claude API` `Google BigQuery` `Streamlit`

---

### 🏗️ E-Commerce Medallion Data Platform
**[`03-e-commerce-medallion-platform`](./03-e-commerce-medallion-platform)** · Data engineering & BI

One trusted pipeline on the real ~100K-order Olist dataset, so every team reads the same numbers.

- **Bronze → silver → gold** on Databricks Unity Catalog: 5 dbt silver models with 14 automated tests, plus 3 PySpark gold aggregates (revenue by region, delivery performance, customer LTV).
- **Documented data quality:** 26.2% duplicate geolocation rows, and a CSV-upload parsing bug that null-shredded 2,236 review rows. Pandas missed that bug; it was caught and fixed with a preprocessing script. Also found 6 "canceled" orders that were actually delivered, verified by SQL.
- **Orchestrated daily** via GitHub Actions: `dbt run` + `dbt test`, then the gold job is triggered through the Databricks Jobs API with explicit failure checks.
- **Findings:** São Paulo drives ~R$6.0M in revenue, 2.8x the next state. Delivered orders average 12.5 days. Customer LTV is a steep one-time-buyer long tail.

`Databricks` `PySpark` `dbt` `Unity Catalog` `GitHub Actions` `Tableau`

---

### 💳 Loan Default Risk Prediction
Classical ML with explainability: an XGBoost default-risk model with SHAP explaining which borrower features drive each prediction.

`Python` `XGBoost` `SHAP` `scikit-learn`

---

## Skills Demonstrated

| Area | Where it shows up |
|---|---|
| **Experimentation & causal inference** | SRM checks, power analysis, bootstrapped ATE, causal forests, doubly-robust estimation, Qini/uplift (Promo) |
| **Machine learning & explainability** | XGBoost + SHAP (Loan), SHAP on treatment effects (Promo) |
| **GenAI & agentic AI** | LangGraph orchestration, tool-calling, schema grounding, SQL guardrails, LLM evaluation harness (Agent) |
| **Data engineering** | Medallion architecture, PySpark, dbt models and tests, Databricks Jobs API, CI/CD orchestration (Medallion) |
| **SQL** | BigQuery (Agent), Databricks SQL (Medallion), data-quality verification queries |
| **BI & dashboards** | Tableau (Medallion), Streamlit (Promo, Agent) |
| **Cloud** | Google Cloud / BigQuery, Databricks |
| **Engineering practice** | pytest, automated data tests, eval harnesses, documented bug fixes, reproducible setup |

---

## Repository Structure

```
Portfolio/
├── README.md                          ← you are here
├── 03-e-commerce-medallion-platform/  # Data engineering + BI
├── 07-promo-causal-impact/            # Causal inference + experimentation
├── complaint-investigation-agent/     # Agentic AI
└── LICENSE
```

Each project folder has its own README with full methodology, results, limitations, and setup instructions.

---

## How I Approach Projects

1. **Start with the business problem**, not the tool.
2. **Use real data** and document what's messy instead of pretending it arrived clean.
3. **Measure whether it works**: eval harnesses, dbt tests, experiment validation, unit tests.
4. **Report results honestly**, including the failed run, the ambiguous question, and the limitations.
5. **Ship something usable**: a dashboard, a chat app, or a scheduled pipeline.

---

## Contact

- **Email:** hetta.ds@gmail.com
- **LinkedIn:** [LINKEDIN_URL]
- **Portfolio site:** [PORTFOLIO_URL]

---

## License

MIT. See [LICENSE](LICENSE).