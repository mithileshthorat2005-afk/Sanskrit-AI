#!/usr/bin/env python
"""
BKT initial-mastery prior (P(L0)) optimisation and evaluation.

Read-only with respect to production: this script imports the real BKT
equations and the real INITIAL_MASTERY table, and never writes to the live
SQLite database or to `data/bkt_progress.json`.

Pipeline
--------
For every scenario in config.json:

  1. Simulate the synthetic population (generate_dataset.simulate).
  2. Split students into train / validation / test.  Splits are at STUDENT
     level, so no learner's answer sequence ever straddles two splits.
  3. Optimise candidate priors on the VALIDATION split only:
        - common            : one prior for everybody
        - group_specific    : one prior per proficiency group
        - group_x_tier      : one prior per (group, tier) - structural match
                              to production, reported as an extra comparison
  4. Report the near-optimal interval with a student-level bootstrap.
  5. Evaluate the selected priors exactly ONCE on the held-out TEST split,
     alongside the production baseline and an oracle reference.
  6. Compute the practical consequences (zero-attempt "mastered" counts,
     classification churn, simulation-only false-mastered rates).

Predictions for observation n always use the mastery estimate that existed
BEFORE answer n was incorporated, so the answer being scored can never leak
into its own prediction.

Usage
-----
    python run_experiment.py                     # primary + all sensitivities
    python run_experiment.py --scenarios primary
    python run_experiment.py --quick             # small smoke run
    python run_experiment.py --no-sensitivity

Exit status 0 on success, 1 on any failure.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import sys
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bkt_core  # noqa: E402
import generate_dataset as gd  # noqa: E402

GROUPS = ("beginner", "intermediate", "advanced")
TIERS = ("easy", "intermediate", "advanced")
SPLITS = ("train", "validation", "test")

OVERALL = "overall"


# ── Sequence container ───────────────────────────────────────────────────

class SequenceSet:
    """Per-(student, lesson) chronological answer sequences for one split."""

    __slots__ = ("records", "students", "groups", "by_student")

    def __init__(self, records: List[Dict], students: List[str], groups: Dict[str, str]):
        self.records = records
        self.students = students
        self.groups = groups
        self.by_student: Dict[str, List[Dict]] = {}
        for rec in records:
            self.by_student.setdefault(rec["student"], []).append(rec)


def build_sequence_sets(bundle: Dict) -> Dict[str, SequenceSet]:
    """Turn flat observation rows into per-split sequence containers."""
    obs = bundle["observations"]
    groups = {
        sid: g for sid, g in zip(bundle["student_ids"], bundle["student_groups"])
    }

    buckets: Dict[Tuple[str, str, int], Dict] = {}
    for sid, group, split, lesson_id, _skill, tier, attempt, correct in obs:
        key = (split, sid, lesson_id)
        rec = buckets.get(key)
        if rec is None:
            rec = {
                "split": split,
                "student": sid,
                "group": group,
                "lesson": lesson_id,
                "tier": tier,
                "_pairs": [],
            }
            buckets[key] = rec
        rec["_pairs"].append((int(attempt), int(correct)))

    per_split_rows: Dict[str, List[Dict]] = {s: [] for s in SPLITS}
    for rec in buckets.values():
        rec["_pairs"].sort(key=lambda p: p[0])
        rec["answers"] = [c for _a, c in rec["_pairs"]]
        del rec["_pairs"]
        per_split_rows[rec["split"]].append(rec)

    out: Dict[str, SequenceSet] = {}
    for split in SPLITS:
        rows = per_split_rows[split]
        rows.sort(key=lambda r: (r["student"], r["lesson"]))
        students = sorted({r["student"] for r in rows})
        out[split] = SequenceSet(rows, students, groups)
    return out


# ── Core scoring ─────────────────────────────────────────────────────────

def candidate_loss_matrix(
    sequences: Sequence[Dict],
    grid: Sequence[float],
    params: Dict,
    n_students: int,
    clip: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Per-student total NLL for every candidate prior.

    Returns ``(losses, counts)``:
        losses[c, s] = total negative log-likelihood of student s's sequences
                       under candidate grid[c]
        counts[s]    = number of observations contributed by student s
                       (identical for every candidate)

    Keeping the per-student breakdown is what makes the student-level
    bootstrap cheap: resampling students becomes a row-sum, not a re-simulation.
    """
    losses = np.zeros((len(grid), n_students), dtype=np.float64)
    counts = np.zeros(n_students, dtype=np.int64)

    sidx_of = {sid: i for i, sid in enumerate(sorted({r["student"] for r in sequences}))}
    t, g, s = params["t"], params["g"], params["s"]
    log = math.log

    # Group sequences by student once so the inner loop touches each answer
    # once per candidate rather than once per (candidate, sequence) pair.
    by_student: Dict[int, List[List[int]]] = {}
    for rec in sequences:
        by_student.setdefault(sidx_of[rec["student"]], []).append(rec["answers"])

    for ci, prior in enumerate(grid):
        row = losses[ci]
        for si, answer_lists in by_student.items():
            total = 0.0
            for answers in answer_lists:
                L = prior
                for raw in answers:
                    # Prediction BEFORE this answer is incorporated.
                    pred = L * (1.0 - s) + (1.0 - L) * g
                    if pred < clip:
                        pred = clip
                    elif pred > 1.0 - clip:
                        pred = 1.0 - clip
                    if raw:
                        total -= log(pred)
                    else:
                        total -= log(1.0 - pred)

                    # Production BKT update (posterior, then learning).
                    if raw:
                        posterior = (L * (1.0 - s)) / pred if pred > 0 else L
                    else:
                        denom = 1.0 - pred
                        posterior = (L * s) / denom if denom > 0 else L
                    if posterior < 0.0:
                        posterior = 0.0
                    elif posterior > 1.0:
                        posterior = 1.0
                    L = posterior + (1.0 - posterior) * t
                    if L > 1.0:
                        L = 1.0
            row[si] = total

    for si in by_student:
        counts[si] = sum(len(a) for a in by_student[si])
    return losses, counts


