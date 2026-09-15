"""
evaluation.py — Phase 3: Qini curve, decile targeting table, and the
business/dollar translation.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DATA_PATH = "data/criteo_sample_with_uplift.csv"
OUTCOME = "conversion"
ASSUMED_AOV = 50.0  # illustrative average order value — clearly labeled as an assumption


def qini_curve(df, uplift_col="predicted_uplift", treatment_col="treatment", outcome_col=OUTCOME):
    df_sorted = df.sort_values(uplift_col, ascending=False).reset_index(drop=True)
    df_sorted["cum_treat_outcome"] = (df_sorted[outcome_col] * df_sorted[treatment_col]).cumsum()
    df_sorted["cum_control_outcome"] = (df_sorted[outcome_col] * (1 - df_sorted[treatment_col])).cumsum()
    df_sorted["cum_treat_n"] = df_sorted[treatment_col].cumsum()
    df_sorted["cum_control_n"] = (1 - df_sorted[treatment_col]).cumsum().replace(0, np.nan)

    ratio = df_sorted["cum_treat_n"] / df_sorted["cum_control_n"]
    df_sorted["qini"] = df_sorted["cum_treat_outcome"] - df_sorted["cum_control_outcome"] * ratio
    df_sorted["qini"] = df_sorted["qini"].bfill().fillna(0)  # fix early rows with no control yet
    df_sorted["population_frac"] = (df_sorted.index + 1) / len(df_sorted)
    return df_sorted


def qini_coefficient(df_sorted):
    """Area between the actual Qini curve and the random-targeting diagonal,
    normalized — analogous to a Gini coefficient for uplift targeting."""
    x = df_sorted["population_frac"].values
    y = df_sorted["qini"].values
    total_incremental = y[-1]
    random_line = x * total_incremental  # straight line from (0,0) to (1, total_incremental)

    area_model = np.trapezoid(y, x)
    area_random = np.trapezoid(random_line, x)
    qini_coef = (area_model - area_random) / len(df_sorted)  # normalized
    return qini_coef, total_incremental


def decile_table(df_sorted):
    """% of incremental conversions captured vs. % of spend (population) per decile."""
    total_incremental = df_sorted["qini"].iloc[-1]
    rows = []
    for decile in range(1, 11):
        frac = decile / 10
        idx = int(len(df_sorted) * frac) - 1
        incremental_at_decile = df_sorted["qini"].iloc[idx]
        pct_incremental_captured = incremental_at_decile / total_incremental if total_incremental != 0 else np.nan
        rows.append({
            "decile": decile,
            "pct_of_spend": frac,
            "cumulative_incremental_conversions": incremental_at_decile,
            "pct_of_incremental_captured": pct_incremental_captured,
            "efficiency_ratio": pct_incremental_captured / frac,
        })
    return pd.DataFrame(rows)


def plot_qini(df_sorted, save_path="docs/qini_curve.png"):
    x = df_sorted["population_frac"].values
    y = df_sorted["qini"].values
    total_incremental = y[-1]
    random_line = x * total_incremental

    fig, ax = plt.subplots(figsize=(8, 5.5), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")

    ax.plot(x, y, color="#2a78d6", linewidth=2, label="Causal forest targeting (model)")
    ax.plot(x, random_line, color="#c3c2b7", linewidth=2, linestyle="--", label="Random targeting (baseline)")

    ax.set_xlabel("Fraction of population targeted (sorted by predicted uplift)", color="#52514e", fontsize=10)
    ax.set_ylabel("Cumulative incremental conversions", color="#52514e", fontsize=10)
    ax.set_title("Qini Curve: Model-Guided vs. Random Promo Targeting",
                 color="#0b0b0b", fontsize=13, fontweight="bold", pad=12)

    ax.grid(True, color="#e1e0d9", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#c3c2b7")
    ax.tick_params(colors="#898781")
    ax.legend(frameon=False, fontsize=9, labelcolor="#0b0b0b")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
    print(f"Saved Qini curve to {save_path}")


def business_translation(decile_df, df_sorted, n_total, assumed_aov=ASSUMED_AOV):
    total_incremental_full = decile_df["cumulative_incremental_conversions"].iloc[-1]

    peak_idx = df_sorted["qini"].idxmax()
    peak_frac = df_sorted["population_frac"].iloc[peak_idx]
    peak_value = df_sorted["qini"].iloc[peak_idx]
    excluded_frac = 1 - peak_frac
    gain_vs_blanket = (peak_value - total_incremental_full) / total_incremental_full

    dollar_value_optimal = peak_value * assumed_aov
    dollar_value_blanket = total_incremental_full * assumed_aov

    print("\n--- Business translation (illustrative, AOV assumed) ---")
    print(f"Assumed average order value: ${assumed_aov:.2f} (label as illustrative in README)")
    print(f"\nExcluding the bottom {excluded_frac:.1%} of customers (predicted 'sleeping dogs' — "
          f"negative response to the promo):")
    print(f"  -> Net incremental conversions rise from {total_incremental_full:.1f} (blanket) "
          f"to {peak_value:.1f} (optimal targeting)")
    print(f"  -> That's a {gain_vs_blanket:.1%} INCREASE in incremental conversions")
    print(f"  -> ...while spending {excluded_frac:.1%} LESS (only targeting {peak_frac:.1%} of customers)")
    print(f"  -> ~${dollar_value_optimal:,.0f} in incremental revenue under optimal targeting "
          f"vs. ~${dollar_value_blanket:,.0f} under blanket rollout")


def find_optimal_cutoff(df_sorted):
    """Find the population fraction that maximizes cumulative incremental
    conversions — this is the actual optimal targeting policy, not necessarily
    the top decile. Points past this are net-negative to include (sleeping dogs)."""
    peak_idx = df_sorted["qini"].idxmax()
    peak_frac = df_sorted["population_frac"].iloc[peak_idx]
    peak_value = df_sorted["qini"].iloc[peak_idx]
    total_at_100pct = df_sorted["qini"].iloc[-1]

    print(f"\n--- Optimal targeting cutoff (peak of Qini curve) ---")
    print(f"Optimal fraction to target: {peak_frac:.1%} of population")
    print(f"Incremental conversions at optimal cutoff: {peak_value:.1f}")
    print(f"vs. blanket rollout (100%): {total_at_100pct:.1f} incremental conversions")
    print(f"Targeting only the optimal {peak_frac:.1%} captures "
          f"{peak_value / total_at_100pct:.1%} of blanket rollout's result, "
          f"using {peak_frac:.1%} of the spend")
    print(f"Beyond this cutoff, additional targeting REDUCES net incremental conversions "
          f"(the added customers have negative predicted uplift — 'sleeping dogs')")
    return peak_frac, peak_value


if __name__ == "__main__":
    df = pd.read_csv(DATA_PATH)
    df_sorted = qini_curve(df)

    qini_coef, total_incremental = qini_coefficient(df_sorted)
    print(f"Qini coefficient: {qini_coef:.5f}")
    print(f"Total incremental conversions (full population): {total_incremental:.1f}")

    decile_df = decile_table(df_sorted)
    print("\n--- Decile targeting table ---")
    print(decile_df.to_string(index=False))

    plot_qini(df_sorted)
    find_optimal_cutoff(df_sorted)
    business_translation(decile_df, df_sorted, len(df))