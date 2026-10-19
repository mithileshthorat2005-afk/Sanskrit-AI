# BKT Initial-Mastery Prior Experiment (`P(L0)`)

A reproducible, code-based investigation into whether the Sanskrit AI Tutor's
proficiency-based **initial mastery priors** should be retained, revised, or
tested further.

The experiment simulates synthetic learners, then asks how well different
choices of `P(L0)` predict their answers when run through the application's
**real, unmodified** Bayesian Knowledge Tracing update.

> **Scope.** This is an *evaluation* of the existing system. It does not change
> the architecture, authentication, database schema, frontend behaviour, or any
> production API, and it does **not** modify production `INITIAL_MASTERY`,
> `P(T)`, `P(G)`, `P(S)`, or the BKT equations. Nothing is staged, committed or
> pushed by this experiment.

---

## Contents

| Path | Purpose |
| --- | --- |
| `config.json` | Single source of truth: seed, sample sizes, splits, candidate grid, metrics, hidden simulation assumptions, all 13 scenarios, bootstrap settings |
| `bkt_core.py` | Imports production constants; scoring primitives; metrics; near-optimal rule |
| `generate_dataset.py` | Synthetic data generator + schema/distribution validation |
| `run_experiment.py` | Optimisation, bootstrap, held-out evaluation, sensitivity, practical consequences |
| `make_figures.py` | Renders the seven PNG figures from the saved CSVs |
| `test_bkt_research.py` | 88 assertions across the 10 required test properties |
| `README.md` | This file — how to reproduce |
| `REPORT.md` | Methodology, assumptions, findings, limitations, recommendation |
| `data/` | Generated dataset (`observations.csv`, `ground_truth.csv`, `manifest.json`) |
| `results/` | Generated tables: curves, ranges, metrics, deltas, bootstrap, calibration, practical, trajectories, `summary.json` |
| `figures/` | Generated `fig1` … `fig7` `.png` |

Generated artifacts are excluded from version control via the local
`.gitignore` (the dataset alone is ~10 MB and is fully reproducible from
`config.json` + seed).

---

## Reproduce the whole experiment

From `backend/research/bkt_prior_experiment/`:

```bash
# 0. One-time dependency (only matplotlib was missing from the project env).
python -m pip install matplotlib

# 1. Generate the primary synthetic dataset (~10 MB, ~5 s).
python generate_dataset.py --write

# 2. Run the optimisation, bootstrap, held-out evaluation and all 13
#    sensitivity scenarios (~3 minutes), writing results/*.csv + summary.json.
python run_experiment.py

# 3. Render the seven figures (~10 s).
python make_figures.py

# 4. Run the research test suite (88 assertions; exit 0 = all passed).
python test_bkt_research.py
```

Useful variants:

```bash
python generate_dataset.py --list-scenarios     # show the 13 scenario ids
python generate_dataset.py --scenario shifted_up --write   # one scenario only
python run_experiment.py --scenarios primary     # just the main scenario
python run_experiment.py --no-sensitivity        # primary only, skip sensitivities
python run_experiment.py --quick                 # tiny smoke run (~1 s)
python test_bkt_research.py near_optimal_rule    # run one named test group
```

**Expected runtimes** (Python 3.14, this machine): dataset ~5 s;
`run_experiment.py` ~165 s for all 13 scenarios; `make_figures.py` ~10 s;
`test_bkt_research.py` ~45 s.

---

## What the experiment does *not* do

Enforced both by design and by `test_bkt_research.py`:

* **No live data access.** The research tree never imports `sqlite3`,
  `modules.database` or `SQLiteRepository`, and never opens
  `data/sanskrit_ai.sqlite3`, `data/bkt_progress.json` or `data/users.json`.
  SHA-256 hashes of all three are captured before and after and must be
  byte-identical. (`BKTEngine` is deliberately constructed via `__new__`, which
  skips the `__init__` that would create/write the legacy progress file; only
  the pure `update_mastery` method is used.)

  *Nuance for the sake of accuracy:* the integrity guard itself reads those
  three files in order to hash them. That read is verification only — no value
  from them ever enters a computation.

* **No mutation of production constants.** `DEFAULT_PARAMS`, `INITIAL_MASTERY`
  and `CATALOG_LEVEL_TO_TIER` are imported and snapshotted at import time,
  re-checked after the experiment runs, and re-read from source by reloading
  the module. Tests assert the exact documented values.

* **No algorithm replacement.** Scoring calls the production
  `BKTEngine.update_mastery` itself (test 5 asserts bit-identity over a grid of
  states), so the experiment cannot drift from the equations the app runs.

* **No test-set leakage.** Splits are at student level; priors are selected on
  validation only; the test set is evaluated once at the end. Test 7 proves
  this by flipping 500+ test answers and showing the selected prior is
  unchanged.

---

## Data-generating model (experimental assumptions, not measurements)

Each synthetic learner draws a *hidden* initial mastery per lesson, then
generates answers probabilistically:

```
theta_1    ~ Beta(alpha, beta)                      # hidden initial mastery
p(correct) = theta_n * (1 - s) + (1 - theta_n) * g  # guessing / slipping
y_n        ~ Bernoulli(p(correct))
theta_{n+1} = theta_n + (1 - theta_n) * t           # learning transition
```

Answers are **never** assigned from the proficiency label — the group only
selects which *distribution* of hidden mastery a learner is drawn from. In the
primary scenario the DGP uses the production `t/g/s` (0.15 / 0.25 / 0.10) and
population means equal to the production seeds. All of this is recorded in
`config.json` under `dgp` and documented in `REPORT.md`.

---

## Strategies compared

| Key | Description |
| --- | --- |
| `production` | **A.** Current production priors — one value per (proficiency group, tier), 9 cells |
| `common` | **B.** One prior shared by everybody |
| `group_specific` | **C.** One prior per proficiency group (3 values) |
| `group_x_tier` | **E.** One prior per (group, tier) — structural match to production, reported as an extra comparison |
| `oracle_reference` | **D.** The hidden data-generating mean — *simulation only, unavailable in a real deployment* |

The primary metric is **log loss**; Brier score, accuracy at threshold 0.5 and
expected calibration error (10 equal-width bins) are reported alongside it.

---

## Validation and tests

`python test_bkt_research.py` — **88 assertions, 10 properties, exit 0**:

1. Dataset reproducible for a fixed seed (including byte-identical CSV output).
2. Valid labels, catalog lesson ids and contiguous `attempt_index` sequences.
3. No student's observations leak across train/validation/test.
4. Production parameters are loaded and never modified.
5. The experiment's BKT update matches the production formula exactly.
6. Predictions are computed **before** incorporating the answer they score.
7. The optimizer chooses the best *validation* candidate, not the best test one.
8. Near-optimal ranges follow the documented one-standard-error rule.
9. Sensitivity scenarios stay separately identified in every output table.
10. Nothing reads or writes the live SQLite database or legacy progress JSON.

The suite is self-contained: it builds small sandbox datasets in a temporary
directory and deletes them afterwards.
