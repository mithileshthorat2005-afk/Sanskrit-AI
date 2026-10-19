# REPORT — BKT Initial-Mastery Prior (`P(L0)`) Experiment

**Repository:** Sanskrit AI Tutor · **Location:** `backend/research/bkt_prior_experiment/`
**Production `INITIAL_MASTERY` was not modified. Nothing was staged, committed or pushed.**

---

## Headline

Under every one of the 13 simulated scenarios, a **structurally matched**
group×tier optimizer (`E`) beat the current production priors on held-out log
loss — but only by **0.02 % to 1.08 %** (0.0001–0.0071 nats/answer), and the
optimizer independently converged on values close to the ones production already
uses. Conversely, **collapsing** the three proficiency groups into one prior is
significantly *worse* in 12 of 13 scenarios.

**Recommendation: retain the current configuration and validate it on real
students.** The evidence does not support changing production values
automatically. See [§9](#9-recommendation).

---

## 1. The exact current production configuration

Read from `backend/modules/bkt_engine.py`, not from documentation.

**`INITIAL_MASTERY`** (keyed by proficiency group → difficulty tier) — the values
the onboarding popup seeds on a learner's first selection:

| proficiency group | `easy` | `intermediate` | `advanced` |
|---|---|---|---|
| `beginner` | **0.20** | **0.05** | **0.01** |
| `intermediate` | **0.55** | **0.30** | **0.08** |
| `advanced` | **0.80** | **0.60** | **0.30** |

**BKT parameters — `DEFAULT_PARAMS`:**

| symbol | value | meaning |
|---|---|---|
| `t` | **0.15** | `P(T)` — learning per attempt |
| `g` | **0.25** | `P(G)` — guess correctly while not knowing |
| `s` | **0.10** | `P(S)` — slip while knowing |

**Two separate `l0` tables exist.** Besides `INITIAL_MASTERY` above,
`DEFAULT_PARAMS["l0"] = {beginner: 0.25, intermediate: 0.10, advanced: 0.05}`
is returned by `get_skill_params()` whenever *no mastery record exists yet*. It
is a distinct, difficulty-derived table (its own comments say "Difficulty 1-4 /
5-7 / 8-10"). **This experiment optimises `INITIAL_MASTERY`**, the onboarding
seeds, because those are what a brand-new user receives. The secondary table is
documented here so it is not silently conflated.

**Tier vocabulary:** `CATALOG_LEVEL_TO_TIER = {beginner→easy, intermediate→intermediate, advanced→advanced}`;
`difficulty_band()` maps difficulty ≤4 → `easy`, ≤7 → `intermediate`, else `advanced`.
The catalog `level` is preferred, `difficulty_band` is the fallback.

**Mastery threshold: `0.7`, used consistently in all five places it appears**
(`main.py` `mastered_skills`; `bkt_engine.get_user_summary`; the prerequisite
gate in `get_recommendation`; the lessons-page bar accent; dashboard copy
"70% mastery"). **The threshold is not what varies — the *attempts condition*
attached to it is:**

- `/dashboard` `mastered_skills` and `get_user_summary` count `mastery ≥ 0.7`
  **regardless of attempt count** → this is where "mastered with zero attempts"
  surfaces.
- The prerequisite gate also ignores attempts → a lesson can become *eligible*
  purely from the seed.
- The lessons-page bar renders width 0 and the label "Not attempted yet" until
  `hasGradedAttempts` is true, so that page visually suppresses the same value.

This experiment does not change any of that; it only quantifies it (§8).

---

## 2. Synthetic population assumptions and sample sizes

All values live in `config.json`. **These are experimental assumptions, not
measured properties of Sanskrit learners.**

**Population** (seed **42**, fully configurable):

| quantity | value |
|---|---|
| proficiency groups | `beginner`, `intermediate`, `advanced` |
| students per group | **1,000** (3,000 total) |
| lessons per student | 6, drawn *distinctly* from the real 25-lesson catalog |
| questions per lesson | 10 (matches real quiz lengths) |
| **total observations** | **180,000** |
| split | 60 / 20 / 20 → 1,800 / **600** / **600** students, stratified by group |
| test observations | 36,000 (12,000 per group), over 3,600 (student, lesson) pairs |

Learners up-weight their own tier by **×3** while sampling, so all nine
(group, tier) cells receive data — a learner's own tier is likelier but not
exclusive, as in the real app where any lesson is reachable.

**Hidden data-generating process** — per (student, lesson):

```
theta_1     ~ Beta(alpha, beta)        # method-of-moments from (mu[group][tier], sd=0.15)
p(correct)  = theta_n * (1 - s) + (1 - theta_n) * g
y_n         ~ Bernoulli(p(correct))
theta_{n+1} = theta_n + (1 - theta_n) * t      # learning, independent of correctness
```

- Primary scenario: `t/g/s = 0.15 / 0.25 / 0.10` (the production values) and
  `mu[group][tier] = INITIAL_MASTERY[group][tier]` exactly.
- `theta` clipped to `[0.001, 0.999]`.

**Answers are never assigned from the proficiency label.** The label only
chooses a *distribution* to draw hidden mastery from; correctness comes from the
Bernoulli draw. The realised answer rates — **beginner 0.598, intermediate
0.667, advanced 0.741** — emerge from the simulation rather than being written
in, and are held under test 2.

**Why DGP = production for the primary scenario.** It is the natural null
hypothesis ("the seeds are unbiased population means") and it gives a built-in
method check: if the plumbing is right, the oracle reference must coincide with
production exactly. It does — to the bit (`Δ = 0.0000000000`). Scenarios that
*violate* the null are what reveal whether production is robust.

**Other settings:** candidate grid `0.01 … 0.99` step `0.01` = **99 candidates**
(all nine production values are exact multiples of 0.01 and the code *asserts*
their presence rather than assuming it); primary metric **log loss**; accuracy
threshold **0.5**; ECE with **10** equal-width bins; student-level bootstrap of
**500** draws (selection) and **1,000** draws (test CIs) at 95 %.

---

## 3. Selected prior per proficiency group

Chosen on the **validation** split only (600 students).

| group | **selected `P(L0)`** | production tiers for that group |
|---|---|---|
| beginner | **0.05** | 0.20 / 0.05 / 0.01 |
| intermediate | **0.23** | 0.55 / 0.30 / 0.08 |
| advanced | **0.52** | 0.80 / 0.60 / 0.30 |
| *(common prior, all groups)* | **0.26** | — |

These are **strategy C** numbers — *one* prior per group. Production uses *nine*
values (3 groups × 3 tiers), so C is structurally coarser by construction; see
§5 for why that distinction decides the interpretation.

For the structurally matched strategy **E** (one prior per group×tier) the
optimizer independently selected:

| group × tier | E selected | production | Δ |
|---|---|---|---|
| beginner / easy | 0.09 | 0.20 | −0.11 |
| beginner / intermediate | 0.01 | 0.05 | −0.04 |
| beginner / advanced | 0.01 | 0.01 | 0.00 |
| intermediate / easy | 0.59 | 0.55 | +0.04 |
| intermediate / intermediate | 0.14 | 0.30 | −0.16 |
| intermediate / advanced | 0.04 | 0.08 | −0.04 |
| advanced / easy | 0.86 | 0.80 | +0.06 |
| advanced / intermediate | 0.62 | 0.60 | +0.02 |
| advanced / advanced | 0.21 | 0.30 | −0.09 |

Eight of nine land within 0.11 of production, most within 0.06 — **given a DGP
built from the production seeds, the optimizer reproduces values close to
production without being told to.**

---

## 4. Near-optimal intervals

**Definition (primary rule, `config.bootstrap.rule = "within_1_se_of_min"`):**

> Let `p̂` be the validation arg-min and `LL(p)` the mean validation log loss.
> The near-optimal set is `{ p : LL(p) ≤ LL(p̂) + SE_boot(p̂) }`, where
> `SE_boot` is the student-level bootstrap standard error of the mean log loss
> *at `p̂`*.

The bootstrap resamples **whole students**, preserving within-student answer
correlation that a row-level bootstrap would destroy.

A stricter **paired-difference** interval is also recorded
(`{ p : mean(LL(p) − LL(p̂)) ≤ 1 · SE_boot of that difference }`); because the
same draws score both candidates, it removes shared variance and is therefore
narrower. Both are in `results/near_optimal_ranges.csv` and both are asserted
against the written rule by test 8.

| group | selected | min log loss | SE at min | **primary interval** | paired interval | prod. tiers inside primary? |
|---|---|---|---|---|---|---|
| beginner | 0.05 | 0.683533 | 0.004866 | **[0.01, 0.21]** | [0.03, 0.07] | **all three** (0.01, 0.05, 0.20) |
| intermediate | 0.23 | 0.662665 | 0.004719 | **[0.07, 0.42]** | [0.19, 0.25] | 0.08, 0.30 — **0.55 outside** |
| advanced | 0.52 | 0.586514 | 0.006133 | **[0.30, 0.74]** | [0.49, 0.56] | 0.30, 0.60 — **0.80 outside** |

**Read this carefully.** The curves in Figure 1 are *single-prior* curves
(strategy C), while production assigns three different values per group. Placing
a tier-specific production value on a single-prior curve is therefore
suggestive, not decisive: it says "if you had to pick one number for this group,
where does each production value sit?" The apples-to-apples test is strategy
`E` vs `A` on held-out data (§5).

The primary intervals are **wide** (widths 0.20 / 0.35 / 0.44): no single value
is uniquely optimal. The paired intervals are much tighter and are the better
guide to where the *difference* between candidates actually resolves.

---

## 5. Held-out predictive performance

Evaluated **once** on the test split (36,000 answers), never used for selection.

**Overall:**

| strategy | log loss | Brier | accuracy@0.5 | ECE | Δ log loss vs A | relative |
|---|---|---|---|---|---|---|
| **A. production** | 0.642881 | 0.222033 | 0.653000 | 0.087900 | — | — |
| B. common | 0.649654 | 0.225602 | 0.637222 | 0.091717 | +0.006762 | **+1.05 %** (worse) |
| C. group-specific | 0.645267 | 0.223443 | 0.646750 | 0.095036 | +0.002386 | **+0.37 %** (worse) |
| **E. group×tier** | **0.641510** | **0.221669** | 0.652056 | 0.094981 | **−0.001367** | **−0.21 %** (better) |
| D. oracle *(sim only)* | 0.642881 | 0.222033 | 0.653000 | 0.087900 | 0.000000 | 0.00 % |

**Log loss by group:**

| group | A | B | C | E | best |
|---|---|---|---|---|---|
| beginner | 0.685205 | 0.691953 | 0.684001 | **0.683425** | E |
| intermediate | 0.653470 | 0.654676 | 0.654301 | **0.651840** | E |
| advanced | 0.589968 | 0.602334 | 0.597499 | **0.589266** | E |

**Interpretation, stated plainly:**

- **B is a significant regression.** Collapsing the three groups loses real
  signal — the groups genuinely differ in the simulation.
- **C is worse overall, and its deficit is concentrated in `advanced`
  (−0.0075, significant).** Most of C's loss is *structural*: one number cannot
  represent three tiers. It is not evidence that the group distinction is wrong.
- **E is better, but barely.** Since E has the same 9-cell structure as A, this
  is the fair comparison — and the gain is ~0.0014 nats, i.e. **a fifth of one
  percent**. Statistically resolved (600 test students), practically negligible.
- **The oracle equals production exactly**, confirming the primary DGP.

---

## 6. Confidence intervals

Paired student-level bootstrap, **1,000** draws, **95 %**, on held-out test log
loss. Positive = strategy worse than production.

| comparison | group | mean Δ | 95 % CI | significant? |
|---|---|---|---|---|
| **B − A** | beginner | +0.006783 | [+0.005518, +0.007881] | **yes — B worse** |
| **B − A** | intermediate | +0.001203 | [+0.000034, +0.002510] | **yes — B worse** |
| **B − A** | advanced | +0.012332 | [+0.009804, +0.014843] | **yes — B worse** |
| **B − A** | overall | **+0.006762** | **[+0.005709, +0.007854]** | **yes — B worse** |
| C − A | beginner | −0.001211 | [−0.002446, +0.000016] | no |
| C − A | intermediate | +0.000835 | [−0.000588, +0.002276] | no |
| **C − A** | advanced | +0.007544 | [+0.005611, +0.009371] | **yes — C worse** |
| **C − A** | overall | **+0.002386** | **[+0.001485, +0.003331]** | **yes — C worse** |
| **E − A** | beginner | −0.001785 | [−0.002645, −0.000988] | **yes — E better** |
| **E − A** | intermediate | −0.001601 | [−0.002655, −0.000491] | **yes — E better** |
| **E − A** | advanced | −0.000710 | [−0.001356, −0.000092] | **yes — E better** |
| **E − A** | overall | **−0.001367** | **[−0.001850, −0.000864]** | **yes — E better** |
| D − A | all | 0.000000 | [0, 0] | identical by construction |

The narrow CIs reflect the large simulated sample; they are **not** evidence of
precision about real learners.

---

## 7. Sensitivity analysis

13 scenarios, **each reported separately and never pooled** (test 9 asserts
every scenario × group pair has its own row). See `results/sensitivity` rows in
`near_optimal_ranges.csv`, `strategy_deltas.csv`.

**Δ log loss of each strategy vs production, overall:**

| scenario | B common | C group-specific | **E group×tier** |
|---|---|---|---|
| primary | +1.054 % | +0.371 % | **−0.213 %** |
| dgp_no_tier | +0.222 % | −0.652 % | **−0.618 %** |
| shifted_up | +1.716 % | +0.752 % | **−0.181 %** |
| shifted_down | +0.427 % | −0.053 % | **−0.621 %** |
| group_overlap | **−0.447 %** | −0.500 % | **−1.078 %** |
| wide_spread | +1.306 % | +0.532 % | **−0.015 %** |
| low_learning | +0.355 % | −0.325 % | **−0.941 %** |
| high_learning | +0.929 % | +0.368 % | **−0.102 %** |
| low_guess_slip | +1.210 % | +0.181 % | **−0.669 %** |
| high_guess_slip | +0.330 % | +0.102 % | **−0.072 %** |
| short_sequences | +1.953 % | +0.721 % | **−0.152 %** |
| seed_7 | +1.318 % | +0.601 % | **−0.147 %** |
| seed_99 | +1.467 % | +0.481 % | **−0.251 %** |

**Findings:**

1. **E beats production in 13/13 scenarios**, but the margin ranges from
   0.015 % to 1.078 % — never material.
2. **B loses in 12/13.** The single exception is `group_overlap`, the one
   scenario constructed so the groups genuinely *are* identical — exactly when a
   shared prior should win. This is a meaningful validation of the design.
3. **C is mixed** (better in 4/13, worse in 9/13), driven by whether the
   scenario removes the tier effect (`dgp_no_tier`, `shifted_down`) or not.
4. **The optimum is sensitive to assumptions that are unknown in production.**
   Selected priors swing widely: advanced ranges from **0.40**
   (`low_learning`, DGP `t=0.05`) to **0.68** (`high_learning`, `t=0.35`), and
   to **0.18** under `group_overlap`. Intermediate ranges 0.10 → 0.41.
   Figure 6 shows the near-optimal bands shifting with the scenario.
5. **Independent validation of the scenario plumbing:** the oracle equals
   production *exactly* in all 9 scenarios whose `mean_mode` is `production`, and
   differs in all 4 whose `mean_mode` differs. Asserted by test 9.

**Do the groups genuinely differ?** Under this simulation, yes: B (a shared
prior) is significantly worse in 12/13 scenarios. But the answer is partly
*designed in*, because the DGP assigns different means per group. The honest
statement is: **if** proficiency groups have different true mastery
distributions — as the seeding scheme already assumes — then a shared prior
costs predictive accuracy, and the existing group distinction is justified.

---

## 8. Practical consequences for the application

Measured on the test split: **3,600 (student, lesson) pairs**, 1,200 per group.
"Initially mastered" = prior ≥ the production threshold **0.7**, with **zero**
attempts recorded.

### 8.1 Lessons mastered with zero attempts

| strategy | beginner | intermediate | advanced | overall |
|---|---|---|---|---|
| **A. production** | 0 (0.00 %) | 0 (0.00 %) | **340 (28.33 %)** | **340 (9.44 %)** |
| B. common (0.26) | 0 | 0 | 0 (0.00 %) | 0 (0.00 %) |
| C. group-specific | 0 | 0 | 0 (0.00 %) | 0 (0.00 %) |
| E. group×tier | 0 | 0 | **340 (28.33 %)** | 340 (9.44 %) |
| D. oracle *(sim only)* | 0 | 0 | 340 (28.33 %) | 340 (9.44 %) |

**This reproduces the previously reported limitation numerically.** The effect
comes entirely from `advanced / easy = 0.80 ≥ 0.70`: an advanced-graded learner
starts with ~29 % of their attempted lessons showing `≥ 0.70` mastery on the
dashboard and unlocking the prerequisite gate — before a single answer is
recorded. Beginner and intermediate seeds (max 0.20 and 0.55) never cross 0.70,
so they are unaffected.

### 8.2 False-mastery vs false-unmastered (simulation-only)

Against the hidden data-generating state (`theta ≥ 0.7`). **These two rates
trade off, so both must be read together:**

| strategy | false-**mastered** (of init-mastered) | false-**unmastered** (of truly mastered) | hidden mastered |
|---|---|---|---|
| **A. production** | 84 → **24.71 %** | 178 → **41.01 %** | 434 |
| B. common | 0 → **0.00 %** | 434 → **100.00 %** | 434 |
| C. group-specific | 0 → **0.00 %** | 434 → **100.00 %** | 434 |
| E. group×tier | 84 → **24.71 %** | 178 → **41.01 %** | 434 |

For production, broken down by group:

| group | init-mastered | false-mastered | hidden mastered | false-unmastered |
|---|---|---|---|---|
| beginner | 0 | 0 | 6 | 6 (100.00 %) |
| intermediate | 0 | 0 | 54 | 54 (100.00 %) |
| advanced | 340 | 84 (24.71 %) | 374 | 118 (31.55 %) |

**This is the key practical trade-off.** Strategies B and C eliminate
zero-attempt mastery completely — but only by flagging *nothing* as mastered,
which makes them miss **100 %** of learners who genuinely already know the
material. Production has the opposite bias: it over-claims 24.71 % of what it
flags for advanced learners while correctly catching 256 of 374 genuinely
mastered lessons. **There is no free reduction here; the error rates move
against each other.**

### 8.3 Classification churn

Share of (student, lesson) pairs whose mastered/unmastered label differs from
the seed, by number of observations:

| strategy | after 1 | after 3 | after 5 | after 10 |
|---|---|---|---|---|
| A. production | 14.00 % | — | — | **81.69 %** |
| B. common | 0.00 % | — | — | 90.89 % |
| C. group-specific | 19.25 % | — | — | 90.75 % |
| E. group×tier | 14.00 % | — | — | 81.36 % |

By group under production: **beginner** 0.00 % → 86.50 %; **intermediate**
13.67 % → 91.08 %; **advanced** 28.33 % → 67.50 %.

Two observations:
- **Every** zero-attempt-mastered advanced lesson (340/340 = 28.33 %) flips after
  a single answer — the seed is immediately contradicted by evidence.
- Production's higher seeds make classifications *more stable* than B/C over
  ten answers (81.7 % vs ~91 % churn), because B/C start further from the
  learners' eventual steady state.

### 8.4 Provisional seed vs evidence-supported mastery

Mean `|L₀ − L̂(n)|`, overall:

| strategy | n=1 | n=3 | n=5 | n=10 | signed at n=10 |
|---|---|---|---|---|---|
| A. production | 0.203 | 0.300 | 0.407 | **0.592** | **+0.588** |
| B. common | 0.208 | 0.335 | 0.464 | 0.667 | +0.665 |
| C. group-specific | 0.210 | 0.344 | 0.468 | 0.662 | +0.658 |

The gap **widens** with experience and is strongly positive: observed answers
push mastery *up* relative to the seed. By ten answers the provisional seed and
the evidence-supported estimate differ by ~0.59 on average — i.e. **the seed
matters mainly for the first few answers**, which is precisely when it is least
justified. Production's seeds track the evidence slightly better than the
alternatives (0.592 vs 0.667).

*(Per-checkpoint per-group values are in `results/practical_consequences.csv`.)*

### 8.5 What this means

The zero-attempt-mastery limitation is **real and quantified** (28.33 % of an
advanced learner's lessons, 9.44 % overall), and it is a direct consequence of
`advanced/easy = 0.80` crossing the 0.7 threshold. But the experiment also shows
the naive "fix" — lowering seeds so nothing starts mastered — simply relocates
the error to 100 % false-unmastered. **Reducing this effect requires a change in
how mastery is *displayed* (e.g. gating on attempt count, as the lessons page
already does), not a change in the prior.** This report proposes no such change.

---

## 9. Recommendation

### Retain the current configuration, and validate it on real students.

**Reasons to retain:**

1. **No strategy materially outperforms production.** The best alternative (E)
   gains 0.21 % relative — statistically resolved, practically negligible, and
   measured entirely on simulated data.
2. **The cheap simplifications are regressions.** A single shared prior is
   significantly worse in 12/13 scenarios (up to 1.95 % worse).
3. **The near-optimal intervals are wide and mostly overlap production's
   values.** Production's beginner tier values all sit inside the interval; two
   of three do for intermediate and advanced.
4. **Under a DGP built from the production seeds, the optimizer independently
   returns values close to production** — 8 of 9 cells within 0.11, most within
   0.06.
5. **Changing production `INITIAL_MASTERY` would alter learner-facing behaviour
   for every future user**, on the strength of synthetic evidence alone.

**Reasons to test further rather than declare it optimal:**

1. **The optimum is highly sensitive to assumptions nobody can currently
   measure** — the advanced-selected prior moves 0.40 → 0.68 depending on the
   assumed learning rate. Synthetic data cannot resolve that.
2. **Two production values sit outside the single-prior near-optimal band**
   (`advanced/easy = 0.80`, `intermediate/easy = 0.55`). Under the
   correctly-specified scenario these are the two values the structured
   optimizer would most want to change (E picks 0.86 and 0.59 respectively, so
   in fact it keeps them high — the band is a different comparison; see §4).
3. **The zero-attempt-mastery effect is genuine** and is not solved by any prior
   choice tested here.

**Specifically: do not adopt the optimised values automatically.** If this is to
be revisited, the decisive experiment needs **real learner answer sequences** —
log loss and calibration computed on actual students, ideally with the
proficiency groups held out — not more simulation.

---

## 10. Generated artifacts

All under `backend/research/bkt_prior_experiment/`:

**Scripts**
| path | role |
|---|---|
| `config.json` | seed, sample sizes, assumptions, grid, metrics, 13 scenarios |
| `bkt_core.py` | production imports, scoring primitives, metrics, near-optimal rule |
| `generate_dataset.py` | dataset generation + validation |
| `run_experiment.py` | optimisation, bootstrap, held-out evaluation, sensitivity, practical analysis |
| `make_figures.py` | renders `fig1`…`fig7` |
| `test_bkt_research.py` | 88 assertions / 10 required properties |
| `README.md` | reproduction instructions |

**Dataset**
| path | contents |
|---|---|
| `data/observations.csv` | 180,000 rows — **observed fields only** (8 columns) |
| `data/ground_truth.csv` | 18,000 rows — hidden simulation parameters, keyed by (student, lesson) |
| `data/manifest.json` | schema, group/split sizes, answer rates, checksums, DGP |
| `.gitignore` | excludes generated `*.csv` (≈10 MB, reproducible) |

**Ground truth is deliberately kept out of `observations.csv`.** The two §4
requirements — "each observation should contain `true_initial_mastery`" and
"keep ground-truth information separate… the model must never receive it as an
input feature" — are satisfied by storing truth in its own file, joined only for
the simulation-only measures. Test 2 asserts the observation rows contain no
truth column; scoring reads only `observations.csv`.

**Results** (`results/`)
| file | rows |
|---|---|
| `validation_curves.csv` | 5,148 — every candidate × group × scenario |
| `near_optimal_ranges.csv` | 39 — selected, SE, primary and paired intervals |
| `strategy_test_metrics.csv` | 260 — log loss / Brier / accuracy / ECE |
| `strategy_deltas.csv` | 208 — Δ vs production |
| `bootstrap_intervals.csv` | 208 — 95 % paired CIs |
| `calibration_bins.csv` | 1,950 — reliability-diagram bins |
| `practical_consequences.csv` | 260 — §8 measures |
| `mastery_trajectories.csv` | 2,145 — mean mastery per observation index |
| `summary.json` | production config, selected priors per scenario |

**Figures** (`figures/`)
| file | content |
|---|---|
| `fig1_prior_optimization_curves.png` | candidate `P(L0)` vs validation log loss, 3 groups, production priors + near-optimal band |
| `fig2_brier_comparison.png` | Brier: production / common / group-specific / group×tier / oracle |
| `fig3_heldout_performance.png` | held-out log loss, Brier and ECE by group |
| `fig4_calibration.png` | reliability diagrams per group |
| `fig5_mastery_trajectories.png` | mastery over observations 0–10, seed vs optimized |
| `fig6_sensitivity.png` | near-optimal ranges across all 13 scenarios |
| `fig7_zero_attempt_mastery.png` | zero-attempt mastery, false-mastery, false-unmastered, churn |

**Report:** `REPORT.md` (this file) · **Reproduce:** `README.md`

---

## 11. Commands to reproduce everything

```bash
cd backend/research/bkt_prior_experiment

python -m pip install matplotlib          # only dependency missing from the project env

python generate_dataset.py --write         # ~5 s   -> data/*.csv + manifest.json
python run_experiment.py                   # ~165 s -> results/*.csv + summary.json
python make_figures.py                     # ~10 s  -> figures/fig1..fig7.png
python test_bkt_research.py                # ~45 s  -> 88 assertions, exit 0
```

Optional: `python run_experiment.py --quick` (≈1 s smoke run),
`--scenarios primary`, `--no-sensitivity`, `python generate_dataset.py --list-scenarios`.

---

## 12. Conclusions, separated by evidence class

### ✅ Established by code and tests (88/88 passing, exit 0)

- The synthetic dataset is **reproducible**: same seed → byte-identical CSV.
- Labels, catalog lesson ids, `skill_id == lesson_id` and contiguous
  `attempt_index` sequences are valid; no missing values; answers are
  probabilistic, not label-derived.
- **No student leaks** across train/validation/test; no (student, lesson)
  sequence straddles a split.
- **Production `t/g/s` (0.15/0.25/0.10), `INITIAL_MASTERY` and
  `CATALOG_LEVEL_TO_TIER` are loaded, never modified**, and unchanged after the
  full run and after a module reload.
- The experiment's BKT update is **bit-identical** to `BKTEngine.update_mastery`
  over a 22-case grid; the research engine skips `BKTEngine.__init__` and cannot
  create or open the progress file.
- **Predictions pre-date their answers**: flipping the last answer leaves the
  last prediction unchanged while changing the next state.
- **Selection uses validation only**: flipping 500+ test answers does not move
  the selected prior.
- **Near-optimal ranges obey the written rule** exactly, and the bootstrap is
  reproducible for a fixed seed.
- **All 13 scenarios remain separately identified** in every output table; the
  oracle differs from production in exactly the 4 scenarios whose `mean_mode`
  differs.
- **The live SQLite DB, legacy `bkt_progress.json` and `users.json` are
  byte-identical before and after**; `sqlite_repository` is never imported; no
  research module imports or opens the database layer.

### 🔬 Supported by these synthetic experiments (conditional on the assumptions)

- A shared prior across proficiency groups is **worse** in 12/13 scenarios.
- Collapsing the three tiers into one prior per group is **worse overall**,
  mostly for `advanced`.
- A structurally matched group×tier optimizer is **better in 13/13 scenarios,
  but by only 0.02–1.08 %** — the optimizer lands close to production values.
- Near-optimal intervals are **wide**; no single prior is uniquely optimal.
- The selected optimum is **sensitive to the assumed learning/guessing/slip
  parameters**, which production cannot currently observe.
- Production seeds cause **28.33 % of an advanced learner's attempted lessons
  (9.44 % overall) to show `≥ 0.70` mastery with zero attempts**, and the error
  rates of every alternative trade against each other rather than improving.

### ❌ Still unverified — requires real students

- **Which `P(L0)` values are actually best for real Sanskrit learners.** No
  conclusion here transfers without validation on real answer sequences.
- Whether the three proficiency groups genuinely have different true mastery
  distributions (the simulation *assumes* they do, because production does).
- Whether `0.80` / `0.55` are too high, or the tier structure itself is right.
- The true `P(T)`, `P(G)`, `P(S)` for this learner population — the dominant
  source of sensitivity in §7.
- Whether the zero-attempt-mastery effect bothers real users, or how best to
  address it.

---

## 13. Scope, disclosures and limitations

- **Production was not modified.** `INITIAL_MASTERY`, `P(T)/P(G)/P(S)`, the BKT
  equations, database schema, authentication, frontend behaviour and APIs are
  untouched. No mastery records or seed data were modified.
- **Nothing was staged, committed or pushed.** All work is local and uncommitted.
- **No live data was read or written** beyond the integrity guard hashing three
  files to prove they were unchanged (§"What the experiment does not do").
- **One new dependency was installed: `matplotlib`** (3.11.2, plus its own
  transitive deps). It was absent from the project environment and is required
  by the figure specification. Nothing was uninstalled or replaced; `numpy` and
  `pandas` were already present and unchanged. `requirements.txt` files were not
  modified — `README.md` documents the install.
- **Scope kept to new files.** Everything lives under
  `backend/research/bkt_prior_experiment/`; no existing script was edited.
- **Browser/UI testing has never been performed for this project**, and nothing
  in this task changed any UI — the work is HTTP/file-level and verified by the
  test suite plus full reruns of the experiment.
- **No fabricated results.** Every number above is transcribed from the
  generated CSVs; every test result reported as passing was actually executed
  (88/88, exit 0). Figures were rendered from those same CSVs and inspected.
