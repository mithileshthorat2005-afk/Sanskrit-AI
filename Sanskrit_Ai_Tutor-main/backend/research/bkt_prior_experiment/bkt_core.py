"""
Shared helpers for the BKT P(L0) prior experiment.

Design rules enforced here:

  * Production constants are IMPORTED, never redefined.  `DEFAULT_PARAMS`,
    `INITIAL_MASTERY`, `CATALOG_LEVEL_TO_TIER` and `difficulty_band` all come
    from `modules.bkt_engine`; this module only reads them.
  * The BKT update used for scoring is the production method
    `BKTEngine.update_mastery` itself, so the experiment cannot drift away from
    the equations the app actually runs.
  * `BKTEngine` is created with `__new__`, deliberately skipping `__init__`.
    `__init__` calls `_ensure_data_file()`, which creates/opens the legacy
    `data/bkt_progress.json`.  Every method the experiment uses
    (`update_mastery`, `get_skill_params`) is pure and never touches `self`, so
    skipping construction guarantees the experiment neither reads nor writes the
    live progress file or the live SQLite database.
  * The research tree never imports `main`, `SQLiteRepository` or `MockDB`.

Run as a module from `backend/research/bkt_prior_experiment/`.
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
    "bktengine_for_scoring",
    "candidate_grid",
    "catalog",
    "difficulty_band",
    "ece",
    "load_config",
    "log_loss",
    "brier",
    "accuracy",
    "params_with_prior",
    "predict_correct",
    "production_prior",
    "run_sequence",
    "tier_of_lesson",
]

# A byte-for-byte snapshot of the production configuration taken at import
# time.  `test_bkt_research.py` compares it against the live module after the
# experiment has run; any mutation of a production constant fails the tests.
PRODUCTION_BKT: Dict = {
    "DEFAULT_PARAMS": json.loads(json.dumps(DEFAULT_PARAMS)),
    "INITIAL_MASTERY": json.loads(json.dumps(INITIAL_MASTERY)),
    "CATALOG_LEVEL_TO_TIER": dict(CATALOG_LEVEL_TO_TIER),
    "MASTERY_THRESHOLD": 0.7,
}

MASTERY_THRESHOLD: float = 0.7

_GROUPS: Tuple[str, ...] = ("beginner", "intermediate", "advanced")

_ENGINE: Optional[BKTEngine] = None


def bktengine_for_scoring() -> BKTEngine:
    """A BKT engine that cannot touch any file.

    `__init__` is skipped on purpose (see the module docstring).  Only the pure
    methods `update_mastery` and `get_skill_params` are used on the result.
    """
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = BKTEngine.__new__(BKTEngine)
    return _ENGINE


# ── Configuration ────────────────────────────────────────────────────────

def load_config(path: Optional[str] = None) -> Dict:
    target = path or os.path.join(HERE, "config.json")
    with open(target, "r", encoding="utf-8") as handle:
        return json.load(handle)


def config_path() -> str:
    return os.path.join(HERE, "config.json")


def resolve(rel_path: str) -> str:
    return os.path.join(HERE, rel_path) if not os.path.isabs(rel_path) else rel_path


# ── Lesson catalog ───────────────────────────────────────────────────────

_CATALOG_CACHE: Optional[List[Dict]] = None


def catalog() -> List[Dict]:
    """The application's real lesson catalog, read straight from lessons.json.

    `AdaptiveLearning.load_lessons()` returns `data["lessons"]` unchanged when
    the file parses, so reading the same key gives an identical list without
    importing the learning engine (whose failure path silently substitutes a
    hardcoded default catalog we never want in an experiment).
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


def tier_of_lesson(lesson_id: int) -> str:
    """Tier of a lesson using the SAME rule production seeding uses."""
    lesson = _lesson_by_id()[int(lesson_id)]
    declared = str(lesson.get("level") or "").strip().lower()
    mapped = CATALOG_LEVEL_TO_TIER.get(declared)
    if mapped is not None:
        return mapped
    return difficulty_band(lesson.get("difficulty", 3))


_LESSON_BY_ID: Optional[Dict[int, Dict]] = None


def _lesson_by_id() -> Dict[int, Dict]:
    global _LESSON_BY_ID
    if _LESSON_BY_ID is None:
        _LESSON_BY_ID = {int(l["id"]): l for l in catalog()}
    return _LESSON_BY_ID


