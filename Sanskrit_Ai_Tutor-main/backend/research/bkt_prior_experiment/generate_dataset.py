#!/usr/bin/env python
"""
Synthetic dataset generator for the BKT P(L0) prior experiment.

What is simulated
-----------------
For every synthetic learner we draw a *hidden* initial mastery for each lesson
they attempt, then generate a chronological stream of correct/incorrect answers
with a documented probabilistic observation model:

    theta_1 ~ Beta(alpha, beta)          # hidden initial mastery, per lesson
    p(y = 1) = theta_n * (1 - s) + (1 - theta_n) * g      # guess / slip
    y_n     ~ Bernoulli(p(y = 1))
    theta_{n+1} = theta_n + (1 - theta_n) * t              # learning transition

Answers are NEVER assigned from the proficiency label.  A learner's group only
influences which *distribution* of hidden mastery they are drawn from, exactly
as in a real classroom where the label correlates with, but does not determine,
performance.

Two output files, deliberately separated (see README):

    data/observations.csv   - observed fields only. This is the ONLY file the
                              optimizer and scorer are allowed to read.
    data/ground_truth.csv   - hidden simulation parameters. Used solely for the
                              clearly-labelled simulation-only measures and the
                              optional oracle reference.

Usage
-----
    python generate_dataset.py                       # primary scenario -> data/
    python generate_dataset.py --scenario low_learning --write
    python generate_dataset.py --list-scenarios

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
    "split",
    "lesson_id",
    "skill_id",
    "true_initial_mastery",
    "true_mastery_after_last_attempt",
    "true_group_tier_mean",
    "dgp_t",
    "dgp_g",
    "dgp_s",
    "questions",
]

SPLITS = ("train", "validation", "test")

# Guard rails: reject a Beta parameterisation that would put mass outside the
# range where "a probability of knowing" is meaningful.
THETA_MIN, THETA_MAX = 0.001, 0.999


# ── Scenario resolution ──────────────────────────────────────────────────

def load_scenarios(config: Dict) -> Dict[str, Dict]:
    return {s["id"]: s for s in config["scenarios"]}


def resolve_scenario(config: Dict, scenario_id: Optional[str]) -> Tuple[str, Dict, Dict]:
    """Return ``(scenario_id, spec, effective_population_and_dgp)``.

    ``spec`` is the raw config entry; the third element is the merged view of
    population + DGP settings after the scenario's overrides are applied.
    """
    scenarios = load_scenarios(config)
    if scenario_id in (None, "", "primary"):
        scenario_id = "primary"
    if scenario_id not in scenarios:
        raise KeyError(
            f"unknown scenario {scenario_id!r}; known: {sorted(scenarios)}"
        )
    spec = scenarios[scenario_id]

    pop = dict(config["population"])
    for key in ("lessons_per_student", "questions_per_lesson"):
        if key in spec:
            pop[key] = int(spec[key])

    dgp = dict(config["dgp"])
    for key in ("within_group_sd", "dgp_t", "dgp_g", "dgp_s"):
        if key in spec:
            field = {
                "within_group_sd": "within_group_sd",
                "dgp_t": "t",
                "dgp_g": "g",
                "dgp_s": "s",
            }[key]
            dgp[field] = float(spec[key])

    seed = int(spec.get("seed", config["seed"]))
    mean_mode = str(spec.get("mean_mode", "production"))
    if mean_mode not in config["dgp"]["mean_modes"]:
        raise KeyError(f"unknown mean_mode {mean_mode!r}")
    dgp["mean_mode"] = mean_mode

    return scenario_id, spec, {"seed": seed, "population": pop, "dgp": dgp}


# ── Hidden mastery means ─────────────────────────────────────────────────

def group_tier_means(config: Dict, mean_mode: str) -> Dict[str, Dict[str, float]]:
    """The hidden population means mu[group][tier] for a given mean mode.

    Every mode is *derived from* the production INITIAL_MASTERY table so the
    assumptions stay auditable, and each is documented in config.json under
    `dgp.mean_modes`.  These are assumptions, not measurements.
    """
    base = {
        g: {t: float(v) for t, v in table.items()}
        for g, table in bkt_core.INITIAL_MASTERY.items()
    }
    tiers = list(bkt_core.DIFFICULTY_TIERS)
    groups = list(base)

    if mean_mode == "production":
        return base

    if mean_mode == "group_mean_only":
        return {
            g: {t: sum(base[g][t] for t in tiers) / len(tiers) for t in tiers}
            for g in groups
        }

    if mean_mode == "shifted_up":
        return {
            g: {t: min(0.95, base[g][t] + 0.10) for t in tiers} for g in groups
        }

    if mean_mode == "shifted_down":
        return {
            g: {t: max(0.05, base[g][t] - 0.10) for t in tiers} for g in groups
        }

    if mean_mode == "group_overlap":
        return {
            g: {
                t: sum(base[gg][t] for gg in groups) / len(groups)
                for t in tiers
            }
            for g in groups
        }

    raise KeyError(f"unknown mean_mode {mean_mode!r}")


def beta_params(mean: float, sd: float) -> Tuple[float, float]:
    """Method-of-moments Beta(alpha, beta) for a target (mean, sd).

    The requested sd is clamped when it exceeds the largest sd a Beta on
    [0, 1] can have at that mean, so the generator cannot produce an invalid
    parameterisation instead of failing silently.
    """
    m = min(max(float(mean), THETA_MIN), THETA_MAX)
    max_sd = math.sqrt(m * (1.0 - m))
    sigma = min(max(float(sd), 1e-6), max_sd * 0.99)
    var = sigma * sigma
    kappa = (m * (1.0 - m)) / var - 1.0
    if kappa <= 0:
        kappa = 1e-6
    alpha = max(m * kappa, 1e-6)
    beta = max((1.0 - m) * kappa, 1e-6)
    return alpha, beta


# ── Learner sampling ─────────────────────────────────────────────────────

def sample_lessons(
    rng: np.random.Generator,
    catalog: Sequence[Dict],
    own_tier: str,
    k: int,
    own_weight: float,
) -> List[int]:
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


def assign_splits(config: Dict, student_ids: Sequence[str], groups: Sequence[str]) -> Dict[str, str]:
    """Stratified, student-level split. No student can appear in two splits."""
    spec = config["split"]
    fractions = {
        "train": float(spec["train"]),
        "validation": float(spec["validation"]),
        "test": float(spec["test"]),
    }
    if abs(sum(fractions.values()) - 1.0) > 1e-9:
        raise ValueError("split fractions must sum to 1")

    seed = int(config["seed"])
    mapping: Dict[str, str] = {}
    for group in sorted(set(groups)):
        members = [sid for sid, g in zip(student_ids, groups) if g == group]
        order = np.random.default_rng([seed, 101, sum(map(ord, group))])
        shuffled = list(members)
        order.shuffle(shuffled)
        n = len(shuffled)
        n_train = int(round(fractions["train"] * n))
        n_val = int(round(fractions["validation"] * n))
        n_train = min(n_train, n)
        n_val = min(n_val, n - n_train)
        n_test = n - n_train - n_val
        if min(n_train, n_val, n_test) <= 0:
            raise ValueError(f"split leaves an empty partition for group {group}")
        idx = 0
        for sid in shuffled[idx: idx + n_train]:
            mapping[sid] = "train"
        idx += n_train
        for sid in shuffled[idx: idx + n_val]:
            mapping[sid] = "validation"
        idx += n_val
        for sid in shuffled[idx: idx + n_test]:
            mapping[sid] = "test"
    return mapping


# ── Simulation ───────────────────────────────────────────────────────────

def simulate(config: Dict, scenario_id: Optional[str] = None) -> Dict:
    """Build one scenario's population, observations and hidden truth in memory."""
    scenario_id, spec, env = resolve_scenario(config, scenario_id)
    pop = env["population"]
    dgp = env["dgp"]
    seed = env["seed"]

    catalog = bkt_core.catalog()
    lessons = {int(l["id"]): l for l in catalog}
    groups = list(pop["groups"])
    per_group = int(pop["students_per_group"])
    k_lessons = int(pop["lessons_per_student"])
    q_per_lesson = int(pop["questions_per_lesson"])
    own_weight = float(pop["own_tier_sampling_weight"])

    if per_group < 10:
        raise ValueError("students_per_group must be at least 10")
    if not (1 <= k_lessons <= len(catalog)):
        raise ValueError("lessons_per_student out of range")
    if q_per_lesson < 1:
        raise ValueError("questions_per_lesson must be >= 1")

    means = group_tier_means(config, dgp["mean_mode"])
    sd = float(dgp["within_group_sd"])
    dgp_t = float(dgp["t"])
    dgp_g = float(dgp["g"])
    dgp_s = float(dgp["s"])
    if not (0.0 <= dgp_t <= 1.0 and 0.0 <= dgp_g <= 1.0 and 0.0 <= dgp_s <= 1.0):
        raise ValueError("DGP t/g/s must lie in [0, 1]")
    if dgp_g + dgp_s >= 1.0:
        raise ValueError("DGP g + s must be < 1, otherwise the observation model inverts")

    rng = np.random.default_rng(seed)

    # Student ids are prefixed with the group so they sort deterministically
    # and so a split violation is visible at a glance in the CSV.
    prefixes = {"beginner": "beg", "intermediate": "int", "advanced": "adv"}
    student_ids: List[str] = []
    student_groups: List[str] = []
    for group in groups:
        prefix = prefixes.get(group, group[:3])
        for i in range(per_group):
            student_ids.append(f"{prefix}_{i:05d}")
            student_groups.append(group)

    splits = assign_splits(config, student_ids, student_groups)

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
            alpha, beta = beta_params(mu, sd)
            theta = float(rng.beta(alpha, beta))
            theta = min(max(theta, THETA_MIN), THETA_MAX)
            initial_theta = theta

            split = splits[sid]
            for n in range(1, q_per_lesson + 1):
                p_correct = theta * (1.0 - dgp_s) + (1.0 - theta) * dgp_g
                p_correct = min(max(p_correct, 0.0), 1.0)
                correct = 1 if rng.random() < p_correct else 0
                observations.append([
                    sid, group, split, lesson_id, lesson_id, tier, n, correct,
                ])
                theta = theta + (1.0 - theta) * dgp_t
                theta = min(max(theta, THETA_MIN), THETA_MAX)

            truth.append([
                sid, group, split, lesson_id, lesson_id,
                round(initial_theta, 10),
                round(theta, 10),
                round(mu, 10),
                dgp_t, dgp_g, dgp_s, q_per_lesson,
            ])

    return {
        "scenario_id": scenario_id,
        "spec": spec,
        "env": env,
        "observations": observations,
        "truth": truth,
        "student_ids": student_ids,
        "student_groups": student_groups,
        "splits": splits,
        "lessons_by_student": lessons_by_student,
        "means": means,
    }