def _local_students(sequences: Sequence[Dict]) -> List[str]:
    return sorted({r["student"] for r in sequences})


def summarise_grid(
    grid: Sequence[float],
    losses: np.ndarray,
    counts: np.ndarray,
) -> Tuple[int, List[float], float]:
    """Return (best index, mean log loss per candidate, total observations)."""
    total_obs = int(counts.sum())
    if total_obs == 0:
        raise ValueError("cannot summarise an empty candidate evaluation")
    mean_ll = [float(losses[c].sum()) / total_obs for c in range(len(grid))]
    best = min(range(len(grid)), key=lambda c: mean_ll[c])
    return best, mean_ll, total_obs


# ── Near-optimal range (student bootstrap) ───────────────────────────────

def near_optimal_range(
    grid: Sequence[float],
    losses: np.ndarray,
    counts: np.ndarray,
    n_students: int,
    n_boot: int,
    seed: int,
    chunk: int = 128,
) -> Dict:
    """Near-optimal interval under the documented one-standard-error rule.

    Primary rule (config `bootstrap.rule == "within_1_se_of_min"`):

        near_optimal = { p : mean_LL(p) <= mean_LL(p*) + SE_boot(p*) }

    where p* is the validation arg-min and ``SE_boot`` is the student-level
    bootstrap standard error of the mean log loss AT p*.  The bootstrap
    resamples whole students, so within-student answer correlation - which a
    row-level bootstrap would destroy - is preserved.

    A stricter paired-difference interval is also reported: candidates whose
    mean log-loss *difference from p** is within one bootstrap standard error
    of zero.  Because the same bootstrap draws score both candidates, this
    removes shared variance and is the tighter (usually more honest) interval.
    """
    total_obs = int(counts.sum())
    mean_ll = [float(losses[c].sum()) / total_obs for c in range(len(grid))]
    best_c = min(range(len(grid)), key=lambda c: mean_ll[c])

    obs_of = counts.astype(np.float64)
    rng = np.random.default_rng(seed)

    # `losses` is (n_grid, n_students); the bootstrap resamples STUDENTS, so
    # transpose once and index the student axis.
    losses_by_student = losses.T  # (n_students, n_grid)
    ll_boot = np.empty((n_boot, len(grid)), dtype=np.float64)
    for start in range(0, n_boot, chunk):
        stop = min(start + chunk, n_boot)
        idx = rng.integers(0, n_students, size=(stop - start, n_students))
        denom = obs_of[idx].sum(axis=1)
        sums = losses_by_student[idx].sum(axis=1)  # (chunk, n_grid)
        ll_boot[start:stop] = sums / denom[:, None]

    se_at_min = float(ll_boot[:, best_c].std(ddof=1)) if n_boot > 1 else 0.0
    threshold = mean_ll[best_c] + se_at_min
    primary = [i for i in range(len(grid)) if mean_ll[i] <= threshold + 1e-15]

    diffs = ll_boot - ll_boot[:, [best_c]]
    diff_mean = diffs.mean(axis=0)
    diff_se = diffs.std(axis=0, ddof=1) if n_boot > 1 else np.zeros(len(grid))
    paired = [
        i for i in range(len(grid))
        if diff_mean[i] <= 1.0 * diff_se[i] + 1e-15
    ]

    def _span(indices: List[int]) -> Tuple[float, float]:
        if not indices:
            return (float(grid[best_c]), float(grid[best_c]))
        return (float(grid[min(indices)]), float(grid[max(indices)]))

    return {
        "best_index": best_c,
        "best_prior": float(grid[best_c]),
        "min_log_loss": mean_ll[best_c],
        "se_at_min": se_at_min,
        "threshold": threshold,
        "primary_indices": primary,
        "primary_span": _span(primary),
        "primary_width": _span(primary)[1] - _span(primary)[0],
        "paired_indices": paired,
        "paired_span": _span(paired),
        "paired_width": _span(paired)[1] - _span(paired)[0],
        "n_obs": total_obs,
    }


