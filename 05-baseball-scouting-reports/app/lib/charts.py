"""Shared Plotly charts so every page draws pitches the same way (consistent colors per pitch type)."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PITCH_COLORS = {
    "FF": "#d62728", "SI": "#ff7f0e", "FC": "#8c564b",                     # fastballs
    "SL": "#1f77b4", "ST": "#17becf", "CU": "#2ca02c", "KC": "#98df8a",    # breaking
    "SV": "#9edae5", "CS": "#bcbd22",
    "CH": "#9467bd", "FS": "#e377c2", "FO": "#c5b0d5", "SC": "#f7b6d2",    # offspeed
    "KN": "#7f7f7f", "EP": "#c7c7c7", "FA": "#d62728",
}


def name_colors(df: pd.DataFrame) -> dict:
    """Maps each pitch_name in df to the color of its pitch_type."""
    pairs = df[["pitch_type", "pitch_name"]].drop_duplicates()
    return {n: PITCH_COLORS.get(t, "#7f7f7f") for t, n in zip(pairs["pitch_type"], pairs["pitch_name"])}


def movement_chart(arsenal: pd.DataFrame, throws: str) -> go.Figure:
    """Pitch movement from the pitcher's side: x = arm side (+) vs glove side (-), y = induced vertical break."""
    d = arsenal.copy()
    d["arm_side_in"] = -d["horz_break_in"] if throws == "R" else d["horz_break_in"]
    d["usage"] = (100 * d["usage_pct"]).round(1)
    fig = px.scatter(
        d, x="arm_side_in", y="vert_break_in", size="usage", color="pitch_name",
        color_discrete_map=name_colors(d), size_max=40,
        hover_data={"avg_velo": True, "usage": True, "whiff_rate": ":.1%", "arm_side_in": ":.1f",
                    "vert_break_in": ":.1f", "pitch_name": False},
        labels={"arm_side_in": "← glove side   horizontal break (in)   arm side →",
                "vert_break_in": "induced vertical break (in)", "pitch_name": "Pitch",
                "avg_velo": "mph", "usage": "usage %"},
    )
    fig.add_hline(y=0, line_color="gray", line_width=1)
    fig.add_vline(x=0, line_color="gray", line_width=1)
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10), legend_title_text="")
    return fig
