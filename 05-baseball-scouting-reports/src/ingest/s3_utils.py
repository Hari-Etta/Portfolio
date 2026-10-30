"""Writes/checks Parquet objects in S3 — every ingestion step goes through here."""
import io
import os

import boto3
import pandas as pd
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()
BUCKET = os.environ["S3_BUCKET"]
_s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-2"))


def write_parquet(df: pd.DataFrame, key: str) -> None:
    """Object (mixed-type) columns are cast to nullable strings so Parquet writes never fail
    on messy API fields; real typing happens in the silver layer."""
    df = df.copy()
    for col in df.columns[df.dtypes == "object"]:
        df[col] = df[col].astype("string")
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    _s3.put_object(Bucket=BUCKET, Key=key, Body=buf.getvalue())
    print(f"wrote {len(df):,} rows -> s3://{BUCKET}/{key}")


def key_exists(key: str) -> bool:
    """Lets the backfill skip chunks already uploaded, so a failed run can resume.
    Only 'not found' counts as missing; permission errors fail loudly."""
    try:
        _s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise
