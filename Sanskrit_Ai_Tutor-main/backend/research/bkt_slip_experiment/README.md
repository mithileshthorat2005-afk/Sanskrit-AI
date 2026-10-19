# BKT Slip-Probability Experiment

A reproducible, read-only synthetic-data study of the Bayesian Knowledge
Tracing **slip probability P(S)** for the Sanskrit AI Tutor.

**This is research only.** No production constant, configuration, database
table, learner record, API, skill mapper, onboarding flow or frontend file is
read-and-written or modified by anything in this directory.

---

## 1. Verified production values

Read from source before any code was written — *not* assumed:

| Parameter | Value | Source |
|---|---|---|
| **P(S)** slip | **0.10** | `backend/modules/bkt_engine.py:24` — `DEFAULT_PARAMS["s"]` |
| P(G) guess | 0.25 | `backend/modules/bkt_engine.py:22` — `DEFAULT_PARAMS["g"]` |
| P(T) learning | 0.15 | `backend/modules/bkt_engine.py:20` — `DEFAULT_PARAMS["t"]` |
| P(L0) per-difficulty | beg 0.25 / int 0.10 / adv 0.05 | `backend/modules/bkt_engine.py:14-18` via `get_skill_params` |
| P(L0) onboarding seeds | 9-cell proficiency × tier table | `backend/modules/bkt_engine.py:42-58` (`INITIAL_MASTERY`) |
| Mastery threshold | 0.7 | `main.py` `get_persisted_dashboard`, `bkt_engine.py` `get_user_summary`, `get_recommendation` |

**Key structural fact:** production slip is a **single global constant**.
`get_skill_params` (`bkt_engine.py:142`) returns `DEFAULT_PARAMS["s"]`
unconditionally — there is no skill-, group- or tier-specific slip anywhere in
production. This experiment therefore fits a single global slip by default and
treats cell-varying slip as a hypothesis to *test* (Experiment D), not as a
fact.

The production value is **asserted at import time** (`bkt_core.PRODUCTION_SLIP`)
and re-asserted to be present on the candidate grid, so a future change to
production makes the experiment fail loudly instead of silently comparing
against a stale baseline.

## 2. BKT convention

The experiment scores with production's own `BKTEngine.update_mastery`
(`bkt_engine.py:145-206`), which applies, **in this order**:

```
Step 1  P(C)      = L·(1−s) + (1−L)·g
Step 2  posterior = L·(1−s)/P(C)                     if correct
                  = L·s/(L·s + (1−L)·(1−g))          if incorrect
Step 3  L_next    = posterior + (1−posterior)·t
```

Step 2's incorrect branch is algebraically identical to the specification's
`P(L|I) = L·S / (L·S + (1−L)(1−G))`, because `L·S + (1−L)(1−G) = 1 − P(C)`.
So **observation precedes the learning transition**, exactly as specified.
Zero denominators fall back to the prior state rather than dividing by zero.

`BKTEngine` is constructed with `__new__`, deliberately skipping `__init__`
(which would create/open the legacy `data/bkt_progress.json`). The research tree
never imports `main`, `SQLiteRepository` or `MockDB`.

## 3. Pre-registered hypotheses

Recorded in `config.json` → `hypotheses` **before any result was inspected**:

- **H1 — Sensitivity:** prediction and mastery metrics change measurably as P(S) changes.
- **H2 — Production comparison:** the configured production P(S) may or may not be near-optimal under the synthetic DGP.
- **H3 — Recovery:** with a known generating slip and other parameters correctly specified, fitting recovers that slip or a justified near-optimal interval.
- **H4 — Confounding:** wrong assumptions about P(G), P(L0) or P(T) shift the estimated slip.
- **H5 — Identifiability:** multiple slip values may be statistically indistinguishable.

Findings are reported even where they contradict these expectations — see
`REPORT.md` §7 for a case where the initial interpretation of a result had to be
corrected.

## 4. The two data-generating processes (important)

`config.json` → `dgp.transition_mode` selects one of two genuinely different
generators. **The choice determines whether H3 can be tested fairly**, so both
are always reported side by side:

| Mode | Hidden state | Learning | Status vs the fitted model |
|---|---|---|---|
| `bkt_binary` | binary `Z ∈ {0,1}`, `Z₁ ~ Bernoulli(l0)` | `Z ← Z OR Bernoulli(t)` | **Exactly specified** — this is the canonical BKT HMM, of which BKT is the exact filter |
| `deterministic` | continuous `θ ~ Beta(μ, sd)` | `θ ← θ + (1−θ)·t` regardless of the answer | **Structurally misspecified** — BKT conditions the next belief on the observed answer, this generator does not |

Because `deterministic` makes mastery evolve independently of correctness while
BKT conditions on the answer, and because **slip is precisely the knob that
damps answer-conditioning**, any slip fitted under `deterministic` absorbs that
structural mismatch as a positive bias. This is a measured finding, not an
assumption — see `REPORT.md` §6.2.

Two additional variants (`within_group_sd` 0.01 vs 0.15) separate *point prior
vs Beta spread*, so the two sources of bias can be attributed independently.

## 5. Running the experiment

