#!/usr/bin/env python
"""
Synthetic dataset generator for the BKT slip-probability experiment.

What is simulated
-----------------
For every synthetic learner we draw a *hidden* initial mastery per lesson, then
generate a chronological stream of correct/incorrect answers:

    theta_1      ~ Beta(alpha, beta)                  # hidden initial mastery
    p(correct)   = theta_n * (1 - s) + (1 - theta_n) * g
    y_n          ~ Bernoulli(p(correct))
    theta_{n+1}  = theta_n + (1 - theta_n) * t

`s` (slip), `g` (guess) and `t` (learning) are all configurable; the default is
the production parameterisation (0.10 / 0.25 / 0.15).  Slip may additionally be
made to VARY by difficulty tier or by learner proficiency group, which is what
Experiment D uses to test the "one slip rate for everyone" assumption.

Answers are NEVER assigned from a proficiency label - the label only selects
which *distribution* of hidden mastery a learner is drawn from.

Two output files, deliberately separated:

    observations.csv   - observed fields only.  This is the ONLY file the
                         optimizer and scorer may read.
    ground_truth.csv   - the hidden mastery theta at EVERY attempt index, plus
                         the generating parameters.  Used solely for the
                         clearly-labelled simulation-only mastery metrics and
                         the oracle reference.

Per-attempt hidden theta is recorded (unlike the sibling experiment, which
stored only initial/final) because slip's effect on *mastery estimation* has to
be judged against the hidden state at the same index.

Usage
-----
    python generate_dataset.py --name expA_primary --write
    python generate_dataset.py --name expB_s030 --dgp-s 0.30 --write
    python generate_dataset.py --list-checksums

Exit status 0 on success, 1 on any validation failure.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bkt_core  # noqa: E402

OBS_COLUMNS = [
    "student_id",
    "proficiency_group",
    "split",
    "lesson_id",
    "skill_id",
    "tier",
    "attempt_index",
    "correct",
]

TRUTH_COLUMNS = [
    "student_id",
    "proficiency_group",
    "lesson_id",
    "tier",
    "attempt_index",
    "hidden_mastery",
    "dgp_s",
    "dgp_g",
    "dgp_t",
    "group_tier_mean",
]

SPLITS = ("train", "validation", "test")

# Guard rails: reject a Beta parameterisation that would put mass outside the
# range where "a probability of knowing" is meaningful.
THETA_MIN, THETA_MAX = 0.001, 0.999

_SLIP_MODES = ("constant", "by_tier", "by_group")

# Two genuinely different ways a learner's hidden state can evolve.  The choice
# matters enormously for slip recovery, so both are reported:
#
#   "deterministic"  theta grows by theta <- theta + (1-theta)*t REGARDLESS of
#                    whether the answer was correct.  This is the model the
#                    sibling prior experiment uses.  It is structurally
#                    MISSPECIFIED for BKT: BKT conditions the next belief on the
#                    observed answer, whereas this generator does not.  Because
#                    slip is exactly the knob that damps answer-conditioning,
#                    any slip fitted here absorbs that structural mismatch.
#
#   "bkt_binary"     The canonical BKT generative process (the HMM BKT is the
#                    exact filter for):
#                        Z_1     ~ Bernoulli(l0)          # binary latent state
#                        y | Z   : P(correct|Z=1)=1-s, P(correct|Z=0)=g
#                        Z_{n+1} = Z_n OR Bernoulli(t)    # learning
#                    Here BKT with the true (s, g, t, l0) IS the correct model,
#                    so recovery of the generating slip is a fair test of H3.
#                    Hidden mastery labels are the actual binary Z_n in {0,1}.
_TRANSITION_MODES = ("deterministic", "bkt_binary")


# ── Data-generating specification ────────────────────────────────────────

def make_dgp(config: Dict, **overrides) -> Dict:
    """Build a validated DGP specification.

    Every field can be overridden by keyword; anything left alone falls back to
    ``config["dgp"]``.  Raises on any invalid value rather than clipping.
    """
    base = dict(config["dgp"])
    base.pop("comment", None)
    base.pop("observation_model", None)
    base.pop("mean_mode", None)
    base.pop("learning_depends_on_correctness", None)
    base.pop("transition_mode_note", None)

    dgp = {
        "s": float(overrides.get("s", base.get("s", 0.10))),
        "g": float(overrides.get("g", base.get("g", 0.25))),
        "t": float(overrides.get("t", base.get("t", 0.15))),
        "within_group_sd": float(overrides.get("within_group_sd", base.get("within_group_sd", 0.15))),
        "logit_shift": float(overrides.get("logit_shift", base.get("logit_shift", 0.0))),
        "slip_mode": str(overrides.get("slip_mode", "constant")),
        "slip_values": dict(overrides.get("slip_values", {})),
        "transition_mode": str(overrides.get(
            "transition_mode", base.get("transition_mode", "deterministic"))),
        "seed": int(overrides.get("seed", config["seed"])),
        "students_per_group": int(overrides.get(
            "students_per_group", config["population"]["students_per_group"])),
        "lessons_per_student": int(overrides.get(
            "lessons_per_student", config["population"]["lessons_per_student"])),
        "questions_per_lesson": int(overrides.get(
            "questions_per_lesson", config["population"]["questions_per_lesson"])),
    }

    for name in ("s", "g", "t"):
        v = dgp[name]
        if not (0.0 <= v <= 1.0) or math.isnan(v):
            raise ValueError(f"dgp {name}={v!r} is not a valid probability")
    if dgp["g"] + dgp["s"] >= 1.0:
        raise ValueError(
            "dgp g + s must be < 1, otherwise the observation model inverts")
    if dgp["slip_mode"] not in _SLIP_MODES:
        raise ValueError(f"slip_mode must be one of {_SLIP_MODES}, got {dgp['slip_mode']!r}")
    if dgp["transition_mode"] not in _TRANSITION_MODES:
        raise ValueError(
            f"transition_mode must be one of {_TRANSITION_MODES}, "
            f"got {dgp['transition_mode']!r}")
    if dgp["within_group_sd"] <= 0:
        raise ValueError("within_group_sd must be positive")
    if dgp["students_per_group"] < 10:
        raise ValueError("students_per_group must be at least 10")
    if dgp["questions_per_lesson"] < 1:
        raise ValueError("questions_per_lesson must be >= 1")

    # Validate the slip lookup table matches the declared mode.
    values = dgp["slip_values"]
    if dgp["slip_mode"] == "constant":
        v = float(values.get("constant", dgp["s"]))
        if not (0.0 <= v < 1.0):
            raise ValueError(f"constant slip {v!r} out of range")
        dgp["slip_values"] = {"constant": v}
    elif dgp["slip_mode"] == "by_tier":
        missing = [t for t in bkt_core.DIFFICULTY_TIERS if t not in values]
        if missing:
            raise ValueError(f"slip_by_tier missing tiers: {missing}")
        for t in bkt_core.DIFFICULTY_TIERS:
            if not (0.0 <= float(values[t]) < 1.0):
                raise ValueError(f"slip for tier {t} out of range")
        dgp["slip_values"] = {t: float(values[t]) for t in bkt_core.DIFFICULTY_TIERS}
    else:  # by_group
        missing = [g for g in bkt_core.groups() if g not in values]
        if missing:
            raise ValueError(f"slip_by_group missing groups: {missing}")
        for g in bkt_core.groups():
            if not (0.0 <= float(values[g]) < 1.0):
                raise ValueError(f"slip for group {g} out of range")
        dgp["slip_values"] = {g: float(values[g]) for g in bkt_core.groups()}

    # Slip must stay strictly below 1 for every cell, and g+s<1 must hold for
    # the worst combination, otherwise the model inverts for that subgroup.
    worst_slip = max(dgp["slip_values"].values())
    if dgp["g"] + worst_slip >= 1.0:
        raise ValueError(
            f"g + max(slip) = {dgp['g']} + {worst_slip} must be < 1")

    # Reject a logit shift that would push any production seed out of (0, 1).
    if dgp["logit_shift"] != 0.0:
        for group, table in bkt_core.INITIAL_MASTERY.items():
            for tier, value in table.items():
                bkt_core.logit_shifted_prior(float(value), dgp["logit_shift"])

    if not (1 <= dgp["lessons_per_student"] <= len(bkt_core.catalog())):
        raise ValueError("lessons_per_student out of range")

    return dgp


def slip_for(dgp: Dict, group: str, tier: str) -> float:
    """The generating slip for a (group, tier) cell."""
    mode = dgp["slip_mode"]
    if mode == "constant":
        return float(dgp["slip_values"]["constant"])
    if mode == "by_tier":
        return float(dgp["slip_values"][tier])
    return float(dgp["slip_values"][group])


# ── Hidden mastery means ─────────────────────────────────────────────────

def group_tier_means(config: Dict, logit_shift: float = 0.0) -> Dict[str, Dict[str, float]]:
    """Hidden population means mu[group][tier], derived from production seeds.

    Using the production `INITIAL_MASTERY` table as the mean is the natural null
    hypothesis for "is the production slip plausible?" - it assumes the onboarding
    seeds are unbiased population means.  `logit_shift` applies the Experiment-C
    misspecification knob (offset in logit space, always valid for every cell).
    """
    base = {
        g: {t: float(v) for t, v in table.items()}
        for g, table in bkt_core.INITIAL_MASTERY.items()
    }
    if logit_shift == 0.0:
        return base
    return {
        g: {t: bkt_core.logit_shifted_prior(v, logit_shift) for t, v in table.items()}
        for g, table in base.items()
    }


def beta_params(mean: float, sd: float) -> Tuple[float, float]:
    """Method-of-moments Beta(alpha, beta) for a target (mean, sd).

    The requested sd is clamped when it exceeds the largest sd a Beta on
    [0,1] can have at that mean, so the generator cannot emit an invalid
    parameterisation instead of failing silently.
    """
    m = min(max(float(mean), THETA_MIN), THETA_MAX)
    max_sd = math.sqrt(m * (1.0 - m))
    sigma = min(max(float(sd), 1e-6), max_sd * 0.99)
    var = sigma * sigma
    kappa = (m * (1.0 - m)) / var - 1.0
    if kappa <= 0:
        kappa = 1e-6
    return max(m * kappa, 1e-6), max((1.0 - m) * kappa, 1e-6)


# ── Sampling helpers ─────────────────────────────────────────────────────

def sample_lessons(rng, catalog: Sequence[Dict], own_tier: str, k: int,
                   own_weight: float) -> List[int]:
    """Pick `k` DISTINCT lesson ids, upweighting the learner's own tier."""
    ids = [int(l["id"]) for l in catalog]
    tiers = [bkt_core.tier_of_lesson(i) for i in ids]
    weights = np.array([own_weight if t == own_tier else 1.0 for t in tiers])
    weights = weights / weights.sum()
    if k >= len(ids):
        chosen = list(ids)
        rng.shuffle(chosen)
        return chosen
    picked = rng.choice(len(ids), size=k, replace=False, p=weights)
    return [ids[int(i)] for i in sorted(picked)]


def assign_splits(config: Dict, student_ids: Sequence[str],
                  groups: Sequence[str], seed: int) -> Dict[str, str]:
    """Stratified, student-level split.  No student can appear in two splits."""
    spec = config["split"]
    fractions = {
        "train": float(spec["train"]),
        "validation": float(spec["validation"]),
        "test": float(spec["test"]),
    }
    if abs(sum(fractions.values()) - 1.0) > 1e-9:
        raise ValueError("split fractions must sum to 1")

    mapping: Dict[str, str] = {}
    for group in sorted(set(groups)):
        members = [sid for sid, g in zip(student_ids, groups) if g == group]
        order = np.random.default_rng([seed, 101, sum(map(ord, group))])
        shuffled = list(members)
        order.shuffle(shuffled)
        n = len(shuffled)
        n_train = min(int(round(fractions["train"] * n)), n)
        n_val = min(int(round(fractions["validation"] * n)), n - n_train)
        n_test = n - n_train - n_val
        if min(n_train, n_val, n_test) <= 0:
            raise ValueError(f"split leaves an empty partition for group {group}")
        for sid in shuffled[:n_train]:
            mapping[sid] = "train"
        for sid in shuffled[n_train:n_train + n_val]:
            mapping[sid] = "validation"
        for sid in shuffled[n_train + n_val:]:
            mapping[sid] = "test"
    return mapping


_PREFIXES = {"beginner": "beg", "intermediate": "int", "advanced": "adv"}


def _own_tier_for_group(group: str) -> str:
    return bkt_core.CATALOG_LEVEL_TO_TIER[group]


# ── Simulation ───────────────────────────────────────────────────────────

def simulate(config: Dict, dgp: Optional[Dict] = None, **overrides) -> Dict:
    """Build one population, its observations and its hidden truth in memory."""
    if dgp is None:
        dgp = make_dgp(config, **overrides)

    catalog = bkt_core.catalog()
    groups = list(config["population"]["groups"])
    per_group = dgp["students_per_group"]
    k_lessons = dgp["lessons_per_student"]
    q_per_lesson = dgp["questions_per_lesson"]
    own_weight = float(config["population"]["own_tier_sampling_weight"])

    means = group_tier_means(config, dgp["logit_shift"])
    sd = dgp["within_group_sd"]
    rng = np.random.default_rng(dgp["seed"])

    student_ids: List[str] = []
    student_groups: List[str] = []
    for group in groups:
        prefix = _PREFIXES.get(group, group[:3])
        for i in range(per_group):
            student_ids.append(f"{prefix}_{i:05d}")
            student_groups.append(group)

    splits = assign_splits(config, student_ids, student_groups, dgp["seed"])

    observations: List[List] = []
    truth: List[List] = []
    lessons_by_student: Dict[str, List[int]] = {}

    for sid, group in zip(student_ids, student_groups):
        own_tier = _own_tier_for_group(group)
        chosen = sample_lessons(rng, catalog, own_tier, k_lessons, own_weight)
        lessons_by_student[sid] = chosen

        for lesson_id in chosen:
            tier = bkt_core.tier_of_lesson(lesson_id)
            mu = means[group][tier]
            s_cell = slip_for(dgp, group, tier)

            alpha, beta = beta_params(mu, sd)
            mode = dgp["transition_mode"]

            if mode == "bkt_binary":
                # Canonical BKT HMM: binary latent state Z in {0, 1}.
                z = 1 if rng.random() < mu else 0
            else:
                theta = min(max(float(rng.beta(alpha, beta)), THETA_MIN), THETA_MAX)

            for n in range(1, q_per_lesson + 1):
                if mode == "bkt_binary":
                    # P(correct | Z=1) = 1 - s ; P(correct | Z=0) = g
                    p_correct = (1.0 - s_cell) if z else dgp["g"]
                    correct = 1 if rng.random() < p_correct else 0
                    # Hidden truth is the actual binary state Z_n.
                    hidden_state = float(z)
                else:
                    p_correct = theta * (1.0 - s_cell) + (1.0 - theta) * dgp["g"]
                    p_correct = min(max(p_correct, 0.0), 1.0)
                    correct = 1 if rng.random() < p_correct else 0
                    hidden_state = theta

                observations.append([
                    sid, group, splits[sid], lesson_id, lesson_id, tier, n, correct,
                ])
                truth.append([
                    sid, group, lesson_id, tier, n,
                    round(hidden_state, 10),
                    round(s_cell, 10),
                    dgp["g"], dgp["t"], round(mu, 10),
                ])

                if mode == "bkt_binary":
                    # Learning transition: once mastered, always mastered.
                    if not z and rng.random() < dgp["t"]:
                        z = 1
                else:
                    theta = min(max(theta + (1.0 - theta) * dgp["t"], THETA_MIN), THETA_MAX)

    return {
        "dgp": dgp,
        "observations": observations,
        "truth": truth,
        "student_ids": student_ids,
        "student_groups": student_groups,
        "splits": splits,
        "lessons_by_student": lessons_by_student,
        "means": means,
    }