def _own_tier_for_group(group: str) -> str:
    """A proficiency group's own tier under the catalog vocabulary."""
    return bkt_core.CATALOG_LEVEL_TO_TIER[group]


# ── Validation ───────────────────────────────────────────────────────────

def validate(bundle: Dict, config: Dict) -> Dict:
    """Schema / distribution / leakage checks. Raises on any failure."""
    obs = bundle["observations"]
    truth = bundle["truth"]
    splits = bundle["splits"]
    catalog_ids = {int(l["id"]) for l in bkt_core.catalog()}

    problems: List[str] = []
    if not obs:
        problems.append("no observations generated")

    valid_groups = set(config["population"]["groups"])
    valid_tiers = set(bkt_core.DIFFICULTY_TIERS)
    seen_students = set()
    per_student_lesson: Dict[Tuple[str, int], List[int]] = {}

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
        seen_students.add(sid)
        per_student_lesson.setdefault((sid, lesson_id), []).append(attempt_index)
        if len(problems) > 20:
            break

    for (sid, lesson_id), indices in per_student_lesson.items():
        if indices != list(range(1, len(indices) + 1)):
            problems.append(f"attempt_index not 1..n for {sid}/{lesson_id}")
            break

    # No student in more than one split.
    student_split = {}
    for row in obs:
        sid, _g, split = row[0], row[1], row[2]
        if sid in student_split and student_split[sid] != split:
            problems.append(f"student {sid} appears in two splits")
            break
        student_split[sid] = split

    # Missing values.
    if any(v is None for row in obs for v in row):
        problems.append("None value in observations")
    if any(v is None for row in truth for v in row):
        problems.append("None value in ground truth")

    # Ground truth must be absent from the observation rows (leakage guard).
    if len(obs[0]) != len(OBS_COLUMNS):
        problems.append(
            f"observations have {len(obs[0])} columns, expected {len(OBS_COLUMNS)} "
            "(ground-truth columns must not appear here)"
        )

    # Group sizes and split counts.
    group_counts: Dict[str, int] = {}
    correct_by_group: Dict[str, List[int]] = {}
    for row in obs:
        group = row[1]
        correct = row[7]
        group_counts[group] = group_counts.get(group, 0) + 1
        correct_by_group.setdefault(group, []).append(correct)

    student_counts = {g: 0 for g in valid_groups}
    student_split_counts: Dict[str, Dict[str, int]] = {g: {s: 0 for s in SPLITS}
                                                       for g in valid_groups}
    for sid, group in zip(bundle["student_ids"], bundle["student_groups"]):
        student_counts[group] += 1
        student_split_counts[group][splits[sid]] += 1

    for group in valid_groups:
        expected = int(config["population"]["students_per_group"])
        if student_counts[group] != expected:
            problems.append(
                f"group {group} has {student_counts[group]} students, expected {expected}"
            )

    # Every group must be represented in every split (otherwise per-group
    # validation curves are undefined).
    for group in valid_groups:
        for split in SPLITS:
            if student_split_counts[group][split] <= 0:
                problems.append(f"group {group} has no students in split {split}")

    # Answer distribution sanity: neither degenerate nor group-determined.
    rates = {g: sum(v) / len(v) for g, v in correct_by_group.items()}
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
        "observations_per_group": group_counts,
        "students_per_group_per_split": student_split_counts,
        "answer_rate_per_group": {g: round(r, 6) for g, r in rates.items()},
        "answer_rate_overall": round(
            sum(sum(v) for v in correct_by_group.values())
            / sum(len(v) for v in correct_by_group.values()), 6),
        "missing_values": 0,
        "catalog_lessons": sorted(catalog_ids),
        "schema_observations": OBS_COLUMNS,
        "schema_ground_truth": TRUTH_COLUMNS,
        "leakage_check": "ground-truth columns absent from observations.csv",
    }


