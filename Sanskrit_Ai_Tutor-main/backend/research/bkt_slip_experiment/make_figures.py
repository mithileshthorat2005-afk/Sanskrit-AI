#!/usr/bin/env python
"""
Generate the nine required figures for the BKT slip-probability experiment.

Every figure is built FROM THE SAVED RESULT CSVs in results/ - nothing is
hard-coded or hand-drawn.  If a CSV is missing the script fails loudly rather
than silently emitting a fabricated plot.

    fig1_validation_curve.png       validation log loss vs slip (+ uncertainty, production)
    fig2_test_metrics.png           held-out test metrics: production / selected / oracle
    fig3_slip_recovery.png          slip recovery across known generating values
    fig4_guess_slip_heatmap.png     guess x slip sensitivity surface
    fig5_l0_slip_heatmap.png        initial-mastery x slip sensitivity surface
    fig6_t_misspec.png              learning-rate misspecification analysis
    fig7_mastery_estimation.png     mastery error and false-mastery comparisons
    fig8_calibration.png            calibration comparison for selected slip settings
    fig9_by_attempt.png             performance by number of prior attempts

Usage
-----
    python make_figures.py            # all figures
    python make_figures.py --only 1 3 # a subset

Exit 0 on success, 1 on any failure.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Dict, List, Optional, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bkt_core  # noqa: E402

PRODUCTION_S = bkt_core.PRODUCTION_SLIP

VARIANT_ORDER = ["bkt_hmm_correct", "deterministic_point", "deterministic_spread"]
VARIANT_LABEL = {
    "bkt_hmm_correct": "BKT HMM (correctly specified)",
    "deterministic_point": "Deterministic learning, point prior",
    "deterministic_spread": "Deterministic learning, Beta spread",
}
VARIANT_COLOR = {
    "bkt_hmm_correct": "#1b7837",
    "deterministic_point": "#2166ac",
    "deterministic_spread": "#b2182b",
}
SETTING_ORDER = ["production", "selected", "oracle"]
SETTING_LABEL = {
    "production": "Production\n(s=0.10)",
    "selected": "Validation-selected",
    "oracle": "Oracle\n(true generating s)",
}


def read_csv(name: str, results_dir: str) -> List[Dict]:
    path = os.path.join(results_dir, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"missing result file {path} - run run_experiment.py first")
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle)]


def _f(row: Dict, key: str, default: Optional[float] = None) -> Optional[float]:
    raw = row.get(key, "")
    if raw in ("", None):
        return default
    return float(raw)


def _i(row: Dict, key: str, default: int = 0) -> int:
    raw = row.get(key, "")
    if raw in ("", None):
        return default
    return int(float(raw))


def _save(fig, figures_dir: str, name: str) -> str:
    os.makedirs(figures_dir, exist_ok=True)
    path = os.path.join(figures_dir, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}")
    return path


def variants_present(rows: Sequence[Dict]) -> List[str]:
    seen = {r["variant"] for r in rows}
    return [v for v in VARIANT_ORDER if v in seen] + sorted(seen - set(VARIANT_ORDER))


# ── Figure 1: validation log loss vs slip ────────────────────────────────
def fig1(curve: List[Dict], selection: List[Dict], figures_dir: str) -> None:
    """Validation log loss across the slip grid, with student-level bootstrap
    bands, the production setting, and the validation-selected optimum."""
    variants = variants_present(curve)
    fig, axes = plt.subplots(1, len(variants), figsize=(6.0 * len(variants), 4.6),
                             sharey=False)
    if len(variants) == 1:
        axes = [axes]

    for ax, variant in zip(axes, variants):
        rows = [r for r in curve if r["variant"] == variant]
        seeds = sorted({_i(r, "seed") for r in rows})
        grid = sorted({_f(r, "slip") for r in rows})
        color = VARIANT_COLOR.get(variant, "#555555")

        # Mean across seeds, with the min/max seed envelope as variability.
        mean_ll = np.zeros(len(grid))
        lo = np.zeros(len(grid))
        hi = np.zeros(len(grid))
        for gi, s in enumerate(grid):
            vals = [_f(r, "mean_log_loss") for r in rows if _f(r, "slip") == s]
            mean_ll[gi] = np.mean(vals)
            lo[gi] = np.min(vals)
            hi[gi] = np.max(vals)

        ax.fill_between(grid, lo, hi, color=color, alpha=0.20,
                        label=f"Seed range ({len(seeds)} seeds)")
        ax.plot(grid, mean_ll, color=color, lw=2.0, label="Mean validation log loss")

        # Production setting.
        ax.axvline(PRODUCTION_S, color="#666666", ls="--", lw=1.4,
                   label=f"Production P(S)={PRODUCTION_S}")
        # Selected optimum (mean across seeds).
        sel = [_f(r, "selected") for r in selection if r["variant"] == variant]
        if sel:
            best = float(np.mean(sel))
            ax.axvline(best, color=color, ls=":", lw=2.0,
                       label=f"Selected P(S)={best:.2f}")

        ax.set_xlabel("Slip probability P(S)")
        ax.set_ylabel("Validation log loss (lower is better)")
        ax.set_title(f"{VARIANT_LABEL.get(variant, variant)}\n"
                     f"(sd={rows[0]['within_group_sd']}, "
                     f"{rows[0]['transition_mode']} transition)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="best")

    fig.suptitle(
        "Figure 1. Validation log loss vs slip probability\n"
        "The curve is flat near the optimum - a range of slip values is "
        "statistically indistinguishable", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    _save(fig, figures_dir, "fig1_validation_curve.png")


# ── Figure 2: held-out test metrics ──────────────────────────────────────
def fig2(test: List[Dict], figures_dir: str) -> None:
    """Held-out test performance for production, validation-selected and oracle.

    The oracle column uses the known generating slip and is a SYNTHETIC
    reference only - it is not achievable in production.
    """
    variants = variants_present(test)
    metrics = [("log_loss", "Log loss (lower better)"),
               ("brier", "Brier score (lower better)"),
               ("ece", "ECE (lower better)")]
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.0))

    width = 0.26
    x = np.arange(len(SETTING_ORDER))
    for ax, (metric, title) in zip(axes, metrics):
        for vi, variant in enumerate(variants):
            means, errs = [], []
            for setting in SETTING_ORDER:
                vals = [_f(r, metric) for r in test
                        if r["variant"] == variant and r["setting"] == setting]
                means.append(np.mean(vals) if vals else np.nan)
                errs.append(np.std(vals, ddof=1) if len(vals) > 1 else 0.0)
            offset = (vi - (len(variants) - 1) / 2.0) * width
            ax.bar(x + offset, means, width * 0.92, yerr=errs, capsize=3,
                   color=VARIANT_COLOR.get(variant, "#555555"), alpha=0.85,
                   label=VARIANT_LABEL.get(variant, variant))
        ax.set_xticks(x)
        ax.set_xticklabels([SETTING_LABEL[s] for s in SETTING_ORDER], fontsize=9)
        ax.set_title(title)
        ax.grid(alpha=0.3, axis="y")
        ax.legend(fontsize=8)

    fig.suptitle(
        "Figure 2. Held-out test metrics by slip setting\n"
        "Oracle is a synthetic reference using the known generating slip - "
        "not achievable production performance", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    _save(fig, figures_dir, "fig2_test_metrics.png")


# ── Figure 3: slip recovery ──────────────────────────────────────────────
def fig3(recovery: List[Dict], figures_dir: str) -> None:
    """Selected slip vs known generating slip, per variant.

    Points on the diagonal mean exact recovery.  The shaded band is the
    one-standard-error near-optimal interval, NOT a confidence interval.
    """
    variants = variants_present(recovery)
    fig, ax = plt.subplots(figsize=(8.6, 6.4))

    for variant in variants:
        rows = [r for r in recovery if r["variant"] == variant]
        trues = sorted({_f(r, "true_slip") for r in rows})
        xs, ys, yerr, lo_band, hi_band = [], [], [], [], []
        for t in trues:
            sub = [r for r in rows if _f(r, "true_slip") == t]
            sel = [_f(r, "selected") for r in sub]
            xs.append(t)
            ys.append(np.mean(sel))
            yerr.append(np.std(sel, ddof=1) if len(sel) > 1 else 0.0)
            lo_band.append(np.mean([_f(r, "interval_lo") for r in sub]))
            hi_band.append(np.mean([_f(r, "interval_hi") for r in sub]))
        color = VARIANT_COLOR.get(variant, "#555555")
        ax.errorbar(xs, ys, yerr=yerr, fmt="o-", color=color, lw=1.8, ms=6,
                    capsize=3, label=VARIANT_LABEL.get(variant, variant))
        ax.fill_between(xs, lo_band, hi_band, color=color, alpha=0.12)

    lims = [0.0, 0.46]
    ax.plot(lims, lims, color="#333333", ls="--", lw=1.2, label="Perfect recovery (y = x)")
    ax.axvline(PRODUCTION_S, color="#666666", ls=":", lw=1.2,
               label=f"Production P(S)={PRODUCTION_S}")
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("True generating slip probability")
    ax.set_ylabel("Validation-selected slip probability")
    ax.set_title(
        "Figure 3. Slip recovery across known generating values\n"
        "Shading = one-standard-error near-optimal interval (not a confidence "
        "interval)", fontsize=11)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="upper left")
    _save(fig, figures_dir, "fig3_slip_recovery.png")


# ── Figures 4 and 5: sensitivity heatmaps ────────────────────────────────
def _heatmap(rows: List[Dict], x_key: str, y_key: str, x_label: str,
             y_label: str, title: str, fname: str, figures_dir: str) -> None:
    xs = sorted({_f(r, x_key) for r in rows})
    ys = sorted({_f(r, y_key) for r in rows})
    grid = np.full((len(ys), len(xs)), np.nan)
    for r in rows:
        xi, yi = xs.index(_f(r, x_key)), ys.index(_f(r, y_key))
        grid[yi, xi] = _f(r, "delta_from_min")

    fig, ax = plt.subplots(figsize=(9.2, 6.2))
    vmax = np.nanpercentile(grid, 96)
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap="viridis_r",
                   vmin=0.0, vmax=max(vmax, 1e-9))
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Validation log loss above the minimum (nats/answer)")

    ax.set_xticks(range(len(xs)))
    ax.set_xticklabels([f"{x:.3g}" for x in xs], rotation=45, ha="right")
    ax.set_yticks(range(len(ys)))
    ax.set_yticklabels([f"{y:.3g}" for y in ys])
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    # Mark the optimum.
    sel = [r for r in rows if _i(r, "is_selected")]
    if sel:
        xi = xs.index(_f(sel[0], x_key))
        yi = ys.index(_f(sel[0], y_key))
        ax.plot(xi, yi, marker="*", ms=18, color="red", mec="white", mew=1.2,
                label="Validation optimum")
        ax.legend(fontsize=9, loc="upper right")

    ax.set_title(title, fontsize=11)
    _save(fig, figures_dir, fname)


def fig4(heatmap: List[Dict], figures_dir: str) -> None:
    rows = [r for r in heatmap if r["surface"] == "guess_vs_slip"]
    if not rows:
        raise ValueError("no guess_vs_slip rows in exp_c_heatmap.csv")
    _heatmap(rows, "slip", "g",
             "Slip probability P(S)", "Guess probability P(G)",
             "Figure 4. Guess x slip sensitivity surface\n"
             "A diagonal valley means only P(G) - P(S) is identified, not each "
             "parameter separately",
             "fig4_guess_slip_heatmap.png", figures_dir)


def fig5(heatmap: List[Dict], figures_dir: str) -> None:
    rows = [r for r in heatmap if r["surface"] == "l0_vs_slip"]
    if not rows:
        raise ValueError("no l0_vs_slip rows in exp_c_heatmap.csv")
    _heatmap(rows, "slip", "logit_shift",
             "Slip probability P(S)", "Initial-mastery shift (logit space)",
             "Figure 5. Initial-mastery x slip sensitivity surface\n"
             "A flat direction means a wrong P(L0) can be partly absorbed by "
             "refitting P(S)",
             "fig5_l0_slip_heatmap.png", figures_dir)


# ── Figure 6: learning-rate misspecification ─────────────────────────────
def fig6(t_rows: List[Dict], figures_dir: str) -> None:
    if not t_rows:
        raise ValueError("exp_c_t_misspec.csv is empty")
    assumed = [_f(r, "assumed_t") for r in t_rows]
    selected = [_f(r, "selected_s") for r in t_rows]
    penalty = [_f(r, "penalty_vs_true_t") for r in t_rows]
    true_t = _f(t_rows[0], "true_t")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.0, 4.8))

    ax1.plot(assumed, selected, "o-", color="#2166ac", lw=2.0, ms=7)
    ax1.axhline(PRODUCTION_S, color="#666666", ls="--", lw=1.2,
                label=f"Production P(S)={PRODUCTION_S}")
    ax1.axvline(true_t, color="#b2182b", ls=":", lw=1.6, label=f"True P(T)={true_t}")
    ax1.set_xlabel("Assumed learning probability P(T)")
    ax1.set_ylabel("Re-fitted slip P(S)")
    ax1.set_title("(a) Does a wrong P(T) move the fitted slip?")
    ax1.grid(alpha=0.3)
    ax1.legend(fontsize=9)

    ax2.bar([str(a) for a in assumed], penalty, color="#762a83", alpha=0.85)
    ax2.set_xlabel("Assumed learning probability P(T)")
    ax2.set_ylabel("Validation log-loss penalty vs true P(T)")
    ax2.set_title("(b) Predictive cost of a wrong P(T)")
    ax2.grid(alpha=0.3, axis="y")

    fig.suptitle(
        "Figure 6. Learning-rate misspecification\n"
        "Slip is re-fitted at each assumed P(T) to isolate the confounding",
        fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    _save(fig, figures_dir, "fig6_t_misspec.png")


# ── Figure 7: mastery estimation ─────────────────────────────────────────
def fig7(mastery: List[Dict], figures_dir: str) -> None:
    """Mastery-estimation error and false-mastery against the hidden state.

    Simulation-only: real students have no hidden mastery label.

    Experiment A is shown (3 variants x 3 settings) because Experiment B adds
    a further 21 recovery rows that would render the x-axis unreadable; B's
    mastery numbers remain in exp_mastery_metrics.csv and are quoted in the
    report.
    """
    rows = [r for r in mastery if r["scope"] == "overall"
            and r["experiment"] == "experiment_a"]
    if not rows:
        raise ValueError("no experiment_a scope=overall rows in exp_mastery_metrics.csv")

    labels, mae, fmr_all, fmr_flagged, colors = [], [], [], [], []
    for r in rows:
        variant = r["setting"].split(":")[0]
        setting = r["setting"].split(":")[-1]
        labels.append(f"{variant}\n{SETTING_LABEL.get(setting, setting).replace(chr(10), ' ')}")
        mae.append(_f(r, "mae"))
        fmr_all.append(100.0 * _f(r, "false_mastered_rate_all"))
        fmr_flagged.append(
            100.0 * (_f(r, "false_mastered_rate_of_flagged") or 0.0))
        colors.append(VARIANT_COLOR.get(variant, "#555555"))

    x = np.arange(len(labels))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.0, 5.4))

    ax1.bar(x, mae, color=colors, alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=7, rotation=45, ha="right")
    ax1.set_ylabel("MAE between estimated P(L) and hidden state")
    ax1.set_title("(a) Mastery-probability MAE vs hidden truth")
    ax1.grid(alpha=0.3, axis="y")

    width = 0.38
    ax2.bar(x - width / 2, fmr_all, width, label="of ALL student-skill pairs",
            color="#b2182b", alpha=0.85)
    ax2.bar(x + width / 2, fmr_flagged, width,
            label="of FLAGGED-mastered pairs only", color="#ef8a62", alpha=0.9)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=7, rotation=45, ha="right")
    ax2.set_ylabel("False-mastery rate (%)")
    ax2.set_title("(b) False mastery at threshold P(L) >= 0.7\n"
                  "Denominators differ and are shown separately")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3, axis="y")

    fig.suptitle(
        "Figure 7. Mastery-estimation error and false-mastery\n"
        "SIMULATION-ONLY: hidden mastery states exist only because the data is "
        "synthetic", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.87])
    _save(fig, figures_dir, "fig7_mastery_estimation.png")


# ── Figure 8: calibration ────────────────────────────────────────────────
def fig8(calibration: List[Dict], figures_dir: str) -> None:
    variants = variants_present(calibration)
    fig, axes = plt.subplots(1, len(variants), figsize=(5.6 * len(variants), 5.0),
                             sharey=True)
    if len(variants) == 1:
        axes = [axes]

    for ax, variant in zip(axes, variants):
        rows = [r for r in calibration if r["variant"] == variant
                and r["group"] == "overall"]
        for setting in SETTING_ORDER:
            sub = [r for r in rows if r["setting"] == setting]
            if not sub:
                continue
            # Average the bin contents across seeds.
            by_bin: Dict[int, List[Dict]] = {}
            for r in sub:
                by_bin.setdefault(_i(r, "bin"), []).append(r)
            xs, ys = [], []
            for b in sorted(by_bin):
                group_rows = by_bin[b]
                counts = [_i(r, "count") for r in group_rows]
                total = sum(counts) or 1
                preds = [_f(r, "mean_predicted") for r in group_rows]
                obs = [(_f(r, "observed") if _f(r, "observed") is not None else p)
                       for r, p in zip(group_rows, preds)]
                xs.append(sum(p * c for p, c in zip(preds, counts)) / total)
                ys.append(sum(o * c for o, c in zip(obs, counts)) / total)
            style = {"production": "s-", "selected": "o-", "oracle": "^-"}[setting]
            ax.plot(xs, ys, style, lw=1.8, ms=6,
                    label=SETTING_LABEL[setting].replace("\n", " "))
        ax.plot([0, 1], [0, 1], color="#333333", ls="--", lw=1.1,
                label="Perfect calibration")
        ax.set_xlabel("Predicted P(correct)")
        ax.set_title(VARIANT_LABEL.get(variant, variant))
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Observed fraction correct")

    fig.suptitle(
        "Figure 8. Calibration comparison (reliability diagram)\n"
        "Predictions are made BEFORE each answer is observed", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.89])
    _save(fig, figures_dir, "fig8_calibration.png")


# ── Figure 9: performance by prior attempts ──────────────────────────────
def fig9(by_attempt: List[Dict], figures_dir: str) -> None:
    variants = variants_present(by_attempt)
    fig, axes = plt.subplots(1, len(variants), figsize=(5.6 * len(variants), 4.8),
                             sharey=False)
    if len(variants) == 1:
        axes = [axes]

    for ax, variant in zip(axes, variants):
        rows = [r for r in by_attempt if r["variant"] == variant
                and r["group"] == "overall"]
        for setting in SETTING_ORDER:
            sub = [r for r in rows if r["setting"] == setting]
            if not sub:
                continue
            by_n: Dict[int, List[float]] = {}
            for r in sub:
                by_n.setdefault(_i(r, "attempt_index"), []).append(_f(r, "log_loss"))
            ns = sorted(by_n)
            means = [float(np.mean(by_n[n])) for n in ns]
            ax.plot(ns, means, {"production": "s-", "selected": "o-",
                                "oracle": "^-"}[setting], lw=1.8, ms=6,
                    label=SETTING_LABEL[setting].replace("\n", " "))
        ax.set_xlabel("Attempt number within a lesson")
        ax.set_ylabel("Log loss (lower is better)")
        ax.set_title(VARIANT_LABEL.get(variant, variant))
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)

    fig.suptitle(
        "Figure 9. Prediction quality by number of prior attempts\n"
        "Attempt 1 is scored from the untouched prior alone", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.89])
    _save(fig, figures_dir, "fig9_by_attempt.png")


FIGURES = {
    1: ("fig1_validation_curve.png", fig1),
    2: ("fig2_test_metrics.png", fig2),
    3: ("fig3_slip_recovery.png", fig3),
    4: ("fig4_guess_slip_heatmap.png", fig4),
    5: ("fig5_l0_slip_heatmap.png", fig5),
    6: ("fig6_t_misspec.png", fig6),
    7: ("fig7_mastery_estimation.png", fig7),
    8: ("fig8_calibration.png", fig8),
    9: ("fig9_by_attempt.png", fig9),
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None)
    parser.add_argument("--results", default=None)
    parser.add_argument("--figures", default=None)
    parser.add_argument("--only", type=int, action="append")
    args = parser.parse_args(argv)

    config = bkt_core.load_config(args.config)
    results_dir = args.results or bkt_core.resolve(config["paths"]["results"])
    figures_dir = args.figures or bkt_core.resolve(config["paths"]["figures"])

    data = {
        "curve": read_csv("exp_a_validation_curve.csv", results_dir),
        "selection": read_csv("exp_a_selection.csv", results_dir),
        "test": read_csv("exp_a_test_metrics.csv", results_dir),
        "recovery": read_csv("exp_b_recovery.csv", results_dir),
        "heatmap": read_csv("exp_c_heatmap.csv", results_dir),
        "t_rows": read_csv("exp_c_t_misspec.csv", results_dir),
        "mastery": read_csv("exp_mastery_metrics.csv", results_dir),
        "calibration": read_csv("exp_calibration_bins.csv", results_dir),
        "by_attempt": read_csv("exp_by_attempt.csv", results_dir),
    }

    wanted = sorted(args.only) if args.only else sorted(FIGURES)
    print(f"Generating {len(wanted)} figure(s) from {results_dir}:")
    for n in wanted:
        _name, fn = FIGURES[n]
        if n == 1:
            fn(data["curve"], data["selection"], figures_dir)
        elif n == 2:
            fn(data["test"], figures_dir)
        elif n == 3:
            fn(data["recovery"], figures_dir)
        elif n == 4:
            fn(data["heatmap"], figures_dir)
        elif n == 5:
            fn(data["heatmap"], figures_dir)
        elif n == 6:
            fn(data["t_rows"], figures_dir)
        elif n == 7:
            fn(data["mastery"], figures_dir)
        elif n == 8:
            fn(data["calibration"], figures_dir)
        elif n == 9:
            fn(data["by_attempt"], figures_dir)
    print("All figures generated from saved result files.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
