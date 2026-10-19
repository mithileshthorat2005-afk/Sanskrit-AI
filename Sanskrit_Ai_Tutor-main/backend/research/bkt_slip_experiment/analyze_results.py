#!/usr/bin/env python
"""
Analysis utilities for the BKT slip-probability experiment.

This module owns everything that turns raw response sequences into numbers:

  * fitting a candidate parameter grid to a split by student-level log loss
  * student-level bootstrap standard errors (resampling STUDENTS, never rows)
  * the pre-registered one-standard-error near-optimal interval
  * held-out prediction metrics (log loss / Brier / ECE / accuracy)
  * hidden-state mastery metrics (MAE, false-mastered, false-unmastered)
  * parameter-recovery summaries across generating values and seeds

It never reads the live database and never imports the application's data layer.
"""

from __future__ import annotations

import math
import os
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bkt_core  # noqa: E402

__all__ = [
    "build_sequences",
    "split_sequences",
    "fit_grid",
    "bootstrap_curve_se",
    "summarise_grid",
    "bootstrap_se",
    "select_candidate",
    "evaluate_params",
    "evaluate_by_attempt",
    "mastery_evaluation",
    "recovery_summary",
]


# ── Sequence construction ────────────────────────────────────────────────

def build_sequences(observations: Sequence[Sequence],
                    prior_fn) -> List[Dict]:
    """Group observations into chronological (student, lesson) sequences.

    ``prior_fn(group, tier, lesson_id)`` supplies the starting P(L0), which is
    the production seed by default.  Answers are stored in attempt order.
    """
    grouped: Dict[Tuple[str, int], Dict] = {}
    for row in observations:
        sid, group, _split, lesson_id, _skill, tier, attempt_index, correct = row
        key = (sid, int(lesson_id))
        rec = grouped.get(key)
        if rec is None:
            rec = {
                "student": sid,
                "group": group,
                "tier": tier,
                "lesson": int(lesson_id),
                "prior": float(prior_fn(group, tier, int(lesson_id))),
                "answers": [],
            }
            grouped[key] = rec
        rec["answers"].append((sid, int(attempt_index), int(correct)))

    out: List[Dict] = []
    for rec in grouped.values():
        ordered = sorted(rec["answers"], key=lambda t: t[1])
        rec["answers"] = [c for _s, _n, c in ordered]
        rec["attempt_indices"] = [n for _s, n, _c in ordered]
        out.append(rec)
    return out


def split_sequences(sequences: Sequence[Dict],
                    observations: Sequence[Sequence]) -> Dict[str, List[Dict]]:
    """Partition sequences by the student's split (never by row)."""
    split_of: Dict[str, str] = {}
    for row in observations:
        split_of[row[0]] = row[2]
    out: Dict[str, List[Dict]] = {"train": [], "validation": [], "test": []}
    for rec in sequences:
        out[split_of[rec["student"]]].append(rec)
    return out


def _students_of(records: Sequence[Dict]) -> List[str]:
    return sorted({r["student"] for r in records})


# ── Grid fitting ─────────────────────────────────────────────────────────

def fit_grid(
    records: Sequence[Dict],
    param_sets: Sequence[Dict],
    clip: float = bkt_core.PROB_CLIP,
) -> Dict:
    """Total NLL and observation count per (candidate, student).

    ``param_sets`` is a list of ``{"s":..., "g":..., "t":...}`` dicts, so the
    same routine serves the 1-D slip sweep and the joint (g, slip, l0) fits.

    Returns ``{"losses": (n_grid, n_students), "counts": (n_students,),
    "students": [...]}``.  ``counts`` is candidate-independent because every
    candidate replays exactly the same observations.
    """
    if not records:
        raise ValueError("fit_grid needs at least one sequence")
    if not param_sets:
        raise ValueError("fit_grid needs at least one candidate")

    students = _students_of(records)
    index_of = {s: i for i, s in enumerate(students)}
    n_students = len(students)
    n_grid = len(param_sets)

    losses = np.zeros((n_grid, n_students), dtype=float)
    counts = np.zeros(n_students, dtype=float)

    for record in records:
        si = index_of[record["student"]]
        counts[si] += len(record["answers"])

    for gi, p in enumerate(param_sets):
        s, g, t = p["s"], p["g"], p["t"]
        for record in records:
            si = index_of[record["student"]]
            state = max(0.0, min(1.0, record["prior"]))
            total = 0.0
            for y in record["answers"]:
                pred = state * (1.0 - s) + (1.0 - state) * g
                pc = min(max(pred, clip), 1.0 - clip)
                total += -(y * math.log(pc) + (1 - y) * math.log(1.0 - pc))
                state = bkt_core.step(state, bool(y), {"s": s, "g": g, "t": t})
            losses[gi, si] += total

    return {"losses": losses, "counts": counts, "students": students}


def bootstrap_curve_se(
    fit: Dict,
    n_resamples: int,
    seed: int,
) -> np.ndarray:
    """Bootstrap SE of the mean log loss for EVERY candidate at once.

    All candidates share the same resample indices, so the resulting bands are
    PAIRED: the uncertainty of the whole curve moves together rather than each
    candidate being resampled independently.  This is what makes the error bars
    on the validation curve meaningful when comparing neighbouring slip values.
    """
    if n_resamples < 2:
        raise ValueError("bootstrap needs at least 2 resamples")
    losses, counts = fit["losses"], fit["counts"]
    n_students = len(counts)
    rng = np.random.default_rng(seed)

    # (n_resamples, n_students) index matrix, reused for every candidate.
    indices = rng.integers(0, n_students, size=(n_resamples, n_students))
    denom = counts[indices].sum(axis=1)                     # (n_resamples,)
    numer = losses[:, indices].sum(axis=2)                  # (n_grid, n_resamples)
    means = numer / denom                                   # (n_grid, n_resamples)
    return means.std(axis=1, ddof=1)                        # (n_grid,)


def summarise_grid(grid: Sequence[float], fit: Dict) -> Dict:
    """Per-candidate mean validation log loss and the arg-min."""
    losses, counts = fit["losses"], fit["counts"]
    total_obs = float(counts.sum())
    if total_obs <= 0:
        raise ValueError("no observations to score")
    means = np.array([float(losses[i].sum()) / total_obs for i in range(len(grid))])
    argmin = int(np.argmin(means))
    return {
        "mean_log_loss": means,
        "argmin": argmin,
        "best_prior": grid[argmin],
        "min_log_loss": float(means[argmin]),
        "n_obs": int(total_obs),
        "n_students": len(fit["students"]),
    }


def bootstrap_se(
    fit: Dict,
    candidate_index: int,
    n_resamples: int,
    seed: int,
) -> float:
    """Student-level bootstrap SE of the mean log loss at one candidate.

    Resamples whole students and recomputes the weighted mean
    ``sum(NLL_i) / sum(n_obs_i)``.  Resampling students (rather than individual
    answers) preserves the within-sequence correlation.
    """
    if n_resamples < 2:
        raise ValueError("bootstrap needs at least 2 resamples")
    losses = fit["losses"][candidate_index]
    counts = fit["counts"]
    n = len(counts)
    rng = np.random.default_rng(seed)
    means = np.empty(n_resamples, dtype=float)
    for b in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[b] = losses[idx].sum() / counts[idx].sum()
    return float(means.std(ddof=1))


def select_candidate(
    grid: Sequence[float],
    fit: Dict,
    n_resamples: int,
    seed: int,
) -> Dict:
    """Validation-only selection plus the one-standard-error interval."""
    summary = summarise_grid(grid, fit)
    se = bootstrap_se(fit, summary["argmin"], n_resamples, seed)
    interval = bkt_core.near_optimal_interval(
        list(grid), list(summary["mean_log_loss"]), se)
    interval.update({
        "n_obs": summary["n_obs"],
        "n_students": summary["n_students"],
        "rule": "within_1_se_of_min",
        "n_resamples": n_resamples,
        "seed": seed,
    })
    return interval


# ── Held-out evaluation ──────────────────────────────────────────────────

def _collect_predictions(records: Sequence[Dict], p: Dict,
                         clip: float) -> Tuple[List[int], List[float]]:
    """Pre-answer predictions for every observation in ``records``."""
    ys: List[int] = []
    ps: List[float] = []
    for record in records:
        state = max(0.0, min(1.0, record["prior"]))
        s, g, t = p["s"], p["g"], p["t"]
        for y in record["answers"]:
            pred = state * (1.0 - s) + (1.0 - state) * g
            ps.append(min(max(pred, clip), 1.0 - clip))
            ys.append(int(y))
            state = bkt_core.step(state, bool(y), {"s": s, "g": g, "t": t})
    return ys, ps


def evaluate_params(
    records: Sequence[Dict],
    p: Dict,
    config: Dict,
    clip: float = bkt_core.PROB_CLIP,
) -> Dict:
    """Held-out prediction metrics for one parameterisation."""
    m = config["metrics"]
    ys, ps = _collect_predictions(records, p, clip)
    if not ys:
        raise ValueError("evaluate_params needs at least one observation")
    ece_value, rows = bkt_core.ece(ys, ps, n_bins=int(m["ece_bins"]))
    return {
        "log_loss": bkt_core.log_loss(ys, ps, clip=clip),
        "brier": bkt_core.brier(ys, ps),
        "accuracy": bkt_core.accuracy(ys, ps, threshold=float(m["accuracy_threshold"])),
        "ece": ece_value,
        "n_obs": len(ys),
        "n_students": len({r["student"] for r in records}),
        "calibration_bins": rows,
    }


def evaluate_by_attempt(
    records: Sequence[Dict],
    p: Dict,
    clip: float = bkt_core.PROB_CLIP,
) -> List[Dict]:
    """Prediction metrics broken down by attempt number.

    Attempt 1 is scored from the untouched prior, so this also exposes how much
    of the model's accuracy comes from the seed rather than from evidence.
    """
    buckets: Dict[int, Tuple[List[int], List[float]]] = {}
    for record in records:
        state = max(0.0, min(1.0, record["prior"]))
        s, g, t = p["s"], p["g"], p["t"]
        for i, y in enumerate(record["answers"], start=1):
            pred = state * (1.0 - s) + (1.0 - state) * g
            ys, ps = buckets.setdefault(i, ([], []))
            ys.append(int(y))
            ps.append(min(max(pred, clip), 1.0 - clip))
            state = bkt_core.step(state, bool(y), {"s": s, "g": g, "t": t})

    out: List[Dict] = []
    for i in sorted(buckets):
        ys, ps = buckets[i]
        out.append({
            "attempt_index": i,
            "log_loss": bkt_core.log_loss(ys, ps, clip=clip),
            "brier": bkt_core.brier(ys, ps),
            "accuracy": bkt_core.accuracy(ys, ps),
            "n_obs": len(ys),
        })
    return out


# ── Hidden-state mastery evaluation ──────────────────────────────────────

def mastery_evaluation(
    records: Sequence[Dict],
    hidden_by_key: Dict[Tuple[str, int, int], float],
    p: Dict,
    threshold: float = bkt_core.MASTERY_THRESHOLD,
    by_group: bool = True,
) -> Dict:
    """Mastery-estimation quality against the generator's hidden theta.

    ``hidden_by_key`` maps (student, lesson_id, attempt_index) -> hidden theta.
    Estimates are the model's mastery AFTER incorporating each answer, which is
    the same index at which the generator records its theta.

    These metrics are simulation-only: real students have no hidden-state label.
    """
    per_group: Dict[str, Dict[str, List[float]]] = {}
    overall_est: List[float] = []
    overall_hid: List[float] = []

    for record in records:
        sid, lesson = record["student"], record["lesson"]
        state = max(0.0, min(1.0, record["prior"]))
        s, g, t = p["s"], p["g"], p["t"]
        for i, y in enumerate(record["answers"], start=1):
            state = bkt_core.step(state, bool(y), {"s": s, "g": g, "t": t})
            hidden = hidden_by_key.get((sid, lesson, i))
            if hidden is None:
                continue
            overall_est.append(state)
            overall_hid.append(hidden)
            if by_group:
                bucket = per_group.setdefault(
                    record["group"], {"est": [], "hid": []})
                bucket["est"].append(state)
                bucket["hid"].append(hidden)

    if not overall_est:
        raise ValueError("mastery_evaluation found no hidden labels to score")

    result = {
        "overall": bkt_core.mastery_metrics(overall_est, overall_hid, threshold),
        "by_group": {},
    }
    if by_group:
        for group in sorted(per_group):
            bucket = per_group[group]
            result["by_group"][group] = bkt_core.mastery_metrics(
                bucket["est"], bucket["hid"], threshold)
    return result


def paired_delta_bootstrap(
    records: Sequence[Dict],
    p_ref: Dict,
    p_alt: Dict,
    n_resamples: int,
    seed: int,
    clip: float = bkt_core.PROB_CLIP,
    confidence: float = 0.95,
) -> Dict:
    """Paired student-level bootstrap of the test log-loss difference.

    ``delta = mean_LL(p_alt) - mean_LL(p_ref)``; negative favours ``p_alt``.

    Both parameterisations are scored on the SAME students and the SAME
    answers, and the whole student is resampled as a unit, so the paired
    design removes the between-student variance that an unpaired comparison
    would have to pay for.  Resampling rows instead would wrongly treat the
    ten answers of one lesson as independent evidence.
    """
    if n_resamples < 2:
        raise ValueError("paired bootstrap needs at least 2 resamples")
    if not records:
        raise ValueError("paired bootstrap needs at least one sequence")

    students = sorted({r["student"] for r in records})
    index_of = {s: i for i, s in enumerate(students)}
    n_students = len(students)

    nll_ref = np.zeros(n_students, dtype=float)
    nll_alt = np.zeros(n_students, dtype=float)
    counts = np.zeros(n_students, dtype=float)

    for record in records:
        si = index_of[record["student"]]
        counts[si] += len(record["answers"])
        for tag, p, store in (("ref", p_ref, nll_ref), ("alt", p_alt, nll_alt)):
            del tag  # ordering only
            state = max(0.0, min(1.0, record["prior"]))
            total = 0.0
            s_, g_, t_ = p["s"], p["g"], p["t"]
            for y in record["answers"]:
                pred = state * (1.0 - s_) + (1.0 - state) * g_
                pc = min(max(pred, clip), 1.0 - clip)
                total += -(y * math.log(pc) + (1 - y) * math.log(1.0 - pc))
                state = bkt_core.step(state, bool(y), {"s": s_, "g": g_, "t": t_})
            store[si] += total

    rng = np.random.default_rng(seed)
    deltas = np.empty(n_resamples, dtype=float)
    for b in range(n_resamples):
        idx = rng.integers(0, n_students, size=n_students)
        denom = counts[idx].sum()
        deltas[b] = (nll_alt[idx].sum() - nll_ref[idx].sum()) / denom

    point = float((nll_alt.sum() - nll_ref.sum()) / counts.sum())
    alpha = (1.0 - confidence) / 2.0
    lo = float(np.percentile(deltas, 100 * alpha))
    hi = float(np.percentile(deltas, 100 * (1.0 - alpha)))
    return {
        "delta": point,
        "delta_rel_pct": None,          # filled by the caller if it knows the base
        "ci_lo": lo,
        "ci_hi": hi,
        "se": float(deltas.std(ddof=1)),
        "significant": bool(lo > 0.0 or hi < 0.0),
        "favour_alt": bool(hi < 0.0),
        "n_students": n_students,
        "n_obs": int(counts.sum()),
        "n_resamples": n_resamples,
        "confidence": confidence,
        "resample_unit": "student_id",
    }


# ── Recovery summary ─────────────────────────────────────────────────────