```powershell
$env:PYTHONIOENCODING = 'utf-8'
# PowerShell has no `&&` - run these one line at a time.
& C:\Users\ASUS\Downloads\Sanskrit_Ai_Tutor-main\venv\Scripts\python.exe run_experiment.py
& C:\Users\ASUS\Downloads\Sanskrit_Ai_Tutor-main\venv\Scripts\python.exe analyze_results.py --summary
& C:\Users\ASUS\Downloads\Sanskrit_Ai_Tutor-main\venv\Scripts\python.exe make_figures.py
& C:\Users\ASUS\Downloads\Sanskrit_Ai_Tutor-main\venv\Scripts\python.exe test_bkt_slip_experiment.py
```

Run them from `backend/research/bkt_slip_experiment/`.

| Command | Purpose | Approx. runtime |
|---|---|---|
| `run_experiment.py` | All four experiments, writes `results/` + `summary.json` | ~8–12 min (3,000 students × 3 seeds) |
| `run_experiment.py --quick` | Reduced smoke run into `results_quick/` | ~1–2 min |
| `run_experiment.py --only a` | A single experiment (`a`/`b`/`c`/`d`) | seconds–minutes |
| `run_experiment.py --no-write` | Skip writing `datasets/` | same |
| `generate_dataset.py --name X --write` | Just build + validate one dataset | seconds |
| `make_figures.py` | Rebuild all 9 PNGs from `results/` | seconds |
| `test_bkt_slip_experiment.py` | 14 property tests, exit 0 only if all pass | ~30 s (`--fast` ~15 s) |

Sample size rationale: 1,000 students per proficiency group × 6 lessons ×
10 questions = 180,000 observations per dataset, split 60/20/20 **by student**.
That yields ≈600 validation students (≈36,000 observations) per dataset, which
puts the student-level bootstrap SE of mean log loss near 1e-4 — an order of
magnitude finer than the between-candidate differences we need to resolve.
Adding more students would shrink that SE further but would not change any
conclusion; what *would* change conclusions is real learner data, not more
simulation.

## 6. Leakage safeguards

- **Split by student identity**, stratified by proficiency group. Test 6 asserts the three partitions are pairwise disjoint and that every sequence lands in exactly one.
- **Pre-answer predictions:** for observation *n*, the predicted probability comes from the state that existed *before* answer *n*; mastery updates only after the answer is scored.
- **Hidden truth is a separate file.** `observations.csv` carries observed columns only; `ground_truth.csv` carries `hidden_mastery` and the generating parameters. Test 7 asserts no hidden-truth key ever reaches a fitting record.
- **Validation-only selection.** Test 8 deletes every `test` row and re-runs selection, asserting the chosen slip and validation loss are bit-identical. The test set is touched exactly once, at the end.
- **Oracle never leaks:** the oracle setting uses the known generating slip only as a synthetic reference and is always labelled as such.

## 7. Metrics

**Prediction** (primary: mean binary log loss; also Brier, ECE with 10
equal-width bins, accuracy @ 0.5). These measure *answer-prediction quality*,
**not** whether the true mastery state was identified.

**Mastery estimation** (simulation-only): MAE and Brier against the hidden
state, false-mastery and false-unmastered at threshold P(L) ≥ 0.7. Every rate
carries its denominator explicitly — *all student-skill pairs*, *flagged-mastered
pairs only*, or *hidden-mastered pairs only* — because those three numbers differ
substantially and are not interchangeable.

**Uncertainty:** student-level bootstrap (resampling whole students preserves
within-sequence correlation), 400 resamples for selection, 1,000 for test CIs.

**Near-optimal interval** (pre-registered): `{p : LL(p) ≤ LL(p*) + SE(p*)}`,
where `p*` is the validation arg-min and `SE(p*)` is the student-level bootstrap
SE of the mean log loss evaluated at `p*`. **This is not a confidence interval
for the true parameter** — it is the width of the flat region of the validation
surface. A wide interval means no unique optimum was established.

## 8. Outputs

```
config.json                  seeds, grids, sample sizes, splits, hypotheses
bkt_core.py                  read-only production imports + equations + metrics
generate_dataset.py          reproducible synthetic data + validation
run_experiment.py            Experiments A–D
analyze_results.py           metrics, bootstrap, selection, recovery
make_figures.py              9 PNGs, built only from saved CSVs
test_bkt_slip_experiment.py  14 property tests
README.md  REPORT.md
datasets/    observations.csv (observed only) + ground_truth.csv + manifest
results/     per-candidate validation, held-out metrics, recovery, confounding,
             heterogeneity, mastery, calibration, by-attempt + summary.json
figures/     fig1 … fig9.png
```

## 9. What this experiment does **not** do

- It does **not** change production `P(S)`, `P(G)`, `P(T)`, `P(L0)` or `INITIAL_MASTERY`.
- It does **not** replace BKT, or alter any update equation.
- It does **not** modify the database, learner records, seed data, auth, APIs or the frontend.
- It does **not** prove any slip value is optimal **for real students**. Synthetic data can falsify a claim (e.g. "0.10 is recoverable under this DGP") but cannot establish ground truth about human learners.
- It does **not** claim hidden-state mastery accuracy is measurable on real data — real students have no hidden-mastery label.
- **Browser/UI testing has never been performed** for this work.

## 10. Dependencies

Reuses only what is already installed: `numpy` (already required by the sibling
prior experiment) and `matplotlib` (already present). Nothing is installed,
uninstalled or replaced. `pytest` is absent by project convention, so the test
suite is a plain script with PASS/FAIL lines and an exit code.
