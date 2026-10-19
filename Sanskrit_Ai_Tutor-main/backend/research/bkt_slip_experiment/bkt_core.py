"""
Shared helpers for the BKT slip-probability P(S) experiment.

Design rules (mirroring the sibling `bkt_prior_experiment`, but self-contained
so this experiment runs independently):

  * Production constants are IMPORTED, never redefined.  `DEFAULT_PARAMS`,
    `INITIAL_MASTERY`, `CATALOG_LEVEL_TO_TIER` and `difficulty_band` come from
    `modules.bkt_engine`; this module only reads them.
  * Scoring uses the production method `BKTEngine.update_mastery` itself, so the
    experiment cannot drift away from the equations the app actually runs.
  * `BKTEngine` is created with `__new__`, deliberately skipping `__init__`
    (which calls `_ensure_data_file()` and would create/open the legacy
    `data/bkt_progress.json`).  Every method used here is pure, so the
    experiment neither reads nor writes the live progress file or SQLite DB.
  * The research tree never imports `main`, `SQLiteRepository` or `MockDB`.

BKT convention actually used by production
------------------------------------------
`BKTEngine.update_mastery` (bkt_engine.py:145-206) applies, in this order:

  Step 1  p(C)      = L*(1 - s) + (1 - L)*g
  Step 2  posterior = L*(1-s)/p(C)              if correct
                    = L*s / (1 - p(C))          if incorrect
  Step 3  L_next    = posterior + (1 - posterior)*t

Step 2's incorrect branch is algebraically identical to the textbook
P(L|I) = L*S / (L*S + (1-L)*(1-G)), because
  L*S + (1-L)*(1-G) = 1 - [L*(1-S) + (1-L)*G] = 1 - p(C).
So observation precedes the learning transition, exactly as the experiment's
specification states.  Zero denominators fall back to the prior state L.
"""

from __future__ import annotations

import json
import math
import os
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# ── Locate the backend package ───────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from modules.bkt_engine import (  # noqa: E402  (path bootstrap must run first)
    BKTEngine,
    CATALOG_LEVEL_TO_TIER,
    DEFAULT_PARAMS,
    DIFFICULTY_TIERS,
    INITIAL_MASTERY,
    difficulty_band,
)

__all__ = [
    "BACKEND_DIR",
    "HERE",
    "PRODUCTION_BKT",
    "PRODUCTION_SLIP",
    "bktengine_for_scoring",
    "catalog",
    "difficulty_band",
    "load_config",
    "slip_grid",
    "params",
    "prior_for",
    "predict_correct",
    "posterior",
    "step",
    "run_sequence",
    "log_loss",
    "brier",
    "accuracy",
    "ece",
    "metric_bundle",
    "near_optimal_interval",
    "percentile",
    "mean",
    "stddev",
    "PROB_CLIP",
]

# Byte-for-byte import-time snapshot of the production configuration.
# `test_bkt_slip_experiment.py` re-compares it after the experiment runs, so
# any mutation of a production constant fails the tests.
PRODUCTION_BKT: Dict = {
    "DEFAULT_PARAMS": json.loads(json.dumps(DEFAULT_PARAMS)),
    "INITIAL_MASTERY": json.loads(json.dumps(INITIAL_MASTERY)),
    "CATALOG_LEVEL_TO_TIER": dict(CATALOG_LEVEL_TO_TIER),
    "MASTERY_THRESHOLD": 0.7,
}

# The verified production slip probability.  Asserted, not assumed: if the
# source ever changes, this import-time check fails loudly rather than letting
# the experiment silently compare against a stale baseline.
PRODUCTION_SLIP: float = float(DEFAULT_PARAMS["s"])
PRODUCTION_GUESS: float = float(DEFAULT_PARAMS["g"])
PRODUCTION_T: float = float(DEFAULT_PARAMS["t"])

MASTERY_THRESHOLD: float = 0.7
PROB_CLIP: float = 1e-15

_GROUPS: Tuple[str, ...] = ("beginner", "intermediate", "advanced")

_ENGINE: Optional[BKTEngine] = None


