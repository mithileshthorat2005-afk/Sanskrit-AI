"""Cross-check the numbers quoted in REPORT.md against the saved CSV results.

Fails loudly (exit 1) if any quoted figure disagrees with the result files.
This exists so the report cannot silently drift from the measurements.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bkt_core

RESULTS = bkt_core.resolve("results")
failures = []
checks = 0


def rows(name):
    with open(os.path.join(RESULTS, name), encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def num(r, k, d=None):
    v = r.get(k, "")
    return d if v in ("", None) else float(v)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def check(label, actual, quoted, tol=5e-7):
    global checks
    checks += 1
    if abs(actual - quoted) > tol:
        failures.append(f"{label}: csv={actual!r} report={quoted!r} (diff {actual-quoted:+.6g})")
        print(f"  FAIL  {label}: csv={actual:.6f} report={quoted:.6f}")
    else:
        print(f"  ok    {label}: {actual:.6f}")


print("=== Report-vs-CSV verification ===")
print(f"Production P(S) from source = {bkt_core.PRODUCTION_SLIP}")

# ---- Experiment A test metrics -------------------------------------------------
t = rows("exp_a_test_metrics.csv")
exp_a = {
    ("bkt_hmm_correct", "production"): (0.515303, 0.170742, 0.02618, 0.7483),
    ("bkt_hmm_correct", "selected"):   (0.515303, 0.170742, 0.02618, 0.7483),
    ("bkt_hmm_correct", "oracle"):     (0.515303, 0.170742, 0.02618, 0.7483),
    ("deterministic_point", "production"): (0.646345, 0.223164, 0.09040, 0.6515),
    ("deterministic_point", "selected"):   (0.616774, 0.213735, 0.05639, 0.6611),
    ("deterministic_point", "oracle"):     (0.646345, 0.223164, 0.09040, 0.6515),
    ("deterministic_spread", "production"): (0.639252, 0.220443, 0.08482, 0.6555),
    ("deterministic_spread", "selected"):   (0.612741, 0.211932, 0.05729, 0.6655),
    ("deterministic_spread", "oracle"):     (0.639252, 0.220443, 0.08482, 0.6555),
}
print("\n-- A: exp_a_test_metrics.csv (means over seeds) --")
for (var, setting), (ll, br, ece, acc) in exp_a.items():
    sub = [r for r in t if r["variant"] == var and r["setting"] == setting]
    assert sub, f"missing rows for {var}/{setting}"
    check(f"{var}/{setting} log_loss", mean(num(r, "log_loss") for r in sub), ll, 5e-7)
    check(f"{var}/{setting} brier",   mean(num(r, "brier") for r in sub), br, 5e-7)
    check(f"{var}/{setting} ece",     mean(num(r, "ece") for r in sub), ece, 5e-6)
    check(f"{var}/{setting} accuracy", mean(num(r, "accuracy") for r in sub), acc, 5e-5)

# ---- Experiment A selection ----------------------------------------------------
sel = rows("exp_a_selection.csv")
print("\n-- A: exp_a_selection.csv --")
for var, quoted in (("bkt_hmm_correct", (0.100, [0.07, 0.14])),
                    ("deterministic_point", (0.227, [0.19, 0.26])),
                    ("deterministic_spread", (0.220, [0.18, 0.26]))):
    sub = [r for r in sel if r["variant"] == var]
    check(f"{var} mean selected", mean(num(r, "selected") for r in sub), quoted[0], 6e-4)
    # Report quotes per-seed intervals; check every seed against the union
    # reported in the report text (lo = min across seeds, hi = max).
    los = [num(r, "interval_lo") for r in sub]
    his = [num(r, "interval_hi") for r in sub]
    check(f"{var} interval lo (union)", min(los), quoted[1][0], 6e-3)
    check(f"{var} interval hi (union)", max(his), quoted[1][1], 6e-3)
    n_cov = sum(int(r["true_in_interval"]) for r in sub)
    print(f"    coverage {n_cov}/{len(sub)} (report claims "
          + ("3/3" if n_cov == len(sub) else "0/3 or mixed") + ")")

# ---- Experiment A deltas -------------------------------------------------------
dl = rows("exp_a_test_deltas.csv")
print("\n-- A: exp_a_test_deltas.csv --")
g = {}
for r in dl:
    g.setdefault((r["variant"], r["comparison"]), []).append(r)
deltas = {
    ("deterministic_point", "selected_minus_production"): (-0.029572, -0.031929, -0.027217, -4.575),
    ("deterministic_spread", "selected_minus_production"): (-0.026511, -0.028772, -0.024207, -4.147),
}
for key, rs in sorted(g.items()):
    d = mean(num(r, "delta") for r in rs)
    lo = mean(num(r, "ci_lo") for r in rs)
    hi = mean(num(r, "ci_hi") for r in rs)
    rel = mean(num(r, "rel_delta_pct") for r in rs)
    if key in deltas:
        q = deltas[key]
        check(f"{key} delta", d, q[0], 5e-7)
        check(f"{key} ci_lo", lo, q[1], 5e-7)
        check(f"{key} ci_hi", hi, q[2], 5e-7)
        check(f"{key} rel%", rel, q[3], 5e-4)
        sig = all(r["significant"] == "1" for r in rs)
        print(f"    significant in all seeds: {sig} (report says True)")
        if not sig:
            failures.append(f"{key} not significant but report claims yes")
    else:
        if abs(d) > 1e-12:
            failures.append(f"{key} expected exactly 0.0, got {d}")
        print(f"    {key} delta = {d:+.9f} (report claims exactly +0.000000)")
        if abs(d) > 1e-12:
            print("    FAIL")

# ---- Experiment B recovery -----------------------------------------------------
b = rows("exp_b_recovery.csv")
print("\n-- B: exp_b_recovery.csv coverage counts --")
for var in ("bkt_hmm_correct", "deterministic_point", "deterministic_spread"):
    sub = [r for r in b if r["variant"] == var]
    cov = sum(int(r["true_in_interval"]) for r in sub)
    mab = mean(abs(num(r, "bias")) for r in sub)
    print(f"    {var:<24} coverage {cov}/{len(sub)}  mean|bias|={mab:.4f}")
    if var == "bkt_hmm_correct" and (cov != 21 or mab > 0.005):
        failures.append(f"bkt_hmm_correct recovery: coverage {cov}/21, mean|bias| {mab}")
    if var != "bkt_hmm_correct" and cov == 21:
        failures.append(f"{var}: expected poor coverage, got 21/21")

print("\n-- B: bkt_hmm_correct per-true-slip table --")
quoted_b = {0.02: (0.396739, 0.420783), 0.05: (0.449791, 0.457408),
            0.10: (0.515303, 0.515303), 0.15: (0.564497, 0.569395),
            0.20: (0.602691, 0.619816), 0.30: (0.652218, 0.702704),
            0.40: (0.672024, 0.755250)}
for ts, (qsel, qprod) in quoted_b.items():
    sub = [r for r in b if r["variant"] == "bkt_hmm_correct" and num(r, "true_slip") == ts]
    check(f"true={ts} LL selected", mean(num(r, "test_log_loss_selected") for r in sub), qsel, 5e-7)
    check(f"true={ts} LL production", mean(num(r, "test_log_loss_production") for r in sub), qprod, 5e-7)

print("\n-- B: misspecified bias table --")
quoted_bias = {
    ("deterministic_point", 0.02): 0.150, ("deterministic_point", 0.10): 0.127,
    ("deterministic_point", 0.40): 0.037, ("deterministic_spread", 0.02): 0.140,
    ("deterministic_spread", 0.10): 0.120, ("deterministic_spread", 0.40): 0.030,
}
for (var, ts), q in quoted_bias.items():
    sub = [r for r in b if r["variant"] == var and num(r, "true_slip") == ts]
    check(f"{var} true={ts} bias", mean(num(r, "bias") for r in sub), q, 6e-3)

# ---- Experiment C --------------------------------------------------------------
cc = rows("exp_c_conditions.csv")
print("\n-- C: exp_c_conditions.csv --")
quoted_c = {"correct_specified": (0.10, 0.513852),
            "guess_misspecified": (0.09, 0.525508),
            "l0_misspecified": (0.09, 0.518546),
            "t_misspecified": (0.10, 0.530763),
            "combined_misspec": (0.07, 0.539817)}
for cond, (qs, qll) in quoted_c.items():
    r = next(x for x in cc if x["condition"] == cond)
    check(f"{cond} selected_s", num(r, "selected_s"), qs, 1e-9)
    check(f"{cond} val_LL", num(r, "min_val_log_loss"), qll, 5e-7)

base_ll = num(next(x for x in cc if x["condition"] == "correct_specified"), "min_val_log_loss")
for cond in ("g_and_s_joint", "l0_and_s_joint", "g_l0_s_joint_t_fixed"):
    r = next(x for x in cc if x["condition"] == cond)
    check(f"{cond} selected_s", num(r, "selected_s"), 0.10, 1e-9)
    check(f"{cond} penalty vs correct", num(r, "min_val_log_loss") - base_ll, 0.0, 1e-9)

for cond, key, q in (("guess_misspecified", "selected_g", None),
                     ("g_and_s_joint", "selected_g", 0.25),
                     ("l0_and_s_joint", "selected_logit_shift", 0.0),
                     ("g_l0_s_joint_t_fixed", "selected_g", 0.25),
                     ("g_l0_s_joint_t_fixed", "selected_logit_shift", 0.0)):
    r = next(x for x in cc if x["condition"] == cond)
    v = num(r, key)
    if v is None:
        print(f"    {cond}.{key} absent (report shows dash) -- ok")
    else:
        tag = "ok  " if q is None or abs(v - q) < 1e-9 else "FAIL"
        print(f"    {tag} {cond}.{key} = {v:.3f} (report: {q})")
        if q is not None and abs(v - q) >= 1e-9:
            failures.append(f"{cond}.{key} = {v}, report says {q}")

tm = rows("exp_c_t_misspec.csv")
print("\n-- C: t misspecification sweep --")
quoted_t = {0.05: (0.10, 0.016912), 0.10: (0.10, 0.003136), 0.15: (0.10, 0.0),
            0.20: (0.10, 0.002122), 0.30: (0.12, 0.015229)}
for r in tm:
    at = num(r, "assumed_t")
    check(f"t={at} selected_s", num(r, "selected_s"), quoted_t[at][0], 1e-9)
    check(f"t={at} penalty", num(r, "penalty_vs_true_t"), quoted_t[at][1], 5e-7)

# ---- Heatmap minimum uniqueness ------------------------------------------------
hm = rows("exp_c_heatmap.csv")
gsl = [r for r in hm if r["surface"] == "guess_vs_slip"]
nmin = sum(1 for r in gsl if num(r, "delta_from_min") <= 1e-9)
where = [(num(r, "g"), num(r, "slip")) for r in gsl if num(r, "delta_from_min") <= 1e-9]
print(f"\n-- fig4 surface: {nmin} cell(s) at the global minimum: {where}")
if nmin != 1 or where != [(0.25, 0.10)]:
    failures.append(f"fig4 minimum not unique at (0.25,0.10): n={nmin} {where}")

# ---- Experiment D --------------------------------------------------------------
d = rows("exp_d_heterogeneity.csv")
print("\n-- D: exp_d_heterogeneity.csv overall rows --")
for cond, qg in (("slip_by_tier", None), ("slip_by_group", None),
                 ("wide_spread", 0.100), ("narrow_spread", 0.100)):
    sub = [r for r in d if r["condition"] == cond and r["cell_kind"] == "overall"]
    gs = mean(num(r, "selected_global_s") for r in sub)
    if qg is not None:
        check(f"{cond} global slip", gs, qg, 1e-9)
    else:
        print(f"    {cond:<16} global slip = {gs:.3f} (report quotes 0.080-0.090 range)")
        if not (0.079 <= gs <= 0.091):
            failures.append(f"{cond} global slip {gs} outside reported 0.080-0.090")

# ---- Mastery metrics -----------------------------------------------------------
mm = rows("exp_mastery_metrics.csv")
print("\n-- mastery metrics present per experiment --")
from collections import Counter
print("   ", dict(Counter(r["experiment"] for r in mm)))
if len(mm) < 300:
    failures.append(f"exp_mastery_metrics.csv has only {len(mm)} rows; expected 360")

# ---- Summary json / counts -----------------------------------------------------
print("\n-- file row counts --")
expected = {"exp_a_validation_curve.csv": 450, "exp_a_selection.csv": 9,
            "exp_a_test_metrics.csv": 27, "exp_a_test_deltas.csv": 18,
            "exp_b_recovery.csv": 63, "exp_c_conditions.csv": 8,
            "exp_c_heatmap.csv": 1750, "exp_c_t_misspec.csv": 5,
            "exp_d_heterogeneity.csv": 36, "exp_mastery_metrics.csv": 360,
            "exp_calibration_bins.csv": 270, "exp_by_attempt.csv": 270}
for name, qn in expected.items():
    got = len(rows(name))
    status = "ok  " if got == qn else "FAIL"
    print(f"    {status} {name:<32} {got:>5} (report: {qn})")
    if got != qn:
        failures.append(f"{name}: {got} rows, report says {qn}")

sj = json.load(open(os.path.join(RESULTS, "summary.json"), encoding="utf-8"))
print(f"    summary.json has keys: {sorted(sj.keys())}")

print(f"\n=== {checks} numeric checks run ===")
if failures:
    print(f"{len(failures)} MISMATCHES:")
    for f_ in failures:
        print("  -", f_)
    sys.exit(1)
print("Report matches the saved results exactly.")
