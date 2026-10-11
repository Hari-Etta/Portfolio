"""Fixes multi-line review text in the raw CSV that broke Databricks' naive upload parser.
Pandas parses quoted multi-line fields correctly; this collapses embedded newlines to spaces
so any naive line-based parser (including Databricks' upload UI) reads it correctly too."""
import pandas as pd

SRC = "data/raw/olist_order_reviews_dataset.csv"
DEST = "data/raw/olist_order_reviews_dataset_cleaned.csv"

df = pd.read_csv(SRC)
text_cols = ["review_comment_title", "review_comment_message"]
for col in text_cols:
    df[col] = df[col].astype(str).str.replace(r"[\r\n]+", " ", regex=True)
    df[col] = df[col].replace("nan", pd.NA)

df.to_csv(DEST, index=False)
print(f"Wrote cleaned file to {DEST}, {len(df)} rows, 0 order_id nulls expected: "
      f"{df['order_id'].isnull().sum()} nulls found")