def production_prior(group: str, lesson_id: int) -> float:
    """The exact value production seeds for this (proficiency, lesson)."""
    if group not in INITIAL_MASTERY:
        raise KeyError(f"unknown proficiency group {group!r}")
    return float(INITIAL_MASTERY[group][tier_of_lesson(lesson_id)])


def production_prior_for_tier(group: str, tier: str) -> float:
    if group not in INITIAL_MASTERY:
        raise KeyError(f"unknown proficiency group {group!r}")
    if tier not in INITIAL_MASTERY[group]:
        raise KeyError(f"unknown tier {tier!r}")
    return float(INITIAL_MASTERY[group][tier])


def groups() -> Tuple[str, ...]:
    return _GROUPS


# ── Candidate grid ───────────────────────────────────────────────────────

def candidate_grid(config: Dict) -> List[float]:
    """Sorted, de-duplicated candidate priors over (0, 1).

    Production values are added explicitly and the result asserted, so the
    baseline is guaranteed to be evaluated even if the grid definition changes
    later.
    """
    spec = config["candidate_grid"]
    start, stop, delta = float(spec["start"]), float(spec["stop"]), float(spec["step"])
    if not (0.0 < start < stop < 1.0):
        raise ValueError("candidate grid must lie strictly inside (0, 1)")
    if delta <= 0:
        raise ValueError("candidate step must be positive")

    values: List[float] = []
    count = int(round((stop - start) / delta)) + 1
    for i in range(count):
        value = round(start + i * delta, 10)
        if 0.0 < value < 1.0:
            values.append(value)

    if spec.get("include_production_values", True):
        for table in INITIAL_MASTERY.values():
            for value in table.values():
                if 0.0 < float(value) < 1.0:
                    values.append(round(float(value), 10))

    values = sorted({round(v, 10) for v in values})

    if spec.get("include_production_values", True):
        for group, table in INITIAL_MASTERY.items():
            for tier, value in table.items():
                if round(float(value), 10) not in values:
                    raise AssertionError(
                        f"production prior {group}/{tier}={value} missing from grid"
                    )
    if len(values) < 90:
        raise ValueError("candidate grid is too coarse to be informative")
    return values


def params_with_prior(prior: float) -> Dict:
    """Production BKT parameters with a substituted P(L0).

    t, g and s are copied from DEFAULT_PARAMS untouched - only `l0` differs,
    and `update_mastery` never reads `l0` anyway (it takes the state as an
    argument), so this dict documents intent and is used by `get_skill_params`
    -parity assertions.
    """
    return {
        "l0": float(prior),
        "t": float(DEFAULT_PARAMS["t"]),
        "g": float(DEFAULT_PARAMS["g"]),
        "s": float(DEFAULT_PARAMS["s"]),
    }


def bkt_params() -> Dict:
    """Production t/g/s only - what the update equations actually consume."""
    return {
        "t": float(DEFAULT_PARAMS["t"]),
        "g": float(DEFAULT_PARAMS["g"]),
        "s": float(DEFAULT_PARAMS["s"]),
    }


# ── BKT scoring primitives (production equations) ────────────────────────

def predict_correct(mastery_before: float, params: Dict) -> float:
    """P(correct) computed from mastery BEFORE the answer is incorporated.

    Identical to step 1 of the production `BKTEngine.update_mastery`
    docstring:  p(correct) = L*(1-s) + (1-L)*g.
    """
    L = max(0.0, min(1.0, float(mastery_before)))
    return L * (1.0 - params["s"]) + (1.0 - L) * params["g"]


def step(mastery_before: float, is_correct: bool, params: Dict) -> float:
    """One production BKT update (posterior + learning transition)."""
    return bktengine_for_scoring().update_mastery(mastery_before, bool(is_correct), params)


def run_sequence(
    prior: float,
    answers: Sequence[int],
    params: Optional[Dict] = None,
) -> List[Tuple[float, float, int]]:
    """Walk a chronological answer sequence.

    Returns, per observation, the triple ``(mastery_before, p_correct, y)`` -
    the prediction for answer ``n`` is always derived from the state that
    existed *before* answer ``n`` was seen, never from a state that already
    absorbed it.
    """
    p = params or bkt_params()
    state = max(0.0, min(1.0, float(prior)))
    out: List[Tuple[float, float, int]] = []
    for raw in answers:
        y = 1 if raw else 0
        pred = predict_correct(state, p)
        out.append((state, pred, y))
        state = step(state, bool(y), p)
    return out