# ── Validation ───────────────────────────────────────────────────────────

def validate(bundle: Dict, config: Dict) -> Dict:
    """Schema / distribution / leakage checks.  Raises on any failure."""
    obs = bundle["observations"]
    truth = bundle["truth"]
    splits = bundle["splits"]
    catalog_ids = {int(l["id"]) for l in bkt_core.catalog()}
    problems: List[str] = []

    if not obs:
        problems.append("no observations generated")

    valid_groups = set(config["population"]["groups"])
    valid_tiers = set(bkt_core.DIFFICULTY_TIERS)
    per_student_lesson: Dict[Tuple[str, int], List[int]] = {}
    student_split: Dict[str, str] = {}

    for row in obs:
        sid, group, split, lesson_id, skill_id, tier, attempt_index, correct = row
        if group not in valid_groups:
            problems.append(f"bad proficiency_group {group!r}")
        if split not in SPLITS:
            problems.append(f"bad split {split!r}")
        if lesson_id not in catalog_ids:
            problems.append(f"lesson_id {lesson_id} not in catalog")
        if skill_id != lesson_id:
            problems.append(f"skill_id != lesson_id for {sid}/{lesson_id}")
        if tier not in valid_tiers:
            problems.append(f"bad tier {tier!r}")
        if correct not in (0, 1):
            problems.append(f"correct must be 0/1, got {correct!r}")
        if split != splits.get(sid):
            problems.append(f"split disagrees with student map for {sid}")
        if sid in student_split and student_split[sid] != split:
            problems.append(f"student {sid} appears in two splits")
        student_split[sid] = split
        per_student_lesson.setdefault((sid, lesson_id), []).append(attempt_index)
        if len(problems) > 20:
            break

    for (sid, _lesson), indices in per_student_lesson.items():
        if indices != list(range(1, len(indices) + 1)):
            problems.append(f"attempt_index not 1..n for {sid}")
            break

    if any(v is None for row in obs for v in row):
        problems.append("None value in observations")
    if any(v is None for row in truth for v in row):
        problems.append("None value in ground truth")

    # Leakage guard: ground truth must be absent from observation rows.
    if len(obs[0]) != len(OBS_COLUMNS):
        problems.append(
            f"observations have {len(obs[0])} columns, expected {len(OBS_COLUMNS)} "
            "(ground-truth columns must not appear here)")

    # Truth rows must be 1:1 with observations on (student, lesson, attempt).
    if len(truth) != len(obs):
        problems.append(
            f"ground truth has {len(truth)} rows but there are {len(obs)} observations")
    for row in truth:
        if len(row) != len(TRUTH_COLUMNS):
            problems.append(f"ground truth row has {len(row)} columns")
            break
    for row in truth:
        hid = float(row[5])
        if not (0.0 <= hid <= 1.0):
            problems.append(f"hidden mastery {hid} outside [0, 1]")
            break

    # Group sizes.
    student_counts = {g: 0 for g in valid_groups}
    split_counts: Dict[str, Dict[str, int]] = {g: {s: 0 for s in SPLITS}
                                               for g in valid_groups}
    for sid, group in zip(bundle["student_ids"], bundle["student_groups"]):
        student_counts[group] += 1
        split_counts[group][splits[sid]] += 1
    for group in valid_groups:
        expected = dgp_expected_per_group(config, bundle["dgp"])
        if student_counts[group] != expected:
            problems.append(
                f"group {group} has {student_counts[group]} students, expected {expected}")
        for split in SPLITS:
            if split_counts[group][split] <= 0:
                problems.append(f"group {group} has no students in split {split}")

    # Answer distribution: neither degenerate nor group-determined.
    by_group: Dict[str, List[int]] = {}
    for row in obs:
        by_group.setdefault(row[1], []).append(row[7])
    rates = {g: sum(v) / len(v) for g, v in by_group.items()}
    for g, rate in rates.items():
        if not (0.05 < rate < 0.99):
            problems.append(f"answer rate for {g} is degenerate ({rate:.4f})")

    if problems:
        raise ValueError("dataset validation failed:\n  - " + "\n  - ".join(problems))

    return {
        "n_observations": len(obs),
        "n_truth_rows": len(truth),
        "n_students": len(bundle["student_ids"]),
        "students_per_group": student_counts,
        "observations_per_group": {g: len(v) for g, v in by_group.items()},
        "students_per_group_per_split": split_counts,
        "answer_rate_per_group": {g: round(r, 6) for g, r in rates.items()},
        "answer_rate_overall": round(
            sum(sum(v) for v in by_group.values())
            / sum(len(v) for v in by_group.values()), 6),
        "missing_values": 0,
        "catalog_lessons": sorted(catalog_ids),
        "schema_observations": OBS_COLUMNS,
        "schema_ground_truth": TRUTH_COLUMNS,
        "leakage_check": "ground-truth columns absent from observations.csv",
        "dgp": bundle["dgp"],
    }