# ── IO ───────────────────────────────────────────────────────────────────

def write_dataset(bundle: Dict, out_dir: str, manifest_extra: Optional[Dict] = None) -> Dict[str, str]:
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

    checksums = {
        "observations.csv": sha256_file(obs_path),
        "ground_truth.csv": sha256_file(truth_path),
    }
    manifest = {
        "scenario_id": bundle["scenario_id"],
        "seed": bundle["env"]["seed"],
        "population": bundle["env"]["population"],
        "dgp": bundle["env"]["dgp"],
        "mean_mode": bundle["env"]["dgp"]["mean_mode"],
        "hidden_group_tier_means": bundle["means"],
        "checksums": checksums,
        "bytes": {
            "observations.csv": os.path.getsize(obs_path),
            "ground_truth.csv": os.path.getsize(truth_path),
        },
    }
    if manifest_extra:
        manifest["validation"] = manifest_extra

    manifest_path = os.path.join(out_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
    return {"observations": obs_path, "truth": truth_path, "manifest": manifest_path}


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None, help="path to config.json")
    parser.add_argument("--scenario", default="primary", help="scenario id")
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--out", default=None, help="output directory")
    parser.add_argument("--write", action="store_true", help="write files")
    args = parser.parse_args(argv)

    config = bkt_core.load_config(args.config)

    if args.list_scenarios:
        for s in config["scenarios"]:
            print(f"  {s['id']:<18} {s['label']}")
        return 0

    scenario_id, _spec, _env = resolve_scenario(config, args.scenario)
    print(f"scenario: {scenario_id}")

    bundle = simulate(config, scenario_id)
    stats = validate(bundle, config)
    print(f"  students     : {stats['n_students']}")
    print(f"  observations : {stats['n_observations']}")
    print(f"  answer rate  : {stats['answer_rate_overall']}")
    for g in config["population"]["groups"]:
        print(f"    {g:<13} students={stats['students_per_group'][g]:<5} "
              f"obs={stats['observations_per_group'][g]:<7} "
              f"rate={stats['answer_rate_per_group'][g]}")

    if args.write:
        out_dir = args.out or (
            bkt_core.resolve("data") if scenario_id == "primary"
            else os.path.join(bkt_core.resolve("data"), "scenarios", scenario_id)
        )
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