def sequence_log_loss(prior: float, answers: Sequence[int], params: Optional[Dict] = None,
                      clip: float = 1e-15) -> float:
    """Total negative log-likelihood of one sequence under a candidate prior."""
    total = 0.0
    for _state, pred, y in run_sequence(prior, answers, params):
        p = min(max(pred, clip), 1.0 - clip)
        total += -(y * math.log(p) + (1 - y) * math.log(1.0 - p))
    return total


# ── Metrics ──────────────────────────────────────────────────────────────

def log_loss(y_true: Sequence[int], y_prob: Sequence[float], clip: float = 1e-15) -> float:
    total = 0.0
    n = 0
    for y, p in zip(y_true, y_prob):
        pc = min(max(float(p), clip), 1.0 - clip)
        total += -(y * math.log(pc) + (1 - y) * math.log(1.0 - pc))
        n += 1
    if n == 0:
        raise ValueError("log_loss needs at least one observation")
    return total / n


def brier(y_true: Sequence[int], y_prob: Sequence[float]) -> float:
    total, n = 0.0, 0
    for y, p in zip(y_true, y_prob):
        total += (float(p) - float(y)) ** 2
        n += 1
    if n == 0:
        raise ValueError("brier needs at least one observation")
    return total / n


def accuracy(y_true: Sequence[int], y_prob: Sequence[float], threshold: float = 0.5) -> float:
    if not len(y_true):
        raise ValueError("accuracy needs at least one observation")
    hits = sum(1 for y, p in zip(y_true, y_prob) if (float(p) >= threshold) == bool(y))
    return hits / len(y_true)


def ece(
    y_true: Sequence[int],
    y_prob: Sequence[float],
    n_bins: int = 10,
) -> Tuple[float, List[Dict]]:
    """Expected calibration error with equal-width bins on [0, 1].

    Returns ``(ece, rows)`` where each row carries the bin's mean predicted
    probability, observed frequency and count - the same rows the reliability
    diagram is drawn from.
    """
    if n_bins < 2:
        raise ValueError("ece needs at least 2 bins")
    if not len(y_true):
        raise ValueError("ece needs at least one observation")

    buckets: List[List[float]] = [[] for _ in range(n_bins)]
    for y, p in zip(y_true, y_prob):
        idx = int(float(p) * n_bins)
        if idx >= n_bins:
            idx = n_bins - 1
        if idx < 0:
            idx = 0
        buckets[idx].append(float(y))

    rows: List[Dict] = []
    total = len(y_true)
    ece_value = 0.0
    for i, members in enumerate(buckets):
        if not members:
            rows.append({
                "bin": i,
                "lo": i / n_bins,
                "hi": (i + 1) / n_bins,
                "mean_predicted": None,
                "observed": None,
                "count": 0,
            })
            continue
        lo, hi = i / n_bins, (i + 1) / n_bins
        mid = (lo + hi) / 2.0
        mean_pred = mid  # equal-width bin midpoint, the value plotted
        observed = sum(members) / len(members)
        rows.append({
            "bin": i,
            "lo": lo,
            "hi": hi,
            "mean_predicted": mean_pred,
            "observed": observed,
            "count": len(members),
        })
        ece_value += (len(members) / total) * abs(observed - mean_pred)
    return ece_value, rows


def metric_bundle(y_true: Sequence[int], y_prob: Sequence[float], config: Dict) -> Dict:
    m = config["metrics"]
    ece_value, _ = ece(y_true, y_prob, n_bins=int(m["ece_bins"]))
    return {
        "log_loss": log_loss(y_true, y_prob, clip=float(m["probability_clip"])),
        "brier": brier(y_true, y_prob),
        "accuracy": accuracy(y_true, y_prob, threshold=float(m["accuracy_threshold"])),
        "ece": ece_value,
        "n_obs": len(y_true),
    }


# ── Statistics helpers ───────────────────────────────────────────────────

def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile, no numpy dependency."""
    if not values:
        raise ValueError("percentile of an empty sequence")
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * (q / 100.0)
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return ordered[low]
    frac = pos - low
    return ordered[low] * (1.0 - frac) + ordered[high] * frac


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    if not vals:
        raise ValueError("mean of an empty sequence")
    return sum(vals) / len(vals)