# ── Strategy evaluation on the held-out test split ───────────────────────

def collect_predictions_by_group(
    sequences: Sequence[Dict],
    prior_fn: Callable[[str, str], float],
    params: Dict,
    clip: float,
) -> Tuple[Dict[str, List[int]], Dict[str, List[float]]]:
    """Produce (y_true, y_prob) per group, predictions pre-dating their answers.

    The prediction for observation n is computed from the mastery state that
    existed *before* answer n was seen; the answer is then folded in with the
    production BKT update so observation n+1 sees it.
    """
    t, g, s = params["t"], params["g"], params["s"]
    ys: Dict[str, List[int]] = {grp: [] for grp in GROUPS}
    ps: Dict[str, List[float]] = {grp: [] for grp in GROUPS}
    for rec in sequences:
        L = prior_fn(rec["group"], rec["tier"])
        bucket_y = ys[rec["group"]]
        bucket_p = ps[rec["group"]]
        for raw in rec["answers"]:
            pred = L * (1.0 - s) + (1.0 - L) * g
            if pred < clip:
                pred = clip
            elif pred > 1.0 - clip:
                pred = 1.0 - clip
            bucket_y.append(int(raw))
            bucket_p.append(pred)

            if raw:
                posterior = (L * (1.0 - s)) / pred if pred > 0 else L
            else:
                denom = 1.0 - pred
                posterior = (L * s) / denom if denom > 0 else L
            if posterior < 0.0:
                posterior = 0.0
            elif posterior > 1.0:
                posterior = 1.0
            L = posterior + (1.0 - posterior) * t
            if L > 1.0:
                L = 1.0
    return ys, ps


def per_student_nll(
    sequences: Sequence[Dict],
    prior_fn: Callable[[str, str], float],
    params: Dict,
    clip: float,
    students: Sequence[str],
) -> np.ndarray:
    """Total NLL per student for one strategy (for paired bootstrap CIs)."""
    index = {sid: i for i, sid in enumerate(students)}
    out = np.zeros(len(students), dtype=np.float64)
    t, g, s = params["t"], params["g"], params["s"]
    log = math.log
    for rec in sequences:
        L0 = prior_fn(rec["group"], rec["tier"])
        total = 0.0
        L = L0
        for raw in rec["answers"]:
            pred = L * (1.0 - s) + (1.0 - L) * g
            if pred < clip:
                pred = clip
            elif pred > 1.0 - clip:
                pred = 1.0 - clip
            total -= log(pred) if raw else log(1.0 - pred)
            if raw:
                posterior = (L * (1.0 - s)) / pred if pred > 0 else L
            else:
                denom = 1.0 - pred
                posterior = (L * s) / denom if denom > 0 else L
            if posterior < 0.0:
                posterior = 0.0
            elif posterior > 1.0:
                posterior = 1.0
            L = posterior + (1.0 - posterior) * t
            if L > 1.0:
                L = 1.0
        out[index[rec["student"]]] += total
    return out


def bootstrap_paired_delta(
    a: np.ndarray,
    b: np.ndarray,
    counts: np.ndarray,
    n_boot: int,
    seed: int,
    confidence: float,
) -> Dict:
    """Student-level paired bootstrap CI for (a - b) in log loss per observation.

    Positive delta means strategy ``a`` is WORSE than ``b``.
    """
    rng = np.random.default_rng(seed)
    n = len(a)
    idx = rng.integers(0, n, size=(n_boot, n))
    denom = counts[idx].sum(axis=1)
    delta = (a[idx].sum(axis=1) - b[idx].sum(axis=1)) / denom
    alpha = (1.0 - confidence) / 2.0
    lo = float(np.quantile(delta, alpha))
    hi = float(np.quantile(delta, 1.0 - alpha))
    return {
        "mean_delta": float(delta.mean()),
        "ci_lo": lo,
        "ci_hi": hi,
        "confidence": confidence,
        "significant": not (lo <= 0.0 <= hi),
        "n_boot": n_boot,
    }


# ── Practical consequences (section 8) ───────────────────────────────────

