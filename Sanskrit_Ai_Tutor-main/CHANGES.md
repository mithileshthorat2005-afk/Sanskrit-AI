# CHANGES.md — what was changed locally, and why

**Status: everything described here is LOCAL and UNCOMMITTED.** Nothing has been staged,
committed or pushed. `git status` in the repository root shows the full working tree.

Last updated: **16 October 2026**. At the end of this pass the backend (`:8005`) and
frontend (`:3000`) processes were terminated; no server is running.

This file exists so the working tree can be reviewed, tested and committed deliberately
rather than by accident. It lists **every** modified and new file, the reason for the
change, the measurement behind it, and — just as important — what was *not* touched.

---

## Table of Contents

- [1. Summary of every change](#1-summary-of-every-change)
- [2. New files](#2-new-files)
- [3. Files present in the tree but not authored here](#3-files-present-in-the-tree-but-not-authored-here)
- [4. Phase A — AI provider wiring (Ollama Cloud)](#4-phase-a--ai-provider-wiring-ollama-cloud)
- [5. Phase B — server-side security fixes](#5-phase-b--server-side-security-fixes)
- [6. Phase C — frontend fixes](#6-phase-c--frontend-fixes)
- [7. Phase D — grammar engine generalization](#7-phase-d--grammar-engine-generalization)
- [8. Phase E — evaluation harness and sealed datasets](#8-phase-e--evaluation-harness-and-sealed-datasets)
- [9. Phase F — documentation](#9-phase-f--documentation)
- [10. Before / after measurements](#10-before--after-measurements)
- [11. Tests added and how they stay independent](#11-tests-added-and-how-they-stay-independent)
- [12. Reproducing the results](#12-reproducing-the-results)
- [13. Known limitations and remaining failures](#13-known-limitations-and-remaining-failures)
- [14. Outstanding manual actions](#14-outstanding-manual-actions)
- [15. Deliberately not changed](#15-deliberately-not-changed)

---

## 1. Summary of every change

Diff against `HEAD` (`bf3ac32`), counted with `git diff --stat`:

| File | ± lines | Phase | Why |
|---|---:|---|---|
| `backend/modules/nlp_processor.py` | 853 | A, D | Provider routing + grammar generalization rules |
| `backend/modules/noun_analyzer.py` | 101 | D | Surface variants and paradigm-based accusative |
| `backend/modules/auth.py` | 114 | B | Username/role policy, crash-proof login |
| `backend/modules/odd_one_out.py` | 72 | B | Server-side answer grading |
| `frontend/src/app/grammar/page.tsx` | 30 | C | Surface why the AI pass did not run |
| `backend/modules/translator.py` | 27 | A | Mirror the same provider routing; fix retired model id |
| `backend/modules/auth_dependency.py` | 23 | B | `isinstance` guards on the user store |
| `frontend/src/components/SupportChat.tsx` | 11 | C | Do not render a blank assistant bubble |
| `backend/main.py` | 7 | B | Map grading `ValueError` → HTTP 400 |
| `backend/modules/snake_ladder.py` | 7 | B | Pick the word once, not twice |
| `README.md` | 120 | F | Corrected inaccuracies; documented routing, suites, limits |
| **Total (tracked)** | **1 556 + / 206 −** across 14 files | | |

Two tracked files in that diff are **live application data, not code** — see
[§3](#3-files-present-in-the-tree-but-not-authored-here).

---

## 2. New files

| File | Purpose |
|---|---|
| `backend/evaluate_generalization.py` | Runs the sealed dev + held-out sets through the engine and prints accuracy, P/R/F1, FP/FN, correction exact-match, uncertainty precision/coverage, per-split and per-dimension breakdowns. `--baseline` replays the pre-change engine through a shim; `--validate-baseline` proves the shim reproduces the recorded baseline exactly. |
| `backend/test_generalization.py` | 63 rule-level assertions (R1–R9) covering every fix: positive, negative, boundary and lexical cases. Exits non-zero on any failure. |
| `backend/data/generalization_dev.json` | 30 development cases across dimensions A–D plus an `accepted_nonsense` control set. Used during development. |
| `backend/data/generalization_heldout.json` | 38 held-out cases (34 determinate + 4 uncertainty) in splits A–D. Sealed before the fixes were written; never used for tuning. |
| `CHANGES.md` | This file. |

Untracked scratch artifacts also in `backend/data/`, **not** authored as part of this work:
`new_progress.json`, `zz_audit_0a2ae3d1_progress.json`,
`zz_audit_36eddd61_progress.json`.

---

## 3. Files present in the tree but not authored here

`git status` shows three modified data files. They were changed by **live application
activity**, not by this work, and must not be reverted:

| File | Change | Cause |
|---|---|---|
| `backend/data/sanskrit_words.csv` | +7 lines (103 → 110) | Words added through the running API |
| `backend/data/sanskrit_sentences.json` | +336 lines | Sentences added through the running API |
| `backend/data/bkt_progress.json` | 43 lines | Mastery updates from real quiz/grammar attempts |

The startup log reports `SanskritNLP: lexicon loaded 1239 words from disk`, which is the
combined on-disk lexicon (all `data/*.csv`), not this one file's line count.

The database (`users`, `grammar_attempts`) was **not** deleted or restored at any point.
Two throwaway accounts created by verification scripts, `zz_audit_0a2ae3d1` and
`zz_audit_36eddd61`, remain in the store by explicit decision to delete nothing.

---

## 4. Phase A — AI provider wiring (Ollama Cloud)

**Files:** `backend/modules/nlp_processor.py`, `backend/modules/translator.py`

### What

- **Ollama Cloud added as the first-choice provider.** The key shape `<32 hex>.<token>`
  is unique to Ollama, so it is matched with `OLLAMA_KEY_SHAPE = re.compile(r'^[0-9a-f]{32}\.')`.
  Because the shape is distinctive, a key pasted into the wrong environment variable still
  routes correctly.
- **Routing is now one consistent order**, identical in the grammar engine and the
  translator, so the two AI features no longer come up on different providers:

  ```
  OLLAMA_API_KEY set, or key matches <32 hex>.   → Ollama Cloud  https://ollama.com/v1
  key starts with gsk_                           → Groq          https://api.groq.com/openai/v1
  anything else                                  → xAI (Grok)    https://api.x.ai/v1
  no key                                          → rule-based only
  ```

  Defaults: `gemma4:31b-cloud` (Ollama), `openai/gpt-oss-120b` (Groq), `grok-4-fast`
  (xAI). `AI_MODEL` overrides any of them. `XAI_API_KEY` stays supported so the existing
  Render deployment keeps working untouched.
- **Fixed a retired model id.** `translator.py` hardcoded `grok-beta`, which xAI retired;
  a valid key therefore returned 400/404 and translation silently fell back to the local
  dictionary. Now `grok-4-fast`, overridable with `AI_MODEL`.
- **Failures are made visible instead of silent.** `last_ai_error` carries the provider's
  own message and `_resolve_model()` re-reads `GET /models` after a model-related
  rejection, so "no key", "bad key", "retired model" and "provider down" are
  distinguishable rather than all looking like an unexplained fallback.

### Verified

Ollama Cloud checked live: real translation returned with `source: Ollama Cloud_ai`.

---

## 5. Phase B — server-side security fixes

**Files:** `backend/modules/auth.py`, `backend/modules/auth_dependency.py`,
`backend/main.py`, `backend/modules/odd_one_out.py`, `backend/modules/snake_ladder.py`

These are input-validation and crash-safety fixes only. No authentication scheme,
password hashing, token format, CORS policy or deployment configuration was altered.

1. **Odd One Out grading was client-trustable** (`odd_one_out.py`, `main.py`).
   `/game/odd/answer` received the question back from the browser and read
   `correct_index` / `correct_word` straight out of it, so a caller could send their own
   choice and be graded correct every time. Added `resolve_question()`, which re-matches
   the echoed `(category, options)` pair against the server's own `QUESTIONS` catalog and
   uses the catalog's own indices. All 8 categories and all 8 `(category, options)` pairs
   are unique, so the match is unambiguous. A payload that matches nothing raises
   `ValueError`, which `main.py` maps to HTTP 400.
2. **Login returned HTTP 500 for a bad credential** (`auth.py`). A record missing its
   `password` key raised `KeyError`; a corrupt `users.json` that parsed to a list raised
   `AttributeError`. Both now fall through to a normal `None` → HTTP 401. Uses
   `record.get('password', '')` so an empty stored value simply fails verification.
3. **Every protected endpoint could be turned into a 500**
   (`auth_dependency.py`, three functions). A hand-edited record that is a string/list/
   number crashed `user_data['role']` with `AttributeError`. Added `isinstance(..., dict)`
   guards in `get_current_user`, `get_optional_user` and `get_current_user_id`; the token
   has already proved identity, so defaults are used instead.
4. **Signup accepted arbitrary usernames** (`auth.py`). The signup form performs no
   client-side validation and `users.json` is a flat object keyed by username, so an empty
   name, a name with leading/trailing whitespace, a control character, or an unbounded
   string all produced an account that could not be logged into again or that corrupted
   the file. Added `username_policy_error()` (3–50 chars, no inner/leading/trailing
   whitespace, no control characters) — validated against the **raw** value, because
   silently stripping would create an account the same keystrokes cannot reopen.
5. **`role` was unrestricted** (`auth.py`). It is stored straight from the request body.
   Added `role_policy_error()` with the allowlist `student` / `teacher` / `admin`.
   Both raise `ValueError`, which `/auth/signup` already maps to HTTP 400.
6. **Snake & Ladder asked the same question twice** (`snake_ladder.py`).
   `pick_random_word()` was called once for the `sanskrit` field and again for `hint`, so
   the two could come from *different* words. Now picked once and reused.
7. **Odd One Out `ValueError` surfaced as 500** (`main.py`). Wrapped in `try/except` →
   HTTP 400 with the explanatory message.

---

## 6. Phase C — frontend fixes

**Files:** `frontend/src/components/SupportChat.tsx`,
`frontend/src/app/grammar/page.tsx`

1. **SupportChat rendered an empty bubble.** The server answers an unsupported question
   with an empty `response` and a populated `error`, still as HTTP 200. The client read
   only `response`. Now falls back `response → error →` a fixed apology.
2. **The AI failure was invisible.** `grammar/page.tsx` rendered nothing when
   `ai_verified` was false, so a learner could not tell the AI pass had been attempted
   and rejected. Added an `AI check unavailable: {ai_error}` status panel (only rendered
   when the backend supplies `ai_error`, which rule-based mode never does), stating that
   the analysis shown comes from the rule-based engine.

No API contract, routing, state management or styling system was changed. Both files
added to the existing types and the existing `AlertCircle` icon already imported.

---

## 7. Phase D — grammar engine generalization

**Files:** `backend/modules/nlp_processor.py`, `backend/modules/noun_analyzer.py`

The goal was to make the checker work on words, inflections and sentences it has not
seen, **without changing the architecture**: same 5-layer classifier, same check
pipeline, same score formula, same response shape. Seven rules, each individually
measurable:

| # | Rule | Problem it removes |
|---|---|---|
| **R1** | Sandhi-resilient lookup — a form ending in `ो`/`र्` is retried against a dictionary entry ending in `ः` | Unseen `सिंहो` / `व्याघ्रो` fell through to *Unknown* |
| **R2** | Surface variants — `ं` ↔ `म्` tried in Layer 1 **before** any lower layer can claim the word | `गच्छन्ति` / `कर्मन्` mis-analysed or missed |
| **R3** | `(stem, paradigm)` attestation with a **self-confirmation guard** | A parse was believed because the engine could produce it itself — not independent evidence |
| **R4** | Same-stem number contestation → leave the number blank | The engine invented a number it had two contradictory readings for |
| **R5** | Nominal-sentence guard | Sanskrit sentences with no finite verb (`अहं विद्यार्थी।`) raised a *no verb* error |
| **R6** | Destination rule derives the accusative from the verb's own paradigm instead of a hardcoded stem list | Rule fired only for a handful of special-cased verbs |
| **R7** | `accusative_form()` looks the cell up in the paradigm table and returns `None` when the cell is absent | Fabricated accusatives for paradigms that do not have that form |

Supporting changes: `_surface_variants`, `_build_stem_attestation`, the ambiguity branch
in `_disambiguate`, `_destination_accusative` / `_fix_destination_accusative`, and the
matching `analyze()` variant loop plus `accusative_endings` / `accusative_form()` in
`noun_analyzer.py`.

### Three regressions introduced during development, then fixed

Honest disclosure — none of these survived into the final state, and each is covered by
a test now:

1. **`सिंहाः` / `गुरवः`** broke when R3 was first restricted too tightly (same-stem
   requirement rejected legitimate attestations).
2. **`गुरवः`** — same cause.
3. **`त्वं`** — Layer-1 precedence had to apply across *all* spellings, not just the first
   variant tried.

### Label corrections made before any measurement

- **`H-U01`** duplicated a development sentence. Replaced before the first run.
- **`H-D03`** was factually wrong: `आवाम्` is **1st person dual**, so `गच्छावः` is the
  correct form. The label was corrected for both the baseline and the improved run —
  i.e. it was wrong for the *old* engine too, and did not flatter the new one.

No benchmark label or threshold was edited to improve a metric.

---

## 8. Phase E — evaluation harness and sealed datasets

**New:** `backend/evaluate_generalization.py`, `backend/test_generalization.py`,
`backend/data/generalization_dev.json`, `backend/data/generalization_heldout.json`

- **Splits are separate files.** Development (30 cases + accepted-nonsense controls) and
  held-out (38 cases: 34 determinate + 4 uncertainty) never mix. Nothing was tuned on
  held-out.
- **Ten generalization dimensions** are represented, each with its own per-dimension
  report: `unseen_vocabulary`, `known_root_unseen_inflection`,
  `incorrect_inflection_unseen`, `unseen_combination`, `unseen_sentence`,
  `person_verb_agreement`, `active_passive`, `noun_case_number`, `ambiguous_analysis`,
  `correct_resembling_incorrect`, `false_positive_guard`, `missing_verb`, `punctuation`,
  `sandhi_avagraha`.
- **Independence is checked by the label validator**, which runs **without invoking the
  engine**: it verifies there are no dataset collisions, that every claimed "unseen"
  token really is absent from the live resources, and that the uncertainty labels are
  structurally derived rather than hand-written to match the engine's output.
- **Baseline is a validated shim, not `git HEAD`.** `HEAD` (`bf3ac32`) predates unrelated
  earlier work (`_load_lexicon`, Ollama wiring), so comparing against it would be
  comparing against a different program. `--validate-baseline` replays the shim and
  reproduces all 7 recorded pre-change development misses — DEV-01/02/07/11/12/29/30 at
  scores 95/95/95/85/85/100/100 — returning **YES**. That makes the before/after in
  §10 a like-for-like comparison.

### Two pre-existing test-harness bugs fixed (no assertions changed)

`verify_grammar_uncertainty.py` and `verify_lexicon.py` (throwaway harness scripts kept
in the scratch directory, **not** part of the repository) omitted `use_ai` from the
request, so they were silently running in **AI** mode and only passing when the provider
degraded. They now send `use_ai=False`. **No assertion, label or threshold was touched** —
this changed which code path the scripts exercise, not what they require.

---

## 9. Phase F — documentation

**File:** `README.md` (406 → 508 lines, +114 / −12)

- Added a pointer to this file.
- **Corrected two factual errors:** `evaluate_grammar.py` was described as a "300-case
  grammar benchmark" in two places — it actually runs the 51-case
  `grammar_test_dataset.json`. The 300-case benchmark is
  `evaluate_agreement_benchmark.py`. Both the Repository Layout and the Testing table
  now name the right suites and add the two new ones.
- **Environment variables:** documented `OLLAMA_API_KEY`, `AI_MODEL` and `BASE_URL`
  accurately, and added the AI routing order as a code block.
- **Grammar Checker:** documented the six generalization behaviours and pointed at the
  suites that measure them.
- **Data & Storage:** added the two new datasets (marked *not yet tracked*, because they
  are still untracked).
- **Testing & Verification:** full suite table, the last full run's results, and the
  before/after generalization metric table.
- **Security Notes:** added Odd One Out server-side grading, username/role policy, and
  the corrupt-store behaviour.
- **Known Limitations:** replaced the stale `XAI_API_KEY` wording; added the avagraha
  case, accepted-nonsense control, first-person-only destination rule, and an explicit
  statement that **browser/UI testing has never been performed** — only HTTP API and
  build verification.
- **Render environment:** added the optional AI keys.

---

## 10. Before / after measurements

### Held-out (34 determinate cases + 4 uncertainty cases)

| Metric | Baseline (validated shim) | Current |
|---|---:|---:|
| Accuracy | 82.35% | **97.06%** |
| Precision | 75.00% | **93.33%** |
| Recall | 85.71% | **100.00%** |
| F1 | 80.00% | **96.55%** |
| TP / FP / TN / FN | 12 / 4 / 16 / 2 | **14 / 1 / 19 / 0** |
| FP rate | 20.00% | **5.00%** |
| FN rate | 14.29% | **0.00%** |
| Correction exact-match | 11/13 | **13/13** |
| Uncertainty precision | 44.4% | **80.0%** |
| Uncertainty coverage | 23.7% | 13.2% |
| False-uncertainty count | 5 | 1 |

Per split: **A 9/9 · B 6/10 → 10/10 · C 7/8 · D 6/7 → 7/7.**

Per dimension (current): every dimension at 100% except `sandhi_avagraha` (0/1) — see
[§13](#13-known-limitations-and-remaining-failures).

### Development split

**23/30 → 30/30**; FP 5 → 0, FN 2 → 0.

### Why this counts as generalization rather than memorization

- Dev and held-out are physically separate files; held-out was never used for tuning.
- The held-out set contains vocabulary and inflections **verified absent** from every
  development resource by the engine-free label validator.
- The label corrections in §7 were applied to *both* runs, so they cannot advantage the
  new engine.
- 10 dimensions are reported individually, not collapsed into one number.
- The accepted-nonsense control set (2 cases) is reported separately and is **not** folded
  into the accuracy figure.

---

## 11. Tests added and how they stay independent

| Suite | Cases | Independence |
|---|---:|---|
| `test_generalization.py` | 63 | Rule-level: each of R1–R9 has positive, negative, boundary and lexical assertions. R9 asserts the fixture words are genuinely absent from development resources, so a "fix" that merely memorizes the test data fails. |
| `evaluate_generalization.py` | 34 + 4 held-out, 30 dev | Scores against a **sealed** file written before the fixes. Exits non-zero while any case fails, so a regression cannot pass silently. |
| `evaluate_grammar.py` | 51 | Pre-existing, unmodified, `grammar_test_dataset.json` untouched. |
| `evaluate_agreement_benchmark.py` | 300 | Pre-existing, unmodified. |

**Assertions, labels and thresholds were not changed to obtain any number in §10.**

Verification suites run against the live server and were re-run after every change:

```
51-case 100%  ·  300-case 100%  ·  uncertainty 68/0/0  ·  agreement 46/46
layers 21/21  ·  lexicon 21/21  ·  fixes 36/36  ·  generalization rules 63/63
AI 23/23  ·  auth 14/14  ·  quiz 24/24
tsc --noEmit 0  ·  next build 0  ·  eslint 205 (104 errors / 101 warnings, unchanged baseline)
```

`evaluate_generalization.py` reports **33/34** on held-out and exits `1` by design while
any case still fails.

---

## 12. Reproducing the results

From `backend/`, with the same interpreter:

```bash
python evaluate_generalization.py --validate-baseline   # proves the shim == recorded baseline
python evaluate_generalization.py                       # current engine, held-out (exits 1 while any case fails)
python evaluate_generalization.py --baseline            # replay of the pre-change engine
python test_generalization.py                           # 63 rule-level assertions
python evaluate_grammar.py                              # 51-case regression suite
python evaluate_agreement_benchmark.py                  # 300-case benchmark
python test_agreement.py
```

Frontend quality gates, from `frontend/`:

```bash
npx tsc --noEmit
npx next build
npx eslint "src/**/*.{ts,tsx}"
```

Windows notes: PowerShell has no `&&`; Devanagari passed through `python -c` is
unreliable — write a temporary `.py` file with `Set-Content -Encoding UTF8` and capture
`$LASTEXITCODE`.

---

## 13. Known limitations and remaining failures

1. **Held-out failure H-C08 — avagraha (`sandhi_avagraha`, split C).**
   `रामोऽस्ति वीरः।` is labelled `expected_valid: true`. The engine raises **no** error
   (`issues=[]`) — nothing is wrongly reported — but `ऽस्ति` is not tokenised, so the
   word is listed as *Uncertain — Unable to Verify* and the score is capped at **92**.
   Since `engine_valid` is defined as `score == 100`, this counts as one false positive.
   It is the only held-out case in any dimension that does not score 100.
   *Why it was not fixed:* supporting it requires changing the `breakdown` /
   `word_count` response contract — an architecture boundary, not a rule gap. The case is
   deliberately retained and labelled in the data as an expected-unsupported construction.
2. **Accepted nonsense scores 100.** `क्लान्ब्रः गच्छति` and `रामः ब्लर्फम् गच्छति`
   (2/2 measured) pass because the engine checks agreement and case, not whether the
   words are real. Reported separately; not folded into accuracy.
3. **Destination rule fires on first person only.**
4. **One false uncertainty remains** on determinate input (was 5 at baseline).
5. **AI-mode `unknown_words` reflects what the model flagged**, not the rule engine's own
   uncertainty — a pre-existing, documented design property.
6. **The AI pass is opt-in.** `/grammar/check` always overrides `use_ai` from the request
   body, and the Grammar page toggle defaults to **off**. No environment variable can
   force AI mode. Options were offered (toggle default on / server-side force / client
   default) and **no option has been chosen yet** — no code was changed for this.
7. **Browser/UI testing has never been performed.** All verification has been HTTP API +
   build only.
8. **Production Render backend has no `OLLAMA_API_KEY`.** `backend/.env` is gitignored, so
   the key used locally does not reach Render.

---

## 14. Outstanding manual actions

These cannot be done from this working tree and remain open:

1. **Set `OLLAMA_API_KEY` in Render** (and optionally `AI_MODEL`) for the deployed
   backend, otherwise production stays on the legacy provider.
2. **Rotate every credential pasted in chat**, including the working Ollama Cloud key.
3. **Rotate `backend/data/.token_secret`.** It is committed to git history; adding it to
   `.gitignore` alone does not remove it.
4. **Decide what to do with `use_ai`** (always-on vs. toggle) — options presented, none
   chosen.
5. **Decide the `गमन्ति` policy** — undecided.
6. **Decide whether to fix avagraha** — requires a response-contract change.
7. **Review the two `zz_audit_*` accounts** and the three untracked `*_progress.json`
   scratch files; the user's instruction so far has been to delete nothing.

---

## 15. Deliberately not changed

- **Architecture.** Same 5-layer classifier, same check pipeline, same score formula,
  same response shape, same endpoint signatures.
- `backend/data/grammar_test_dataset.json` and every benchmark label file.
- Authentication scheme, password hashing, token format, CORS policy, deployment
  configuration.
- No dependency was installed, uninstalled, replaced or version-pinned.
- No `any` and no `@ts-ignore` were introduced.
- No database rows or user data files were deleted or restored.
- No activity, vocabulary, XP, mastery, accuracy or scheduling data was fabricated.
- `fix_nlp.py`, `test_api_key.py` and the other pre-existing standalone scripts are
  tracked but not imported; left alone.
- The `zz_audit_*` accounts and all `grammar_attempts` — kept, per the user's instruction.
