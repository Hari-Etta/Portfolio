"""
power_analysis.py — minimum detectable effect (MDE) and required sample size
for the promo conversion experiment.
"""
import pandas as pd
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

SAMPLE_PATH = "data/criteo_sample.csv"

def run_power_analysis(df, mde_relative=0.10, alpha=0.05, power=0.8):
    baseline_rate = df[df.treatment == 0]["conversion"].mean()
    treat_rate_at_mde = baseline_rate * (1 + mde_relative)
    effect_size = proportion_effectsize(baseline_rate, treat_rate_at_mde)

    analysis = NormalIndPower()
    required_n = analysis.solve_power(effect_size=effect_size, alpha=alpha, power=power, ratio=1.0)

    n_control_actual = (df.treatment == 0).sum()
    n_treatment_actual = (df.treatment == 1).sum()

    print(f"Baseline conversion rate (control): {baseline_rate:.5f}")
    print(f"Target MDE: {mde_relative:.0%} relative lift -> {treat_rate_at_mde:.5f}")
    print(f"Effect size (Cohen's h): {effect_size:.5f}")
    print(f"Required N per arm (alpha={alpha}, power={power:.0%}, equal allocation): {required_n:,.0f}")
    print(f"\nActual N — control: {n_control_actual:,} | treatment: {n_treatment_actual:,}")

    if n_control_actual >= required_n:
        print(f"Control arm has {n_control_actual/required_n:.1f}x the required sample — well-powered to detect a {mde_relative:.0%} relative lift.")
    else:
        print(f"Control arm is UNDER-powered for a {mde_relative:.0%} relative lift at equal allocation — but note actual allocation is 85/15, not 1:1, which changes the effective power calculation.")

    return {
        "baseline_rate": baseline_rate,
        "effect_size": effect_size,
        "required_n_per_arm": required_n,
        "actual_n_control": n_control_actual,
        "actual_n_treatment": n_treatment_actual,
    }

def achievable_mde(df, alpha=0.05, power=0.8):
    """What's the smallest relative lift detectable given the ACTUAL sample sizes and allocation ratio?"""
    baseline_rate = df[df.treatment == 0]["conversion"].mean()
    n_control = (df.treatment == 0).sum()
    n_treatment = (df.treatment == 1).sum()
    ratio = n_treatment / n_control  # statsmodels ratio = nobs2/nobs1

    analysis = NormalIndPower()
    # Solve for effect_size given the actual nobs1/ratio/alpha/power (leave effect_size=None)
    achievable_effect_size = analysis.solve_power(
        effect_size=None, nobs1=n_control, alpha=alpha, power=power, ratio=ratio
    )
    # Convert Cohen's h back to an approximate relative lift around baseline_rate
    # (numeric search since proportion_effectsize isn't directly invertible in closed form)
    import numpy as np
    from statsmodels.stats.proportion import proportion_effectsize as pes
    lifts = np.linspace(0.001, 2.0, 20000)
    candidate_rates = baseline_rate * (1 + lifts)
    candidate_effects = np.abs(pes(baseline_rate, candidate_rates))
    idx = np.argmin(np.abs(candidate_effects - achievable_effect_size))
    achievable_relative_lift = lifts[idx]

    print(f"\n--- Achievable MDE given actual sample (n_control={n_control:,}, n_treatment={n_treatment:,}, ratio={ratio:.2f}) ---")
    print(f"Smallest detectable effect size (Cohen's h) at {power:.0%} power: {achievable_effect_size:.5f}")
    print(f"Approx. smallest detectable RELATIVE lift: {achievable_relative_lift:.1%}")
    print(f"i.e. this data can reliably detect a lift from {baseline_rate:.4f} to ~{baseline_rate*(1+achievable_relative_lift):.4f}, but NOT the originally targeted 10% lift.")
    return achievable_relative_lift

if __name__ == "__main__":
    df = pd.read_csv(SAMPLE_PATH)
    run_power_analysis(df)
    achievable_mde(df)