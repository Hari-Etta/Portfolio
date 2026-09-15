"""Aggregation/summary statistics tool — lets the agent compute quick descriptive
stats (counts, percentages, min/max/mean) over a set of query results without
having to round-trip another SQL query for something simple."""
import pandas as pd


def summarize(data: list[dict], group_col: str | None = None, value_col: str | None = None) -> dict:
    """Summarizes a list of result rows. If group_col is given, returns counts (and
    optionally value_col aggregates) per group. Otherwise returns overall stats."""
    if not data:
        return {"error": "No data to summarize"}

    df = pd.DataFrame(data)

    if group_col:
        if group_col not in df.columns:
            return {"error": f"Column '{group_col}' not found, have {list(df.columns)}"}
        counts = df[group_col].value_counts()
        summary = {
            "group_counts": {str(k): int(v) for k, v in counts.to_dict().items()},
            "total_rows": len(df),
            "unique_groups": int(counts.shape[0]),
        }
        if value_col and value_col in df.columns:
            sums = df.groupby(group_col)[value_col].sum().to_dict()
            summary["group_value_sums"] = {str(k): float(v) for k, v in sums.items()}
        return summary

    numeric_cols = df.select_dtypes(include="number").columns
    return {
        "total_rows": len(df),
        "columns": list(df.columns),
        "numeric_summary": {
            col: {
                "mean": float(df[col].mean()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "sum": float(df[col].sum()),
            }
            for col in numeric_cols
        },
    }


def percentage(data: list[dict], condition_col: str, condition_value) -> dict:
    """Computes what percentage of rows have condition_col == condition_value —
    e.g. 'what % of complaints got a timely response' -> percentage(rows, 'timely_response', True)."""
    if not data:
        return {"error": "No data to compute percentage from"}

    df = pd.DataFrame(data)
    if condition_col not in df.columns:
        return {"error": f"Column '{condition_col}' not found, have {list(df.columns)}"}

    matches = int((df[condition_col] == condition_value).sum())
    total = len(df)
    return {
        "matches": matches,
        "total": total,
        "percentage": round(float(matches / total) * 100, 2) if total else 0.0,
    }