def practical_consequences(
    sequences: Sequence[Dict],
    prior_fn: Callable[[str, str], float],
    params: Dict,
    truth_lookup: Dict[Tuple[str, int], float],
    threshold: float,
    checkpoints: Sequence[int],
) -> Dict:
    """Zero-attempt mastery, classification churn, simulation-only error rates."""
    t, g, s = params["t"], params["g"], params["s"]
    max_ckpt = max(checkpoints)

    init_mastered = 0
    total = 0
    changed = {k: 0 for k in checkpoints}
    false_mastered = 0
    false_unmastered = 0
    truth_mastered = 0
    abs_gap = {k: 0.0 for k in checkpoints}
    signed_gap = {k: 0.0 for k in checkpoints}
    n_gap = {k: 0 for k in checkpoints}

    for rec in sequences:
        L0 = prior_fn(rec["group"], rec["tier"])
        total += 1
        init_label = L0 >= threshold
        if init_label:
            init_mastered += 1

        truth = truth_lookup.get((rec["student"], rec["lesson"]))
        if truth is not None:
            truth_label = truth >= threshold
            if truth_label:
                truth_mastered += 1
            if init_label and not truth_label:
                false_mastered += 1
            elif truth_label and not init_label:
                false_unmastered += 1

        L = L0
        state_at = {0: L0}
        for i, raw in enumerate(rec["answers"], start=1):
            if raw:
                pred = L * (1.0 - s) + (1.0 - L) * g
                posterior = (L * (1.0 - s)) / pred if pred > 0 else L
            else:
                pred = L * (1.0 - s) + (1.0 - L) * g
                denom = 1.0 - pred
                posterior = (L * s) / denom if denom > 0 else L
            if posterior < 0.0:
                posterior = 0.0
            elif posterior > 1.0:
                posterior = 1.0
            L = min(1.0, posterior + (1.0 - posterior) * t)
            if i <= max_ckpt:
                state_at[i] = L

        for k in checkpoints:
            if k not in state_at:
                continue
            Lk = state_at[k]
            if (Lk >= threshold) != init_label:
                changed[k] += 1
            gap = Lk - L0
            abs_gap[k] += abs(gap)
            signed_gap[k] += gap
            n_gap[k] += 1

    return {
        "n_lesson_sequences": total,
        "init_mastered": init_mastered,
        "init_mastered_pct": 100.0 * init_mastered / total if total else 0.0,
        "truth_mastered": truth_mastered,
        "false_mastered": false_mastered,
        "false_mastered_pct_of_init_mastered": (
            100.0 * false_mastered / init_mastered if init_mastered else 0.0
        ),
        "false_unmastered": false_unmastered,
        "false_unmastered_pct_of_truth_mastered": (
            100.0 * false_unmastered / truth_mastered if truth_mastered else 0.0
        ),
        "changed": {str(k): changed[k] for k in checkpoints},
        "changed_pct": {
            str(k): 100.0 * changed[k] / total if total else 0.0 for k in checkpoints
        },
        "mean_abs_gap": {
            str(k): abs_gap[k] / n_gap[k] if n_gap[k] else 0.0 for k in checkpoints
        },
        "mean_signed_gap": {
            str(k): signed_gap[k] / n_gap[k] if n_gap[k] else 0.0 for k in checkpoints
        },
    }


def mastery_trajectories(
    sequences: Sequence[Dict],
    prior_fn: Callable[[str, str], float],
    params: Dict,
    group: str,
    max_steps: int,
) -> Dict[int, float]:
    """Mean BKT mastery after 0..max_steps observations for one group."""
    t, g, s = params["t"], params["g"], params["s"]
    totals = {k: 0.0 for k in range(0, max_steps + 1)}
    counts = {k: 0 for k in range(0, max_steps + 1)}
    for rec in sequences:
        if rec["group"] != group:
            continue
        L = prior_fn(rec["group"], rec["tier"])
        totals[0] += L
        counts[0] += 1
        for i, raw in enumerate(rec["answers"], start=1):
            if i > max_steps:
                break
            pred = L * (1.0 - s) + (1.0 - L) * g
            if raw:
                posterior = (L * (1.0 - s)) / pred if pred > 0 else L
            else:
                denom = 1.0 - pred
                posterior = (L * s) / denom if denom > 0 else L
            if posterior < 0.0:
                posterior = 0.0
            elif posterior > 1.0:
                posterior = 1.0
            L = min(1.0, posterior + (1.0 - posterior) * t)
            totals[i] += L
            counts[i] += 1
    return {k: (totals[k] / counts[k] if counts[k] else float("nan"))
            for k in range(0, max_steps + 1)}


# ── CSV helpers ──────────────────────────────────────────────────────────

