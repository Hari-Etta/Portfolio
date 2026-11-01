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


def zone_heatmap(cells: pd.DataFrame, value: str, fmt: str, colorscale: str = "Reds") -> go.Figure:
    """Strike zone from the CATCHER's view: Statcast zones 1-9 as a 3x3 grid, outside zones 11-14 in the corners.
    cells: one row per zone with a numeric column `value`."""
    import numpy as np

    grid = np.full((3, 3), np.nan)
    text = [["" for _ in range(3)] for _ in range(3)]
    outside = {}
    for _, r in cells.iterrows():
        z, v = int(r["zone"]), r[value]
        label = fmt.format(v) if pd.notna(v) else "-"
        if 1 <= z <= 9:
            grid[(z - 1) // 3][(z - 1) % 3] = v
            text[(z - 1) // 3][(z - 1) % 3] = label
        else:
            outside[z] = label
    fig = go.Figure(go.Heatmap(z=grid, x=[0, 1, 2], y=[0, 1, 2], text=text, texttemplate="%{text}",
                               textfont={"size": 16}, colorscale=colorscale, showscale=False,
                               xgap=4, ygap=4, hoverinfo="skip"))
    corners = {11: (-0.95, -0.95, "high, catcher's left"), 12: (2.95, -0.95, "high, catcher's right"),
               13: (-0.95, 2.95, "low, catcher's left"), 14: (2.95, 2.95, "low, catcher's right")}
    for z, (x, y, name) in corners.items():
        fig.add_annotation(x=x, y=y, text=f"<b>{outside.get(z, '-')}</b><br><span style='font-size:10px'>{name}</span>",
                           showarrow=False, font={"size": 13})
    fig.update_xaxes(visible=False, range=[-1.7, 3.7])
    fig.update_yaxes(visible=False, range=[3.7, -1.7])
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=10, b=10))
    return fig


DEPTH_RADII = {"infield_front": (0, 100), "infield_back": (100, 160),
               "outfield_front": (160, 275), "outfield_back": (275, 400)}
DIRECTION_ANGLE = {"left": -30, "center": 0, "right": 30}


def field_chart(zones: pd.DataFrame) -> go.Figure:
    """The 12 field zones as a fan (home plate at the center; left field on the left).
    zones: one row per field zone with depth, direction, share (0-1) and batted_balls."""
    d = zones.copy()
    d["base"] = d["depth"].map(lambda x: DEPTH_RADII[x][0])
    d["length"] = d["depth"].map(lambda x: DEPTH_RADII[x][1] - DEPTH_RADII[x][0])
    d["theta"] = d["direction"].map(DIRECTION_ANGLE)
    d["label"] = d.apply(lambda r: f"{r['depth'].replace('_', ' ')} {r['direction']}: "
                                   f"{100 * r['share']:.0f}% ({int(r['batted_balls'])} balls)", axis=1)
    fig = go.Figure(go.Barpolar(
        r=d["length"], base=d["base"], theta=d["theta"], width=[29.5] * len(d),
        marker=dict(color=100 * d["share"], colorscale="YlOrRd", cmin=0, showscale=True,
                    colorbar=dict(title="% of balls", thickness=12)),
        hovertext=d["label"], hoverinfo="text",
    ))
    for _, r in d.iterrows():
        rad = r["base"] + r["length"] / 2
        fig.add_trace(go.Scatterpolar(r=[rad], theta=[r["theta"]], mode="text",
                                      text=[f"{100 * r['share']:.0f}%"], textfont=dict(size=12, color="black"),
                                      hoverinfo="skip", showlegend=False))
    fig.update_layout(
        polar=dict(angularaxis=dict(rotation=90, direction="clockwise", showticklabels=False, showgrid=False),
                   radialaxis=dict(range=[0, 400], showticklabels=False, showgrid=False), bgcolor="rgba(0,0,0,0)"),
        height=460, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    )
    return fig