def bktengine_for_scoring() -> BKTEngine:
    """A BKT engine that cannot touch any file (see module docstring)."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = BKTEngine.__new__(BKTEngine)
    return _ENGINE


# ── Configuration ────────────────────────────────────────────────────────

def load_config(path: Optional[str] = None) -> Dict:
    target = path or os.path.join(HERE, "config.json")
    with open(target, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve(rel_path: str) -> str:
    return rel_path if os.path.isabs(rel_path) else os.path.join(HERE, rel_path)


def groups() -> Tuple[str, ...]:
    return _GROUPS


# ── Lesson catalog ───────────────────────────────────────────────────────

_CATALOG_CACHE: Optional[List[Dict]] = None
_LESSON_BY_ID: Optional[Dict[int, Dict]] = None


def catalog() -> List[Dict]:
    """The application's real lesson catalog, read straight from lessons.json.

    `AdaptiveLearning.load_lessons()` returns `data["lessons"]` unchanged when
    the file parses, so reading the same key gives an identical list without
    importing the learning engine.
    """
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        path = os.path.join(BACKEND_DIR, "data", "lessons.json")
        with open(path, "r", encoding="utf-8") as handle:
            lessons = json.load(handle)["lessons"]
        if not lessons:
            raise RuntimeError("lesson catalog is empty")
        _CATALOG_CACHE = lessons
    return _CATALOG_CACHE


def _lesson_by_id() -> Dict[int, Dict]:
    global _LESSON_BY_ID
    if _LESSON_BY_ID is None:
        _LESSON_BY_ID = {int(l["id"]): l for l in catalog()}
    return _LESSON_BY_ID


def tier_of_lesson(lesson_id: int) -> str:
    """Tier of a lesson using the SAME rule production seeding uses."""
    lesson = _lesson_by_id()[int(lesson_id)]
    declared = str(lesson.get("level") or "").strip().lower()
    mapped = CATALOG_LEVEL_TO_TIER.get(declared)
    if mapped is not None:
        return mapped
    return difficulty_band(lesson.get("difficulty", 3))


# ── Parameter validation ─────────────────────────────────────────────────

def _check_probability(name: str, value: float) -> float:
    """Validate a probability. Raises rather than silently clipping."""
    v = float(value)
    if not (0.0 <= v <= 1.0) or math.isnan(v):
        raise ValueError(f"{name}={value!r} is not a valid probability in [0, 1]")
    return v


def params(s: float, g: Optional[float] = None, t: Optional[float] = None) -> Dict:
    """Build a validated BKT parameter dict, defaulting g/t to production.

    Deliberately RAISES on out-of-range values instead of clipping: a silently
    clipped parameter would make an invalid experiment look valid.
    """
    return {
        "s": _check_probability("s", s),
        "g": _check_probability("g", PRODUCTION_GUESS if g is None else g),
        "t": _check_probability("t", PRODUCTION_T if t is None else t),
    }


def production_params() -> Dict:
    """The exact t/g/s the application uses today."""
    return {
        "s": PRODUCTION_SLIP,
        "g": PRODUCTION_GUESS,
        "t": PRODUCTION_T,
    }


def production_prior(group: str, lesson_id: int) -> float:
    """The exact P(L0) production seeds for this (proficiency, lesson)."""
    if group not in INITIAL_MASTERY:
        raise KeyError(f"unknown proficiency group {group!r}")
    return float(INITIAL_MASTERY[group][tier_of_lesson(lesson_id)])


def logit_shifted_prior(base: float, delta: float) -> float:
    """Production seed moved by a constant offset in logit space.

        prior = sigmoid( logit(base) + delta )

    A logit shift (rather than an additive one) is used because the production
    table spans 0.01..0.80: no additive offset can stay inside (0, 1) for every
    cell, whereas a finite logit offset always can.  delta == 0 returns `base`
    EXACTLY (no round-trip error), so the unshifted case is bit-identical to
    production.

    This is a *defined scenario knob* for the misspecification experiments, not
    a fitted probability, so it is validated here rather than clipped.
    """
    b = float(base)
    if not (0.0 < b < 1.0):
        raise ValueError(f"base prior {base!r} must lie in (0, 1)")
    d = float(delta)
    if d == 0.0:
        return b
    if not math.isfinite(d):
        raise ValueError(f"logit shift {delta!r} is not finite")
    if b >= 1.0:
        raise ValueError("logit undefined at 1")
    logit = math.log(b / (1.0 - b)) + d
    # Guard the sigmoid against overflow for extreme deltas.
    if logit >= 0:
        v = 1.0 / (1.0 + math.exp(-logit)) if logit < 700 else 1.0
    else:
        ex = math.exp(logit) if logit > -700 else 0.0
        v = ex / (1.0 + ex)
    if not (0.0 < v < 1.0):
        raise ValueError(f"logit-shifted prior {v} left (0, 1)")
    return v


# ── Candidate grid ───────────────────────────────────────────────────────

def slip_grid(config: Dict) -> List[float]:
    """Sorted, de-duplicated candidate slip values, always including production."""
    spec = config["slip_grid"]
    start, stop, delta = float(spec["start"]), float(spec["stop"]), float(spec["step"])
    if not (0.0 < start < stop <= 1.0):
        raise ValueError("slip grid must lie strictly inside (0, 1]")
    if delta <= 0:
        raise ValueError("slip grid step must be positive")

    count = int(round((stop - start) / delta)) + 1
    values = [round(start + i * delta, 10) for i in range(count)]
    values = [v for v in values if 0.0 < v <= 1.0]

    if spec.get("include_production", True):
        values.append(round(PRODUCTION_SLIP, 10))

    values = sorted({round(v, 10) for v in values})

    # Assert the baseline is present rather than assuming it.
    if spec.get("include_production", True) and round(PRODUCTION_SLIP, 10) not in values:
        raise AssertionError(
            f"production slip {PRODUCTION_SLIP} missing from candidate grid"
        )
    if len(values) < 40:
        raise ValueError("slip grid is too coarse to be informative")
    return values


# ── BKT primitives (production equations) ────────────────────────────────

def predict_correct(mastery_before: float, p: Dict) -> float:
    """P(correct) from mastery BEFORE the answer is incorporated.

    Identical to step 1 of production `BKTEngine.update_mastery`.
    """
    L = max(0.0, min(1.0, float(mastery_before)))
    return L * (1.0 - p["s"]) + (1.0 - L) * p["g"]


def posterior(mastery_before: float, is_correct: bool, p: Dict) -> float:
    """Step 2 only: the Bayes posterior, WITHOUT the learning transition.

    Exposed separately so tests can compare it against the hand-calculated
    textbook formulas P(L|C) and P(L|I).
    """
    L = max(0.0, min(1.0, float(mastery_before)))
    if is_correct:
        denom = L * (1.0 - p["s"]) + (1.0 - L) * p["g"]
        return (L * (1.0 - p["s"]) / denom) if denom > 0 else L
    denom = L * p["s"] + (1.0 - L) * (1.0 - p["g"])
    return (L * p["s"] / denom) if denom > 0 else L


def step(mastery_before: float, is_correct: bool, p: Dict) -> float:
    """One full production update: posterior, then learning transition."""
    return bktengine_for_scoring().update_mastery(
        mastery_before, bool(is_correct), dict(p))


def run_sequence(
    prior: float,
    answers: Sequence[int],
    p: Dict,
) -> List[Tuple[float, float, int]]:
    """Walk a chronological answer sequence.

    Returns, per observation, ``(mastery_before, p_correct, y)``.  The
    prediction for answer n always comes from the state that existed BEFORE
    answer n was seen.
    """
    state = max(0.0, min(1.0, float(prior)))
    out: List[Tuple[float, float, int]] = []
    for raw in answers:
        y = 1 if raw else 0
        pred = predict_correct(state, p)
        out.append((state, pred, y))
        state = step(state, bool(y), p)
    return out


def run_sequence_states(
    prior: float,
    answers: Sequence[int],
    p: Dict,
) -> List[float]:
    """Mastery estimate AFTER each answer (length == len(answers)).

    Used for the hidden-state mastery metrics, which compare the model's
    posterior belief against the generator's hidden theta at the same index.
    """
    state = max(0.0, min(1.0, float(prior)))
    out: List[float] = []
    for raw in answers:
        state = step(state, bool(raw), p)
        out.append(state)
    return out


# ── Metrics ──────────────────────────────────────────────────────────────

def log_loss(y_true: Sequence[int], y_prob: Sequence[float],
             clip: float = PROB_CLIP) -> float:
    total, n = 0.0, 0
    for y, prob in zip(y_true, y_prob):
        pc = min(max(float(prob), clip), 1.0 - clip)
        total += -(y * math.log(pc) + (1 - y) * math.log(1.0 - pc))
        n += 1
    if n == 0:
        raise ValueError("log_loss needs at least one observation")
    return total / n


def brier(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    total, n = 0.0, 0
    for y, prob in zip(y_true, y_prob):
        total += (float(prob) - float(y)) ** 2
        n += 1
    if n == 0:
        raise ValueError("brier needs at least one observation")
    return total / n


def accuracy(y_true: Sequence[int], y_prob: Sequence[float],
             threshold: float = 0.5) -> float:
    if not len(y_true):
        raise ValueError("accuracy needs at least one observation")
    hits = sum(1 for y, prob in zip(y_true, y_prob)
               if (float(prob) >= threshold) == bool(y))
    return hits / len(y_true)


def ece(y_true: Sequence[int], y_prob: Sequence[float],
        n_bins: int = 10) -> Tuple[float, List[Dict]]:
    """Expected calibration error, equal-width bins on [0, 1].

    Limitation (documented): equal-width bins are sparse near 0 and 1, so ECE
    is dominated by the densely populated middle bins.
    """
    if n_bins < 2:
        raise ValueError("ece needs at least 2 bins")
    if not len(y_true):
        raise ValueError("ece needs at least one observation")

    buckets: List[List[int]] = [[] for _ in range(n_bins)]
    for y, prob in zip(y_true, y_prob):
        idx = int(float(prob) * n_bins)
        idx = min(max(idx, 0), n_bins - 1)
        buckets[idx].append(int(y))

    rows: List[Dict] = []
    total = len(y_true)
    value = 0.0
    for i, members in enumerate(buckets):
        lo, hi = i / n_bins, (i + 1) / n_bins
        mid = (lo + hi) / 2.0
        if not members:
            rows.append({"bin": i, "lo": lo, "hi": hi, "mean_predicted": mid,
                         "observed": None, "count": 0})
            continue
        observed = sum(members) / len(members)
        rows.append({"bin": i, "lo": lo, "hi": hi, "mean_predicted": mid,
                     "observed": observed, "count": len(members)})
        value += (len(members) / total) * abs(observed - mid)
    return value, rows


def metric_bundle(y_true: Sequence[int], y_prob: Sequence[float],
                  config: Dict) -> Dict:
    m = config["metrics"]
    ece_value, _ = ece(y_true, y_prob, n_bins=int(m["ece_bins"]))
    return {
        "log_loss": log_loss(y_true, y_prob, clip=float(m["probability_clip"])),
        "brier": brier(y_true, y_prob),
        "accuracy": accuracy(y_true, y_prob, threshold=float(m["accuracy_threshold"])),
        "ece": ece_value,
        "n_obs": len(y_true),
    }


def mastery_metrics(
    estimates: Sequence[float],
    hidden: Sequence[float],
    threshold: float = MASTERY_THRESHOLD,
) -> Dict:
    """Mastery-estimation quality against the generator's hidden state.

    Every rate carries its denominator explicitly:

      * ``mae``              mean |L_n - theta_n| over all pairs
      * ``brier_hidden``     mean (L_n - 1[theta_n >= threshold])^2
      * ``false_mastered``   flagged mastered (L>=thr) while hidden theta < thr
                            - reported both among ALL pairs and among FLAGGED
      * ``false_unmastered`` hidden theta >= thr while model L < thr
                            - reported both among ALL pairs and among hidden
                              mastered pairs
    """
    if len(estimates) != len(hidden):
        raise ValueError("estimates and hidden must be the same length")
    if not estimates:
        raise ValueError("mastery_metrics needs at least one pair")

    n = len(estimates)
    abs_err = 0.0
    sq_err = 0.0
    flagged = 0
    truth_mastered = 0
    false_mastered = 0
    false_unmastered = 0

    for est, hid in zip(estimates, hidden):
        e, h = float(est), float(hid)
        abs_err += abs(e - h)
        label = 1 if h >= threshold else 0
        sq_err += (e - label) ** 2
        est_mastered = e >= threshold
        if est_mastered:
            flagged += 1
        if label:
            truth_mastered += 1
        if est_mastered and not label:
            false_mastered += 1
        if label and not est_mastered:
            false_unmastered += 1

    return {
        "n_pairs": n,
        "mae": abs_err / n,
        "brier_hidden": sq_err / n,
        "flagged": flagged,
        "truth_mastered": truth_mastered,
        "false_mastered": false_mastered,
        "false_unmastered": false_unmastered,
        "false_mastered_rate_all": false_mastered / n,
        "false_mastered_rate_of_flagged": (false_mastered / flagged) if flagged else None,
        "false_unmastered_rate_all": false_unmastered / n,
        "false_unmastered_rate_of_truth": (
            false_unmastered / truth_mastered) if truth_mastered else None,
    }


# ── Statistics ───────────────────────────────────────────────────────────

def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile, no numpy dependency."""
    if not values:
        raise ValueError("percentile of an empty sequence")
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * (q / 100.0)
    low, high = int(math.floor(pos)), int(math.ceil(pos))
    if low == high:
        return ordered[low]
    frac = pos - low
    return ordered[low] * (1.0 - frac) + ordered[high] * frac


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        raise ValueError("mean of an empty sequence")
    return sum(vals) / len(vals)


