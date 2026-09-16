"""Documents what's actually in the raw data BEFORE any cleaning — don't assume it's clean."""
import pandas as pd
import glob

def check_raw_files(raw_dir: str = "data/raw"):
    report = {}
    for filepath in glob.glob(f"{raw_dir}/*.csv"):
        df = pd.read_csv(filepath)
        report[filepath] = {
            "rows": len(df),
            "null_counts": df.isnull().sum().to_dict(),
            "duplicate_rows": df.duplicated().sum(),
        }
    return report

if __name__ == "__main__":
    for filepath, stats in check_raw_files().items():
        print(f"\n{filepath}: {stats['rows']} rows, {stats['duplicate_rows']} duplicates")
        nulls = {k: v for k, v in stats["null_counts"].items() if v > 0}
        if nulls:
            print(f"  Columns with nulls: {nulls}")