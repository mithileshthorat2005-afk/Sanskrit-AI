#!/usr/bin/env python
"""
Publication-quality figures for the BKT P(L0) prior experiment.

Reads the CSVs produced by `run_experiment.py` and writes PNG files to the
`figures/` directory.  Nothing here touches production data; every number
plotted comes from the saved result tables, so a figure can be regenerated
without re-running the simulation.

Figures
-------
  1  fig1_prior_optimization_curves.png  candidate P(L0) vs validation log loss
  2  fig2_brier_comparison.png           Brier: production / common / group-specific
  3  fig3_heldout_performance.png        held-out log loss and Brier by group
  4  fig4_calibration.png                reliability diagrams
  5  fig5_mastery_trajectories.png       mastery over repeated observations
  6  fig6_sensitivity.png                near-optimal ranges across scenarios
  7  fig7_zero_attempt_mastery.png       zero-attempt mastery and false-mastery

Usage:  python make_figures.py [--results DIR] [--figures DIR]
Exit status 0 on success, 1 on any failure.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Dict, List, Optional, Sequence

import matplotlib
matplotlib.use("Agg")  # headless: always write files, never open a window
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bkt_core  # noqa: E402

GROUPS = ("beginner", "intermediate", "advanced")
OVERALL = "overall"
PRIMARY = "primary"

GROUP_COLOR = {
    "beginner": "#2b6cb0",
    "intermediate": "#2f855a",
    "advanced": "#c05621",
    OVERALL: "#4a5568",
}
STRATEGY_COLOR = {
    "production": "#1a365d",
    "common": "#805ad5",
    "group_specific": "#2b6cb0",
    "group_x_tier": "#2f855a",
    "oracle_reference": "#a0aec0",
}
STRATEGY_LABEL = {
    "production": "A. Production",
    "common": "B. Common",
    "group_specific": "C. Group-specific",
    "group_x_tier": "E. Group x tier",
    "oracle_reference": "D. Oracle (sim only)",
}
STRATEGY_ORDER = ["production", "common", "group_specific", "group_x_tier",
                  "oracle_reference"]

TIER_COLOR = {"easy": "#2b6cb0", "intermediate": "#2f855a", "advanced": "#c05621"}


def read_csv(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def fnum(row: Dict[str, str], key: str) -> float:
    raw = row.get(key, "")
    if raw in ("", None):
        return float("nan")
    return float(raw)


def _caption(fig, text: str) -> None:
    fig.text(0.01, 0.012, text, ha="left", va="bottom", fontsize=8,
             color="#4a5568")


# ── Figure 1: prior optimisation curves ──────────────────────────────────

def fig1(results_dir: str, figures_dir: str) -> str:
    curves = read_csv(os.path.join(results_dir, "validation_curves.csv"))
    ranges = read_csv(os.path.join(results_dir, "near_optimal_ranges.csv"))
    config = bkt_core.load_config()

    rows = [r for r in curves
            if r["scenario"] == PRIMARY and r["scope"] == "group_specific"]
    range_by_group = {
        r["group"]: r for r in ranges
        if r["scenario"] == PRIMARY and r["scope"] == "group_specific"
    }

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8), sharey=False)
    for ax, group in zip(axes, GROUPS):
        data = [r for r in rows if r["group"] == group]
        xs = [fnum(r, "candidate_prior") for r in data]
        ys = [fnum(r, "mean_log_loss") for r in data]

        rng = range_by_group[group]
        lo, hi = fnum(rng, "near_opt_lo"), fnum(rng, "near_opt_hi")
        sel = fnum(rng, "selected_prior")
        ymin, ymax = min(ys), max(ys)
        pad = (ymax - ymin) * 0.10 + 1e-9

        # Near-optimal band (within one bootstrap SE of the minimum).
        ax.axvspan(lo, hi, color="#f6ad55", alpha=0.28, zorder=0,
                   label=f"Near-optimal range [{lo:.2f}, {hi:.2f}]")

        # Production tier priors for this proficiency group.
        for tier in ("easy", "intermediate", "advanced"):
            pv = bkt_core.INITIAL_MASTERY[group][tier]
            ax.axvline(pv, color=TIER_COLOR[tier], linestyle="--",
                       linewidth=1.6, alpha=0.9, zorder=2,
                       label=f"Production prior ({tier}) = {pv:.2f}")

        ax.plot(xs, ys, color="#1a365d", linewidth=2.0, zorder=3,
                label="Validation log loss")
        ax.plot([sel], [fnum(rng, "min_log_loss")], marker="o", markersize=10,
                color="#c53030", zorder=5,
                label=f"Selected P(L0) = {sel:.2f}")

        ax.set_title(f"{group.capitalize()} learners", fontsize=12, fontweight="bold")
        ax.set_xlabel(r"Candidate prior $P(L_0)$")
        ax.set_ylim(ymin - pad, ymax + pad)
        ax.grid(alpha=0.3, linewidth=0.6)
        ax.set_xlim(0, 1)
        if group == GROUPS[0]:
            ax.set_ylabel("Validation log loss (lower is better)")

    handles, labels = axes[0].get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    fig.legend(by_label.values(), by_label.keys(), loc="upper center",
               bbox_to_anchor=(0.5, 1.045), ncol=3, fontsize=8.5, frameon=False)
    fig.suptitle("Figure 1 - Validation log loss over candidate $P(L_0)$ priors, "
                 "by proficiency group", fontsize=13.5, fontweight="bold", y=1.13)
    _caption(fig,
             "Scenario 'primary' (data-generating means equal to the production "
             "seeds). Dashed lines are the three production tier priors each group "
             "currently uses; the shaded band is the near-optimal set "
             "(candidates within one student-level bootstrap standard error of the "
             "validation minimum). Selection uses the VALIDATION split only.")
    fig.tight_layout(rect=(0, 0.035, 1, 0.93))
    path = os.path.join(figures_dir, "fig1_prior_optimization_curves.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


# ── Figure 2: Brier comparison ───────────────────────────────────────────

def fig2(results_dir: str, figures_dir: str) -> str:
    metrics = read_csv(os.path.join(results_dir, "strategy_test_metrics.csv"))
    rows = [r for r in metrics if r["scenario"] == PRIMARY]
    lookup = {(r["strategy"], r["group"]): r for r in rows}

    groups = list(GROUPS) + [OVERALL]
    strategies = [s for s in STRATEGY_ORDER
                  if any((s, g) in lookup for g in groups)]

    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    width = 0.16
    xs = range(len(groups))
    for i, strat in enumerate(strategies):
        offset = (i - (len(strategies) - 1) / 2) * width
        vals = [fnum(lookup[(strat, g)], "brier") if (strat, g) in lookup else 0.0
                for g in groups]
        bars = ax.bar([x + offset for x in xs], vals, width=width,
                      color=STRATEGY_COLOR[strat],
                      edgecolor="white", linewidth=0.7,
                      label=STRATEGY_LABEL[strat],
                      hatch=("///" if strat == "oracle_reference" else None))
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.004, f"{v:.3f}",
                    ha="center", va="bottom", fontsize=7.5, rotation=90)

    ax.set_xticks(list(xs))
    ax.set_xticklabels([g.capitalize() for g in groups], fontsize=11)
    ax.set_ylabel("Brier score (lower is better)")
    ax.set_title("Figure 2 - Held-out Brier score by initialization strategy",
                 fontsize=13.5, fontweight="bold")
    ax.legend(fontsize=9, ncol=3, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.10))
    ax.grid(axis="y", alpha=0.3, linewidth=0.6)
    ax.set_ylim(0, max(fnum(r, "brier") for r in rows) * 1.35)
    _caption(fig, "Scenario 'primary', held-out TEST split (never used for "
                  "selection). Lower is better. Hatched bar is the simulation-only "
                  "oracle reference, unavailable in a real deployment.")
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    path = os.path.join(figures_dir, "fig2_brier_comparison.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


# ── Figure 3: held-out performance ───────────────────────────────────────

def fig3(results_dir: str, figures_dir: str) -> str:
    metrics = read_csv(os.path.join(results_dir, "strategy_test_metrics.csv"))
    rows = [r for r in metrics if r["scenario"] == PRIMARY]
    lookup = {(r["strategy"], r["group"]): r for r in rows}
    groups = list(GROUPS) + [OVERALL]
    strategies = [s for s in STRATEGY_ORDER
                  if any((s, g) in lookup for g in groups)]

    fig, axes = plt.subplots(1, 3, figsize=(17.5, 5.2))
    specs = [("log_loss", "Log loss", axes[0]),
             ("brier", "Brier score", axes[1]),
             ("ece", "Calibration error (ECE)", axes[2])]
    width = 0.16

    for metric, ylabel, ax in specs:
        xs = range(len(groups))
        for i, strat in enumerate(strategies):
            offset = (i - (len(strategies) - 1) / 2) * width
            vals = [fnum(lookup[(strat, g)], metric) if (strat, g) in lookup else 0.0
                    for g in groups]
            ax.bar([x + offset for x in xs], vals, width=width,
                   color=STRATEGY_COLOR[strat], edgecolor="white", linewidth=0.7,
                   label=STRATEGY_LABEL[strat],
                   hatch=("///" if strat == "oracle_reference" else None))
        ax.set_xticks(list(xs))
        ax.set_xticklabels([g.capitalize() for g in groups], fontsize=10)
        ax.set_ylabel(f"{ylabel} (lower is better)")
        ax.grid(axis="y", alpha=0.3, linewidth=0.6)
        ax.set_ylim(0, max(fnum(r, metric) for r in rows) * 1.30)

    axes[0].set_title("Log loss", fontsize=12, fontweight="bold")
    axes[1].set_title("Brier score", fontsize=12, fontweight="bold")
    axes[2].set_title("Expected calibration error (10 bins)", fontsize=12,
                      fontweight="bold")
    fig.suptitle("Figure 3 - Held-out predictive performance by proficiency group",
                 fontsize=13.5, fontweight="bold", y=1.14)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, 1.055))
    _caption(fig, "Scenario 'primary', held-out TEST split, 12,000 answers per "
                  "group. Probabilities are predicted BEFORE each answer is "
                  "incorporated. The hatched oracle bar is simulation-only, "
                  "unavailable in a real deployment.")
    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    path = os.path.join(figures_dir, "fig3_heldout_performance.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


# ── Figure 4: calibration / reliability diagrams ─────────────────────────

def fig4(results_dir: str, figures_dir: str) -> str:
    rows = read_csv(os.path.join(results_dir, "calibration_bins.csv"))
    rows = [r for r in rows if r["scenario"] == PRIMARY]
    shown = ["production", "common", "group_specific"]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.0))
    for ax, group in zip(axes, GROUPS):
        for strat in shown:
            data = [r for r in rows
                    if r["group"] == group and r["strategy"] == strat
                    and fnum(r, "count") > 0]
            if not data:
                continue
            data.sort(key=lambda r: fnum(r, "mean_predicted"))
            xs = [fnum(r, "mean_predicted") for r in data]
            ys = [fnum(r, "observed") for r in data]
            ece = data[0].get("ece_group", "")
            ax.plot(xs, ys, marker="o", markersize=5.5, linewidth=1.9,
                    color=STRATEGY_COLOR[strat],
                    label=f"{STRATEGY_LABEL[strat]} (ECE={float(ece):.3f})")
        ax.plot([0, 1], [0, 1], linestyle=":", color="#718096", linewidth=1.4,
                label="Perfect calibration")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(group.capitalize(), fontsize=12, fontweight="bold")
        ax.set_xlabel("Mean predicted P(correct)")
        ax.grid(alpha=0.3, linewidth=0.6)
        if group == GROUPS[0]:
            ax.set_ylabel("Observed correctness rate")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, 1.05))
    fig.suptitle("Figure 4 - Reliability diagrams (scenario 'primary', TEST split)",
                 fontsize=13.5, fontweight="bold", y=1.13)
    _caption(fig, "Points on the diagonal are perfectly calibrated. Bins with zero "
                  "observations are omitted. ECE uses 10 equal-width bins on [0,1].")
    fig.tight_layout(rect=(0, 0.035, 1, 0.93))
    path = os.path.join(figures_dir, "fig4_calibration.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


# ── Figure 5: mastery trajectories ───────────────────────────────────────

def fig5(results_dir: str, figures_dir: str) -> str:
    rows = read_csv(os.path.join(results_dir, "mastery_trajectories.csv"))
    rows = [r for r in rows if r["scenario"] == PRIMARY]

    panels = [("production", "A. Under production priors"),
              ("group_specific", "C. Under group-specific optimized priors")]

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 5.2), sharey=True)
    for ax, (strat, title) in zip(axes, panels):
        for group in GROUPS:
            data = sorted(
                [r for r in rows if r["strategy"] == strat and r["group"] == group],
                key=lambda r: int(r["observation_index"]))
            xs = [int(r["observation_index"]) for r in data]
            ys = [fnum(r, "mean_mastery") for r in data]
            ax.plot(xs, ys, marker="o", markersize=4.5, linewidth=2.0,
                    color=GROUP_COLOR[group], label=group.capitalize())
        ax.axhline(0.7, linestyle="--", color="#c53030", linewidth=1.6,
                   label="Mastery threshold (0.70)")
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xlabel("Observation index (0 = the initial seed, no attempts)")
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 1.0)
        ax.grid(alpha=0.3, linewidth=0.6)

    axes[0].set_ylabel("Mean BKT mastery")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, 1.05))
    fig.suptitle("Figure 5 - Mean mastery trajectories over repeated observations",
                 fontsize=13.5, fontweight="bold", y=1.13)
    _caption(fig, "Held-out TEST split, scenario 'primary'. Left panel starts each "
                  "learner at the production seed; right panel at the optimized "
                  "group prior. Horizontal distance above the 0.70 line at index 0 "
                  "is exactly the 'mastered with zero attempts' effect.")
    fig.tight_layout(rect=(0, 0.035, 1, 0.93))
    path = os.path.join(figures_dir, "fig5_mastery_trajectories.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


# ── Figure 6: sensitivity of near-optimal ranges ─────────────────────────

def fig6(results_dir: str, figures_dir: str, config: Dict) -> str:
    rows = read_csv(os.path.join(results_dir, "near_optimal_ranges.csv"))
    rows = [r for r in rows if r["scope"] == "group_specific"]

    scenario_ids = [s["id"] for s in config["scenarios"]]
    labels = {s["id"]: s["label"] for s in config["scenarios"]}

    fig, axes = plt.subplots(1, 3, figsize=(17.5, 7.4), sharex=True)
    for ax, group in zip(axes, GROUPS):
        prod_vals = [bkt_core.INITIAL_MASTERY[group][t]
                     for t in ("easy", "intermediate", "advanced")]
        plo, phi = min(prod_vals), max(prod_vals)
        ax.axvspan(plo, phi, color="#bee3f8", alpha=0.55, zorder=0,
                   label=f"Production tier priors ({plo:.2f}-{phi:.2f})")

        ypos = []
        for i, sid in enumerate(scenario_ids):
            match = [r for r in rows if r["scenario"] == sid and r["group"] == group]
            if not match:
                continue
            r = match[0]
            lo, hi = fnum(r, "near_opt_lo"), fnum(r, "near_opt_hi")
            sel = fnum(r, "selected_prior")
            y = len(scenario_ids) - 1 - i
            ypos.append(y)
            ax.hlines(y, lo, hi, color=GROUP_COLOR[group], linewidth=6,
                      alpha=0.75, zorder=3)
            ax.plot([sel], [y], marker="D", markersize=7, color="#c53030",
                    zorder=4)
            ax.plot([lo, hi], [y, y], marker="|", markersize=13,
                    color=GROUP_COLOR[group], zorder=4)

        ax.set_yticks(list(range(len(scenario_ids))))
        ax.set_yticklabels([labels.get(s, s) for s in
                            reversed(scenario_ids)], fontsize=8)
        ax.set_xlim(0, 1)
        ax.set_xlabel(r"Prior $P(L_0)$")
        ax.set_title(f"{group.capitalize()}", fontsize=12, fontweight="bold")
        ax.grid(axis="x", alpha=0.3, linewidth=0.6)

    handles, labels_h = axes[0].get_legend_handles_labels()
    extra = [Patch(facecolor="#718096", alpha=0.75, label="Near-optimal range"),
             plt.Line2D([], [], marker="D", color="#c53030", linestyle="",
                        label="Selected prior")]
    fig.legend(handles + extra, labels_h + [e.get_label() for e in extra],
               loc="upper center", ncol=3, fontsize=9, frameon=False,
               bbox_to_anchor=(0.5, 1.04))
    fig.suptitle("Figure 6 - Robustness of the near-optimal prior range across "
                 "simulation scenarios", fontsize=13.5, fontweight="bold", y=1.11)
    _caption(fig, "Each row is an INDEPENDENT scenario; rows are never pooled. "
                  "Bars are the one-standard-error near-optimal set on validation; "
                  "red diamonds mark the arg-min. The blue band is the span of the "
                  "three production tier priors for that proficiency group. Ranges "
                  "that stay inside the blue band support retaining production.")
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    path = os.path.join(figures_dir, "fig6_sensitivity.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


# ── Figure 7: zero-attempt mastery ───────────────────────────────────────

def fig7(results_dir: str, figures_dir: str) -> str:
    rows = read_csv(os.path.join(results_dir, "practical_consequences.csv"))
    rows = [r for r in rows if r["scenario"] == PRIMARY]
    lookup = {(r["strategy"], r["group"]): r for r in rows}
    groups = list(GROUPS) + [OVERALL]
    strategies = [s for s in STRATEGY_ORDER if (s, groups[0]) in lookup]

    fig, axes = plt.subplots(1, 4, figsize=(22.5, 5.4))
    width = 0.16
    specs = [
        ("init_mastered_pct", "% lessons initially >= 0.70\n(zero attempts)",
         "Seed-only classification"),
        ("false_mastered_pct_of_init_mastered",
         "% falsely 'mastered'\nvs hidden truth", "False-mastery (sim only)"),
        ("false_unmastered_pct_of_truth_mastered",
         "% truly mastered but\nNOT flagged at seed", "False-unmastered (sim only)"),
        ("changed_at_10_pct",
         "% whose mastery class changed\nafter 10 observations", "Churn"),
    ]

    for ax, (key, ylabel, subtitle) in zip(axes, specs):
        xs = range(len(groups))
        for i, strat in enumerate(strategies):
            if (strat, groups[0]) not in lookup:
                continue
            offset = (i - (len(strategies) - 1) / 2) * width
            vals = [fnum(lookup[(strat, g)], key) if (strat, g) in lookup else 0.0
                    for g in groups]
            ax.bar([x + offset for x in xs], vals, width=width,
                   color=STRATEGY_COLOR[strat], edgecolor="white", linewidth=0.7,
                   label=STRATEGY_LABEL[strat],
                   hatch=("///" if strat == "oracle_reference" else None))
        ax.set_xticks(list(xs))
        ax.set_xticklabels([g.capitalize() for g in groups], fontsize=9.5)
        ax.set_ylabel(f"{ylabel} (%)")
        ax.set_title(subtitle, fontsize=11, fontweight="bold")
        ax.grid(axis="y", alpha=0.3, linewidth=0.6)
        ax.set_ylim(0, 105)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, 1.06))
    fig.suptitle("Figure 7 - Practical consequences of the initial prior "
                 "(scenario 'primary', TEST split)", fontsize=13.5,
                 fontweight="bold", y=1.14)
    _caption(fig,
             "Panel 1: share of lessons already >= 0.70 before any attempt is "
             "recorded - the 'mastered with zero attempts' effect, which the "
             "dashboard counts and the prerequisite gate honours. Panels 2-3: "
             "simulation-only error rates against the hidden state; they trade "
             "off, so a strategy with 0% false-mastery (B, C) reaches it only by "
             "flagging NOTHING mastered and therefore missing 100% of genuinely "
             "mastered lessons. Panel 4: share of (learner, lesson) pairs whose "
             "classification flips after 10 answers.")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    path = os.path.join(figures_dir, "fig7_zero_attempt_mastery.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Render experiment figures")
    parser.add_argument("--results", default=None)
    parser.add_argument("--figures", default=None)
    args = parser.parse_args(argv)

    config = bkt_core.load_config()
    results_dir = args.results or bkt_core.resolve(config["paths"]["results"])
    figures_dir = args.figures or bkt_core.resolve(config["paths"]["figures"])
    os.makedirs(figures_dir, exist_ok=True)

    made = [
        fig1(results_dir, figures_dir),
        fig2(results_dir, figures_dir),
        fig3(results_dir, figures_dir),
        fig4(results_dir, figures_dir),
        fig5(results_dir, figures_dir),
        fig6(results_dir, figures_dir, config),
        fig7(results_dir, figures_dir),
    ]
    for path in made:
        print(f"  wrote {os.path.basename(path)}  ({os.path.getsize(path)} bytes)")
    print(f"\n{len(made)} figures written to {figures_dir}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