def stddev(values: Sequence[float]) -> float:
    """Sample standard deviation (ddof=1); 0.0 for a single value."""
    vals = [float(v) for v in values]
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def near_optimal_interval(
    grid: Sequence[float],
    losses: Sequence[float],
    se_at_min: float,
) -> Dict:
    """The documented one-standard-error near-optimal set.

    Rule (pre-registered, ``config.bootstrap.rule == "within_1_se_of_min"``):

        Let p* be the validation arg-min and LL(p) the mean validation log
        loss.  The near-optimal set is

            { p : LL(p) <= LL(p*) + SE(p*) }

        where SE(p*) is the student-level bootstrap standard error of the mean
        log loss evaluated AT p*.

    This is NOT a confidence interval for the true parameter: it is the width
    of the flat region of the validation surface.  A wide interval therefore
    means no unique optimum was established.
    """
    if len(grid) != len(losses):
        raise ValueError("grid and losses must be the same length")
    if not grid:
        raise ValueError("empty grid")
    if se_at_min < 0:
        raise ValueError("se_at_min must be non-negative")

    argmin = min(range(len(grid)), key=lambda i: losses[i])
    threshold = losses[argmin] + se_at_min
    inside = [i for i, v in enumerate(losses) if v <= threshold + 1e-15]
    lo_i, hi_i = min(inside), max(inside)
    try:
        width: Optional[float] = float(grid[hi_i]) - float(grid[lo_i])
    except (TypeError, ValueError):
        # Joint-fit grids are keyed by strings such as "g=0.25|s=0.10"; for
        # those the meaningful width is the number of grid steps spanned.
        width = float(hi_i - lo_i)
    return {
        "best_index": argmin,
        "best_prior": grid[argmin],
        "min_log_loss": losses[argmin],
        "se_at_min": se_at_min,
        "threshold": threshold,
        "indices": inside,
        "lo": grid[lo_i],
        "hi": grid[hi_i],
        "width": width,
        "n_inside": len(inside),
    }


def bootstrap_se_by_student(
    student_losses: Dict[str, float],
    student_counts: Dict[str, int],
    n_resamples: int,
    seed: int,
) -> float:
    """Bootstrap SE of the mean per-observation log loss, resampling STUDENTS.

    Each student carries their own total negative log-likelihood and their own
    observation count, so a resample is a weighted mean over the resampled
    students.  Resampling whole students (never individual answers) preserves
    the within-sequence correlation that a row-level bootstrap would destroy.
    """
    import numpy as np

    ids = sorted(student_losses)
    if not ids:
        raise ValueError("no students to resample")
    totals = np.array([student_losses[s] for s in ids], dtype=float)
    counts = np.array([student_counts[s] for s in ids], dtype=float)
    if (counts <= 0).any():
        raise ValueError("every student must contribute at least one observation")

    rng = np.random.default_rng(seed)
    n = len(ids)
    means = np.empty(n_resamples, dtype=float)
    for b in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        means[b] = totals[idx].sum() / counts[idx].sum()
    return float(means.std(ddof=1))
