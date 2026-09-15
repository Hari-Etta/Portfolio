"""Generates a simple chart from tool results — lets the agent produce a visual,
not just text, when a question calls for one (e.g. "trend over time", "compare
these five products")."""
import matplotlib
matplotlib.use("Agg")  # headless backend — no display needed on a server/Streamlit
import matplotlib.pyplot as plt
import pandas as pd
import io
import base64


def generate_chart(data: list[dict], x_col: str, y_col: str, chart_type: str = "bar") -> dict:
    """Renders a chart from tool-result rows and returns it as a base64 PNG string
    the Streamlit UI can display directly with st.image."""
    if not data:
        return {"error": "No data to chart"}

    df = pd.DataFrame(data)
    if x_col not in df.columns or y_col not in df.columns:
        return {"error": f"Columns not found: need '{x_col}' and '{y_col}', got {list(df.columns)}"}

    fig, ax = plt.subplots(figsize=(8, 4.5))
    try:
        if chart_type == "line":
            df.plot(kind="line", x=x_col, y=y_col, ax=ax, marker="o")
        else:
            df.plot(kind="bar", x=x_col, y=y_col, ax=ax, legend=False)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        encoded = base64.b64encode(buf.getvalue()).decode()
        return {"image_base64": encoded}
    finally:
        plt.close(fig)  # always release the figure, even if plotting raised