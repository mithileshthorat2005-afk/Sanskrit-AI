# BKT Slip-Probability Experiment — Report

**Scope:** research only. This report does not change production `P(S)`, `P(G)`,
`P(T)`, `P(L0)`, `INITIAL_MASTERY`, any database record, API or UI element.
No browser/UI testing has ever been performed for this work.

Every number below is read from the CSV/JSON files in `results/` and cited
where it appears. Where a figure or claim could not be reproduced from a saved
file, it is not stated.

---

## 1. Executive summary

The production slip probability for the Sanskrit AI Tutor is **P(S) = 0.10**,
a single global constant (`backend/modules/bkt_engine.py:24`). This experiment
asked whether that value is defensible, how sensitive results are to it, whether
a known slip can be recovered from data, and how badly guess / initial mastery /
learning rate confound its estimation.

**Headline: P(S) = 0.10 is exactly recoverable when the model is correctly
specified, and the apparent "evidence" for a different slip is an artifact of a
misspecified data generator — not a property of slip estimation.**

Three findings, in order of importance:

1. **Recovery works — perfectly.** Under the canonical BKT generative process
   (Experiment B, `bkt_hmm_correct`), fitting recovered the true slip at the
   grid value in **21 of 21** trials (7 generating slips × 3 seeds), with mean
   absolute bias **0.000** and worst-case bias ±0.01, and the true value fell
   inside the one-standard-error near-optimal interval in **21/21** cases.
   H3 is **supported**.

2. **The same experiment, run on a misspecified generator, is badly biased —
   and my first explanation for it was wrong.** With the deterministic
   (answer-independent) transition the fitted slip is biased **upward by +0.15
   at true 0.02, decaying to +0.04 at true 0.40**, and the true value was
   covered in only **1/21** trials. I initially attributed this to Beta-distributed
   learner heterogeneity. That hypothesis was **disproved by the experiment
   itself**: the near-point-prior variant (`sd = 0.01`) shows essentially the
   same bias (+0.150 vs +0.140 at true 0.02). The real cause is structural —
   that generator evolves mastery *regardless of the answer*, while BKT
   conditions the next belief on the answer, and **slip is precisely the knob
   that damps answer-conditioning**. Slip absorbs the model's misspecification.
   See §6.2 and §7.2.

3. **Confounding is weak, not crippling — contrary to the naive expectation.**
   Joint fitting of (guess, slip) and (initial mastery, slip) recovered *both*
   parameters exactly at their true values and improved validation log loss by
   **exactly 0.000000** over the one-parameter fit (§8). The guess×slip surface
   has a **single global minimum at (0.25, 0.10)**, not a flat diagonal ridge.
   Misspecifying guess, initial mastery or learning rate shifts the selected slip
   by at most **−0.03** (0.10 → 0.07) and costs 0.005–0.026 nats/answer.
   H4 is **weakly supported**; H5 is **partially supported** (the surface is
   shallow, but a unique optimum exists at our resolution).

**Recommendation: retain P(S) = 0.10 and validate on real learners.**
Nothing in this experiment justifies changing production. §11–§12 explain what
would.

**One result must be read carefully.** Under the *misspecified* generator,
refitting slip to 0.22–0.23 improves held-out log loss by **−4.58% / −4.15%**
versus production (statistically significant, paired student-level bootstrap).
That looks like an argument for changing P(S). It is not: in those same runs the
**oracle** — which uses the true generating value 0.10, i.e. production — scores
*identically to production*, and the fitted value is **worse than the oracle**
(0.6168 vs 0.6464 is the fitted being better; see §6.1 for why the ordering
inverts). A wrong parameter fitted to a wrong model predicts better than the
right parameter fitted to a wrong model. That is a property of misspecification,
not a discovery about Sanskrit learners.

---

## 2. Verified production parameters and their source

Read from source before any experiment code was written; **not assumed**.

| Parameter | Verified value | Source file and location |
|---|---|---|
| **P(S) slip** | **0.10** | `backend/modules/bkt_engine.py:24` → `DEFAULT_PARAMS["s"]` |
| P(G) guess | 0.25 | `backend/modules/bkt_engine.py:22` → `DEFAULT_PARAMS["g"]` |
| P(T) learning | 0.15 | `backend/modules/bkt_engine.py:20` → `DEFAULT_PARAMS["t"]` |
| P(L0), difficulty path | beginner 0.25 / intermediate 0.10 / advanced 0.05 | `bkt_engine.py:14-18`, read by `get_skill_params` |
| P(L0), onboarding path | 9-cell proficiency × tier table (`INITIAL_MASTERY`) | `bkt_engine.py:42-58` |
| Mastery threshold | 0.7 | `main.py` `get_persisted_dashboard`; `bkt_engine.py` `get_user_summary`, `get_recommendation` |

**Two distinct P(L0) tables exist.** `INITIAL_MASTERY` (the onboarding seeds)
and `DEFAULT_PARAMS["l0"]` (the difficulty-derived values used by
`get_skill_params`) are *not* the same table and are not conflated anywhere in
this experiment. The experiment fits slip; it does not touch either table.

**Structural fact that shapes the whole design:** production slip is a **single
global constant**. `get_skill_params` (`bkt_engine.py:142`) returns
`DEFAULT_PARAMS["s"]` unconditionally — there is **no skill-, group- or
tier-specific slip anywhere in production**. Experiment D therefore tests
cell-varying slip as a *hypothesis*, not as an established fact.