def dgp_expected_per_group(config: Dict, dgp: Dict) -> int:
    return int(dgp["students_per_group"])


# ── IO ───────────────────────────────────────────────────────────────────

def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_dataset(bundle: Dict, out_dir: str,
                  manifest_extra: Optional[Dict] = None) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    obs_path = os.path.join(out_dir, "observations.csv")
    truth_path = os.path.join(out_dir, "ground_truth.csv")

    with open(obs_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(OBS_COLUMNS)
        writer.writerows(bundle["observations"])

    with open(truth_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(TRUTH_COLUMNS)
        writer.writerows(bundle["truth"])

    manifest = {
        "seed": bundle["dgp"]["seed"],
        "dgp": bundle["dgp"],
        "hidden_group_tier_means": bundle["means"],
        "checksums": {
            "observations.csv": sha256_file(obs_path),
            "ground_truth.csv": sha256_file(truth_path),
        },
        "bytes": {
            "observations.csv": os.path.getsize(obs_path),
            "ground_truth.csv": os.path.getsize(truth_path),
        },
        "n_observations": len(bundle["observations"]),
        "n_students": len(bundle["student_ids"]),
    }
    if manifest_extra:
        manifest["validation"] = manifest_extra

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
    return {"observations": obs_path, "truth": truth_path, "manifest": manifest_path}


def read_dataset(dataset_dir: str) -> Dict:
    """Read a written dataset back, verifying its manifest checksums."""
    manifest_path = os.path.join(dataset_dir, "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    obs_path = os.path.join(dataset_dir, "observations.csv")
    truth_path = os.path.join(dataset_dir, "ground_truth.csv")
    for name, path in (("observations.csv", obs_path), ("ground_truth.csv", truth_path)):
        if sha256_file(path) != manifest["checksums"][name]:
            raise ValueError(f"checksum mismatch for {name} in {dataset_dir}")

    def _load(path, expected_cols):
        with open(path, "r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            if header != expected_cols:
                raise ValueError(f"{path} header {header} != {expected_cols}")
            return [row for row in reader]

    observations = _load(obs_path, OBS_COLUMNS)
    truth = _load(truth_path, TRUTH_COLUMNS)

    for row in observations:
        row[3] = int(row[3]); row[4] = int(row[4]); row[6] = int(row[6]); row[7] = int(row[7])
    for row in truth:
        row[2] = int(row[2]); row[4] = int(row[4]); row[5] = float(row[5])
        row[6] = float(row[6]); row[7] = float(row[7]); row[8] = float(row[8])
        row[9] = float(row[9])

    return {
        "manifest": manifest,
        "dgp": manifest["dgp"],
        "observations": observations,
        "truth": truth,
        "splits": {row[0]: row[2] for row in observations},
    }


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None)
    parser.add_argument("--name", default="primary", help="dataset directory name")
    parser.add_argument("--out", default=None, help="output directory")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--dgp-s", type=float, default=None, dest="dgp_s")
    parser.add_argument("--dgp-g", type=float, default=None, dest="dgp_g")
    parser.add_argument("--dgp-t", type=float, default=None, dest="dgp_t")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--students-per-group", type=int, default=None)
    parser.add_argument("--list-checksums", action="store_true")
    args = parser.parse_args(argv)

    config = bkt_core.load_config(args.config)

    if args.list_checksums:
        root = args.out or bkt_core.resolve(config["paths"]["datasets"])
        if not os.path.isdir(root):
            print(f"(no datasets directory at {root})")
            return 0
        for name in sorted(os.listdir(root)):
            mp = os.path.join(root, name, "manifest.json")
            if os.path.exists(mp):
                with open(mp, encoding="utf-8") as handle:
                    m = json.load(handle)
                print(f"  {name:<28} s={m['dgp']['s']:<6} seed={m['dgp']['seed']:<5} "
                      f"obs={m.get('n_observations')}")
        return 0

    overrides: Dict = {}
    if args.dgp_s is not None:
        overrides["s"] = args.dgp_s
    if args.dgp_g is not None:
        overrides["g"] = args.dgp_g
    if args.dgp_t is not None:
        overrides["t"] = args.dgp_t
    if args.seed is not None:
        overrides["seed"] = args.seed
    if args.students_per_group is not None:
        overrides["students_per_group"] = args.students_per_group

    bundle = simulate(config, **overrides)
    stats = validate(bundle, config)

    print(f"dataset: {args.name}")
    print(f"  dgp          : s={bundle['dgp']['s']} g={bundle['dgp']['g']} "
          f"t={bundle['dgp']['t']} slip_mode={bundle['dgp']['slip_mode']}")
    print(f"  students     : {stats['n_students']}")
    print(f"  observations : {stats['n_observations']}")
    print(f"  answer rate  : {stats['answer_rate_overall']}")
    for g in config["population"]["groups"]:
        print(f"    {g:<13} students={stats['students_per_group'][g]:<5} "
              f"obs={stats['observations_per_group'][g]:<7} "
              f"rate={stats['answer_rate_per_group'][g]}")

    if args.write:
        out_dir = args.out or os.path.join(
            bkt_core.resolve(config["paths"]["datasets"]), args.name)
        paths = write_dataset(bundle, out_dir, stats)
        print("  written:")
        for k, v in paths.items():
            print(f"    {k:<13} {v}")
    else:
        print("  (dry run - pass --write to save)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