def recovery_summary(
    rows: Sequence[Dict],
    true_slip_key: str = "true_slip",
) -> List[Dict]:
    """Aggregate selected-slip estimates per generating value across seeds.

    Reports bias (selected - true), spread across seeds, and whether the known
    generating value fell inside the pre-registered one-SE interval.
    """
    by_value: Dict[float, List[Dict]] = {}
    for row in rows:
        by_value.setdefault(round(float(row[true_slip_key]), 10), []).append(row)

    out: List[Dict] = []
    for true_s in sorted(by_value):
        group_rows = by_value[true_s]
        selected = [float(r["selected"]) for r in group_rows]
        inside = [bool(r["true_in_interval"]) for r in group_rows]
        biases = [s - true_s for s in selected]
        widths = [float(r["interval_width"]) for r in group_rows]
        out.append({
            "true_slip": true_s,
            "n_seeds": len(group_rows),
            "selected_mean": bkt_core.mean(selected),
            "selected_sd": bkt_core.stddev(selected),
            "bias_mean": bkt_core.mean(biases),
            "bias_abs_mean": bkt_core.mean([abs(b) for b in biases]),
            "interval_lo_mean": bkt_core.mean([float(r["interval_lo"]) for r in group_rows]),
            "interval_hi_mean": bkt_core.mean([float(r["interval_hi"]) for r in group_rows]),
            "interval_width_mean": bkt_core.mean(widths),
            "coverage": sum(inside) / len(inside),
            "n_covered": sum(inside),
            "exact_hit_rate": sum(1 for s in selected if abs(s - true_s) < 1e-9) / len(selected),
            "all_selected": selected,
        })
    return out


# ── CLI ──────────────────────────────────────────────────────────────────