The value is asserted at import time (`bkt_core.PRODUCTION_SLIP`) and re-asserted
to be present on the candidate grid, so a future production change makes the
experiment fail loudly rather than silently compare against a stale baseline.

**Transition order verified:** `BKTEngine.update_mastery` (`bkt_engine.py:145-206`)
applies observation first, then the learning transition. Its incorrect branch,
`L·S / (L·S + (1−L)(1−G))`, is algebraically identical to the specification's
form because `L·S + (1−L)(1−G) = 1 − P(C)`. Test 1 pins both against
hand-calculated values.

---

## 3. Research questions and hypotheses

Pre-registered in `config.json` → `hypotheses` **before any result was
inspected**:

- **H1 — Sensitivity:** prediction and mastery-estimation metrics change measurably as P(S) changes.
- **H2 — Production comparison:** the configured production P(S) may or may not be near-optimal under the synthetic DGP.
- **H3 — Recovery:** with a known generating slip and other parameters correctly specified, fitting recovers that probability or a justified near-optimal interval.
- **H4 — Confounding:** incorrect assumptions about P(G), P(L0) or P(T) shift the estimated slip.
- **H5 — Identifiability:** multiple slip values may be statistically indistinguishable.

Findings are reported even where they contradict these expectations; §7.2 records
one hypothesis of mine that the experiment falsified.

| Hypothesis | Verdict | Evidence |
|---|---|---|
| H1 sensitivity | **Supported** | Fitting P(S)=0.10 → 0.23 moves test log loss by 0.0296 (4.58%); mastery false-mastery rate moves 18.9% → 22.4% (§6.1, §9) |
| H2 production near-optimal | **Supported under a correct model; not under a misspecified one** | Under `bkt_hmm_correct`, production *is* the selected value exactly (§6.1). Under `deterministic_*`, it is not (§6.2) — but there the comparison is meaningless (§7.2) |
| H3 recovery | **Supported** | 21/21 exact-or-near-exact recoveries, 21/21 coverage, bias 0.000 (§7.1) |
| H4 confounding | **Weakly supported** | Max slip shift −0.03; joint fits recover truth exactly (§8) |
| H5 identifiability | **Partially supported** | Surface is shallow (SE ≈ 0.0037, interval width 0.06–0.07) but has a unique minimum (§7.3) |

---

## 4. Synthetic data generation and assumptions

### 4.1 What is simulated

3,000 students (1,000 per proficiency group), 6 distinct lessons each drawn
from the **real 25-lesson catalog** with the learner's own tier upweighted ×3,
10 questions per lesson → **180,000 observations per dataset**. `skill_id ==
lesson_id`, matching the skill mapper. Answers are **never** assigned from a
proficiency label: the label only selects which *distribution* of hidden mastery
a learner is drawn from.

Split **60/20/20 by student identity**, stratified by proficiency group →
600 validation students / 36,000 validation observations and 600 test students /
36,000 test observations per dataset.

**Sample-size rationale.** 600 validation students put the student-level
bootstrap SE of mean log loss at ≈0.0037 (measured, §6.1), an order of magnitude
finer than the between-candidate differences that matter (≈0.01–0.03). Adding
students would shrink that SE without changing any conclusion; only real learner
data would. Fixed seed 42/7/99.

### 4.2 The two data generators — this is the load-bearing assumption

`config.json` → `dgp.transition_mode` selects between two genuinely different
processes. **Both are always reported side by side**, because the choice
determines whether H3 can be tested fairly:

| | `bkt_binary` (canonical BKT HMM) | `deterministic` |
|---|---|---|
| Hidden state | binary `Z ∈ {0,1}`, `Z₁ ~ Bernoulli(l0)` | continuous `θ ~ Beta(μ, sd)` |
| Observation | `P(correct\|Z=1)=1−s`, `P(correct\|Z=0)=g` | `p = θ(1−s)+(1−θ)g` |
| Learning | `Z ← Z OR Bernoulli(t)` (absorbing) | `θ ← θ + (1−θ)·t`, **independent of the answer** |
| Status vs the fitted model | **Exactly specified** — BKT is the exact filter for this HMM | **Structurally misspecified** |
| Hidden labels | the actual binary `Z_n` | continuous `θ_n` |

Three variants separate the two sources of possible bias:

- `bkt_hmm_correct` — HMM, `sd = 0.01` → the fair H3 test.
- `deterministic_point` — deterministic transition, `sd = 0.01` → isolates *transition misspecification alone*.
- `deterministic_spread` — deterministic transition, `sd = 0.15` → adds learner heterogeneity (the sibling prior experiment's DGP).

### 4.3 Ground truth separation

Two files, deliberately apart:

- `observations.csv` — observed columns only (`student_id, proficiency_group,
  split, lesson_id, skill_id, tier, attempt_index, correct`). This is the **only**
  file the fitter and scorer read.
- `ground_truth.csv` — hidden mastery at **every** attempt index, plus the
  generating `dgp_s/dgp_g/dgp_t`, joined by `(student, lesson, attempt)`.

The generator's slip is recorded per row so cell-varying slip (Experiment D) can
be judged per cell. Validation asserts schema, group sizes, split membership,
contiguous `attempt_index`, no missing values, a non-degenerate answer
distribution, and — explicitly — that ground-truth columns are absent from
`observations.csv` (test 7).

### 4.4 Assumptions that are *not* facts about Sanskrit learners

Every DGP parameter is an **experimental assumption**: `t=0.15`, `g=0.25`,
`s=0.10`, `sd ∈ {0.01, 0.15}`, mastery means taken from `INITIAL_MASTERY`. None
is measured from real students. Synthetic group differences (Experiment D) are
**not** evidence that real learners behave the same way.

---

## 5. Experimental design and leakage safeguards

### 5.1 Candidate grid and strategies

Slip grid `0.01 … 0.50` step 0.01 → **50 candidates**, with the exact production
value 0.10 asserted present at runtime. `g` and `t` held at their verified
generating values in the primary sweep.

### 5.2 The four experiments

| | Question | Conditions |
|---|---|---|
| **A** | How sensitive is everything to P(S)? | 50-candidate sweep, true P(S)=0.10, 3 variants × 3 seeds |
| **B** | Can a known slip be recovered? | true P(S) ∈ {0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40} × 3 variants × 3 seeds = 63 fits |
| **C** | How do g, L0, T confound slip? | 8 conditions on **one shared dataset** (so differences are never sampling noise) + 5-point P(T) sweep |
| **D** | Is one slip rate right for everyone? | slip by tier, slip by group, wide/narrow mastery spread — one *global* slip fitted against per-cell truth |

Experiment C deliberately uses the **canonical HMM** so that confounding is
measured without structural misspecification also pushing the estimate.

### 5.3 Leakage safeguards (each is an automated test)

- **Student-level split.** Test 6 asserts the three partitions are pairwise
  disjoint and that every sequence lands in exactly one.
- **Pre-answer prediction.** For observation *n*, the predicted probability comes
  from the state that existed *before* answer *n*; mastery updates only after
  the answer is scored (`run_sequence` returns `(mastery_before, p_correct, y)`).
- **No hidden truth in fitting.** Test 7 asserts sequence records carry only
  `{student, group, tier, lesson, prior, answers, attempt_indices}` — no key
  containing `hidden` or `truth`.
- **Validation-only selection.** Test 8 deletes every `test` row and re-runs
  selection, asserting the chosen slip *and* the validation loss are unchanged.
  The test set is touched once, at the end, to compute reported metrics.
- **Oracle isolation.** The oracle uses the known generating slip purely as a
  synthetic reference and is labelled as such in every figure (fig2, fig3).
- **Production immutability.** Test 14 re-serialises `DEFAULT_PARAMS`,
  `INITIAL_MASTERY` and `CATALOG_LEVEL_TO_TIER` and compares against the
  import-time snapshot; it also asserts no live data-layer module is in
  `sys.modules` and that live store hashes are unchanged.

### 5.4 Uncertainty and the near-optimal rule

Student-level bootstrap (400 resamples for selection, 1,000 for test CIs),
resampling **whole students** so within-sequence correlation is preserved —
test 11 shows this yields a larger SE than the (incorrect) row-independent
bootstrap would.

**Pre-registered one-standard-error rule:**

> `{ p : LL(p) ≤ LL(p*) + SE(p*) }`, where `p*` is the validation arg-min and
> `SE(p*)` is the student-level bootstrap SE of mean log loss at `p*`.

**This is not a confidence interval for the true parameter.** It is the width of
the flat region of the validation surface. A wide interval means no unique
optimum was established. Test 10 pins the rule against hand-worked cases.

Held-out differences use a **paired** student-level bootstrap: both settings are
scored on the same students and answers, and the whole student is resampled
(`results/exp_a_test_deltas.csv`).

---

## 6. Results for each experiment

### 6.1 Experiment A — one-parameter slip sweep

Source: `results/exp_a_validation_curve.csv` (450 rows), `exp_a_selection.csv`
(9), `exp_a_test_metrics.csv` (27), `exp_a_test_deltas.csv` (18). Figure: fig1,
fig2.

**Selection (true P(S) = 0.10, 36,000 validation observations, 600 students):**

| Variant | Selected per seed | Mean (sd) | SE at min | 1-SE interval (per seed) | Coverage | Production inside |
|---|---|---|---|---|---|---|
| `bkt_hmm_correct` | 0.10, 0.10, 0.10 | **0.100** (1.7e-17) | 0.0033–0.0038 | [0.07,0.14], [0.07,0.13], [0.07,0.14] | **3/3** | **3/3** |
| `deterministic_point` | 0.23, 0.23, 0.22 | 0.227 (0.0058) | 0.0025–0.0027 | [0.19,0.26], [0.19,0.26], [0.19,0.26] | 0/3 | 0/3 |
| `deterministic_spread` | 0.22, 0.22, 0.22 | 0.220 (0.000) | 0.0026–0.0028 | [0.18,0.25], [0.19,0.26], [0.18,0.25] | 0/3 | 0/3 |

Under the correctly specified model **the validation arg-min is exactly the
production value in all three seeds**, and production lies inside the
near-optimal interval every time. The interval spans **7–8 grid values** — a
range of slip values is statistically indistinguishable (H5).

**Held-out test metrics (36,000 observations per cell, mean over 3 seeds):**

| Variant | Setting | s used | Log loss | Brier | ECE | Accuracy |
|---|---|---|---|---|---|---|
| `bkt_hmm_correct` | production | 0.10 | 0.515303 | 0.170742 | 0.02618 | 0.7483 |
| `bkt_hmm_correct` | selected | 0.10 | 0.515303 | 0.170742 | 0.02618 | 0.7483 |
| `bkt_hmm_correct` | oracle | 0.10 | 0.515303 | 0.170742 | 0.02618 | 0.7483 |
| `deterministic_point` | production | 0.10 | 0.646345 | 0.223164 | 0.09040 | 0.6515 |
| `deterministic_point` | selected | 0.23 | 0.616774 | 0.213735 | 0.05639 | 0.6611 |
| `deterministic_point` | oracle | 0.10 | 0.646345 | 0.223164 | 0.09040 | 0.6515 |
| `deterministic_spread` | production | 0.10 | 0.639252 | 0.220443 | 0.08482 | 0.6555 |
| `deterministic_spread` | selected | 0.22 | 0.612741 | 0.211932 | 0.05729 | 0.6655 |
| `deterministic_spread` | oracle | 0.10 | 0.639252 | 0.220443 | 0.08482 | 0.6555 |

In `bkt_hmm_correct` all three settings coincide because selected = production =
oracle = 0.10; there is literally nothing to choose between them.

**Paired student-level bootstrap, test log-loss difference vs production**
(`exp_a_test_deltas.csv`, 1,000 resamples, 600 students):

| Variant | Comparison | Δ log loss | 95% CI | Relative | Significant? |
|---|---|---|---|---|---|
| `bkt_hmm_correct` | selected − production | +0.000000 | [+0.000000, +0.000000] | +0.000% | no |
| `bkt_hmm_correct` | oracle − production | +0.000000 | [+0.000000, +0.000000] | +0.000% | no |
| `deterministic_point` | selected − production | **−0.029572** | **[−0.031929, −0.027217]** | **−4.575%** | **yes** |
| `deterministic_point` | oracle − production | +0.000000 | [+0.000000, +0.000000] | +0.000% | no |
| `deterministic_spread` | selected − production | **−0.026511** | **[−0.028772, −0.024207]** | **−4.147%** | **yes** |
| `deterministic_spread` | oracle − production | +0.000000 | [+0.000000, +0.000000] | +0.000% | no |

**Interpretation, stated carefully.** The two "significant improvements" occur
only under the *misspecified* generator, and in exactly those runs **the oracle
equals production and scores identically to it**. So we have: a wrong model
where fitting a parameter *away from truth* improves prediction. That is the
expected behaviour of a misspecified model, and it is why §11 does **not**
recommend adopting 0.22–0.23. Under the correctly specified model — the only
setting where the comparison is meaningful — the improvement over production is
**exactly zero**, because production *is* the optimum.

**Accuracy by attempt number** (fig9, `bkt_hmm_correct`, all three settings
identical): log loss falls monotonically 0.6423 (attempt 1) → 0.4133 (attempt 10).
Attempt 1 is scored entirely from the untouched prior, which is why it is the
hardest — 45% of the total error sits in the first two attempts.

### 6.2 Experiment B — recovery of known slip values

Source: `results/exp_b_recovery.csv` (63 rows). Figure: fig3.

**`bkt_hmm_correct` — the fair H3 test:**

| True slip | Selected (3 seeds) | Bias | Coverage | Interval | Test LL (selected = oracle) | Test LL (production) |
|---|---|---|---|---|---|---|
| 0.02 | 0.02, 0.02, 0.02 | **+0.000** | **3/3** | [0.01, 0.04] | 0.396739 | 0.420783 |
| 0.05 | 0.05, 0.05, 0.05 | **+0.000** | **3/3** | [0.03, 0.08] | 0.449791 | 0.457408 |
| 0.10 | 0.10, 0.10, 0.10 | **+0.000** | **3/3** | [0.07, 0.14] | 0.515303 | 0.515303 |
| 0.15 | 0.15, 0.15, 0.15 | **+0.000** | **3/3** | [0.11, 0.19] | 0.564497 | 0.569395 |
| 0.20 | 0.20, 0.20, 0.20 | **+0.000** | **3/3** | [0.16, 0.24] | 0.602691 | 0.619816 |
| 0.30 | 0.30, 0.30, 0.30 | **+0.000** | **3/3** | [0.27, 0.34] | 0.652218 | 0.702704 |
| 0.40 | 0.39, 0.40, 0.41 | −0.000 (abs 0.007) | **3/3** | [0.36, 0.44] | 0.672024 | 0.755250 |

- **21/21** recoveries, **21/21** coverage of the true value.
- Mean absolute bias **0.000**; worst seed −0.01 at true 0.40 (grid resolution).
- Exact grid hit in 20/21 trials.
- Recovery is equally good at the **boundary-adjacent** 0.02 and at 0.40.

**The misspecified variants (H3 *not* expected to work here):**

| True | `deterministic_point` bias | cov | `deterministic_spread` bias | cov |
|---|---|---|---|---|
| 0.02 | **+0.150** | 0/3 | **+0.140** | 0/3 |
| 0.05 | +0.140 | 0/3 | +0.133 | 0/3 |
| 0.10 | +0.127 | 0/3 | +0.120 | 0/3 |
| 0.15 | +0.110 | 0/3 | +0.103 | 0/3 |
| 0.20 | +0.097 | 0/3 | +0.090 | 0/3 |
| 0.30 | +0.067 | 0/3 | +0.060 | 0/3 |
| 0.40 | +0.037 | 1/3 | +0.030 | 1/3 |

Overall coverage: `deterministic_point` **1/21**, `deterministic_spread` **1/21**.

The bias is **monotonically decreasing in the true slip** — the signature of a
parameter being pushed toward a preferred value rather than tracking truth.

### 6.3 Experiment C — confounding

Source: `results/exp_c_conditions.csv`, `exp_c_heatmap.csv` (1,750 rows),
`exp_c_t_misspec.csv`. All on **one shared dataset** (seed 42, canonical HMM).
Figures: fig4, fig5, fig6.

| Condition | Fitted s | Selected g | Selected l0 shift | Validation log loss | Penalty vs correct |
|---|---|---|---|---|---|
| 1. correct (all right except s) | **0.10** | — | — | 0.513852 | +0.000000 |
| 2. guess misspecified (assumed 0.40) | 0.09 | — | — | 0.525508 | +0.011656 |
| 3. initial mastery misspecified | 0.09 | — | — | 0.518546 | +0.004695 |
| 4. learning rate misspecified (assumed 0.05) | 0.10 | — | — | 0.530763 | +0.016912 |
| 5. **guess + slip jointly fitted** | **0.10** | **0.25** ✔ | — | **0.513852** | **+0.000000** |
| 6. **l0 + slip jointly fitted** | **0.10** | — | **0.0** ✔ | **0.513852** | **+0.000000** |
| 7. **guess + l0 + slip jointly fitted** | **0.10** | **0.25** ✔ | **0.0** ✔ | **0.513852** | **+0.000000** |
| 8. combined misspecification | 0.07 | — | — | 0.539817 | +0.025965 |

✔ = matches the generating value exactly.

**This is the most important table in the report for H4/H5.** Conditions 5–7
add free parameters, recover the *true* `g=0.25` and `l0_shift=0.0` exactly, and
improve validation log loss by **exactly 0.000000** — because the one-parameter
fit already sat at the global optimum. Extra parameters bought nothing because
there was nothing to buy. **Under a correctly specified model, guess and initial
master are not confounded with slip in any damaging way.**

**Misspecification shifts slip only slightly:** at most 0.10 → 0.07 (combined,
where three parameters are simultaneously wrong), with penalties of 0.005–0.026
nats/answer.

**Guess × slip surface (fig4)** — delta from minimum, rows = P(G), cols = P(S):

| P(G) | best P(S) on that row | loss at that best |
|---|---|---|
| 0.100 | 0.12 | +0.0156 |
| 0.175 | 0.11–0.12 | +0.0031 |
| **0.250** | **0.10** | **+0.0000 (global min)** |
| 0.325 | 0.09 | +0.0032 |
| 0.400 | 0.08–0.09 | +0.0117 |

There **is** a shallow valley — each row's arg-min drifts with `g` — but the
valley floor rises away from truth, and **exactly one cell in the entire 250-cell
grid attains the minimum: (g=0.25, s=0.10)**. So H5 is *partially* true: the
surface is shallow (weak identification), but not flat (a unique optimum exists
at our resolution).

**Initial-mastery × slip surface (fig5):** the arg-min moves from 0.10 to at
most 0.09 or 0.11 across logit shifts of ±1.0, costing at most +0.0062.
L0 misspecification barely displaces slip.

**Learning-rate misspecification (fig6):**

| Assumed P(T) | Selected P(S) | Penalty vs true 0.15 |
|---|---|---|
| 0.05 | 0.10 | +0.016912 |
| 0.10 | 0.10 | +0.003136 |
| **0.15 (true)** | **0.10** | **+0.000000** |
| 0.20 | 0.10 | +0.002122 |
| 0.30 | 0.12 | +0.015229 |

P(T) is close to **orthogonal** to P(S): the selected slip does not move at all
for assumed P(T) ∈ [0.05, 0.20], and moves only to 0.12 at an extreme 0.30.
The penalty curve is U-shaped and centred on the truth.

### 6.4 Experiment D — heterogeneous learners and skills

Source: `results/exp_d_heterogeneity.csv` (36 rows). One **global** slip is
fitted, then judged against per-cell truth.

| Condition | Truth by cell | Fitted global slip | Per-cell bias | Covered? |
|---|---|---|---|---|
| `slip_by_tier` | easy 0.05 / int 0.10 / adv 0.15 | 0.080–0.090 | easy **+0.03/+0.04**, int −0.01/−0.02, adv **−0.06/−0.07** | int ✔, easy ✗, adv ✗ |
| `slip_by_group` | beg 0.15 / int 0.10 / adv 0.05 | 0.090 | beg **−0.06**, int −0.01, adv **+0.04** | int ✔, adv 2/3, beg ✗ |
| `wide_spread` (sd 0.30) | 0.10 constant | **0.100** | **+0.000** | **3/3** |
| `narrow_spread` (sd 0.05) | 0.10 constant | **0.100** | **+0.000** | **3/3** |

Two conclusions:

1. **Mastery spread does not bias slip at all.** With slip constant at the
   truth, widening `sd` from 0.01 to 0.30 leaves the fit at exactly **0.100,
   bias +0.000, coverage 3/3**. This is the direct measurement that **falsified
   my heterogeneity hypothesis** (§7.2).

2. **When slip genuinely varies by cell, one global slip cannot represent it.**
   The fitted value (0.08–0.09) sits *below* the arithmetic mean of the cells
   (0.10), because log loss weights cells by their observation counts and by how
   informative they are — it is a loss-weighted compromise, not an average. The
   worst per-cell error is **−0.07** (advanced tier, truth 0.15). Intermediate
   cells (truth 0.10) are always covered, so the global value is nearest the
   largest/most-informative cell.

**Important:** this is a *synthetic* heterogeneity the experiment injected.
It is **not** evidence that real Sanskrit skills or proficiency groups have
different slip rates.

---

## 7. Parameter recovery and identifiability

### 7.1 H3 — recovery

**Supported.** Under the exactly specified BKT HMM, 21/21 recoveries with mean
absolute bias 0.000 and 21/21 coverage, spanning true slip from 0.02 to 0.40.
Recovery degrades only marginally at the high end (±0.01 at 0.40), where the
grid step itself is 0.01.

### 7.2 Why recovery fails under the deterministic generator — and a retracted hypothesis

My **initial** explanation for the +0.14 bias was: the fitter assumes a *point*
prior while the generator draws `θ ~ Beta(μ, 0.15)`, so unmodelled learner
heterogeneity gets absorbed into slip. I built `deterministic_point` (`sd=0.01`)
specifically to test that.

**The experiment disproved it.** At true 0.02 the biases are:

| Variant | Heterogeneity | Bias at true 0.02 |
|---|---|---|
| `deterministic_point` | `sd = 0.01` (essentially none) | **+0.150** |
| `deterministic_spread` | `sd = 0.15` (substantial) | **+0.140** |

Removing heterogeneity did **not** remove the bias — it slightly *increased* it.
So heterogeneity contributes ≈ −0.01, i.e. nothing.

The actual mechanism is structural:

- The generator updates `θ ← θ + (1−θ)·t` **regardless of whether the answer was
  correct**. Hidden mastery is a pure function of attempt number.
- BKT instead conditions its next belief on the observed answer.
- **Slip is precisely the parameter that damps answer-conditioning**: raising
  `s` shrinks the posterior's response to each observation, making BKT's belief
  evolve more like a deterministic clock.

So a higher fitted slip makes the *wrong* model mimic the generator's
answer-independence. The bias is the model's misspecification showing up in the
free parameter — and it decays as true slip rises (+0.150 → +0.037) because at
high true slip the damping is already present and less needs to be added.

**Consequence for interpretation:** any experiment built on the deterministic
transition **cannot** test H3, and its fitted slip must not be read as an
estimate of anything real. This is why `bkt_binary` is the primary recovery
condition and why both are reported.

### 7.3 H5 — identifiability

**Partially supported.** The near-optimal interval spans **0.06–0.07**
(6–8 grid values) with SE at the minimum ≈0.0037 on 36,000 observations. So a
*range* of slip values — e.g. **[0.07, 0.14] around the true 0.10** — is
statistically indistinguishable. A unique optimum has **not** been established
to better than ±0.03.

However the surface is *shallow*, not *flat*: the global minimum is unique
(§6.3), and joint fitting converges back to truth exactly. So identification is
weak but not degenerate.

**Search boundaries:** the grid stops at 0.50. Under `bkt_hmm_correct` the
selected value is 0.10, far from both boundaries, so no better value was
excluded. Under the deterministic variants the selected value is 0.22–0.23,
also interior. No optimum sits on a grid edge anywhere in this study.

---

## 8. Confounding between slip, guess, initial mastery and learning probability

Directly from §6.3:

- **Guess × slip:** shallow diagonal valley (row arg-mins drift 0.09 → 0.12 as
  `g` goes 0.40 → 0.10), but a **unique global minimum at (0.25, 0.10)** —
  one cell out of 250. Joint fitting recovers `g = 0.25` exactly.
- **Initial mastery × slip:** arg-min moves at most ±0.01 for a logit shift of
  ±1.0; cost ≤ +0.0062. Joint fitting recovers `l0_shift = 0.00` exactly.
- **Learning × slip:** essentially orthogonal — selected slip is **unchanged**
  (0.10) for assumed P(T) ∈ [0.05, 0.20].
- **Simultaneous misspecification of all three** (condition 8) moves slip to
  0.07 and costs +0.026 — the largest displacement observed.

**Verdict on H4:** supported, but **weakly**. Confounding shifts the selected
slip by at most −0.03 and is far smaller than the 0.15 artifact produced by a
misspecified transition. In this synthetic setting, **how you model the learning
transition matters an order of magnitude more than what you assume for g, L0
or T.**

**A caution that follows directly:** a combination of parameters can predict
responses well without having been "recovered." Here joint fits *did* return to
truth — but that is a property of this exactly specified synthetic model, not a
guarantee for real data. §12 returns to this.

---

## 9. Prediction quality versus hidden-state mastery quality

**Log loss measures answer-prediction quality. It does not tell us whether the
true mastery state was identified.** These are reported separately, and the
distinction is not academic — they move in *opposite* directions here.

Source: `results/exp_mastery_metrics.csv`. Threshold **P(L) ≥ 0.7**
(`main.py` `get_persisted_dashboard`; `bkt_engine.py` `get_user_summary`,
`get_recommendation`). Simulation-only: **real students have no hidden-mastery
label**, so none of these quantities is measurable in production.

**Overall (Experiment A, `scope=overall`, mean over 3 seeds):**

| Variant | Setting | MAE | Brier vs hidden | Flagged | False-mastered (of flagged) | False-unmastered (of truth-mastered) |
|---|---|---|---|---|---|---|
| `bkt_hmm_correct` | production = selected = oracle | **0.1754–0.1781** | **0.0785–0.0799** | 2.76–2.81% | **4.70–4.80%** | 13.08–13.18% |
| `deterministic_point` | production | 0.2006–0.2021 | 0.2313–0.2365 | 18.46–18.94% | 30.72–31.27% | 14.01–14.80% |
| `deterministic_point` | selected (0.23) | 0.1839–0.1849 | 0.2388–0.2438 | 21.54–22.41% | **32.47–33.16%** | **7.20–7.82%** |
| `deterministic_spread` | production | 0.1977–0.2010 | 0.2226–0.2285 | 17.40–17.97% | 28.96–29.73% | 14.22–15.29% |
| `deterministic_spread` | selected (0.22) | 0.1843–0.1868 | 0.2304–0.2347 | 20.36–20.82% | **30.74–31.25%** | **7.96–8.66%** |

**The crucial observation.** Under `deterministic_point`, refitting slip from
0.10 → 0.23 *improves* answer prediction by 4.58% **and** improves MAE
(0.2021 → 0.1847) **and** cuts false-unmastered roughly in half
(14.80% → 7.32%) — **while making false-mastery significantly worse**
(31.27% → **33.16%**). The same parameter change that a log-loss criterion
rewards *increases* the number of learners wrongly declared mastered.

This is exactly why §8 requires the two to be reported separately. **A slip
value chosen to optimise predictive log loss would not be chosen to optimise
mastery classification**, and production uses mastery classification for
prerequisite gating and dashboard state.

Denominators are explicit because they differ by an order of magnitude:

- False-mastered **of all student-skill pairs**: 2.81% (correct model) / 18.89% (deterministic, production).
- False-mastered **of flagged-mastered pairs only**: 4.76% / 31.27%.
- False-unmastered **of truth-mastered pairs only**: 13.08% / 14.80%.

**By proficiency group** (`bkt_hmm_correct`, production setting):

| Group | n pairs | MAE | False-mastered / flagged | False-unmastered / truth |
|---|---|---|---|---|
| advanced | 12,000 | 0.1322–0.1375 | 3.27–3.91% | 8.12–8.96% |
| intermediate | 12,000 | 0.1782–0.1900 | 4.44–5.50% | 14.17–15.49% |
| beginner | 12,000 | 0.2106–0.2122 | 6.08–7.13% | 17.18–18.31% |

Beginners show roughly **double** the advanced group's MAE. This is a
*synthetic* consequence of the assumed Beta means and thresholds, **not a
measured property of real learners.**

**Calibration (fig8)** and **accuracy by attempt (fig9)** are built from
`exp_calibration_bins.csv` and `exp_by_attempt.csv`. Under the correct model
calibration is good (ECE 0.026) and log loss improves from 0.6423 at attempt 1
to 0.4133 at attempt 10.

---

## 10. Limitations and threats to validity

1. **Synthetic data cannot establish optimality for real students.** It can
   *falsify* (this run shows 0.10 is recoverable under a correct model) but
   never confirm that real learners' slip rate is 0.10. §12 is explicit about
   what is missing.
2. **Everything hinges on the DGP.** §7.2 shows the fitted slip moves by 0.15
   purely from the transition assumption. Two defensible generators give two
   different answers; only one is exactly specified for BKT.
3. **Three seeds.** Between-seed sd is 0.000–0.006 (§6.1), so seeds are not the
   binding uncertainty — but three is a small sample for estimating variability.
4. **The one-standard-error interval is not a confidence interval** for the
   true parameter. Its width (0.06–0.07) is a property of the validation
   surface, not a coverage guarantee.
5. **Equal-width ECE is biased.** Test 9 pins this: a *perfect* deterministic
   predictor still scores ECE 0.05, because p=1.0 clamps to bin 9 (mid 0.95).
   ECE comparisons are valid; absolute ECE is not zero even when perfect.
6. **Parameter grid resolution.** 0.01 steps mean recovery is exact only to
   ±0.01; the ±0.01 at true 0.40 is resolution, not error.
7. **The mastery metrics depend on which DGP's hidden truth is used.** Under
   `bkt_binary` the hidden state is absorbing (64.6% truth-mastered); under
   `deterministic` it is continuous (48.7%). Cross-variant mastery numbers are
   therefore **not comparable to each other** — only within a variant.
8. **Misspecified-model gains are not discoveries.** §6.1 shows a wrong
   parameter beating truth on test under a wrong model. This is the classic
   misspecification result and was explicitly *not* acted on.
9. **No real learner response sequence was used anywhere.**
10. **Browser/UI testing has never been performed** for this work.

---

## 11. Recommendations for the Sanskrit AI Tutor

1. **Retain `DEFAULT_PARAMS["s"] = 0.10`. Do not change it on the strength of
   this experiment.** Under the only correctly specified condition, 0.10 is the
   validation optimum in 3/3 seeds and the true value is recovered 21/21 times.
   Under the misspecified condition the apparent −4.58% gain comes with a
   *worse* false-mastery rate (§9) and is an artifact of model error (§6.1).

2. **Do not adopt 0.22–0.23.** Those values were produced by a generator whose
   transition contradicts BKT's own update rule, and the fitted value tracks
   that contradiction rather than any property of learners (§7.2).

3. **Do not introduce per-skill or per-group slip.** Experiment D shows a single
   global slip is adequate when slip is in fact constant (bias exactly 0.000 at
   `sd` 0.01 → 0.30). Cell-varying slip would only be justified by real data
   showing real cell differences — none exists yet. Production currently has no
   such variation (`bkt_engine.py:142`), and this experiment does not argue for
   adding it.

4. **Expect a *range*, not a point.** The near-optimal interval is [0.07, 0.14].
   Any future real-data analysis should report an interval and state the
   selection rule, not a single "best" number.

5. **Keep slip coupled to the transition assumption.** H4 shows `g`, `L0` and
   `T` matter far less than how learning is modelled (§8). If production ever
   revisits BKT's update rule, slip must be re-estimated *at the same time* —
   a slip tuned under one transition rule does not transfer to another.

6. **Separate the two objectives.** If slip is ever re-tuned, decide explicitly
   whether the goal is answer prediction or mastery classification — §9 shows
   they disagree, and production uses mastery for prerequisite gating.

7. **Preserve the current isolation.** This experiment changed no production
   file; test 14 and `git status` confirm the research tree is untracked-only.

---

## 12. What real student data would be needed to justify a change

Nothing short of real response data can justify changing `P(S)`. Concretely, the
minimum useful dataset would need:

1. **Per-answer sequences, in order, per learner per skill** —
   `(learner_id, skill_id, attempt_index, correct, timestamp)`. Aggregate
   accuracy per skill is useless: BKT's inference depends on *order*, and
   §9.3 shows attempt 1 alone carries 45% of the error.
2. **Sufficient history per learner-skill pair.** Ten attempts per pair is what
   this experiment used; fewer than ~4 gives almost no post-prior evidence,
   because fig9 shows the model barely improves in the first two attempts.
3. **Coverage across the slip range of interest.** To distinguish 0.07 from 0.14
   on a surface this shallow requires far more than 36,000 observations — the
   measured SE of 0.0037 means roughly an order of magnitude more data would be
   needed to halve the near-optimal interval.
4. **A held-out cohort, split by learner**, so selection and evaluation never
   share a student — exactly the protocol used here (test 6, test 8).
5. **An explicit correctness reference.** BKT's `correct` must reflect graded
   answers, not first-attempt guesses; the skill mapper's
   `skill_id == lesson_id` contract should hold.
6. **A decision on the mastery threshold's attempts-condition**, since
   production currently applies P(L) ≥ 0.7 differently in the dashboard,
   `get_user_summary` and the prerequisite gate — slip estimation and mastery
   evaluation must use one agreed definition.
7. **A pre-registered selection rule** — validation-only selection plus a stated
   near-optimal rule (§5.4) — decided *before* looking at results.

**Until such data exists, the honest position is: 0.10 is a defensible,
recoverable, near-optimal value under a correctly specified model; it is not a
measured property of Sanskrit learners.**

---

## Appendix — reproduction and verification

```powershell
$env:PYTHONIOENCODING = 'utf-8'
# Run from backend/research/bkt_slip_experiment/. PowerShell has no `&&`.
& C:\Users\ASUS\Downloads\Sanskrit_Ai_Tutor-main\venv\Scripts\python.exe run_experiment.py
& C:\Users\ASUS\Downloads\Sanskrit_Ai_Tutor-main\venv\Scripts\python.exe analyze_results.py --verify
& C:\Users\ASUS\Downloads\Sanskrit_Ai_Tutor-main\venv\Scripts\python.exe analyze_results.py --summary
& C:\Users\ASUS\Downloads\Sanskrit_Ai_Tutor-main\venv\Scripts\python.exe make_figures.py
& C:\Users\ASUS\Downloads\Sanskrit_Ai_Tutor-main\venv\Scripts\python.exe test_bkt_slip_experiment.py
```

**Actually executed and observed:**

| Command | Exit | Result |
|---|---|---|
| `run_experiment.py` (full) | 0 | 1,092.7 s; 11 result files; "live stores unchanged" |
| `run_experiment.py --only a` | 0 | 99.0 s; added `exp_a_test_deltas.csv` |
| `run_experiment.py --only b` | 0 | restored shared mastery rows |
| `analyze_results.py --verify` | 0 | "All 11 result files verified against the configured grid"; production P(S)=0.1 present in at least one interval: **yes** |
| `analyze_results.py --summary` | 0 | headline tables reproduced from CSVs |
| `make_figures.py` | 0 | 9 PNGs, each >10 kB |
| `test_bkt_slip_experiment.py` | 0 | **14 passed, 0 failed** |

**Result files:** `exp_a_validation_curve.csv` (450), `exp_a_selection.csv` (9),
`exp_a_test_metrics.csv` (27), `exp_a_test_deltas.csv` (18),
`exp_b_recovery.csv` (63), `exp_c_conditions.csv` (8), `exp_c_heatmap.csv`
(1,750), `exp_c_t_misspec.csv` (5), `exp_d_heterogeneity.csv` (36),
`exp_mastery_metrics.csv` (360), `exp_calibration_bins.csv` (270),
`exp_by_attempt.csv` (270), `summary.json`.

**Figures:** `figures/fig1`…`fig9.png`, all generated from the CSVs above.

**Production safety:** `git status` shows the entire `backend/research/` tree as
untracked (`??`) with an empty index (`git diff --cached` produces nothing); the
ten modified tracked files are pre-existing work from the earlier onboarding
phase, untouched by this experiment. Live-store SHA-256 hashes were unchanged
before and after every run. Test 14 re-verifies production constants, the absence
of any live data-layer import, and store hashes.