def write_rows(path: str, rows: List[Dict], columns: Sequence[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


# ── Per-scenario driver ──────────────────────────────────────────────────

def run_scenario(config: Dict, scenario_id: str, out: Dict, quick: bool) -> Dict:
    """Optimise, bootstrap, evaluate and score one scenario. Returns summary."""
    t0 = time.time()
    params = bkt_core.bkt_params()
    clip = float(config["metrics"]["probability_clip"])
    threshold = float(config["mastery_threshold"]["value"])
    grid = bkt_core.candidate_grid(config)
    boot = config["bootstrap"]
    n_boot = int(boot["n_resamples"])
    ci_boot = int(boot["test_ci_resamples"])
    confidence = float(boot["confidence"])
    boot_seed = int(boot["seed"])

    bundle = gd.simulate(config, scenario_id)
    sets = build_sequence_sets(bundle)

    val = sets["validation"]
    test = sets["test"]

    print(f"\n[{scenario_id}] val students={len(val.students)} "
          f"test students={len(test.students)} grid={len(grid)}", flush=True)

    # ---- Optimise per group on the VALIDATION split --------------------
    curves: List[Dict] = []
    ranges: List[Dict] = []
    selected: Dict[str, Dict[str, float]] = {g: {} for g in GROUPS}
    selected_common: Optional[float] = None
    group_cells: Dict[Tuple[str, str], Dict] = {}

    for group in GROUPS:
        seqs = [r for r in val.records if r["group"] == group]
        students = _local_students(seqs)
        if not seqs:
            raise ValueError(f"no validation sequences for group {group}")
        losses, counts = candidate_loss_matrix(seqs, grid, params, len(students), clip)
        best_c, mean_ll, total_obs = summarise_grid(grid, losses, counts)
        rng_info = near_optimal_range(
            grid, losses, counts, len(students), n_boot,
            seed=boot_seed + sum(map(ord, group)),
        )

        prod_tier_values = sorted({bkt_core.production_prior_for_tier(group, tier)
                                   for tier in TIERS})
        for ci, prior in enumerate(grid):
            curves.append({
                "scenario": scenario_id,
                "scope": "group_specific",
                "group": group,
                "candidate_prior": f"{prior:.2f}",
                "mean_log_loss": f"{mean_ll[ci]:.10f}",
                "n_obs": total_obs,
                "n_students": len(students),
                "is_selected": int(ci == best_c),
                "is_production_value": int(prior in prod_tier_values),
            })

        lo, hi = rng_info["primary_span"]
        ranges.append({
            "scenario": scenario_id,
            "scope": "group_specific",
            "group": group,
            "selected_prior": f"{rng_info['best_prior']:.2f}",
            "min_log_loss": f"{rng_info['min_log_loss']:.10f}",
            "se_at_min": f"{rng_info['se_at_min']:.10f}",
            "threshold": f"{rng_info['threshold']:.10f}",
            "near_opt_lo": f"{lo:.2f}",
            "near_opt_hi": f"{hi:.2f}",
            "near_opt_width": f"{rng_info['primary_width']:.2f}",
            "paired_lo": f"{rng_info['paired_span'][0]:.2f}",
            "paired_hi": f"{rng_info['paired_span'][1]:.2f}",
            "paired_width": f"{rng_info['paired_width']:.2f}",
            "n_candidates_in_range": len(rng_info["primary_indices"]),
            "n_obs": total_obs,
            "n_students": len(students),
            "rule": boot["rule"],
            "n_boot": n_boot,
        })
        selected[group]["group_specific"] = float(rng_info["best_prior"])

        # ---- group x tier cells (structural match to production) ----
        for tier in TIERS:
            cell = [r for r in seqs if r["tier"] == tier]
            if not cell:
                continue
            cell_students = _local_students(cell)
            l2, c2 = candidate_loss_matrix(cell, grid, params, len(cell_students), clip)
            b2, m2, obs2 = summarise_grid(grid, l2, c2)
            group_cells[(group, tier)] = {
                "prior": float(grid[b2]),
                "min_log_loss": m2[b2],
                "n_obs": obs2,
                "n_students": len(cell_students),
            }

    # ---- Common prior over everybody, on VALIDATION ----
    losses_c, counts_c = candidate_loss_matrix(val.records, grid, params,
                                               len(val.students), clip)
    best_common, mean_common, obs_common = summarise_grid(grid, losses_c, counts_c)
    selected_common = float(grid[best_common])
    for ci, prior in enumerate(grid):
        curves.append({
            "scenario": scenario_id,
            "scope": "common",
            "group": OVERALL,
            "candidate_prior": f"{prior:.2f}",
            "mean_log_loss": f"{mean_common[ci]:.10f}",
            "n_obs": obs_common,
            "n_students": len(val.students),
            "is_selected": int(ci == best_common),
            "is_production_value": 0,
        })

    # ---- Prior functions ------------------------------------------------
    def prior_production(group: str, tier: str) -> float:
        return bkt_core.production_prior_for_tier(group, tier)

    def prior_common(_group: str, _tier: str) -> float:
        return selected_common

    def prior_group(group: str, _tier: str) -> float:
        return selected[group]["group_specific"]

    def prior_group_tier(group: str, tier: str) -> float:
        cell = group_cells.get((group, tier))
        if cell is None:  # empty cell: fall back to the production value
            return bkt_core.production_prior_for_tier(group, tier)
        return cell["prior"]

    def prior_oracle(group: str, tier: str) -> float:
        return float(bundle["means"][group][tier])

    strategies = [
        ("production", prior_production, "A - current production priors"),
        ("common", prior_common, "B - one shared prior"),
        ("group_specific", prior_group, "C - one prior per proficiency group"),
        ("group_x_tier", prior_group_tier, "E - one prior per (group, tier)"),
        ("oracle_reference", prior_oracle, "D - hidden DGP mean (unavailable in production)"),
    ]

    # ---- Held-out TEST evaluation, exactly once ------------------------
    metrics_rows: List[Dict] = []
    delta_rows: List[Dict] = []
    calibration_rows: List[Dict] = []
    nll_by_strategy: Dict[str, np.ndarray] = {}
    counts_by_strategy: Dict[str, np.ndarray] = {}

    prod_by_group: Dict[str, Dict] = {}
    for name, fn, _label in strategies:
        ys_by_g, ps_by_g = collect_predictions_by_group(test.records, fn, params, clip)
        for gsel in list(GROUPS) + [OVERALL]:
            if gsel == OVERALL:
                y_sub = [y for g in GROUPS for y in ys_by_g[g]]
                p_sub = [p for g in GROUPS for p in ps_by_g[g]]
            else:
                y_sub, p_sub = ys_by_g[gsel], ps_by_g[gsel]
            if not y_sub:
                continue
            bundle_metrics = bkt_core.metric_bundle(y_sub, p_sub, config)
            row = {
                "scenario": scenario_id,
                "strategy": name,
                "group": gsel,
                "log_loss": f"{bundle_metrics['log_loss']:.10f}",
                "brier": f"{bundle_metrics['brier']:.10f}",
                "accuracy": f"{bundle_metrics['accuracy']:.6f}",
                "ece": f"{bundle_metrics['ece']:.6f}",
                "n_obs": bundle_metrics["n_obs"],
                "prior_used": _describe_prior(name, fn, gsel),
            }
            metrics_rows.append(row)
            if name == "production":
                prod_by_group[gsel] = bundle_metrics
            elif gsel in prod_by_group:
                prod = prod_by_group[gsel]
                dl = bundle_metrics["log_loss"] - prod["log_loss"]
                db = bundle_metrics["brier"] - prod["brier"]
                delta_rows.append({
                    "scenario": scenario_id,
                    "strategy": name,
                    "group": gsel,
                    "delta_log_loss": f"{dl:.10f}",
                    "rel_log_loss_pct": f"{100.0 * dl / prod['log_loss']:.4f}",
                    "delta_brier": f"{db:.10f}",
                    "rel_brier_pct": f"{100.0 * db / prod['brier']:.4f}",
                    "n_obs": bundle_metrics["n_obs"],
                    "interpretation": "negative = better than production",
                })

            if gsel != OVERALL:
                _rows = _calibration_rows(y_sub, p_sub, scenario_id, name, gsel,
                                          int(config["metrics"]["ece_bins"]))
                calibration_rows.extend(_rows)

        nll_by_strategy[name] = per_student_nll(test.records, fn, params, clip,
                                                test.students)
        counts_by_strategy[name] = np.array(
            [sum(len(r["answers"]) for r in test.records if r["student"] == sid)
             for sid in test.students], dtype=np.int64)

    # ---- Paired bootstrap CIs on test log-loss deltas -------------------
    boot_rows: List[Dict] = []
    prod_nll = nll_by_strategy["production"]
    prod_counts = counts_by_strategy["production"]
    for name, _fn, _label in strategies:
        if name == "production":
            continue
        for gsel in list(GROUPS) + [OVERALL]:
            if gsel == OVERALL:
                a, b, c = nll_by_strategy[name], prod_nll, prod_counts
                n_students_used = len(test.students)
            else:
                mask = np.array(
                    [test.groups[s] == gsel for s in test.students], dtype=bool)
                if not mask.any():
                    continue
                a = nll_by_strategy[name][mask]
                b = prod_nll[mask]
                c = prod_counts[mask]
                n_students_used = int(mask.sum())
            info = bootstrap_paired_delta(
                a, b, c, ci_boot, boot_seed + 7 + sum(map(ord, name + gsel)), confidence)
            boot_rows.append({
                "scenario": scenario_id,
                "comparison": f"{name} minus production",
                "group": gsel,
                "mean_delta_log_loss": f"{info['mean_delta']:.10f}",
                "ci_lo": f"{info['ci_lo']:.10f}",
                "ci_hi": f"{info['ci_hi']:.10f}",
                "confidence": confidence,
                "significant": int(info["significant"]),
                "n_boot": ci_boot,
                "n_students": n_students_used,
            })

    # ---- Practical consequences (section 8) ----------------------------
    truth_lookup = {
        (row[0], row[4]): float(row[5]) for row in bundle["truth"]
    }
    checkpoints = [int(k) for k in config["practical_checkpoints"]]
    practical_rows: List[Dict] = []
    for name, fn, _label in strategies:
        for gsel in list(GROUPS) + [OVERALL]:
            seqs = test.records if gsel == OVERALL else [
                r for r in test.records if r["group"] == gsel]
            if not seqs:
                continue
            res = practical_consequences(seqs, fn, params, truth_lookup,
                                         threshold, checkpoints)
            practical_rows.append({
                "scenario": scenario_id,
                "strategy": name,
                "group": gsel,
                "n_lesson_sequences": res["n_lesson_sequences"],
                "init_mastered": res["init_mastered"],
                "init_mastered_pct": f"{res['init_mastered_pct']:.2f}",
                "truth_mastered": res["truth_mastered"],
                "false_mastered_vs_hidden": res["false_mastered"],
                "false_mastered_pct_of_init_mastered":
                    f"{res['false_mastered_pct_of_init_mastered']:.2f}",
                "false_unmastered_vs_hidden": res["false_unmastered"],
                "false_unmastered_pct_of_truth_mastered":
                    f"{res['false_unmastered_pct_of_truth_mastered']:.2f}",
                **{f"changed_at_{k}": res["changed"][str(k)] for k in checkpoints},
                **{f"changed_at_{k}_pct": f"{res['changed_pct'][str(k)]:.2f}"
                   for k in checkpoints},
                **{f"mean_abs_gap_at_{k}": f"{res['mean_abs_gap'][str(k)]:.6f}"
                   for k in checkpoints},
                **{f"mean_signed_gap_at_{k}": f"{res['mean_signed_gap'][str(k)]:.6f}"
                   for k in checkpoints},
            })

    # ---- Trajectories --------------------------------------------------
    traj_rows: List[Dict] = []
    max_steps = max(checkpoints)
    for name, fn, _label in strategies:
        for group in GROUPS:
            traj = mastery_trajectories(test.records, fn, params, group, max_steps)
            for k in sorted(traj):
                traj_rows.append({
                    "scenario": scenario_id,
                    "strategy": name,
                    "group": group,
                    "observation_index": k,
                    "mean_mastery": f"{traj[k]:.6f}",
                })

    out["curves"].extend(curves)
    out["ranges"].extend(ranges)
    out["metrics"].extend(metrics_rows)
    out["deltas"].extend(delta_rows)
    out["calibration"].extend(calibration_rows)
    out["bootstrap"].extend(boot_rows)
    out["practical"].extend(practical_rows)
    out["trajectories"].extend(traj_rows)

    elapsed = time.time() - t0
    print(f"[{scenario_id}] selected common={selected_common:.2f} "
          + " ".join(f"{g}={selected[g]['group_specific']:.2f}" for g in GROUPS)
          + f"  ({elapsed:.1f}s)", flush=True)

    return {
        "scenario": scenario_id,
        "selected_common": selected_common,
        "selected_group": {g: selected[g]["group_specific"] for g in GROUPS},
        "group_x_tier": {f"{g}/{t}": group_cells[(g, t)]["prior"]
                         for (g, t) in sorted(group_cells)},
        "elapsed_seconds": round(elapsed, 2),
    }


def _describe_prior(name: str, fn: Callable[[str, str], float], group: str) -> str:
    """Human-readable summary of which prior(s) a strategy actually used."""
    vals = [fn(g, t) for g in GROUPS for t in TIERS]
    if name == "common":
        return f"single shared prior {fn('beginner', 'easy'):.2f}"
    if name == "group_specific":
        if group == OVERALL:
            return " / ".join(f"{g}={fn(g, 'easy'):.2f}" for g in GROUPS)
        return f"{fn(group, 'easy'):.2f} for {group}"
    if name == "oracle_reference":
        return (f"hidden DGP means (simulation-only, unavailable in production): "
                f"mean={sum(vals) / len(vals):.4f}")
    distinct = sorted({round(v, 2) for v in vals})
    if name == "production":
        return f"production tiers {distinct}"
    return f"{distinct}"


def _calibration_rows(ys, ps, scenario, strategy, group, n_bins):
    ece_value, rows = bkt_core.ece(ys, ps, n_bins=n_bins)
    out = []
    for r in rows:
        out.append({
            "scenario": scenario,
            "strategy": strategy,
            "group": group,
            "bin": r["bin"],
            "lo": f"{r['lo']:.2f}",
            "hi": f"{r['hi']:.2f}",
            "mean_predicted": ("" if r["mean_predicted"] is None
                               else f"{r['mean_predicted']:.4f}"),
            "observed": ("" if r["observed"] is None
                         else f"{r['observed']:.4f}"),
            "count": r["count"],
            "ece_group": f"{ece_value:.6f}",
        })
    return out


# ── Top level ────────────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="BKT P(L0) prior experiment")
    parser.add_argument("--config", default=None)
    parser.add_argument("--scenarios", nargs="*", default=None)
    parser.add_argument("--no-sensitivity", action="store_true")
    parser.add_argument("--quick", action="store_true",
                        help="tiny smoke run (overrides sample sizes)")
    parser.add_argument("--out", default=None, help="results directory override")
    args = parser.parse_args(argv)

    config = bkt_core.load_config(args.config)
    if args.quick:
        config = copy.deepcopy(config)
        config["population"]["students_per_group"] = 60
        config["population"]["lessons_per_student"] = 3
        config["population"]["questions_per_lesson"] = 5
        config["bootstrap"]["n_resamples"] = 60
        config["bootstrap"]["test_ci_resamples"] = 100
        config["scenarios"] = [s for s in config["scenarios"]
                               if s["id"] in ("primary", "high_learning")]

    if args.scenarios is not None:
        wanted = set(args.scenarios)
        config["scenarios"] = [s for s in config["scenarios"] if s["id"] in wanted]
        missing = wanted - {s["id"] for s in config["scenarios"]}
        if missing:
            raise KeyError(f"unknown scenarios: {sorted(missing)}")
    if args.no_sensitivity:
        config["scenarios"] = [s for s in config["scenarios"] if s["id"] == "primary"]

    results_dir = args.out or bkt_core.resolve(config["paths"]["results"])
    os.makedirs(results_dir, exist_ok=True)

    out: Dict[str, List] = {
        "curves": [], "ranges": [], "metrics": [], "deltas": [],
        "calibration": [], "bootstrap": [], "practical": [], "trajectories": [],
    }

    # Snapshot the live stores before any simulation work starts, then verify
    # byte-for-byte at the end that nothing wrote to them.
    live_before = _live_hashes()

    summaries = []
    for spec in config["scenarios"]:
        summaries.append(run_scenario(config, spec["id"], out, args.quick))

    write_rows(os.path.join(results_dir, "validation_curves.csv"), out["curves"],
               ["scenario", "scope", "group", "candidate_prior", "mean_log_loss",
                "n_obs", "n_students", "is_selected", "is_production_value"])
    write_rows(os.path.join(results_dir, "near_optimal_ranges.csv"), out["ranges"],
               ["scenario", "scope", "group", "selected_prior", "min_log_loss",
                "se_at_min", "threshold", "near_opt_lo", "near_opt_hi",
                "near_opt_width", "paired_lo", "paired_hi", "paired_width",
                "n_candidates_in_range", "n_obs", "n_students", "rule", "n_boot"])
    write_rows(os.path.join(results_dir, "strategy_test_metrics.csv"), out["metrics"],
               ["scenario", "strategy", "group", "log_loss", "brier", "accuracy",
                "ece", "n_obs", "prior_used"])
    write_rows(os.path.join(results_dir, "strategy_deltas.csv"), out["deltas"],
               ["scenario", "strategy", "group", "delta_log_loss",
                "rel_log_loss_pct", "delta_brier", "rel_brier_pct", "n_obs",
                "interpretation"])
    write_rows(os.path.join(results_dir, "calibration_bins.csv"), out["calibration"],
               ["scenario", "strategy", "group", "bin", "lo", "hi",
                "mean_predicted", "observed", "count", "ece_group"])
    write_rows(os.path.join(results_dir, "bootstrap_intervals.csv"), out["bootstrap"],
               ["scenario", "comparison", "group", "mean_delta_log_loss",
                "ci_lo", "ci_hi", "confidence", "significant", "n_boot",
                "n_students"])
    write_rows(os.path.join(results_dir, "practical_consequences.csv"),
               out["practical"],
               ["scenario", "strategy", "group", "n_lesson_sequences",
                "init_mastered", "init_mastered_pct", "truth_mastered",
                "false_mastered_vs_hidden",
                "false_mastered_pct_of_init_mastered", "false_unmastered_vs_hidden",
                "false_unmastered_pct_of_truth_mastered"]
               + [f"changed_at_{k}" for k in config["practical_checkpoints"]]
               + [f"changed_at_{k}_pct" for k in config["practical_checkpoints"]]
               + [f"mean_abs_gap_at_{k}" for k in config["practical_checkpoints"]]
               + [f"mean_signed_gap_at_{k}" for k in config["practical_checkpoints"]])
    write_rows(os.path.join(results_dir, "mastery_trajectories.csv"),
               out["trajectories"],
               ["scenario", "strategy", "group", "observation_index", "mean_mastery"])

    summary = {
        "experiment": config["experiment_name"],
        "production_config": bkt_core.PRODUCTION_BKT,
        "mastery_threshold": config["mastery_threshold"]["value"],
        "grid_size": len(bkt_core.candidate_grid(config)),
        "scenarios": summaries,
    }
    with open(os.path.join(results_dir, "summary.json"), "w", encoding="utf-8") as h:
        json.dump(summary, h, indent=2, sort_keys=True)

    _assert_no_live_io(live_before)
    print(f"\nResults written to {results_dir}")
    return 0


#: Live application stores the research tree must never read or write.
LIVE_STORES = (
    "data/sanskrit_ai.sqlite3",
    "data/bkt_progress.json",
    "data/users.json",
)


def _live_hashes() -> Dict[str, Optional[str]]:
    """SHA-256 of each live store (``None`` when the file does not exist)."""
    state: Dict[str, Optional[str]] = {}
    for rel in LIVE_STORES:
        path = os.path.join(bkt_core.BACKEND_DIR, rel)
        state[rel] = gd.sha256_file(path) if os.path.exists(path) else None
    return state


def _assert_no_live_io(before: Dict[str, Optional[str]]) -> None:
    """Fail loudly if the research tree touched a live store or imported it.

    Two independent checks:
      1. Byte-for-byte hashes of the live database, legacy progress file and
         user file must be identical before and after the experiment.
      2. The SQLite repository must never have been imported, so the
         experiment cannot have opened the database at all.
    """
    if "sqlite_repository" in sys.modules or "SQLiteRepository" in sys.modules:
        raise RuntimeError("research code imported the live SQLite repository")

    after = _live_hashes()
    for rel, old in before.items():
        if after.get(rel) != old:
            raise RuntimeError(
                f"live store {rel} changed during the experiment "
                f"({old} -> {after.get(rel)})"
            )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
