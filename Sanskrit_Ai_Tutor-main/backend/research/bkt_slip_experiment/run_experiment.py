#!/usr/bin/env python
"""
Execute the four BKT slip-probability experiments.

    A  one-parameter slip sweep under the production DGP (multiple seeds)
    B  recovery of known generating slip values (low / medium / high / boundary)
    C  parameter-confounding analysis (guess, initial mastery, learning rate)
    D  heterogeneous learners and skills (slip by tier / by group, spread)

Every experiment selects on the VALIDATION split only and touches the held-out
TEST split exactly once, at the end.  Hidden mastery states and generating
parameters never enter the fitting step.

Usage
-----
    python run_experiment.py                 # all four experiments
    python run_experiment.py --only a        # one experiment
    python run_experiment.py --quick         # small smoke run
    python run_experiment.py --no-write      # skip datasets/

Exit 0 on success, 1 on any failure.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import analyze_results as ar  # noqa: E402
import bkt_core  # noqa: E402
import generate_dataset as gd  # noqa: E402

# ── Live-data guard ──────────────────────────────────────────────────────

LIVE_STORES: Tuple[str, ...] = (
    "data/sanskrit_ai.sqlite3",
    "data/bkt_progress.json",
    "data/users.json",
)


def _live_hashes() -> Dict[str, Optional[str]]:
    """SHA-256 (first 16 hex chars) of each live store, or None if absent.

    Read-only integrity check: the experiment never writes these files, and
    this guard proves it by comparing before/after.
    """
    state: Dict[str, Optional[str]] = {}
    for rel in LIVE_STORES:
        path = os.path.join(bkt_core.BACKEND_DIR, rel)
        if not os.path.exists(path):
            state[rel] = None
            continue
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        state[rel] = digest.hexdigest()
    return state


def _assert_no_live_io(before: Dict[str, Optional[str]]) -> None:
    if "sqlite_repository" in sys.modules or "SQLiteRepository" in sys.modules:
        raise RuntimeError("research code imported the live SQLite repository")
    after = _live_hashes()
    for rel, old in before.items():
        if after.get(rel) != old:
            raise RuntimeError(
                f"live store {rel} changed during the experiment "
                f"({old} -> {after.get(rel)})")


# ── Small helpers ────────────────────────────────────────────────────────

def _rows_for_other_experiments(path: str, new_rows: Sequence[Dict],
                                key: str) -> List[Dict]:
    """Rows already on disk that belong to an experiment this run skipped.

    Only files whose rows carry an ``experiment`` tag can be shared between
    experiments (currently `exp_mastery_metrics.csv`, written by both A and
    B).  For every tag present in ``new_rows`` the old rows are superseded;
    rows with a tag absent from ``new_rows`` are preserved.  Files without an
    ``experiment`` tag belong entirely to the run and are replaced.
    """
    if "experiment" not in COLUMNS[key]:
        return []
    try:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            existing = list(csv.DictReader(handle))
    except (OSError, csv.Error):
        return []
    fresh_tags = {r["experiment"] for r in new_rows}
    return [r for r in existing if r.get("experiment") not in fresh_tags]


def write_rows(path: str, rows: Sequence[Dict], columns: Sequence[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def production_prior_fn(logit_shift: float = 0.0) -> Callable:
    """Starting P(L0): production seeds, optionally moved in logit space."""

    def _fn(group: str, tier: str, lesson_id: int) -> float:
        base = float(bkt_core.INITIAL_MASTERY[group][tier])
        return bkt_core.logit_shifted_prior(base, logit_shift) if logit_shift else base

    return _fn


def hidden_index(observations: Sequence[Sequence],
                 truth: Sequence[Sequence]) -> Dict[Tuple[str, int, int], float]:
    """(student, lesson, attempt_index) -> hidden theta, from ground truth."""
    return {(row[0], int(row[2]), int(row[4])): float(row[5]) for row in truth}


def dataset_checksum(bundle: Dict) -> str:
    """Deterministic checksum of a generated dataset, computed in memory."""
    digest = hashlib.sha256()
    for row in bundle["observations"]:
        digest.update((",".join(str(v) for v in row)).encode("utf-8"))
        digest.update(b"|")
    return digest.hexdigest()


def _param_sets(grid: Sequence[float], g: float, t: float) -> List[Dict]:
    return [{"s": float(s), "g": float(g), "t": float(t)} for s in grid]


def _empty_outputs() -> Dict[str, List[Dict]]:
    return {
        "a_curve": [], "a_selection": [], "a_test": [], "a_deltas": [],
        "b_recovery": [],
        "c_conditions": [], "c_heatmap": [], "c_t_misspec": [],
        "d_heterogeneity": [],
        "mastery": [], "calibration": [], "by_attempt": [],
    }


# ── Experiment A: one-parameter slip sweep ───────────────────────────────

def run_experiment_a(config: Dict, out: Dict, seeds: Sequence[int],
                     write_dir: Optional[str] = None) -> Dict:
    print("\n=== Experiment A: one-parameter slip sweep ===")
    spec = config["experiment_a"]
    grid = bkt_core.slip_grid(config)
    clip = float(config["metrics"]["probability_clip"])
    n_boot = int(config["bootstrap"]["n_resamples"])
    boot_seed = int(config["bootstrap"]["seed"])
    true_s = float(spec["dgp_s"])
    oracle_params = {"s": true_s, "g": float(spec["dgp_g"]), "t": float(spec["dgp_t"])}

    for variant in spec["variants"]:
        sd = float(variant["within_group_sd"])
        vname = variant["id"]
        tmode = str(variant.get("transition_mode", "deterministic"))
        print(f"  -- variant={vname} sd={sd} transition={tmode} --")
        for seed in seeds:
            t0 = time.time()
            bundle = gd.simulate(config, s=float(spec["dgp_s"]), g=float(spec["dgp_g"]),
                                 t=float(spec["dgp_t"]), seed=int(seed),
                                 within_group_sd=sd, transition_mode=tmode)
            gd.validate(bundle, config)

            sequences = ar.build_sequences(bundle["observations"], production_prior_fn())
            splits = ar.split_sequences(sequences, bundle["observations"])
            val = splits["validation"]
            test = splits["test"]

            fit = ar.fit_grid(val, _param_sets(grid, float(spec["dgp_g"]),
                                               float(spec["dgp_t"])), clip)
            curve_se = ar.bootstrap_curve_se(fit, n_boot, boot_seed + seed)
            summary = ar.summarise_grid(grid, fit)
            selection = ar.select_candidate(grid, fit, n_boot, boot_seed + seed)

            for i, s in enumerate(grid):
                out["a_curve"].append({
                    "variant": vname, "within_group_sd": sd,
                    "transition_mode": tmode,
                    "seed": seed, "slip": s,
                    "mean_log_loss": float(summary["mean_log_loss"][i]),
                    "se": float(curve_se[i]),
                    "lo": float(summary["mean_log_loss"][i] - curve_se[i]),
                    "hi": float(summary["mean_log_loss"][i] + curve_se[i]),
                    "is_selected": int(i == summary["argmin"]),
                    "is_production": int(abs(s - bkt_core.PRODUCTION_SLIP) < 1e-12),
                })

            out["a_selection"].append({
                "variant": vname, "within_group_sd": sd,
                "transition_mode": tmode,
                "seed": seed,
                "true_slip": true_s,
                "selected": selection["best_prior"],
                "min_log_loss": selection["min_log_loss"],
                "se_at_min": selection["se_at_min"],
                "interval_lo": selection["lo"],
                "interval_hi": selection["hi"],
                "interval_width": selection["width"],
                "n_inside": selection["n_inside"],
                "true_in_interval": int(selection["lo"] <= true_s <= selection["hi"]),
                "production_in_interval": int(
                    selection["lo"] <= bkt_core.PRODUCTION_SLIP <= selection["hi"]),
                "n_val_obs": selection["n_obs"],
                "n_val_students": selection["n_students"],
            })

            selected_params = {"s": selection["best_prior"],
                               "g": float(spec["dgp_g"]), "t": float(spec["dgp_t"])}
            prod_params = bkt_core.production_params()

            for name, p in (("production", prod_params),
                            ("selected", selected_params),
                            ("oracle", oracle_params)):
                m = ar.evaluate_params(test, p, config, clip)
                out["a_test"].append({
                    "variant": vname, "within_group_sd": sd,
                    "transition_mode": tmode,
                    "seed": seed, "setting": name, "slip_used": p["s"],
                    "log_loss": m["log_loss"], "brier": m["brier"],
                    "ece": m["ece"], "accuracy": m["accuracy"],
                    "n_obs": m["n_obs"], "n_students": m["n_students"],
                })

            hidden = hidden_index(bundle["observations"], bundle["truth"])
            for name, p in (("production", prod_params),
                            ("selected", selected_params),
                            ("oracle", oracle_params)):
                mm = ar.mastery_evaluation(test, hidden, p)
                _record_mastery(out, "experiment_a", f"{vname}:{name}", seed,
                                p["s"], mm)

            for name, p in (("production", prod_params),
                            ("selected", selected_params),
                            ("oracle", oracle_params)):
                for row in ar.evaluate_params(test, p, config, clip)["calibration_bins"]:
                    out["calibration"].append({
                        "experiment": "experiment_a", "setting": name, "seed": seed,
                        "variant": vname, "group": "overall", **row,
                    })
                for row in ar.evaluate_by_attempt(test, p, clip):
                    out["by_attempt"].append({
                        "experiment": "experiment_a", "setting": name, "seed": seed,
                        "variant": vname, "group": "overall", **row,
                    })

            # Paired student-level bootstrap of the TEST difference vs production.
            # The held-out set is read here only to summarise a pre-decided
            # comparison; it never feeds back into parameter selection.
            ci_resamples = int(config["bootstrap"].get("test_ci_resamples", 1000))
            base_ll = ar.evaluate_params(test, prod_params, config, clip)["log_loss"]
            for name, p in (("selected", selected_params),
                            ("oracle", oracle_params)):
                d = ar.paired_delta_bootstrap(
                    test, prod_params, p, ci_resamples,
                    seed + 7000, clip,
                    confidence=float(config["bootstrap"]["confidence"]))
                out["a_deltas"].append({
                    "variant": vname, "within_group_sd": sd,
                    "transition_mode": tmode, "seed": seed,
                    "comparison": f"{name}_minus_production",
                    "alt_slip": p["s"], "ref_slip": prod_params["s"],
                    "ref_log_loss": base_ll,
                    "delta": d["delta"],
                    "rel_delta_pct": 100.0 * d["delta"] / base_ll if base_ll else None,
                    "ci_lo": d["ci_lo"], "ci_hi": d["ci_hi"],
                    "se": d["se"], "significant": int(d["significant"]),
                    "favour_alt": int(d["favour_alt"]),
                    "n_students": d["n_students"], "n_obs": d["n_obs"],
                    "n_resamples": d["n_resamples"],
                })

            if write_dir and seed == seeds[0] and vname == spec["variants"][-1]["id"]:
                gd.write_dataset(bundle, write_dir, gd.validate(bundle, config))

            print(f"    seed={seed:<4} selected={selection['best_prior']:.2f} "
                  f"interval=[{selection['lo']:.2f}, {selection['hi']:.2f}] "
                  f"true={true_s:.2f} "
                  f"{'COVERED' if selection['lo'] <= true_s <= selection['hi'] else 'MISSED'} "
                  f"({time.time() - t0:.1f}s)")

    return {"grid": grid}


# ── Experiment B: recovery of known slip values ──────────────────────────

def run_experiment_b(config: Dict, out: Dict, seeds: Sequence[int]) -> None:
    print("\n=== Experiment B: recovery of known generating slip ===")
    spec = config["experiment_b"]
    grid = bkt_core.slip_grid(config)
    clip = float(config["metrics"]["probability_clip"])
    n_boot = int(config["bootstrap"]["n_resamples"])
    boot_seed = int(config["bootstrap"]["seed"])
    g, t = float(spec["dgp_g"]), float(spec["dgp_t"])

    for variant in spec["variants"]:
        sd = float(variant["within_group_sd"])
        vname = variant["id"]
        tmode = str(variant.get("transition_mode", "deterministic"))
        print(f"  -- variant={vname} sd={sd} transition={tmode} --")
        for true_s in spec["generating_slips"]:
            for seed in seeds:
                t0 = time.time()
                bundle = gd.simulate(config, s=float(true_s), g=g, t=t, seed=int(seed),
                                     within_group_sd=sd, transition_mode=tmode)
                gd.validate(bundle, config)
                sequences = ar.build_sequences(bundle["observations"], production_prior_fn())
                splits = ar.split_sequences(sequences, bundle["observations"])
                val, test = splits["validation"], splits["test"]

                fit = ar.fit_grid(val, _param_sets(grid, g, t), clip)
                selection = ar.select_candidate(
                    grid, fit, n_boot,
                    boot_seed + seed + int(float(true_s) * 1000) + int(sd * 100))

                sel_p = {"s": selection["best_prior"], "g": g, "t": t}
                prod_p = bkt_core.production_params()
                oracle_p = {"s": float(true_s), "g": g, "t": t}

                sel_m = ar.evaluate_params(test, sel_p, config, clip)
                prod_m = ar.evaluate_params(test, prod_p, config, clip)
                ora_m = ar.evaluate_params(test, oracle_p, config, clip)

                hidden = hidden_index(bundle["observations"], bundle["truth"])
                mm = ar.mastery_evaluation(test, hidden, sel_p)

                out["b_recovery"].append({
                    "variant": vname, "within_group_sd": sd,
                    "transition_mode": tmode,
                    "seed": seed, "true_slip": float(true_s),
                    "selected": selection["best_prior"],
                    "bias": selection["best_prior"] - float(true_s),
                    "min_log_loss": selection["min_log_loss"],
                    "se_at_min": selection["se_at_min"],
                    "interval_lo": selection["lo"], "interval_hi": selection["hi"],
                    "interval_width": selection["width"],
                    "n_inside": selection["n_inside"],
                    "true_in_interval": int(
                        selection["lo"] <= float(true_s) <= selection["hi"]),
                    "test_log_loss_selected": sel_m["log_loss"],
                    "test_log_loss_oracle": ora_m["log_loss"],
                    "test_log_loss_production": prod_m["log_loss"],
                    "test_brier_selected": sel_m["brier"],
                    "test_ece_selected": sel_m["ece"],
                    "n_test_obs": sel_m["n_obs"],
                    "hidden_mae_selected": mm["overall"]["mae"],
                })
                _record_mastery(out, "experiment_b",
                                f"{vname}:true_s_{true_s}", seed,
                                selection["best_prior"], mm)

                print(f"    true={float(true_s):.2f} seed={seed:<4} "
                      f"selected={selection['best_prior']:.2f} "
                      f"bias={selection['best_prior'] - float(true_s):+.2f} "
                      f"interval=[{selection['lo']:.2f}, {selection['hi']:.2f}] "
                      f"{'COVERED' if selection['lo'] <= float(true_s) <= selection['hi'] else 'MISSED'} "
                      f"({time.time() - t0:.1f}s)")


# ── Experiment C: parameter confounding ──────────────────────────────────

def run_experiment_c(config: Dict, out: Dict) -> None:
    print("\n=== Experiment C: parameter confounding ===")
    spec = config["experiment_c"]
    grid = bkt_core.slip_grid(config)
    clip = float(config["metrics"]["probability_clip"])
    n_boot = int(config["bootstrap"]["n_resamples"])
    boot_seed = int(config["bootstrap"]["seed"])
    seed = int(spec["seeds"][0])
    dgp_spec = spec["dgp"]
    partners = spec["partner_grids"]
    true_g = float(dgp_spec["g"])
    true_t = float(dgp_spec["t"])

    # ONE dataset shared by every condition, so any difference is attributable
    # to the fitted assumptions and never to sampling noise.  The near-deterministic
    # spread is used deliberately (see config.experiment_c.sd_note) so that
    # confounding between g, l0 and s is measured without heterogeneity also
    # pushing the slip estimate.
    c_sd = float(spec.get("within_group_sd", 0.01))
    c_tmode = str(spec.get("transition_mode", "bkt_binary"))
    bundle = gd.simulate(config, s=float(dgp_spec["s"]), g=true_g, t=true_t,
                         seed=seed, within_group_sd=c_sd, transition_mode=c_tmode)
    gd.validate(bundle, config)
    base_sequences = ar.build_sequences(bundle["observations"], production_prior_fn())
    base_splits = ar.split_sequences(base_sequences, bundle["observations"])

    def val_for(shift: float) -> List[Dict]:
        """Validation sequences under a given l0 shift (0 = production seeds)."""
        if abs(shift) < 1e-12:
            return base_splits["validation"]
        return ar.split_sequences(
            ar.build_sequences(bundle["observations"], production_prior_fn(shift)),
            bundle["observations"])["validation"]

    for ci, cond in enumerate(spec["conditions"]):
        t0 = time.time()
        # When a parameter is being FITTED (null in config), its "assumed"
        # value is undefined for reporting purposes; use None rather than
        # crashing.  The fitting branches below ignore these placeholders.
        cond_g = cond["assume_g"]
        cond_t = cond["assume_t"]
        cond_l0 = cond["assume_logit_shift"]
        assume_g = true_g if cond_g is None else float(cond_g)
        assume_t = true_t if cond_t is None else float(cond_t)
        assume_l0 = 0.0 if cond_l0 is None else float(cond_l0)

        row = {
            "condition": cond["id"], "label": cond["label"], "seed": seed,
            "true_slip": float(dgp_spec["s"]),
            "dgp_g": true_g, "dgp_t": true_t,
            "dgp_logit_shift": float(dgp_spec.get("logit_shift", 0.0)),
            "assume_g": (None if cond_g is None else assume_g),
            "assume_t": (None if cond_t is None else assume_t),
            "assume_logit_shift": (None if cond_l0 is None else assume_l0),
        }

        # Order matters: the 3-way joint fit must be tested before the 2-way.
        if cond["fit_g"] and cond["fit_logit_shift"]:
            # Condition 7: (guess, logit_shift, slip) jointly, t fixed.
            loss_rows: List[Dict] = []
            for shift in partners["logit_shift"]:
                labels = [{"s": s, "g": gg, "t": assume_t}
                          for gg in partners["g"] for s in grid]
                fit = ar.fit_grid(val_for(float(shift)), labels, clip)
                keys = [f"g={gg}|s={s}" for gg in partners["g"] for s in grid]
                summ = ar.summarise_grid(keys, fit)
                for i, lab in enumerate(labels):
                    loss_rows.append({
                        "logit_shift": float(shift), "g": lab["g"], "slip": lab["s"],
                        "mean_log_loss": float(summ["mean_log_loss"][i]),
                    })
            best = min(loss_rows, key=lambda r: r["mean_log_loss"])
            row.update({
                "n_free_params": 3, "selected_s": best["slip"],
                "selected_g": best["g"], "selected_logit_shift": best["logit_shift"],
                "selected_t": None, "min_val_log_loss": best["mean_log_loss"],
                "interval_lo": None, "interval_hi": None,
                "interval_width": None, "n_inside": None,
            })
            for r in loss_rows:
                out["c_heatmap"].append({
                    "surface": "g_l0_vs_slip", "condition": cond["id"],
                    "g": r["g"], "logit_shift": r["logit_shift"], "slip": r["slip"],
                    "mean_log_loss": r["mean_log_loss"],
                    "delta_from_min": r["mean_log_loss"] - best["mean_log_loss"],
                    "is_selected": int(
                        r["slip"] == best["slip"] and r["g"] == best["g"]
                        and r["logit_shift"] == best["logit_shift"]),
                })

        elif cond["fit_g"]:
            # Condition 5: (guess, slip) jointly, t and l0 fixed.
            labels = [{"s": s, "g": gg, "t": assume_t}
                      for gg in partners["g"] for s in grid]
            keys = [f"g={gg}|s={s}" for gg in partners["g"] for s in grid]
            fit = ar.fit_grid(base_splits["validation"], labels, clip)
            summ = ar.summarise_grid(keys, fit)
            best = labels[summ["argmin"]]
            sel = ar.select_candidate(keys, fit, n_boot, boot_seed + 100 + ci)
            row.update({
                "n_free_params": 2, "selected_s": best["s"], "selected_g": best["g"],
                "selected_logit_shift": None, "selected_t": None,
                "min_val_log_loss": summ["min_log_loss"],
                "interval_lo": sel["lo"], "interval_hi": sel["hi"],
                "interval_width": sel["width"], "n_inside": sel["n_inside"],
            })
            for i, lab in enumerate(labels):
                out["c_heatmap"].append({
                    "surface": "guess_vs_slip", "condition": cond["id"],
                    "g": lab["g"], "logit_shift": None, "slip": lab["s"],
                    "mean_log_loss": float(summ["mean_log_loss"][i]),
                    "delta_from_min": float(
                        summ["mean_log_loss"][i] - summ["min_log_loss"]),
                    "is_selected": int(i == summ["argmin"]),
                })

        elif cond["fit_logit_shift"]:
            # Condition 6: (logit_shift, slip) jointly, g and t fixed.
            loss_rows = []
            for shift in partners["logit_shift"]:
                fit = ar.fit_grid(
                    val_for(float(shift)),
                    _param_sets(grid, assume_g, assume_t), clip)
                summ = ar.summarise_grid(grid, fit)
                for i, s in enumerate(grid):
                    loss_rows.append({
                        "logit_shift": float(shift), "slip": s,
                        "mean_log_loss": float(summ["mean_log_loss"][i]),
                    })
            best = min(loss_rows, key=lambda r: r["mean_log_loss"])
            row.update({
                "n_free_params": 2, "selected_s": best["slip"],
                "selected_g": None, "selected_logit_shift": best["logit_shift"],
                "selected_t": None, "min_val_log_loss": best["mean_log_loss"],
                "interval_lo": None, "interval_hi": None,
                "interval_width": None, "n_inside": None,
            })
            for r in loss_rows:
                out["c_heatmap"].append({
                    "surface": "l0_vs_slip", "condition": cond["id"],
                    "g": None, "logit_shift": r["logit_shift"], "slip": r["slip"],
                    "mean_log_loss": r["mean_log_loss"],
                    "delta_from_min": r["mean_log_loss"] - best["mean_log_loss"],
                    "is_selected": int(
                        r["slip"] == best["slip"]
                        and r["logit_shift"] == best["logit_shift"]),
                })

        else:
            # Conditions 1-4 and 8: one-dimensional slip sweep under the
            # condition's (possibly wrong) assumptions about g, t and l0.
            fit = ar.fit_grid(val_for(assume_l0),
                              _param_sets(grid, assume_g, assume_t), clip)
            summ = ar.summarise_grid(grid, fit)
            sel = ar.select_candidate(grid, fit, n_boot, boot_seed + 200 + ci)
            row.update({
                "n_free_params": 1, "selected_s": summ["best_prior"],
                "selected_g": None, "selected_logit_shift": None, "selected_t": None,
                "min_val_log_loss": summ["min_log_loss"],
                "interval_lo": sel["lo"], "interval_hi": sel["hi"],
                "interval_width": sel["width"], "n_inside": sel["n_inside"],
            })

        out["c_conditions"].append(row)
        print(f"  {cond['id']:<22} selected_s={row['selected_s']:.2f} "
              f"min_val_ll={row['min_val_log_loss']:.6f} "
              f"({time.time() - t0:.1f}s)")

    # fig6: learning-rate misspecification sweep (slip re-fitted at each t).
    print("  -- learning-rate misspecification sweep --")
    for t_val in partners["t"]:
        fit = ar.fit_grid(base_splits["validation"],
                          _param_sets(grid, true_g, float(t_val)), clip)
        summ = ar.summarise_grid(grid, fit)
        out["c_t_misspec"].append({
            "assumed_t": float(t_val), "true_t": true_t,
            "selected_s": summ["best_prior"],
            "min_val_log_loss": summ["min_log_loss"],
            "penalty_vs_true_t": None,
        })
    base = next(r for r in out["c_t_misspec"]
                if abs(r["assumed_t"] - true_t) < 1e-12)
    for r in out["c_t_misspec"]:
        r["penalty_vs_true_t"] = r["min_val_log_loss"] - base["min_val_log_loss"]
        print(f"    assumed_t={r['assumed_t']:.2f} -> selected_s={r['selected_s']:.2f} "
              f"penalty={r['penalty_vs_true_t']:+.6f}")


# ── Experiment D: heterogeneous learners and skills ──────────────────────

def run_experiment_d(config: Dict, out: Dict, seeds: Sequence[int]) -> None:
    print("\n=== Experiment D: heterogeneous learners and skills ===")
    spec = config["experiment_d"]
    grid = bkt_core.slip_grid(config)
    clip = float(config["metrics"]["probability_clip"])
    n_boot = int(config["bootstrap"]["n_resamples"])
    boot_seed = int(config["bootstrap"]["seed"])

    for cond in spec["conditions"]:
        for seed in seeds:
            t0 = time.time()
            overrides: Dict = {
                "slip_mode": cond["slip_mode"],
                "slip_values": cond["slip_values"],
                "seed": int(seed),
            }
            if "within_group_sd" in cond:
                overrides["within_group_sd"] = float(cond["within_group_sd"])
            overrides["transition_mode"] = str(
                cond.get("transition_mode", spec.get("transition_mode", "bkt_binary")))
            bundle = gd.simulate(config, **overrides)
            gd.validate(bundle, config)

            sequences = ar.build_sequences(bundle["observations"], production_prior_fn())
            splits = ar.split_sequences(sequences, bundle["observations"])
            val, test = splits["validation"], splits["test"]

            # A SINGLE global slip is fitted, against per-cell heterogeneous truth.
            fit = ar.fit_grid(val, _param_sets(grid, bundle["dgp"]["g"],
                                               bundle["dgp"]["t"]), clip)
            selection = ar.select_candidate(grid, fit, n_boot, boot_seed + seed)
            sel_p = {"s": selection["best_prior"], "g": bundle["dgp"]["g"],
                     "t": bundle["dgp"]["t"]}

            values = bundle["dgp"]["slip_values"]
            for cell, true_val in sorted(values.items()):
                key = "tier" if cond["slip_mode"] == "by_tier" else (
                    "group" if cond["slip_mode"] == "by_group" else "constant")
                # Restrict test records to this cell where the cell is a tier
                # or group; for the constant mode there is only one cell.
                if key == "tier":
                    subset = [r for r in test if r["tier"] == cell]
                elif key == "group":
                    subset = [r for r in test if r["group"] == cell]
                else:
                    subset = list(test)

                m = ar.evaluate_params(subset, sel_p, config, clip)
                hidden = hidden_index(bundle["observations"], bundle["truth"])
                mm = ar.mastery_evaluation(subset, hidden, sel_p)
                out["d_heterogeneity"].append({
                    "condition": cond["id"], "label": cond["label"], "seed": seed,
                    "transition_mode": overrides["transition_mode"],
                    "cell_kind": key, "cell": cell, "true_slip": float(true_val),
                    "selected_global_s": selection["best_prior"],
                    "bias_vs_cell_truth": selection["best_prior"] - float(true_val),
                    "interval_lo": selection["lo"], "interval_hi": selection["hi"],
                    "interval_width": selection["width"],
                    "cell_truth_in_interval": int(
                        selection["lo"] <= float(true_val) <= selection["hi"]),
                    "test_log_loss": m["log_loss"], "test_brier": m["brier"],
                    "n_obs": m["n_obs"],
                    "hidden_mae": mm["overall"]["mae"],
                })
            out["d_heterogeneity"].append({
                "condition": cond["id"], "label": cond["label"], "seed": seed,
                "transition_mode": overrides["transition_mode"],
                "cell_kind": "overall", "cell": "overall", "true_slip": None,
                "selected_global_s": selection["best_prior"],
                "bias_vs_cell_truth": None,
                "interval_lo": selection["lo"], "interval_hi": selection["hi"],
                "interval_width": selection["width"], "cell_truth_in_interval": None,
                "test_log_loss": ar.evaluate_params(test, sel_p, config, clip)["log_loss"],
                "test_brier": None, "n_obs": len(test),
                "hidden_mae": None,
            })
            print(f"  {cond['id']:<16} seed={seed:<4} "
                  f"global_s={selection['best_prior']:.2f} "
                  f"interval=[{selection['lo']:.2f}, {selection['hi']:.2f}] "
                  f"({time.time() - t0:.1f}s)")


# ── Recording helpers ────────────────────────────────────────────────────

def _record_mastery(out: Dict, experiment: str, setting: str, seed: int,
                    slip: float, mm: Dict) -> None:
    rows = [("overall", "overall", mm["overall"])]
    for group, payload in sorted(mm["by_group"].items()):
        rows.append(("group", group, payload))
    for scope, label, payload in rows:
        out["mastery"].append({
            "experiment": experiment, "setting": setting, "seed": seed,
            "slip_used": slip, "scope": scope, "label": label,
            "mae": payload["mae"], "brier_hidden": payload["brier_hidden"],
            "n_pairs": payload["n_pairs"],
            "flagged": payload["flagged"],
            "truth_mastered": payload["truth_mastered"],
            "false_mastered": payload["false_mastered"],
            "false_unmastered": payload["false_unmastered"],
            "false_mastered_rate_all": payload["false_mastered_rate_all"],
            "false_mastered_rate_of_flagged": payload["false_mastered_rate_of_flagged"],
            "false_unmastered_rate_all": payload["false_unmastered_rate_all"],
            "false_unmastered_rate_of_truth": payload["false_unmastered_rate_of_truth"],
        })


# ── Main ─────────────────────────────────────────────────────────────────

COLUMNS: Dict[str, List[str]] = {
    "a_curve": ["variant", "within_group_sd", "transition_mode", "seed", "slip",
                "mean_log_loss", "se", "lo", "hi", "is_selected", "is_production"],
    "a_selection": ["variant", "within_group_sd", "transition_mode", "seed", "true_slip",
                    "selected", "min_log_loss", "se_at_min", "interval_lo", "interval_hi",
                    "interval_width", "n_inside", "true_in_interval",
                    "production_in_interval", "n_val_obs", "n_val_students"],
    "a_test": ["variant", "within_group_sd", "transition_mode", "seed", "setting",
               "slip_used", "log_loss", "brier", "ece", "accuracy", "n_obs", "n_students"],
    "a_deltas": ["variant", "within_group_sd", "transition_mode", "seed",
                 "comparison", "alt_slip", "ref_slip", "ref_log_loss", "delta",
                 "rel_delta_pct", "ci_lo", "ci_hi", "se", "significant",
                 "favour_alt", "n_students", "n_obs", "n_resamples"],
    "b_recovery": ["variant", "within_group_sd", "transition_mode", "seed", "true_slip",
                   "selected", "bias", "min_log_loss", "se_at_min", "interval_lo",
                   "interval_hi", "interval_width", "n_inside", "true_in_interval",
                   "test_log_loss_selected", "test_log_loss_oracle",
                   "test_log_loss_production", "test_brier_selected",
                   "test_ece_selected", "n_test_obs", "hidden_mae_selected"],
    "c_conditions": ["condition", "label", "seed", "true_slip", "dgp_g", "dgp_t",
                     "dgp_logit_shift", "assume_g", "assume_t", "assume_logit_shift",
                     "n_free_params", "selected_s", "selected_g",
                     "selected_logit_shift", "selected_t", "min_val_log_loss",
                     "interval_lo", "interval_hi", "interval_width", "n_inside"],
    "c_heatmap": ["surface", "condition", "g", "logit_shift", "slip",
                  "mean_log_loss", "delta_from_min", "is_selected"],
    "c_t_misspec": ["assumed_t", "true_t", "selected_s", "min_val_log_loss",
                    "penalty_vs_true_t"],
    "d_heterogeneity": ["condition", "label", "seed", "transition_mode", "cell_kind",
                        "cell", "true_slip", "selected_global_s", "bias_vs_cell_truth",
                        "interval_lo", "interval_hi", "interval_width",
                        "cell_truth_in_interval", "test_log_loss", "test_brier",
                        "n_obs", "hidden_mae"],
    "mastery": ["experiment", "setting", "seed", "slip_used", "scope", "label",
                "mae", "brier_hidden", "n_pairs", "flagged", "truth_mastered",
                "false_mastered", "false_unmastered", "false_mastered_rate_all",
                "false_mastered_rate_of_flagged", "false_unmastered_rate_all",
                "false_unmastered_rate_of_truth"],
    "calibration": ["experiment", "setting", "seed", "variant", "group", "bin",
                    "lo", "hi", "mean_predicted", "observed", "count"],
    "by_attempt": ["experiment", "setting", "seed", "variant", "group",
                   "attempt_index", "log_loss", "brier", "accuracy", "n_obs"],
}

FILENAMES: Dict[str, str] = {
    "a_curve": "exp_a_validation_curve.csv",
    "a_selection": "exp_a_selection.csv",
    "a_test": "exp_a_test_metrics.csv",
    "a_deltas": "exp_a_test_deltas.csv",
    "b_recovery": "exp_b_recovery.csv",
    "c_conditions": "exp_c_conditions.csv",
    "c_heatmap": "exp_c_heatmap.csv",
    "c_t_misspec": "exp_c_t_misspec.csv",
    "d_heterogeneity": "exp_d_heterogeneity.csv",
    "mastery": "exp_mastery_metrics.csv",
    "calibration": "exp_calibration_bins.csv",
    "by_attempt": "exp_by_attempt.csv",
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=None)
    parser.add_argument("--only", choices=list("abcd"), action="append")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    config = bkt_core.load_config(args.config)
    live_before = _live_hashes()

    out = _empty_outputs()
    only = set(args.only or list("abcd"))

    if args.quick:
        config = json.loads(json.dumps(config))
        config["population"]["students_per_group"] = int(
            config["runtime"]["quick_students_per_group"])
        config["seeds"] = config["runtime"]["quick_seeds"]
        config["experiment_a"]["seeds"] = config["runtime"]["quick_seeds"]
        config["experiment_b"]["seeds"] = config["runtime"]["quick_seeds"]
        config["experiment_d"]["seeds"] = config["runtime"]["quick_seeds"]
        config["bootstrap"]["n_resamples"] = 100

    results_dir = args.out or bkt_core.resolve(config["paths"]["results"])
    datasets_dir = bkt_core.resolve(config["paths"]["datasets"])

    started = time.time()
    if "a" in only:
        run_experiment_a(config, out, config["experiment_a"]["seeds"],
                         write_dir=None if args.no_write
                         else os.path.join(datasets_dir, "exp_a_primary"))
    if "b" in only:
        run_experiment_b(config, out, config["experiment_b"]["seeds"])
    if "c" in only:
        run_experiment_c(config, out)
    if "d" in only:
        run_experiment_d(config, out, config["experiment_d"]["seeds"])

    os.makedirs(results_dir, exist_ok=True)
    for key, rows in out.items():
        if not rows:
            continue
        path = os.path.join(results_dir, FILENAMES[key])
        # A subset run must not destroy rows written by an experiment it did
        # not execute.  Rows that carry an `experiment` tag are merged by that
        # tag; anything else is replaced wholesale (it belongs to this run).
        if set(only) != set("abcd") and os.path.exists(path):
            keep = _rows_for_other_experiments(path, rows, key)
            if keep:
                rows = list(rows) + keep
                print(f"  kept {len(keep)} rows from other experiments in "
                      f"{FILENAMES[key]}")
        write_rows(path, rows, COLUMNS[key])
        print(f"  wrote {FILENAMES[key]} ({len(rows)} rows)")

    summary = build_summary(config, out)
    summary_path = os.path.join(results_dir, "summary.json")
    # A subset run (--only) must not destroy results from the experiments it
    # did not execute, so merge into whatever is already on disk.
    if os.path.exists(summary_path) and (set(only) != set("abcd")):
        try:
            with open(summary_path, "r", encoding="utf-8") as handle:
                existing = json.load(handle)
            for key, value in summary.items():
                if key in ("production_slip", "production_guess", "production_t",
                           "mastery_threshold", "slip_grid_size", "experiment"):
                    continue
                existing[key] = value
            existing.update({k: v for k, v in summary.items()
                             if k in ("production_slip", "production_guess",
                                      "production_t", "mastery_threshold",
                                      "slip_grid_size", "experiment")})
            summary = existing
            print(f"  merged with the existing summary.json")
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  (could not merge existing summary.json: {exc})")
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    print(f"  wrote summary.json")

    _assert_no_live_io(live_before)
    print(f"\nAll experiments finished in {time.time() - started:.1f}s; "
          f"live stores unchanged.")
    return 0


def build_summary(config: Dict, out: Dict) -> Dict:
    """Machine-readable headline results used by the report and tests."""
    summary: Dict = {
        "experiment": config["experiment_name"],
        "production_slip": bkt_core.PRODUCTION_SLIP,
        "production_guess": bkt_core.PRODUCTION_GUESS,
        "production_t": bkt_core.PRODUCTION_T,
        "mastery_threshold": bkt_core.MASTERY_THRESHOLD,
        "slip_grid_size": len(bkt_core.slip_grid(config)),
    }

    if out["a_selection"]:
        by_variant: Dict[str, List[Dict]] = {}
        for r in out["a_selection"]:
            by_variant.setdefault(r["variant"], []).append(r)
        summary["experiment_a"] = {
            "true_slip": out["a_selection"][0]["true_slip"],
            "by_variant": {
                name: {
                    "within_group_sd": rows[0]["within_group_sd"],
                    "transition_mode": rows[0].get("transition_mode"),
                    "selected_by_seed": [r["selected"] for r in rows],
                    "selected_mean": bkt_core.mean([r["selected"] for r in rows]),
                    "selected_sd": bkt_core.stddev([r["selected"] for r in rows]),
                    "coverage": bkt_core.mean([r["true_in_interval"] for r in rows]),
                    "production_in_interval_rate": bkt_core.mean(
                        [r["production_in_interval"] for r in rows]),
                    "interval_width_mean": bkt_core.mean(
                        [r["interval_width"] for r in rows]),
                }
                for name, rows in sorted(by_variant.items())
            },
        }
        if out.get("a_deltas"):
            delta_summary: Dict[str, Dict] = {}
            for r in out["a_deltas"]:
                key = f"{r['variant']}:{r['comparison']}"
                delta_summary.setdefault(key, []).append(r)
            summary["experiment_a"]["test_delta_vs_production"] = {
                key: {
                    "mean_delta": bkt_core.mean([x["delta"] for x in rows]),
                    "ci_lo": bkt_core.mean([x["ci_lo"] for x in rows]),
                    "ci_hi": bkt_core.mean([x["ci_hi"] for x in rows]),
                    "mean_rel_delta_pct": bkt_core.mean(
                        [x["rel_delta_pct"] for x in rows]),
                    "significant_in_all_seeds": all(x["significant"] for x in rows),
                    "favour_alt_in_all_seeds": all(x["favour_alt"] for x in rows),
                }
                for key, rows in sorted(delta_summary.items())
            }

    if out["b_recovery"]:
        by_variant_b: Dict[str, List[Dict]] = {}
        for r in out["b_recovery"]:
            by_variant_b.setdefault(r["variant"], []).append(r)
        summary["experiment_b"] = {
            "by_variant": {
                name: {
                    "within_group_sd": rows[0]["within_group_sd"],
                    "transition_mode": rows[0].get("transition_mode"),
                    "coverage_overall": bkt_core.mean(
                        [r["true_in_interval"] for r in rows]),
                    "mean_abs_bias": bkt_core.mean([abs(r["bias"]) for r in rows]),
                    "bias_range": [min(r["bias"] for r in rows),
                                   max(r["bias"] for r in rows)],
                    "by_true_slip": ar.recovery_summary(rows),
                }
                for name, rows in sorted(by_variant_b.items())
            },
        }

    if out["c_conditions"]:
        summary["experiment_c"] = [
            {k: r[k] for k in ("condition", "selected_s", "selected_g",
                               "selected_logit_shift", "min_val_log_loss",
                               "interval_lo", "interval_hi")}
            for r in out["c_conditions"]
        ]

    if out["d_heterogeneity"]:
        overall = [r for r in out["d_heterogeneity"] if r["cell_kind"] == "overall"]
        summary["experiment_d"] = [
            {"condition": r["condition"], "selected_global_s": r["selected_global_s"],
             "interval_lo": r["interval_lo"], "interval_hi": r["interval_hi"]}
            for r in overall
        ]

    return summary


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
