#!/usr/bin/env python
"""
Tests for the BKT P(L0) prior experiment.

Covers the ten required properties (see README, "Validation and tests"):

   1  the synthetic dataset is reproducible for a fixed seed
   2  labels, lesson ids and attempt sequences are valid
   3  no student's observations leak across train/validation/test
   4  production parameters are loaded, and never modified
   5  the experiment's BKT update matches the production formula exactly
   6  predictions are computed BEFORE the answer they score
   7  the optimizer selects on validation, never on test
   8  near-optimal ranges follow the documented one-standard-error rule
   9  sensitivity scenarios stay separately identified in the outputs
  10  nothing reads or writes the live SQLite DB or legacy progress JSON

The suite is self-contained: it regenerates a small sandbox dataset in a
temporary directory and never touches live application data.

Usage:  python test_bkt_research.py        (exit 0 = all passed, 1 = failures)
"""

from __future__ import annotations

import copy
import csv
import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
from typing import Callable, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

BACKEND_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import bkt_core  # noqa: E402
import generate_dataset as gd  # noqa: E402
import run_experiment as rx  # noqa: E402

RESULTS: List[Tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    suffix = f"  -- {detail}" if detail and not ok else (f"  -- {detail}" if detail else "")
    print(f"  [{mark}] {name}{suffix}")
    return bool(ok)


# ── Helpers ──────────────────────────────────────────────────────────────

def small_config(base: Dict, students: int = 60, lessons: int = 3,
                 questions: int = 5) -> Dict:
    cfg = copy.deepcopy(base)
    cfg["population"]["students_per_group"] = students
    cfg["population"]["lessons_per_student"] = lessons
    cfg["population"]["questions_per_lesson"] = questions
    cfg["bootstrap"]["n_resamples"] = 60
    cfg["bootstrap"]["test_ci_resamples"] = 100
    cfg["scenarios"] = [s for s in cfg["scenarios"]
                        if s["id"] in ("primary", "high_learning", "seed_7")]
    return cfg


def bundle_digest(bundle: Dict) -> str:
    h = hashlib.sha256()
    for row in bundle["observations"]:
        h.update((",".join(str(v) for v in row)).encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


def truth_digest(bundle: Dict) -> str:
    h = hashlib.sha256()
    for row in bundle["truth"]:
        h.update((",".join(str(v) for v in row)).encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()


def fresh_engine():
    """A BKTEngine that cannot create or open any file."""
    return bkt_core.BKTEngine.__new__(bkt_core.BKTEngine)


# ── 1. Reproducibility ───────────────────────────────────────────────────

def t1_reproducibility(base: Dict) -> None:
    print("\n[1] Reproducibility with a fixed seed")
    cfg = small_config(base)
    a = gd.simulate(cfg, "primary")
    b = gd.simulate(cfg, "primary")
    check("same seed -> identical observations", bundle_digest(a) == bundle_digest(b),
          f"{bundle_digest(a)[:16]} vs {bundle_digest(b)[:16]}")
    check("same seed -> identical ground truth", truth_digest(a) == truth_digest(b))

    c = gd.simulate(cfg, "seed_7")
    check("different seed -> different data", bundle_digest(a) != bundle_digest(c))

    # Round-trip through the CSV writer must not change the rows.
    tmp = tempfile.mkdtemp(prefix="bkt_repro_")
    try:
        gd.write_dataset(a, tmp)
        with open(os.path.join(tmp, "observations.csv"), encoding="utf-8",
                  newline="") as handle:
            rows = list(csv.reader(handle))
        header, body = rows[0], rows[1:]
        check("CSV header matches declared schema", header == gd.OBS_COLUMNS)
        expected = [[str(v) for v in row] for row in a["observations"]]
        check("CSV round-trip is lossless", body == expected,
              f"{len(body)} rows")

        # Write the same bundle twice into two directories: byte-identical output.
        tmp2 = tempfile.mkdtemp(prefix="bkt_repro2_")
        try:
            gd.write_dataset(a, tmp2)
            check("CSV output is byte-deterministic across writes",
                  gd.sha256_file(os.path.join(tmp, "observations.csv")) ==
                  gd.sha256_file(os.path.join(tmp2, "observations.csv")),
                  "checksums differ between two writes of the same bundle")
            c2 = gd.simulate(cfg, "primary")
            gd.write_dataset(c2, tmp2)
            check("regenerating from the seed reproduces the same file checksum",
                  gd.sha256_file(os.path.join(tmp, "observations.csv")) ==
                  gd.sha256_file(os.path.join(tmp2, "observations.csv")))
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 2. Schema validity ───────────────────────────────────────────────────

def t2_schema(base: Dict) -> None:
    print("\n[2] Valid labels, lesson ids and observation sequences")
    cfg = small_config(base)
    bundle = gd.simulate(cfg, "primary")
    catalog_ids = {int(l["id"]) for l in bkt_core.catalog()}
    tiers = set(bkt_core.DIFFICULTY_TIERS)
    groups = set(cfg["population"]["groups"])

    bad_correct = [r for r in bundle["observations"] if r[7] not in (0, 1)]
    check("every correct value is 0 or 1", not bad_correct,
          f"{len(bad_correct)} violations")

    bad_lesson = [r for r in bundle["observations"] if r[3] not in catalog_ids]
    check("every lesson_id exists in the real catalog", not bad_lesson,
          f"{len(bad_lesson)} unknown")

    bad_tier = [r for r in bundle["observations"] if r[5] not in tiers]
    check("every tier is a valid difficulty tier", not bad_tier)

    bad_group = [r for r in bundle["observations"] if r[1] not in groups]
    check("every proficiency group is valid", not bad_group)

    bad_skill = [r for r in bundle["observations"] if r[3] != r[4]]
    check("skill_id == lesson_id (project convention)", not bad_skill)

    seqs: Dict[Tuple[str, int], List[int]] = {}
    for r in bundle["observations"]:
        seqs.setdefault((r[0], r[3]), []).append(r[6])
    bad_seq = {k: v for k, v in seqs.items()
               if v != list(range(1, len(v) + 1))}
    check("attempt_index is 1..n contiguous per (student, lesson)",
          not bad_seq, f"{len(bad_seq)} malformed")

    expected_q = int(cfg["population"]["questions_per_lesson"])
    wrong_len = [k for k, v in seqs.items() if len(v) != expected_q]
    check(f"every sequence has exactly {expected_q} observations",
          not wrong_len, f"{len(wrong_len)} wrong")

    missing = sum(1 for r in bundle["observations"] if any(
        v is None or (isinstance(v, str) and v == "") for v in r))
    check("no missing values in observations", missing == 0, f"{missing} found")

    # `validate()` itself must agree.
    stats = gd.validate(bundle, cfg)
    check("gd.validate() accepts the dataset", stats["n_observations"] > 0)
    check("ground truth absent from observation rows",
          len(bundle["observations"][0]) == len(gd.OBS_COLUMNS))

    # Answers must be generated by the probabilistic model, not the label.
    rates = stats["answer_rate_per_group"]
    check("answer rates are not degenerate (0 or 1)",
          all(0.05 < v < 0.99 for v in rates.values()),
          json.dumps(rates))
    check("answer rates are not simply the group ordering hard-coded",
          len(set(round(v, 6) for v in rates.values())) > 1
          and max(rates.values()) - min(rates.values()) < 0.5)


# ── 3. Split leakage ─────────────────────────────────────────────────────

def t3_no_leakage(base: Dict) -> None:
    print("\n[3] No student leaks between train/validation/test")
    cfg = small_config(base)
    bundle = gd.simulate(cfg, "primary")
    sets = {s: set() for s in ("train", "validation", "test")}
    for sid, split in bundle["splits"].items():
        sets[split].add(sid)

    check("split fractions were applied",
          all(len(v) > 0 for v in sets.values()),
          json.dumps({k: len(v) for k, v in sets.items()}))

    overlaps = {
        "train/validation": sets["train"] & sets["validation"],
        "train/test": sets["train"] & sets["test"],
        "validation/test": sets["validation"] & sets["test"],
    }
    check("no student id appears in two splits",
          all(not v for v in overlaps.values()),
          json.dumps({k: sorted(v)[:3] for k, v in overlaps.items() if v}))

    # The split recorded on each observation row must match the student map.
    mismatched = [r for r in bundle["observations"]
                  if bundle["splits"].get(r[0]) != r[2]]
    check("row-level split matches the student-level assignment",
          not mismatched, f"{len(mismatched)} rows")

    # Every (student, lesson) sequence lives wholly inside one split.
    seq_split: Dict[Tuple[str, int], set] = {}
    for r in bundle["observations"]:
        seq_split.setdefault((r[0], r[3]), set()).add(r[2])
    straddlers = {k: v for k, v in seq_split.items() if len(v) > 1}
    check("no (student, lesson) sequence straddles splits",
          not straddlers, f"{len(straddlers)} straddling")

    # Coverage: each group present in each split.
    per_group_split: Dict[str, set] = {}
    for sid, split in bundle["splits"].items():
        grp = bundle["student_groups"][bundle["student_ids"].index(sid)]
        per_group_split.setdefault(grp, set()).add(split)
    check("every group appears in every split",
          all(len(v) == 3 for v in per_group_split.values()),
          json.dumps({k: sorted(v) for k, v in per_group_split.items()}))


# ── 4. Production parameters loaded and unmodified ───────────────────────

def t4_production_untouched(base: Dict) -> None:
    print("\n[4] Production parameters are loaded, never modified")
    import modules.bkt_engine as BE

    before = json.dumps({"d": BE.DEFAULT_PARAMS, "i": BE.INITIAL_MASTERY,
                         "c": BE.CATALOG_LEVEL_TO_TIER}, sort_keys=True)

    check("research snapshot equals the live module (INITIAL_MASTERY)",
          bkt_core.PRODUCTION_BKT["INITIAL_MASTERY"] ==
          json.loads(json.dumps(BE.INITIAL_MASTERY)))
    check("research snapshot equals the live module (DEFAULT_PARAMS)",
          bkt_core.PRODUCTION_BKT["DEFAULT_PARAMS"] ==
          json.loads(json.dumps(BE.DEFAULT_PARAMS)))
    check("research snapshot equals the live module (CATALOG_LEVEL_TO_TIER)",
          bkt_core.PRODUCTION_BKT["CATALOG_LEVEL_TO_TIER"] ==
          dict(BE.CATALOG_LEVEL_TO_TIER))

    # Exact documented production values (guards against silent drift).
    check("documented t/g/s are 0.15/0.25/0.10",
          (BE.DEFAULT_PARAMS["t"], BE.DEFAULT_PARAMS["g"],
           BE.DEFAULT_PARAMS["s"]) == (0.15, 0.25, 0.10),
          str({k: BE.DEFAULT_PARAMS[k] for k in ("t", "g", "s")}))
    check("documented INITIAL_MASTERY matches the specification",
          BE.INITIAL_MASTERY == {
              "beginner": {"easy": 0.20, "intermediate": 0.05, "advanced": 0.01},
              "intermediate": {"easy": 0.55, "intermediate": 0.30, "advanced": 0.08},
              "advanced": {"easy": 0.80, "intermediate": 0.60, "advanced": 0.30},
          }, json.dumps(BE.INITIAL_MASTERY))
    check("production mastery threshold is 0.7",
          bkt_core.MASTERY_THRESHOLD == 0.7 and
          bkt_core.PRODUCTION_BKT["MASTERY_THRESHOLD"] == 0.7)

    # Exercise the experiment, then prove nothing mutated the module.
    cfg = small_config(base)
    gd.simulate(cfg, "primary")
    grid = bkt_core.candidate_grid(cfg)
    bkt_core.production_prior("advanced", 1)
    bkt_core.production_prior_for_tier("beginner", "easy")
    bkt_core.params_with_prior(0.5)
    scoring_engine = bkt_core.bktengine_for_scoring()
    scoring_engine.update_mastery(0.5, True, bkt_core.bkt_params())

    after = json.dumps({"d": BE.DEFAULT_PARAMS, "i": BE.INITIAL_MASTERY,
                        "c": BE.CATALOG_LEVEL_TO_TIER}, sort_keys=True)
    check("production constants byte-identical after running the experiment",
          before == after)
    check("candidate grid includes every production prior",
          all(round(float(v), 10) in grid
              for t in BE.INITIAL_MASTERY.values() for v in t.values()),
          f"grid size {len(grid)}")

    # Reloading the module re-reads the constants from source; they must still
    # equal the snapshot captured when the research package first imported it.
    reloaded = importlib.reload(BE)
    check("module reload yields the same production values as the snapshot",
          json.loads(json.dumps(reloaded.INITIAL_MASTERY)) ==
          bkt_core.PRODUCTION_BKT["INITIAL_MASTERY"]
          and json.loads(json.dumps(reloaded.DEFAULT_PARAMS)) ==
          bkt_core.PRODUCTION_BKT["DEFAULT_PARAMS"],
          "reloaded module diverged from the import-time snapshot")


# ── 5. BKT update parity with production ─────────────────────────────────

def t5_bkt_parity(base: Dict) -> None:
    print("\n[5] Experiment BKT update matches the production formula")
    import modules.bkt_engine as BE

    engine = fresh_engine()
    params = bkt_core.bkt_params()

    mismatches = []
    cases = 0
    for L in [0.0, 0.01, 0.05, 0.2, 0.35, 0.5, 0.6, 0.7, 0.8, 0.95, 1.0]:
        for y in (False, True):
            expected = BE.BKTEngine.update_mastery(engine, L, y, params)
            got = bkt_core.step(L, y, params)
            cases += 1
            if expected != got:
                mismatches.append((L, y, expected, got))
    check(f"step() is bit-identical to BKTEngine.update_mastery "
          f"({cases} cases)", not mismatches, str(mismatches[:3]))

    # Hand-computed reference from the production docstring.
    L0, t, g, s = 0.5, params["t"], params["g"], params["s"]
    p_correct = L0 * (1 - s) + (1 - L0) * g
    posterior = (L0 * (1 - s)) / p_correct
    expected_correct = posterior + (1 - posterior) * t
    check("correct-answer update matches the documented equation",
          bkt_core.step(L0, True, params) == expected_correct,
          f"{bkt_core.step(L0, True, params)} vs {expected_correct}")
    check("predict_correct matches step 1 of the production equation",
          bkt_core.predict_correct(L0, params) == p_correct)

    # The research engine must never have created a progress file.
    check("scoring engine bypasses BKTEngine.__init__ (no file access)",
          not hasattr(bkt_core.bktengine_for_scoring(), "data_file"),
          "data_file attribute should be absent because __init__ was skipped")

    # Production parameters actually flow into the update.
    check("bkt_params() carries production t/g/s",
          bkt_core.bkt_params() == {"t": 0.15, "g": 0.25, "s": 0.10},
          json.dumps(bkt_core.bkt_params()))


# ── 6. Prediction precedes the answer ────────────────────────────────────

def t6_prediction_order(base: Dict) -> None:
    print("\n[6] Predictions are computed before incorporating the answer")
    params = bkt_core.bkt_params()
    prior = 0.4

    # Single observation: the prediction must equal P(correct | L0) exactly,
    # i.e. the state has not yet been updated by the answer.
    for y in (0, 1):
        steps = bkt_core.run_sequence(prior, [y], params)
        state, pred, label = steps[0]
        check(f"first prediction uses the untouched prior (y={y})",
              state == prior and pred == bkt_core.predict_correct(prior, params),
              f"state={state} pred={pred}")
        check(f"returned label equals the answer (y={y})", label == y)

    answers = [1, 0, 1, 1, 0, 1]
    steps = bkt_core.run_sequence(prior, answers, params)

    ok = True
    detail = ""
    for i, (state, pred, y) in enumerate(steps):
        want = bkt_core.predict_correct(state, params)
        if pred != want:
            ok, detail = False, f"step {i}: pred {pred} != f(state) {want}"
            break
        # The state must be the one produced by the PREVIOUS answer only.
        if i == 0:
            if state != prior:
                ok, detail = False, f"step 0 state {state} != prior {prior}"
                break
        else:
            rebuilt = prior
            for prev in answers[:i]:
                rebuilt = bkt_core.step(rebuilt, bool(prev), params)
            if state != rebuilt:
                ok, detail = (False,
                              f"step {i} state {state} != replay of first {i} "
                              f"answers ({rebuilt})")
                break
    check("each state is the prefix update, never the full sequence", ok, detail)

    # Decisive test: flipping the LAST answer must not change the LAST
    # prediction (it only affects predictions that come after it).
    a = bkt_core.run_sequence(prior, [1, 1, 0, 1], params)
    b = bkt_core.run_sequence(prior, [1, 1, 0, 0], params)
    check("last prediction unaffected by the answer it scores",
          a[-1][1] == b[-1][1],
          f"{a[-1][1]} vs {b[-1][1]}")
    check("earlier predictions identical when only the tail differs",
          [x[1] for x in a[:3]] == [x[1] for x in b[:3]])

    # The answers differ, so the state produced BY the final answer must
    # diverge - that divergence is what the next prediction would consume.
    state_a = bkt_core.step(a[-1][0], bool(a[-1][2]), params)
    state_b = bkt_core.step(b[-1][0], bool(b[-1][2]), params)
    check("state does absorb the answer for the next step",
          state_a != state_b,
          f"{state_a} vs {state_b}")

    # collect_predictions_by_group must satisfy the same property.
    recs = [{"student": "s1", "group": "beginner", "tier": "easy",
             "lesson": 1, "answers": [1, 0, 1]}]
    ys, ps = rx.collect_predictions_by_group(
        recs, lambda g, t: prior, params, 1e-15)
    expected = [p for _s, p, _y in bkt_core.run_sequence(prior, [1, 0, 1], params)]
    check("collect_predictions_by_group scores pre-answer states",
          ps["beginner"] == expected and ys["beginner"] == [1, 0, 1])


# ── 7. Optimizer selects on validation, never on test ────────────────────

def t7_selection_uses_validation(base: Dict) -> None:
    print("\n[7] The optimizer chooses the best VALIDATION candidate")
    cfg = small_config(base)
    bundle = gd.simulate(cfg, "primary")
    sets = rx.build_sequence_sets(bundle)
    val, test = sets["validation"], sets["test"]
    grid = bkt_core.candidate_grid(cfg)
    params = bkt_core.bkt_params()
    clip = float(cfg["metrics"]["probability_clip"])

    def best_for(records, group=None):
        """Validation arg-min for a group (or overall when group is None).

        The group filter matters: `run_scenario` optimises each proficiency
        group on THAT group's sequences only, so comparing an all-groups
        arg-min against a group-specific selection would be apples-to-oranges.
        """
        subset = records if group is None else [
            r for r in records if r["group"] == group]
        students = rx._local_students(subset)
        losses, counts = rx.candidate_loss_matrix(
            subset, grid, params, len(students), clip)
        idx, means, _n = rx.summarise_grid(grid, losses, counts)
        return idx, means, subset

    val_idx, val_means, beg_val = best_for(val.records, "beginner")
    test_idx, test_means, _ = best_for(test.records, "beginner")
    common_idx, _cm, _ = best_for(val.records, None)

    check("validation arg-min is a well-defined grid index",
          0 <= val_idx < len(grid), f"grid[{val_idx}]={grid[val_idx]}")
    check("group-specific and common selections are genuinely different "
          "quantities", grid[val_idx] != grid[common_idx],
          f"group={grid[val_idx]} common={grid[common_idx]}")

    # The selected value must equal the validation arg-min BY CONSTRUCTION.
    # Assert it from the real run_scenario wiring, not just this helper.
    summary = rx.run_scenario(cfg, "primary", {
        "curves": [], "ranges": [], "metrics": [], "deltas": [],
        "calibration": [], "bootstrap": [], "practical": [], "trajectories": [],
    }, quick=False)
    reported = summary["selected_group"]["beginner"]
    check("run_scenario reports the validation arg-min for beginner",
          reported == grid[val_idx],
          f"reported={reported} validation_argmin={grid[val_idx]}")

    # The recorded selection flag must sit on the validation curve's minimum.
    cfg2 = copy.deepcopy(cfg)
    out = {"curves": [], "ranges": [], "metrics": [], "deltas": [],
           "calibration": [], "bootstrap": [], "practical": [],
           "trajectories": []}
    rx.run_scenario(cfg2, "primary", out, quick=False)
    beg = [r for r in out["curves"]
           if r["scope"] == "group_specific" and r["group"] == "beginner"]
    check("exactly one candidate flagged as selected",
          sum(int(r["is_selected"]) for r in beg) == 1)
    flagged = [r for r in beg if r["is_selected"] == "1"]
    if flagged:
        losses = [float(r["mean_log_loss"]) for r in beg]
        best_val = min(losses)
        check("flagged candidate attains the minimum validation log loss",
              abs(float(flagged[0]["mean_log_loss"]) - best_val) < 1e-12,
              f"{flagged[0]['mean_log_loss']} vs {best_val}")
        check("flagged candidate lies on the validation split",
              int(flagged[0]["n_students"]) == len(val.students),
              f"n_students={flagged[0]['n_students']}")
        check("selection rows are labelled with the validation scope",
              flagged[0]["scope"] == "group_specific"
              and flagged[0]["group"] == "beginner")

    # Decisive: perturbing TEST answers must not move the selected prior.
    tampered = copy.deepcopy(bundle)
    changed = 0
    for row in tampered["observations"]:
        if row[2] == "test" and changed < 5000:
            row[7] = 1 - row[7]
            changed += 1
    sets_pert = rx.build_sequence_sets(tampered)
    val_pert = sets_pert["validation"]
    p_idx, _m, _ = best_for(val_pert.records, "beginner")
    check("flipping test answers leaves the validation selection unchanged",
          grid[p_idx] == grid[val_idx],
          f"before={grid[val_idx]} after={grid[p_idx]} (flipped {changed} rows)")


# ── 8. Near-optimal range follows the documented rule ────────────────────

def t8_near_optimal_rule(base: Dict) -> None:
    print("\n[8] Near-optimal range uses the documented one-SE rule")
    cfg = small_config(base)
    bundle = gd.simulate(cfg, "primary")
    sets = rx.build_sequence_sets(bundle)
    val = sets["validation"]
    grid = bkt_core.candidate_grid(cfg)
    params = bkt_core.bkt_params()
    clip = float(cfg["metrics"]["probability_clip"])
    n_boot = int(cfg["bootstrap"]["n_resamples"])

    groups = ("beginner",)
    for group in groups:
        seqs = [r for r in val.records if r["group"] == group]
        students = rx._local_students(seqs)
        losses, counts = rx.candidate_loss_matrix(
            seqs, grid, params, len(students), clip)
        info = rx.near_optimal_range(grid, losses, counts, len(students),
                                     n_boot, seed=999)

        total = int(counts.sum())
        means = [float(losses[c].sum()) / total for c in range(len(grid))]
        argmin = min(range(len(grid)), key=lambda c: means[c])

        check(f"[{group}] selected prior is the validation arg-min",
              info["best_prior"] == grid[argmin],
              f"{info['best_prior']} vs {grid[argmin]}")
        check(f"[{group}] min_log_loss equals the recomputed minimum",
              abs(info["min_log_loss"] - means[argmin]) < 1e-12)
        check(f"[{group}] threshold = min + 1 standard error",
              abs(info["threshold"] - (means[argmin] + info["se_at_min"])) < 1e-12,
              f"{info['threshold']} vs {means[argmin]}+{info['se_at_min']}")
        check(f"[{group}] se_at_min is non-negative", info["se_at_min"] >= 0)

        # The range must be exactly {p : LL(p) <= LL(p*) + SE(p*)}.
        expected_set = [i for i, m in enumerate(means)
                        if m <= means[argmin] + info["se_at_min"] + 1e-15]
        check(f"[{group}] range membership matches the written rule",
              sorted(info["primary_indices"]) == sorted(expected_set),
              f"got {len(info['primary_indices'])}, want {len(expected_set)}")
        check(f"[{group}] span endpoints equal min/max of the set",
              info["primary_span"] == (grid[min(expected_set)],
                                       grid[max(expected_set)]))
        check(f"[{group}] range contains the arg-min",
              grid[argmin] >= info["primary_span"][0]
              and grid[argmin] <= info["primary_span"][1])
        check(f"[{group}] paired interval is no wider than the primary rule",
              info["paired_width"] <= info["primary_width"] + 1e-12,
              f"paired {info['paired_width']} vs primary {info['primary_width']}")
        check(f"[{group}] all candidates outside the range strictly exceed "
              f"the threshold",
              all(means[i] > info["threshold"] + 1e-12
                  for i in range(len(grid))
                  if i not in set(info["primary_indices"])))

        # Determinism of the bootstrap for a fixed seed.
        again = rx.near_optimal_range(grid, losses, counts, len(students),
                                      n_boot, seed=999)
        check(f"[{group}] bootstrap is reproducible for a fixed seed",
              again["primary_span"] == info["primary_span"]
              and again["se_at_min"] == info["se_at_min"])


# ── 9. Sensitivity scenarios stay separate ───────────────────────────────

def t9_scenarios_separate(base: Dict) -> None:
    print("\n[9] Sensitivity scenarios are independently identified")
    cfg = small_config(base)
    out = {"curves": [], "ranges": [], "metrics": [], "deltas": [],
           "calibration": [], "bootstrap": [], "practical": [],
           "trajectories": []}
    ids = [s["id"] for s in cfg["scenarios"]]
    for spec in cfg["scenarios"]:
        rx.run_scenario(cfg, spec["id"], out, quick=False)

    check(f"all requested scenarios ran ({ids})",
          sorted({r["scenario"] for r in out["ranges"]}) == sorted(ids))

    for key in ("ranges", "metrics", "curves", "practical"):
        rows = out[key]
        seen = {r["scenario"] for r in rows}
        check(f"'{key}' rows carry a scenario id", seen == set(ids),
              f"found {sorted(seen)}")
        check(f"'{key}' never pools scenarios into one row",
              all(r.get("scenario") in ids for r in rows))

    # Every (scenario, group) pair must exist separately in the ranges table.
    pairs = {(r["scenario"], r["group"]) for r in out["ranges"]}
    expected = {(sid, g) for sid in ids for g in ("beginner", "intermediate",
                                                  "advanced")}
    check("each scenario x group has its own near-optimal range",
          expected <= pairs, f"missing {sorted(expected - pairs)[:5]}")

    # Different DGP assumptions must actually produce different selections.
    by_id = {r["scenario"]: r for r in out["ranges"]
             if r["group"] == "advanced"}
    selected = {sid: r["selected_prior"] for sid, r in by_id.items()}
    check("distinct scenarios are not silently identical",
          len(set(selected.values())) > 1, json.dumps(selected))

    # The four scenarios whose mean_mode differs from production must move the
    # oracle away from production - the others must leave it identical.
    oracle = {r["scenario"]: r for r in out["deltas"]
              if r["strategy"] == "oracle_reference" and r["group"] == "overall"}
    mode_by_id = {s["id"]: s.get("mean_mode", "production")
                  for s in cfg["scenarios"]}
    for sid, row in oracle.items():
        delta = float(row["delta_log_loss"])
        differs = mode_by_id.get(sid, "production") != "production"
        if differs:
            check(f"[{sid}] oracle differs from production (mean_mode="
                  f"{mode_by_id[sid]})", abs(delta) > 0,
                  f"delta={delta}")
        else:
            check(f"[{sid}] oracle is bit-identical to production",
                  delta == 0.0, f"delta={delta}")


# ── 10. No live database or legacy JSON IO ───────────────────────────────

def _ast_io_offenders() -> List[str]:
    """Static guard: find real database references, ignoring documentation.

    A plain substring scan flags the *docstrings that explain we do not touch
    these stores*, so the scan is done on the AST instead: import statements,
    identifier references and string literals passed to a call are code; a
    bare string constant (a docstring) is prose and is skipped.
    """
    import ast

    forbidden_modules = {"sqlite3", "database", "modules.database", "auth"}
    forbidden_names = {"SQLiteRepository", "MockDB"}
    forbidden_paths = ("sanskrit_ai.sqlite3", "bkt_progress.json")
    offenders: List[str] = []

    for fname in ("bkt_core.py", "generate_dataset.py", "run_experiment.py",
                  "make_figures.py"):
        path = os.path.join(HERE, fname)
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:  # pragma: no cover
            offenders.append(f"{fname}: unparseable ({exc})")
            continue

        # Collect docstring nodes so they can be treated as prose.
        docstrings = set()
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if (isinstance(body, list) and body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if alias.name in forbidden_modules or root == "sqlite3":
                        offenders.append(
                            f"{fname}:{node.lineno} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in forbidden_modules or mod.endswith(".database"):
                    offenders.append(
                        f"{fname}:{node.lineno} imports from {mod}")
                for alias in node.names:
                    if alias.name in forbidden_modules:
                        offenders.append(
                            f"{fname}:{node.lineno} imports {alias.name} "
                            f"from {mod or '<relative>'}")
            elif isinstance(node, ast.Name) and node.id in forbidden_names:
                offenders.append(f"{fname}:{node.lineno} references {node.id}")
            elif isinstance(node, ast.Call):
                # Only string literals actually passed to a call count as an
                # attempt to open a store; docstrings are not call arguments.
                for arg in list(node.args) + [kw.value for kw in node.keywords]:
                    if (isinstance(arg, ast.Constant)
                            and isinstance(arg.value, str)
                            and any(tok in arg.value for tok in forbidden_paths)):
                        offenders.append(
                            f"{fname}:{node.lineno} opens {arg.value!r}")
    return offenders


def t10_no_live_io(base: Dict) -> None:
    print("\n[10] The experiment never touches live application data")
    live = {
        "sqlite": os.path.join(BACKEND_DIR, "data", "sanskrit_ai.sqlite3"),
        "bkt_json": os.path.join(BACKEND_DIR, "data", "bkt_progress.json"),
        "users": os.path.join(BACKEND_DIR, "data", "users.json"),
    }

    def snap() -> Dict[str, str]:
        state = {}
        for key, path in live.items():
            if os.path.exists(path):
                with open(path, "rb") as handle:
                    state[key] = hashlib.sha256(handle.read()).hexdigest()
            else:
                state[key] = "<absent>"
        return state

    # Both views must describe the same three files: the test's own snapshot
    # (human-readable keys) and the experiment's guard (relative-path keys).
    before = snap()
    before_guard = rx._live_hashes()
    check("the experiment's live-store guard sees all three stores",
          set(before_guard) == set(rx.LIVE_STORES)
          and all(v is not None for v in before_guard.values()),
          json.dumps(before_guard))
    check("test snapshot and guard agree on the SQLite file",
          before["sqlite"] == before_guard["data/sanskrit_ai.sqlite3"])
    check("test snapshot and guard agree on the legacy progress JSON",
          before["bkt_json"] == before_guard["data/bkt_progress.json"])

    offenders = _ast_io_offenders()
    check("no research module imports or opens the database layer",
          not offenders, "; ".join(offenders[:4]))

    # Skip BKTEngine.__init__, which is the only constructor that writes
    # data/bkt_progress.json.
    engine = bkt_core.bktengine_for_scoring()
    check("the scoring engine has no data_file (construction was skipped)",
          not hasattr(engine, "data_file"))
    check("the scoring engine never gained a data_file after use",
          not hasattr(bkt_core.bktengine_for_scoring(), "data_file"))

    # Exercise the whole pipeline in a sandbox, including figure inputs.
    cfg = small_config(base)
    tmp = tempfile.mkdtemp(prefix="bkt_live_io_")
    try:
        out = {"curves": [], "ranges": [], "metrics": [], "deltas": [],
               "calibration": [], "bootstrap": [], "practical": [],
               "trajectories": []}
        for spec in cfg["scenarios"]:
            rx.run_scenario(cfg, spec["id"], out, quick=False)

        # The live-store guard itself must fire cleanly. It is keyed by
        # relative path, so the path-keyed snapshot is what gets passed.
        rx._assert_no_live_io(before_guard)
        check("run_experiment's own live-store guard passes", True)

        # Write into the sandbox only - never into the research results tree.
        written = os.path.join(tmp, "m.csv")
        rx.write_rows(written, out["metrics"],
                      ["scenario", "strategy", "group", "log_loss", "brier",
                       "accuracy", "ece", "n_obs", "prior_used"])
        check("result files were written to the sandbox directory",
              os.path.exists(written)
              and os.path.commonpath([os.path.realpath(written),
                                      os.path.realpath(tmp)]) ==
              os.path.realpath(tmp),
              written)
        check("no result file was written inside the research tree",
              not written.startswith(os.path.realpath(HERE) + os.sep))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    after = snap()
    check("live SQLite DB, legacy progress JSON and users.json are unchanged",
          before == after,
          json.dumps({k: (before.get(k, "")[:12], after.get(k, "")[:12])
                      for k in live if before.get(k) != after.get(k)}))

    check("sqlite_repository was never imported",
          "sqlite_repository" not in sys.modules,
          "present in sys.modules" if "sqlite_repository" in sys.modules else "")

    # And the on-disk dataset lives under the research directory only.
    research_data = os.path.join(HERE, "data")
    stray = [p for p in (os.path.join(BACKEND_DIR, "data", "observations.csv"),)
             if os.path.exists(p)]
    check("synthetic dataset not written into backend/data", not stray,
          str(stray))


# ── Driver ───────────────────────────────────────────────────────────────

ALL_TESTS: List[Tuple[str, Callable[[Dict], None]]] = [
    ("reproducibility", t1_reproducibility),
    ("schema", t2_schema),
    ("split_leakage", t3_no_leakage),
    ("production_untouched", t4_production_untouched),
    ("bkt_parity", t5_bkt_parity),
    ("prediction_order", t6_prediction_order),
    ("validation_selection", t7_selection_uses_validation),
    ("near_optimal_rule", t8_near_optimal_rule),
    ("scenario_separation", t9_scenarios_separate),
    ("no_live_io", t10_no_live_io),
]


def main() -> int:
    base = bkt_core.load_config()
    selected = sys.argv[1:] or None

    for name, fn in ALL_TESTS:
        if selected and name not in selected:
            continue
        try:
            fn(base)
        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            RESULTS.append((f"{name} (unhandled exception)", False,
                            f"{type(exc).__name__}: {exc}"))

    passed = sum(1 for _n, ok, _d in RESULTS if ok)
    failed = sum(1 for _n, ok, _d in RESULTS if not ok)
    print("\n" + "=" * 70)
    print(f"RESULT: {passed} passed, {failed} failed, {len(RESULTS)} total")
    if failed:
        print("\nFailures:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name}: {detail}")
    print("=" * 70)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
