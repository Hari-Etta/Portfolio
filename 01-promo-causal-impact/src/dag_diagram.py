"""
dag_diagram.py — simple causal DAG for the promo experiment (Phase 2 Step 5).
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

fig, ax = plt.subplots(figsize=(8, 5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 6)
ax.axis("off")

boxes = {
    "treatment": (1.5, 3, "Treatment\n(promo exposure)"),
    "conversion": (8, 3, "Conversion\n(outcome)"),
    "covariates": (4.75, 5, "Pre-treatment\ncovariates (f0-f11)"),
}

for key, (x, y, label) in boxes.items():
    ax.add_patch(mpatches.FancyBboxPatch((x-1, y-0.5), 2, 1, boxstyle="round,pad=0.1",
                                          facecolor="#EAF2FF", edgecolor="#2A5DB0", linewidth=1.5))
    ax.text(x, y, label, ha="center", va="center", fontsize=10)

# Treatment -> Conversion (the causal effect of interest)
ax.add_patch(FancyArrowPatch((2.5, 3), (7, 3), arrowstyle="-|>", mutation_scale=20,
                              color="#2A5DB0", linewidth=2))
ax.text(4.75, 3.3, "causal effect (randomized)", ha="center", fontsize=9, color="#2A5DB0")

# Covariates -> Treatment and Covariates -> Conversion (dashed, NOT confounding since randomized)
ax.add_patch(FancyArrowPatch((4, 4.6), (2, 3.6), arrowstyle="-|>", mutation_scale=15,
                              color="#999999", linewidth=1, linestyle="--"))
ax.add_patch(FancyArrowPatch((5.5, 4.6), (7.5, 3.6), arrowstyle="-|>", mutation_scale=15,
                              color="#999999", linewidth=1, linestyle="--"))
ax.text(4.75, 4.9, "pre-treatment only — NOT a confounder (randomization\nsevers any covariate -> treatment backdoor path)",
        ha="center", fontsize=8, color="#666666")

plt.title("Causal DAG: Promo Treatment -> Conversion", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig("docs/dag_diagram.png", dpi=150, bbox_inches="tight")
print("Saved docs/dag_diagram.png")