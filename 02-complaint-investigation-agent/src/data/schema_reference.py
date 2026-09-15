"""Plain-language column descriptions — fed into the agent's system prompt so it writes
correct SQL against real column names instead of guessing.

Verified directly against the live BigQuery table schema on 2026-09-13
(bigquery-public-data.cfpb_complaints.complaint_database). Column names below are the
REAL ones — note company_name / company_response_to_consumer, not the "company" /
"company_response" placeholders used in early drafts of this project's build guide.
"""

TABLE_REF = "bigquery-public-data.cfpb_complaints.complaint_database"

# Verified directly via GROUP BY queries on 2026-09-15. Giving the agent the EXACT
# real values for commonly-filtered STRING columns, instead of a free-text
# description, is what prevents it from guessing plausible-but-wrong spellings
# (found via manual testing: it guessed submitted_via = 'Mail' when the real value
# is 'Postal mail', and product = 'Credit Reporting' when the real value is the
# full renamed string below — both silently produced wrong/empty results).
PRODUCT_VALUES = """
'Credit reporting, credit repair services, or other personal consumer reports'
'Debt collection'
'Mortgage'
'Credit card or prepaid card'
'Checking or savings account'
'Credit reporting'
'Credit card'
'Bank account or service'
'Student loan'
'Money transfer, virtual currency, or money service'
'Vehicle loan or lease'
'Consumer Loan'
'Payday loan, title loan, or personal loan'
'Payday loan'
'Money transfers'
'Prepaid card'
'Other financial service'
'Virtual currency'
"""

SUBMITTED_VIA_VALUES = "'Web', 'Referral', 'Phone', 'Postal mail', 'Fax', 'Web Referral', 'Email'"

COMPANY_RESPONSE_VALUES = (
    "'Closed with explanation', 'Closed with non-monetary relief', "
    "'Closed with monetary relief', 'In progress', 'Closed without relief', "
    "'Closed', 'Untimely response', 'Closed with relief'"
)

DATASET_EARLIEST_DATE = "2011-12-01"
DATASET_LATEST_DATE = "2023-03-23"  # dataset is NOT updated in real time — do not assume recent data exists

SCHEMA_DESCRIPTION = f"""
Table: `{TABLE_REF}`

- date_received (DATE): date the complaint was received by the CFPB. Data spans
  {DATASET_EARLIEST_DATE} to {DATASET_LATEST_DATE} ONLY — this is a static public snapshot,
  not a live feed. It does NOT contain anything after March 2023. If a question refers to
  "last year", "this year", "recently", or similar, interpret it relative to
  {DATASET_LATEST_DATE} (the dataset's actual latest date), NOT the real-world current date.
  If a relative-time question falls entirely outside the dataset's range, say so explicitly
  in your answer rather than just reporting "no results found".
- product (STRING): product type. The ONLY real values are: {PRODUCT_VALUES}
  Note several near-duplicate pairs exist from CFPB taxonomy changes over time (e.g. 'Credit
  card' vs 'Credit card or prepaid card'; 'Credit reporting' vs 'Credit reporting, credit
  repair services, or other personal consumer reports'; 'Payday loan' vs 'Payday loan, title
  loan, or personal loan'; 'Money transfers' vs 'Money transfer, virtual currency, or money
  service'). NEVER invent or guess a product string — use one of the exact values listed
  above, or a LIKE clause, or a WHERE...IN covering the known related variants. If a question
  is ambiguous about which variant it means, either cover all related variants or state in
  the answer exactly which category string(s) were used.
- subproduct (STRING): sub-product type
- issue (STRING): the specific issue the consumer identified
- subissue (STRING): the specific sub-issue the consumer identified
- consumer_complaint_narrative (STRING): free-text complaint description (often NULL — consumer must opt in)
- company_public_response (STRING): company's optional public-facing response
- company_name (STRING): name of the company complained about
- state (STRING): two-letter US state postal code
- zip_code (STRING): consumer's mailing ZIP code
- tags (STRING): supports easier searching/sorting (e.g. 'Older American', 'Servicemember')
- consumer_consent_provided (STRING): whether the consumer opted in to publish their narrative
- submitted_via (STRING): how the complaint was submitted. The ONLY real values are:
  {SUBMITTED_VIA_VALUES}. Note 'Postal mail' is the real value for physical mail — NOT 'Mail'.
- date_sent_to_company (DATE): date the CFPB forwarded the complaint to the company
- company_response_to_consumer (STRING): the company's response category. The ONLY real
  values are: {COMPANY_RESPONSE_VALUES}
- timely_response (BOOLEAN): whether the company responded within the required time window
- consumer_disputed (BOOLEAN): whether the consumer disputed the company's response
- complaint_id (STRING): unique CFPB complaint identifier

Notes for query generation:
- timely_response and consumer_disputed are BOOLEAN, not strings — compare with TRUE/FALSE, not 'Yes'/'No'.
- consumer_complaint_narrative is frequently NULL; don't assume it's populated.
- consumer_disputed is heavily NULL (the CFPB stopped populating it for most complaints after
  ~2017 — roughly 70%+ NULL overall). A "% disputed" computed over ALL rows (NULL counted as
  not-disputed) will be much lower than a "% disputed" computed only over rows where dispute
  status was actually recorded. These are both defensible but very different numbers — when a
  question about disputes is ambiguous about which one it wants, compute both and explain the
  difference, or state clearly which denominator you used.
- Always fully qualify the table as `{TABLE_REF}` since it's a public dataset outside your own project.
- IMPORTANT: there is NO consumer-identifier column in this table. complaint_id identifies a
  complaint, not a person — the same consumer could have filed multiple complaints. Do NOT
  treat "number of complaints" and "number of consumers" as equivalent. If a question asks
  about "consumers" (e.g. "how many consumers...", "what % of consumers...") when only
  complaint-level counts are derivable, answer using complaint counts but explicitly say so
  rather than silently presenting a complaint count as a consumer count.
"""