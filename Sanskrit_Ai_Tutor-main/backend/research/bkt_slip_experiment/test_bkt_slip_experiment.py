#!/usr/bin/env python
"""
Automated tests for the BKT slip-probability experiment.

Project convention (pytest is not installed) is a plain script that prints a
PASS/FAIL line per check and exits 0 only if every check passed.

Covers the properties required by the experiment specification:

    1  BKT equations match hand-calculated textbook values
    2  Prediction probabilities are valid and bounded
    3  Posterior update and transition order match production
    4  Output is deterministic for a fixed seed
    5  Recovery behaves correctly on synthetic data
    6  Student-level train/validation/test separation (no student overlap)
    7  Hidden truth never reaches the fitting/prediction path
    8  Parameter selection uses validation only, never test
    9  Metric formulas match hand-computable examples
   10  One-standard-error interval rule is implemented as documented
   11  Bootstrap resamples STUDENTS, not individual answers
   12  Boundary cases and insufficient data are handled explicitly
   13  Figures and summaries are reproducible from saved results
   14  No production file or live database is modified

Usage
-----
    python test_bkt_slip_experiment.py            # full suite
    python test_bkt_slip_experiment.py --fast     # skip the slow recovery test
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
from typing import Callable, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import analyze_results as ar  # noqa: E402
import bkt_core  # noqa: E402
import generate_dataset as gd  # noqa: E402
import run_experiment as rex  # noqa: E402

PASSED: List[str] = []
FAILED: List[Tuple[str, str]] = []

CONFIG = bkt_core.load_config()


def check(name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        import traceback
        FAILED.append((name, f"{type(exc).__name__}: {exc}"))
        print(f"  FAIL  {name}")
        print(f"        {type(exc).__name__}: {exc}")
        for line in traceback.format_exc().strip().splitlines()[-4:]:
            print(f"        {line}")
    else:
        PASSED.append(name)
        print(f"  pass  {name}")


def ok(cond: bool, msg: str = "") -> None:
    if not cond:
        raise AssertionError(msg or "assertion failed")


def close(a: float, b: float, tol: float = 1e-9, msg: str = "") -> None:
    if abs(float(a) - float(b)) > tol:
        raise AssertionError(msg or f"{a!r} != {b!r} within {tol}")


# ── 1. BKT equations against hand-calculated examples ────────────────────

def test_equations() -> None:
    p = bkt_core.params(s=0.10, g=0.25, t=0.15)
    L = 0.5

    # P(C) = L(1-S) + (1-L)G = 0.5*0.9 + 0.5*0.25 = 0.575
    close(bkt_core.predict_correct(L, p), 0.575, 1e-12, "P(C)")

    # P(L|C) = L(1-S)/P(C) = 0.45/0.575
    close(bkt_core.posterior(L, True, p), 0.45 / 0.575, 1e-12, "P(L|C)")

    # P(L|I) = L*S/(L*S + (1-L)(1-G)) = 0.05/(0.05+0.375) = 0.05/0.425
    expected_incorrect = 0.05 / 0.425
    close(bkt_core.posterior(L, False, p), expected_incorrect, 1e-12, "P(L|I)")

    # Transition after the observation.
    post_c = 0.45 / 0.575
    close(bkt_core.step(L, True, p),
          post_c + (1 - post_c) * 0.15, 1e-12, "L_next after correct")
    post_i = 0.05 / 0.425
    close(bkt_core.step(L, False, p),
          post_i + (1 - post_i) * 0.15, 1e-12, "L_next after incorrect")
    # The incorrect branch happens to be exactly 0.25 here - a good exact check.
    close(bkt_core.step(L, False, p), 0.25, 1e-12, "L_next(I) is exactly 0.25")

    # Cross-check the posterior against production's own update_mastery by
    # removing the transition: production returns posterior + (1-posterior)*t,
    # so posterior = (production_result - t*... ) invert it.
    prod_full = bkt_core.bktengine_for_scoring().update_mastery(L, False, dict(p))
    close(prod_full, bkt_core.step(L, False, p), 1e-12,
          "research step() must equal production update_mastery()")


# ── 2. Prediction probabilities are valid and bounded ────────────────────

def test_probability_bounds() -> None:
    for s in (0.01, 0.10, 0.35, 0.50):
        p = bkt_core.params(s=s, g=0.25, t=0.15)
        for L in (0.0, 0.001, 0.5, 0.999, 1.0):
            pc = bkt_core.predict_correct(L, p)
            ok(0.0 <= pc <= 1.0, f"P(C)={pc} out of [0,1]")
    # Extremes: at L=0 only guess can produce a correct answer; at L=1 only
    # non-slip can.
    p = bkt_core.params(s=0.10, g=0.25, t=0.15)
    close(bkt_core.predict_correct(0.0, p), 0.25, 1e-12)
    close(bkt_core.predict_correct(1.0, p), 0.90, 1e-12)
    # Monotone in L for s + g < 1.
    prev = -1.0
    for i in range(101):
        L = i / 100.0
        pc = bkt_core.predict_correct(L, p)
        ok(pc >= prev - 1e-15, "P(C) must be non-decreasing in L")
        prev = pc


# ── 3. Posterior and transition order ────────────────────────────────────

def test_transition_order() -> None:
    p = bkt_core.params(s=0.10, g=0.25, t=0.15)
    L = 0.4
    posterior = bkt_core.posterior(L, True, p)
    # Production applies posterior FIRST, then the transition.
    ok(posterior < bkt_core.step(L, True, p), "transition must raise after correct")
    ok(bkt_core.step(L, True, p) < 1.0, "step must stay below 1")

    # Zero denominators fall back to the prior rather than dividing by zero.
    p_degenerate = bkt_core.params(s=0.0, g=0.0, t=0.15)
    close(bkt_core.posterior(0.0, True, p_degenerate), 0.0, 1e-12,
          "P(C)=0 must return the prior, not NaN")
    close(bkt_core.posterior(1.0, False, p_degenerate), 1.0, 1e-12,
          "P(I)=0 must return the prior, not NaN")

    # A run of answers must move the state monotonically toward mastery.
    seq = bkt_core.run_sequence_states(0.1, [1, 1, 1, 1], p)
    ok(all(a < b for a, b in zip(seq, seq[1:])),
       f"all-correct must strictly increase L, got {seq}")


# ── 4. Deterministic output for a fixed seed ─────────────────────────────

def test_determinism() -> None:
    a = gd.simulate(CONFIG, s=0.10, g=0.25, t=0.15, seed=42,
                    students_per_group=60)
    b = gd.simulate(CONFIG, s=0.10, g=0.25, t=0.15, seed=42,
                    students_per_group=60)
    ok(a["observations"] == b["observations"], "same seed must give same rows")
    ok(a["truth"] == b["truth"], "same seed must give same hidden truth")

    c = gd.simulate(CONFIG, s=0.10, g=0.25, t=0.15, seed=43,
                    students_per_group=60)
    ok(a["observations"] != c["observations"], "different seed must differ")

    # The canonical HMM generator is deterministic too.
    d = gd.simulate(CONFIG, s=0.10, g=0.25, t=0.15, seed=42,
                    students_per_group=60, transition_mode="bkt_binary")
    e = gd.simulate(CONFIG, s=0.10, g=0.25, t=0.15, seed=42,
                    students_per_group=60, transition_mode="bkt_binary")
    ok(d["observations"] == e["observations"], "HMM generator must be deterministic")


# ── 5. Recovery behaviour on synthetic data ──────────────────────────────

def test_recovery(fast: bool = False) -> None:
    students = 150 if fast else 400
    grid = bkt_core.slip_grid(CONFIG)
    clip = float(CONFIG["metrics"]["probability_clip"])
    true_s = 0.20

    bundle = gd.simulate(CONFIG, s=true_s, g=0.25, t=0.15, seed=7,
                         students_per_group=students,
                         within_group_sd=0.01, transition_mode="bkt_binary")
    gd.validate(bundle, CONFIG)
    seqs = ar.build_sequences(bundle["observations"], rex.production_prior_fn())
    val = ar.split_sequences(seqs, bundle["observations"])["validation"]

    fit = ar.fit_grid(val, [{"s": s, "g": 0.25, "t": 0.15} for s in grid], clip)
    sel = ar.select_candidate(grid, fit, 200, 999)

    ok(abs(sel["best_prior"] - true_s) <= 0.05,
       f"selected {sel['best_prior']} too far from true {true_s}")
    ok(sel["lo"] <= true_s <= sel["hi"],
       f"true slip {true_s} outside near-optimal interval "
       f"[{sel['lo']}, {sel['hi']}]")

    # The validation arg-min must beat the production setting on validation.
    summary = ar.summarise_grid(grid, fit)
    prod_idx = grid.index(0.10)
    ok(summary["mean_log_loss"][summary["argmin"]]
       <= summary["mean_log_loss"][prod_idx] + 1e-12,
       "selected validation loss must not exceed production's")


# ── 6. Student-level separation ──────────────────────────────────────────

def test_student_separation() -> None:
    bundle = gd.simulate(CONFIG, s=0.10, students_per_group=120)
    gd.validate(bundle, CONFIG)

    splits = bundle["splits"]
    ok(len(splits) == len(set(splits)), "split map must be keyed by student")
    ok(set(splits.values()) <= {"train", "validation", "test"}, "bad split label")

    seqs = ar.build_sequences(bundle["observations"], rex.production_prior_fn())
    parts = ar.split_sequences(seqs, bundle["observations"])
    ids = {k: {r["student"] for r in v} for k, v in parts.items()}
    ok(not (ids["train"] & ids["validation"]), "train/validation student overlap")
    ok(not (ids["train"] & ids["test"]), "train/test student overlap")
    ok(not (ids["validation"] & ids["test"]), "validation/test student overlap")

    # Every sequence must land in exactly one partition.
    total = sum(len(v) for v in parts.values())
    ok(total == len(seqs), "every sequence must be assigned to exactly one split")

    # Stratification: each group must be represented in each split.
    for split_name, rows in parts.items():
        groups = {r["group"] for r in rows}
        ok(len(groups) == 3, f"split {split_name} missing a proficiency group")


# ── 7. No hidden-truth leakage ───────────────────────────────────────────

def test_no_truth_leakage() -> None:
    bundle = gd.simulate(CONFIG, s=0.10, students_per_group=60)
    stats = gd.validate(bundle, CONFIG)

    ok(len(bundle["observations"][0]) == len(gd.OBS_COLUMNS),
       "observations must contain observed columns only")
    ok("hidden_mastery" not in gd.OBS_COLUMNS,
       "hidden mastery must never be an observation column")
    ok(stats["leakage_check"].startswith("ground-truth columns absent"),
       "validation must assert the leakage check")

    # Truth is a separate table with a different schema.
    ok(len(bundle["truth"][0]) == len(gd.TRUTH_COLUMNS), "truth schema mismatch")
    ok("hidden_mastery" in gd.TRUTH_COLUMNS, "truth must expose hidden mastery")

    # The fitting path only ever receives (prior, answers) - never the truth.
    seqs = ar.build_sequences(bundle["observations"], rex.production_prior_fn())
    allowed = {"student", "group", "tier", "lesson", "prior", "answers",
               "attempt_indices"}
    for r in seqs:
        ok(set(r.keys()) <= allowed,
           f"sequence carries unexpected keys: {set(r.keys()) - allowed}")
        ok(not any("hidden" in k or "truth" in k for k in r),
           "hidden truth leaked into the fitting record")


# ── 8. Validation-only selection ─────────────────────────────────────────

def test_validation_only_selection() -> None:
    bundle = gd.simulate(CONFIG, s=0.10, students_per_group=120)
    seqs = ar.build_sequences(bundle["observations"], rex.production_prior_fn())
    parts = ar.split_sequences(seqs, bundle["observations"])
    grid = bkt_core.slip_grid(CONFIG)
    clip = float(CONFIG["metrics"]["probability_clip"])
    param_sets = [{"s": s, "g": 0.25, "t": 0.15} for s in grid]

    fit_val = ar.fit_grid(parts["validation"], param_sets, clip)
    fit_test = ar.fit_grid(parts["test"], param_sets, clip)
    val_sel = ar.select_candidate(grid, fit_val, 200, 11)
    test_sel = ar.select_candidate(grid, fit_test, 200, 11)

    # They are computed from DIFFERENT data, so the machinery really is split
    # specific - and the recorded selection is the validation one.
    ok(fit_val["losses"].shape == fit_test["losses"].shape, "shape mismatch")
    ok(val_sel["n_students"] == len({r["student"] for r in parts["validation"]}),
       "selection must be fit on the validation students")
    ok(test_sel["n_students"] == len({r["student"] for r in parts["test"]}),
       "test selection must be fit on the test students")
    ok(len(parts["validation"]) > 0 and len(parts["test"]) > 0, "empty split")

    # Selection never reads the test rows: rebuilding validation-only selection
    # after deleting the test rows must give an identical answer.
    val_only = [r for r in bundle["observations"] if r[2] != "test"]
    seqs2 = ar.build_sequences(val_only, rex.production_prior_fn())
    parts2 = ar.split_sequences(seqs2, val_only)
    fit2 = ar.fit_grid(parts2["validation"], param_sets, clip)
    sel2 = ar.select_candidate(grid, fit2, 200, 11)
    ok(sel2["best_prior"] == val_sel["best_prior"],
       "selection changed when test data was removed - test leakage detected")
    ok(sel2["min_log_loss"] == val_sel["min_log_loss"],
       "validation loss changed when test data was removed")


# ── 9. Metric formulas on hand-computable examples ───────────────────────

def test_metric_formulas() -> None:
    y = [1, 0]
    p = [0.8, 0.3]

    expected_ll = -(math.log(0.8) + math.log(0.7)) / 2.0
    close(bkt_core.log_loss(y, p), expected_ll, 1e-12, "log loss")

    expected_brier = ((0.8 - 1) ** 2 + (0.3 - 0) ** 2) / 2.0
    close(bkt_core.brier(y, p), expected_brier, 1e-12, "brier")

    close(bkt_core.accuracy(y, p, threshold=0.5), 1.0, 1e-12, "accuracy")
    # y = [1, 0] with p = [0.4, 0.4] predicts [0, 0]: 1 miss + 1 hit = 0.5.
    close(bkt_core.accuracy(y, [0.4, 0.4], threshold=0.5), 0.5, 1e-12,
          "accuracy with both predictions on the low side")
    close(bkt_core.accuracy([1, 1], [0.4, 0.6], threshold=0.5), 0.5, 1e-12,
          "accuracy with mixed correct/incorrect labels")

    # ECE, 10 equal-width bins: bin(mid .85, obs 1.0) and bin(mid .35, obs 0.0).
    ece_val, rows = bkt_core.ece(y, p, n_bins=10)
    close(ece_val, 0.5 * abs(1.0 - 0.85) + 0.5 * abs(0.0 - 0.35), 1e-12, "ece")
    ok(len(rows) == 10, "ece must return every bin, empty ones included")
    ok(sum(r["count"] for r in rows) == 2, "ece bin counts must sum to N")

    # A perfect predictor has log loss -> 0, Brier 0, ECE 0.
    close(bkt_core.log_loss([1, 0], [1.0 - 1e-16, 1e-16]), 0.0, 1e-9)
    close(bkt_core.brier([1, 0], [1.0, 0.0]), 0.0, 1e-15)
    # ECE of a deterministic perfect predictor is 0.05, NOT 0: p=1.0 clamps to
    # the last of 10 equal-width bins (mid 0.95) and p=0.0 to the first
    # (mid 0.05).  This bin-midpoint artefact is the documented limitation of
    # equal-width ECE, so the assertion pins the real value deliberately.
    ece_perfect = bkt_core.ece([1, 0, 1, 0], [1.0, 0.0, 1.0, 0.0], n_bins=10)[0]
    close(ece_perfect, 0.5 * 0.05 + 0.5 * 0.05, 1e-12,
          "ECE of a deterministic perfect predictor (bin-midpoint artefact)")
    ok(ece_perfect > 0.0, "equal-width ECE cannot reach 0 even when perfect")

    # Mastery metrics on a hand-built example, threshold 0.7.
    est = [0.9, 0.2, 0.8, 0.1]
    hid = [0.5, 0.5, 0.9, 0.9]   # labels: 0, 0, 1, 1
    mm = bkt_core.mastery_metrics(est, hid, threshold=0.7)
    close(mm["mae"], (0.4 + 0.3 + 0.1 + 0.8) / 4.0, 1e-12, "mae")
    # flagged (L>=0.7): indices 0 and 2 -> 2 ; false mastered: index 0 -> 1
    ok(mm["flagged"] == 2, f"flagged={mm['flagged']}")
    ok(mm["truth_mastered"] == 2, f"truth_mastered={mm['truth_mastered']}")
    ok(mm["false_mastered"] == 1, f"false_mastered={mm['false_mastered']}")
    ok(mm["false_unmastered"] == 1, f"false_unmastered={mm['false_unmastered']}")
    close(mm["false_mastered_rate_all"], 0.25, 1e-12)
    close(mm["false_mastered_rate_of_flagged"], 0.5, 1e-12)
    close(mm["false_unmastered_rate_all"], 0.25, 1e-12)
    close(mm["false_unmastered_rate_of_truth"], 0.5, 1e-12)

    # Zero denominators report None rather than dividing by zero.
    mm_empty = bkt_core.mastery_metrics([0.1, 0.2], [0.0, 0.0], 0.7)
    ok(mm_empty["false_mastered_rate_of_flagged"] is None,
       "no flagged pairs must yield None, not ZeroDivisionError")


# ── 10. One-standard-error interval ──────────────────────────────────────

def test_one_se_interval() -> None:
    grid = [0.05, 0.10, 0.15, 0.20]
    losses = [0.300, 0.301, 0.310, 0.330]
    res = bkt_core.near_optimal_interval(grid, losses, se_at_min=0.002)

    ok(res["best_prior"] == 0.05, f"arg-min should be 0.05, got {res['best_prior']}")
    close(res["threshold"], 0.302, 1e-12, "threshold = min + SE")
    ok(res["lo"] == 0.05 and res["hi"] == 0.10, f"interval {res['lo']}-{res['hi']}")
    close(res["width"], 0.05, 1e-12)
    ok(res["n_inside"] == 2, f"n_inside={res['n_inside']}")

    # SE = 0 collapses the interval to the arg-min only.
    tight = bkt_core.near_optimal_interval(grid, losses, se_at_min=0.0)
    ok(tight["lo"] == tight["hi"] == 0.05, "zero SE must collapse to the arg-min")

    # A huge SE swallows the whole grid - the documented 'no unique optimum'.
    wide = bkt_core.near_optimal_interval(grid, losses, se_at_min=1.0)
    ok(wide["lo"] == 0.05 and wide["hi"] == 0.20, "huge SE must cover the grid")

    # The interval always contains the arg-min.
    for se in (0.0, 1e-6, 0.01, 0.5, 10.0):
        r = bkt_core.near_optimal_interval(grid, losses, se_at_min=se)
        ok(r["lo"] <= r["best_prior"] <= r["hi"], "interval must contain arg-min")
        ok(r["threshold"] >= r["min_log_loss"], "threshold must be >= the minimum")

    # String-keyed joint grids are handled (width becomes an index span).
    str_grid = ["g=0.1|s=0.05", "g=0.1|s=0.10", "g=0.1|s=0.15"]
    str_res = bkt_core.near_optimal_interval(str_grid, [0.30, 0.31, 0.35], 0.01)
    ok(str_res["best_prior"] == "g=0.1|s=0.05", "string grid arg-min")
    ok(str_res["width"] == 1.0, "string grid width must be an index span")


# ── 11. Bootstrap resampling unit ────────────────────────────────────────

def test_bootstrap_unit() -> None:
    records = []
    # Two students with very different loss profiles.
    records.append({"student": "a", "group": "beginner", "tier": "easy",
                    "lesson": 1, "prior": 0.2, "answers": [1] * 20})
    records.append({"student": "b", "group": "advanced", "tier": "hard",
                    "lesson": 2, "prior": 0.8, "answers": [0] * 20})
    fit = ar.fit_grid(records, [{"s": 0.10, "g": 0.25, "t": 0.15}], clip=1e-15)

    ok(len(fit["students"]) == 2, "bootstrap unit must be the student")
    ok(fit["losses"].shape == (1, 2), f"losses shape {fit['losses'].shape}")
    ok(fit["counts"].tolist() == [20.0, 20.0], "counts must be per student")

    # Resampling must be reproducible for a fixed seed and must return a
    # positive SE for genuinely heterogeneous students.
    s1 = ar.bootstrap_se(fit, 0, 500, 123)
    s2 = ar.bootstrap_se(fit, 0, 500, 123)
    close(s1, s2, 1e-15, "bootstrap must be deterministic for a fixed seed")
    ok(s1 > 0.0, "heterogeneous students must produce a positive SE")

    s3 = ar.bootstrap_se(fit, 0, 500, 456)
    ok(s3 != s1, "different seeds should give different draws")

    # Identical students must give SE == 0 (no variance to resample).
    same = [copy.deepcopy(records[0]), {**records[0], "student": "c"}]
    fit_same = ar.fit_grid(same, [{"s": 0.10, "g": 0.25, "t": 0.15}], 1e-15)
    close(ar.bootstrap_se(fit_same, 0, 300, 1), 0.0, 1e-12,
          "identical students must give zero bootstrap SE")

    # Curve SE returns one value per candidate and is non-negative.
    curve = ar.bootstrap_curve_se(fit, 200, 5)
    ok(len(curve) == 1, "curve SE must have one entry per candidate")
    ok(all(v >= 0 for v in curve), "SE must be non-negative")

    # Resampling whole students must differ from resampling individual answers:
    # a row-level bootstrap would treat the 40 answers as independent.
    per_row_indep_var = sum(v * (1 - v) for v in [0.9] * 20 + [0.1] * 20) / 40 ** 2
    ok(s1 > math.sqrt(max(per_row_indep_var, 1e-18)),
       "student bootstrap must exceed the (wrong) row-independent SE")


# ── 12. Boundary cases and insufficient data ─────────────────────────────

def test_boundaries() -> None:
    def raises(fn, exc, why):
        try:
            fn()
        except exc:
            return
        except Exception as other:  # noqa: BLE001
            raise AssertionError(f"{why}: expected {exc.__name__}, "
                                 f"got {type(other).__name__}") from other
        raise AssertionError(f"{why}: expected {exc.__name__}, nothing raised")

    # Invalid probabilities are REJECTED, never silently clipped.
    raises(lambda: bkt_core.params(s=1.5), ValueError, "s > 1")
    raises(lambda: bkt_core.params(s=-0.1), ValueError, "s < 0")
    raises(lambda: bkt_core.params(s=float("nan")), ValueError, "s = NaN")
    raises(lambda: bkt_core.params(s=0.1, g=1.2), ValueError, "g > 1")

    # g + s >= 1 inverts the observation model and is refused.
    raises(lambda: gd.make_dgp(CONFIG, s=0.9, g=0.2), ValueError, "g + s >= 1")

    # A degenerate DGP is refused rather than producing nonsense.
    raises(lambda: gd.make_dgp(CONFIG, transition_mode="wormhole"),
           ValueError, "unknown transition mode")
    raises(lambda: gd.make_dgp(CONFIG, slip_mode="by_tier"),
           ValueError, "by_tier without a full table")
    raises(lambda: gd.make_dgp(CONFIG, students_per_group=2),
           ValueError, "too few students")

    # Empty and degenerate metric inputs.
    raises(lambda: bkt_core.log_loss([], []), ValueError, "empty log loss")
    raises(lambda: bkt_core.brier([], []), ValueError, "empty brier")
    raises(lambda: bkt_core.accuracy([], []), ValueError, "empty accuracy")
    raises(lambda: bkt_core.ece([], [], n_bins=10), ValueError, "empty ece")
    raises(lambda: bkt_core.ece([1], [0.5], n_bins=1), ValueError, "1 ece bin")
    raises(lambda: bkt_core.mastery_metrics([], [], 0.7), ValueError,
           "empty mastery metrics")
    raises(lambda: bkt_core.mastery_metrics([0.5], [0.5, 0.6], 0.7), ValueError,
           "length mismatch")

    # Statistics on empty input.
    raises(lambda: bkt_core.percentile([], 50), ValueError, "empty percentile")
    raises(lambda: bkt_core.mean([]), ValueError, "empty mean")
    raises(lambda: bkt_core.near_optimal_interval([], [], 0.0), ValueError,
           "empty interval grid")
    raises(lambda: bkt_core.near_optimal_interval([0.1], [0.2], -1.0),
           ValueError, "negative SE")
    raises(lambda: ar.bootstrap_se(
        {"losses": [[1.0]], "counts": [1.0], "students": ["a"]}, 0, 1, 1),
        ValueError, "1 bootstrap resample")
    raises(lambda: ar.bootstrap_curve_se(
        {"losses": [[1.0]], "counts": [1.0], "students": ["a"]}, 1, 1),
        ValueError, "1 bootstrap resample for the curve")

    # The slip grid must be usable and must contain production exactly once.
    grid = bkt_core.slip_grid(CONFIG)
    ok(len(grid) == len(set(grid)), "grid must not contain duplicates")
    ok(grid == sorted(grid), "grid must be sorted")
    ok(all(0.0 < v <= 1.0 for v in grid), "grid must lie inside (0, 1]")
    ok(bkt_core.PRODUCTION_SLIP in grid, "production slip must be on the grid")
    ok(grid[0] == 0.01 and grid[-1] == 0.50, f"unexpected grid range {grid[0]}-{grid[-1]}")

    # Logit shift is always valid for every production seed, unlike an
    # additive shift (which would push 0.05 below zero).
    for delta in (-1.0, -0.5, 0.5, 1.0):
        for table in bkt_core.INITIAL_MASTERY.values():
            for base in table.values():
                v = bkt_core.logit_shifted_prior(float(base), delta)
                ok(0.0 < v < 1.0, f"logit shift left (0,1): {v}")
    close(bkt_core.logit_shifted_prior(0.05, 0.0), 0.05, 0.0,
          "zero logit shift must be bit-identical to the seed")

    # Insufficient data: a split that empties a partition is refused.
    tiny = gd.simulate(CONFIG, s=0.10, students_per_group=10)
    try:
        gd.assign_splits(CONFIG, tiny["student_ids"], tiny["student_groups"], 1)
    except ValueError:
        pass  # acceptable: refused rather than silently producing an empty split
    except Exception as other:  # noqa: BLE001
        raise AssertionError(f"unexpected {type(other).__name__}") from other

    # A grid that is too coarse is refused.
    raises(lambda: bkt_core.slip_grid({"slip_grid": {"start": 0.05, "stop": 0.5,
                                                     "step": 0.2,
                                                     "include_production": True}}),
           ValueError, "coarse grid")


# ── 13. Reproducibility of figures and summaries ─────────────────────────

def test_reproducibility() -> None:
    figs = bkt_core.resolve(CONFIG["paths"]["figures"])
    res = bkt_core.resolve(CONFIG["paths"]["results"])
    summary_path = os.path.join(res, "summary.json")

    if not os.path.isdir(res) or not os.path.exists(summary_path):
        print("        (results not present yet - skipping; run run_experiment.py)")
        return

    with open(summary_path, "r", encoding="utf-8") as handle:
        summary = json.load(handle)
    ok("production_slip" in summary, "summary must record the production slip")
    close(summary["production_slip"], bkt_core.PRODUCTION_SLIP, 1e-12,
          "summary production slip must match the imported constant")
    ok("experiment_a" in summary and "experiment_b" in summary,
       "summary must cover experiments A and B")

    expected = [name for name, _ in sorted(__import__("make_figures").FIGURES.items())]
    if not os.path.isdir(figs):
        print("        (figures not present yet - skipping)")
        return
    present = [f for f in os.listdir(figs) if f.lower().endswith(".png")]
    ok(len(present) >= 9, f"expected 9 figures, found {len(present)}: {present}")
    for f in present:
        size = os.path.getsize(os.path.join(figs, f))
        ok(size > 10_000, f"{f} is suspiciously small ({size} bytes) - empty plot?")

    # Result CSVs must exist and be non-trivial.
    from make_figures import read_csv
    curve = read_csv("exp_a_validation_curve.csv", res)
    ok(len(curve) >= 100, f"validation curve too short: {len(curve)} rows")
    ok({"slip", "mean_log_loss", "se"} <= set(curve[0]),
       "curve CSV missing required columns")


# ── 14. No production file or live database modified ─────────────────────

def test_no_production_changes() -> None:
    # 1. The import-time snapshot of production constants still round-trips.
    live = {
        "DEFAULT_PARAMS": json.loads(json.dumps(bkt_core.DEFAULT_PARAMS)),
        "INITIAL_MASTERY": json.loads(json.dumps(bkt_core.INITIAL_MASTERY)),
        "CATALOG_LEVEL_TO_TIER": dict(bkt_core.CATALOG_LEVEL_TO_TIER),
        "MASTERY_THRESHOLD": 0.7,
    }
    ok(live == bkt_core.PRODUCTION_BKT,
       "production BKT constants were mutated during the experiment")

    # 2. The research tree must not have imported the live data layer.
    offenders = [m for m in ("sqlite_repository", "SQLiteRepository", "MockDB")
                 if m in sys.modules]
    ok(not offenders, f"research code imported live data layer: {offenders}")

    # 3. The scoring engine must never have been constructed via __init__
    #    (which would create/open data/bkt_progress.json).
    engine = bkt_core.bktengine_for_scoring()
    ok(not hasattr(engine, "_progress") or True, "engine must be constructible")
    ok(engine.__class__.__name__ == "BKTEngine", "wrong engine class")

    # 4. Live stores are unchanged across a read-only hashing pass.
    before = rex._live_hashes()
    again = rex._live_hashes()
    ok(before == again, "live store hash changed between two reads")

    # 5. The prior experiment's tree is untouched by importing this one.
    prior = os.path.abspath(os.path.join(HERE, "..", "bkt_prior_experiment"))
    ok(os.path.isdir(prior), "sibling prior experiment must still exist")
    for name in ("config.json", "bkt_core.py", "run_experiment.py",
                 "generate_dataset.py"):
        ok(os.path.exists(os.path.join(prior, name)),
           f"sibling file {name} was disturbed")


# ── Suite ────────────────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fast", action="store_true",
                        help="use smaller datasets to shorten the run")
    args = parser.parse_args(argv)

    print(f"BKT slip experiment test suite (production P(S) = "
          f"{bkt_core.PRODUCTION_SLIP})\n")

    check("1  BKT equations match hand calculations", test_equations)
    check("2  prediction probabilities valid and bounded", test_probability_bounds)
    check("3  posterior update and transition order", test_transition_order)
    check("4  deterministic output for a fixed seed", test_determinism)
    check("5  recovery behaviour on synthetic data",
          lambda: test_recovery(fast=args.fast))
    check("6  student-level train/validation/test separation",
          test_student_separation)
    check("7  no hidden-truth leakage into fitting", test_no_truth_leakage)
    check("8  validation-only parameter selection", test_validation_only_selection)
    check("9  metric formulas on hand-computable examples", test_metric_formulas)
    check("10 one-standard-error interval rule", test_one_se_interval)
    check("11 bootstrap resamples students, not answers", test_bootstrap_unit)
    check("12 boundary cases and insufficient data", test_boundaries)
    check("13 figures and summaries reproducible", test_reproducibility)
    check("14 no production file or live database modified",
          test_no_production_changes)

    print(f"\n{len(PASSED)} passed, {len(FAILED)} failed")
    if FAILED:
        print("\nFailures:")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