def _print_summary(config: Dict) -> int:
    """Print the headline numbers straight from the saved result CSVs.

    Every value shown here is read from disk - nothing is recomputed from an
    in-memory state, so this doubles as a check that REPORT.md quotes the
    files rather than the other way round.
    """
    results_dir = bkt_core.resolve(config["paths"]["results"])
    if not os.path.isdir(results_dir):
        print(f"(no results directory at {results_dir}) - run run_experiment.py")
        return 1

    import csv as _csv

    def _rows(name):
        path = os.path.join(results_dir, name)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8", newline="") as handle:
            return list(_csv.DictReader(handle))

    def _f(r, k, d=None):
        v = r.get(k, "")
        return d if v in ("", None) else float(v)

    print(f"Production P(S) = {bkt_core.PRODUCTION_SLIP}  "
          f"(P(G)={bkt_core.PRODUCTION_GUESS}, P(T)={bkt_core.PRODUCTION_T})")
    print(f"Results directory: {results_dir}\n")

    sel = _rows("exp_a_selection.csv")
    if sel:
        print("Experiment A - one-parameter slip sweep (true P(S) = "
              f"{_f(sel[0], 'true_slip')}):")
        for variant in sorted({r["variant"] for r in sel}):
            rows = [r for r in sel if r["variant"] == variant]
            picked = [_f(r, "selected") for r in rows]
            covered = sum(int(_f(r, "true_in_interval", 0)) for r in rows)
            print(f"  {variant:<24} selected={bkt_core.mean(picked):.3f} "
                  f"(sd {bkt_core.stddev(picked):.3f})  "
                  f"coverage {covered}/{len(rows)}  "
                  f"width {bkt_core.mean([_f(r, 'interval_width') for r in rows]):.3f}")

    rec = _rows("exp_b_recovery.csv")
    if rec:
        print("\nExperiment B - recovery of known generating slip:")
        for variant in sorted({r["variant"] for r in rec}):
            rows = [r for r in rec if r["variant"] == variant]
            print(f"  {variant}")
            for true_s in sorted({_f(r, "true_slip") for r in rows}):
                sub = [r for r in rows if _f(r, "true_slip") == true_s]
                biases = [_f(r, "bias") for r in sub]
                covered = sum(int(_f(r, "true_in_interval", 0)) for r in sub)
                print(f"    true={true_s:.2f}  bias={bkt_core.mean(biases):+.3f} "
                      f"  coverage {covered}/{len(sub)}")

    conds = _rows("exp_c_conditions.csv")
    if conds:
        print("\nExperiment C - parameter confounding (true P(S) = "
              f"{_f(conds[0], 'true_slip')}):")
        for r in conds:
            gs = r.get("selected_g") or "-"
            ls = r.get("selected_logit_shift") or "-"
            print(f"  {r['condition']:<22} s={_f(r, 'selected_s'):.2f}  "
                  f"g={gs}  l0shift={ls}  "
                  f"val_LL={_f(r, 'min_val_log_loss'):.6f}")

    het = _rows("exp_d_heterogeneity.csv")
    if het:
        print("\nExperiment D - heterogeneity (single fitted global slip):")
        for r in het:
            if r["cell_kind"] == "overall":
                print(f"  {r['condition']:<22} global_s="
                      f"{_f(r, 'selected_global_s'):.2f}  "
                      f"interval=[{_f(r, 'interval_lo'):.2f}, "
                      f"{_f(r, 'interval_hi'):.2f}]")

    print("\nMaster metrics are simulation-only (hidden states exist only in "
          "synthetic data).")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None)
    parser.add_argument("--summary", action="store_true",
                        help="print headline results from the saved CSVs")
    parser.add_argument("--verify", action="store_true",
                        help="check that every result file parses and is complete")
    args = parser.parse_args(argv)

    config = bkt_core.load_config(args.config)
    if args.summary:
        return _print_summary(config)

    # Default: verify the result set is complete and internally consistent.
    results_dir = bkt_core.resolve(config["paths"]["results"])
    if not os.path.isdir(results_dir):
        print(f"(no results directory at {results_dir}) - run run_experiment.py")
        return 1

    import csv as _csv
    problems: List[str] = []
    grid = bkt_core.slip_grid(config)
    checked = 0

    path = os.path.join(results_dir, "exp_a_validation_curve.csv")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", newline="") as handle:
            rows = list(_csv.DictReader(handle))
        by_key: Dict[Tuple[str, int], List[float]] = {}
        for r in rows:
            by_key.setdefault((r["variant"], int(r["seed"])), []).append(float(r["slip"]))
        for key, slips in by_key.items():
            if sorted(slips) != grid:
                problems.append(f"validation curve {key} does not span the full grid")
        checked += 1
        print(f"  exp_a_validation_curve.csv   {len(rows)} rows, "
              f"{len(by_key)} variant/seed curves each covering {len(grid)} candidates")

    for name in ("exp_a_selection.csv", "exp_a_test_metrics.csv",
                 "exp_a_test_deltas.csv",
                 "exp_b_recovery.csv", "exp_c_conditions.csv",
                 "exp_c_heatmap.csv", "exp_c_t_misspec.csv",
                 "exp_d_heterogeneity.csv", "exp_mastery_metrics.csv",
                 "exp_calibration_bins.csv", "exp_by_attempt.csv"):
        p = os.path.join(results_dir, name)
        if not os.path.exists(p):
            problems.append(f"missing {name}")
            continue
        with open(p, "r", encoding="utf-8", newline="") as handle:
            nrows = sum(1 for _ in _csv.DictReader(handle))
        if nrows == 0:
            problems.append(f"{name} is empty")
        checked += 1
        print(f"  {name:<30} {nrows} rows")

    # The production value must appear in the comparison.
    sel_path = os.path.join(results_dir, "exp_a_selection.csv")
    if os.path.exists(sel_path):
        with open(sel_path, "r", encoding="utf-8", newline="") as handle:
            ok_prod = any(
                abs(float(r["interval_lo"]) - bkt_core.PRODUCTION_SLIP) <= 1e-9
                or abs(float(r["interval_hi"]) - bkt_core.PRODUCTION_SLIP) <= 1e-9
                or float(r["interval_lo"]) <= bkt_core.PRODUCTION_SLIP <= float(r["interval_hi"])
                for r in _csv.DictReader(handle))
        print(f"\n  production P(S)={bkt_core.PRODUCTION_SLIP} inside at least one "
              f"near-optimal interval: {'yes' if ok_prod else 'no'}")

    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"\nAll {checked} result files verified against the configured grid.")
    return 0


if __name__ == "__main__":
    import sys as _sys
    try:
        _sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"ERROR: {type(exc).__name__}: {exc}")
        _sys.exit(1)
