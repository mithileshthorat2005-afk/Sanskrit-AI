# SanskritAI

Intelligent Sanskrit language learning through adaptive, evidence-based practice.

SanskritAI is a full-stack web application: a **Next.js** frontend talking to a **FastAPI**
backend. It teaches Sanskrit through 25 graded lessons, a rule-based grammar checker, a
bilingual dictionary, and two practice games — and it tracks genuine learning progress with
a Bayesian Knowledge Tracing (BKT) mastery model.

> Migrated from an earlier Streamlit prototype to this full-stack architecture.

> **Local, uncommitted work:** every modification in this working tree is listed file by
> file, with the reason for it, in [CHANGES.md](CHANGES.md).

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Running Locally](#running-locally)
- [Environment Variables](#environment-variables)
- [Features](#features)
- [How Mastery Works](#how-mastery-works)
- [Data & Storage](#data--storage)
- [API Reference](#api-reference)
- [Testing & Verification](#testing--verification)
- [Deployment](#deployment-render--vercel)
- [Security Notes](#security-notes)
- [Known Limitations](#known-limitations)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16.1.6 (App Router, Turbopack), React 19.2.3, TypeScript 5 |
| Styling / motion | Tailwind CSS, framer-motion, lucide-react |
| Transliteration | `@indic-transliteration/sanscript` |
| Backend | FastAPI 0.104.1, Uvicorn, Pydantic |
| Auth | Custom HMAC-SHA256 tokens + bcrypt password hashing |
| Persistence | SQLite (`sanskrit_ai.sqlite3`) + JSON data files |
| NLP / morphology | Prakriya (Pāṇinian derivations), custom noun declension engine |
| Optional AI | xAI Grok (rule-based fallback when unavailable) |

---

## Repository Layout

```
.
├── frontend/                  Next.js application
│   ├── src/app/               Route pages (see below)
│   ├── src/components/        Shared UI + 24 interactive lesson components
│   ├── src/context/           AuthContext (session handling)
│   └── src/lib/api.ts         API client
│
└── backend/                   FastAPI server
    ├── main.py                App entry point + all HTTP routes
    ├── modules/               Core logic (see below)
    ├── data/                  Data files, SQLite DB, user accounts
    ├── evaluate_grammar.py      51-case grammar classification regression suite
    ├── test_agreement.py        Subject–verb agreement regression suite
    ├── evaluate_agreement_benchmark.py   300-case agreement benchmark
    ├── evaluate_generalization.py        Held-out generalization report (splits A–D)
    └── test_generalization.py   Rule-level assertions for the generalization fixes
```

**Backend modules** (`backend/modules/`):

| Module | Responsibility |
|---|---|
| `auth.py` | Account store, bcrypt hashing, password policy |
| `auth_dependency.py` | FastAPI `get_current_user` dependencies |
| `jwt_auth.py` | Token creation/verification, revocation |
| `nlp_processor.py` | Main analysis pipeline: 5-layer word classifier, checks, scoring |
| `paninian_analyzer.py` | Prakriya-based verb derivations |
| `noun_analyzer.py` | Noun declension rules |
| `translator.py` | Dictionary + sentence translation |
| `bkt_engine.py` | Bayesian Knowledge Tracing mastery model |
| `sqlite_repository.py` | Learning database (attempts, mastery, XP, streaks) |
| `database.py` | Legacy JSON progress store |
| `learning_engine.py` | Lesson catalog and recommendations |
| `skill_mapper.py` | Maps grammar errors → skills for mastery updates |
| `snake_ladder.py`, `odd_one_out.py` | Game logic |

**Frontend routes**: `/` (login/signup), `/dashboard`, `/lessons`, `/grammar`,
`/translation`, `/game`, `/game/menu`, `/progress`, `/admin`.

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (20+ recommended)
- npm

> `torch` and `transformers` are listed in `backend/requirements.txt` and are heavy.
> The core grammar engine runs on Prakriya and the local analyzers; the ML packages
> are only needed for optional AI features.

---

## Running Locally

You need **two terminals** — the backend and frontend run as separate processes.

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The backend listens on **`http://127.0.0.1:8005`**. Keep this terminal open while using
the app. Interactive API docs are at **`http://127.0.0.1:8005/docs`**.

From the repository root, `pip install -r requirements.txt` also works — it simply
includes `backend/requirements.txt`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **`http://localhost:3000`**.

The frontend defaults to `http://127.0.0.1:8005`, so no configuration is required for
local development. If your backend runs elsewhere, copy `frontend/.env.example` to
`frontend/.env.local`, set `NEXT_PUBLIC_API_URL`, and restart the frontend.

### Windows note

If `python` is not on your PATH, use your interpreter explicitly:

```powershell
C:\path\to\venv\Scripts\python.exe main.py
```

If the backend is not running, the site still loads but every request fails with
*"Cannot reach the SanskritAI backend"*.

---

## Environment Variables

### Backend (`backend/`)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `AUTH_TOKEN_SECRET` | **In production** | generated dev file | Signing secret for auth tokens. When `APP_ENV=production` the server **refuses to start** without it. |
| `APP_ENV` | Prod only | `development` | Set to `production` to enforce the secret requirement. |
| `ALLOWED_ORIGINS` | No | built-in list | Comma-separated origins added to the CORS allowlist. |
| `SQLITE_DB_PATH` | No | `backend/data/sanskrit_ai.sqlite3` | Location of the learning database. |
| `OLLAMA_API_KEY` | No | — | **Preferred** AI key. Ollama Cloud keys have the shape `<32 hex>.<token>`. Enables AI grammar/translation. |
| `XAI_API_KEY` | No | — | Fallback AI key. Accepts a Groq key (`gsk_…`) or an xAI key; only read when `OLLAMA_API_KEY` is unset. |
| `AI_MODEL` | No | provider default | Overrides the model id — `gemma4:31b-cloud` (Ollama), `openai/gpt-oss-120b` (Groq), `grok-4-fast` (xAI). |
| `BASE_URL` | No | `https://api.x.ai/v1` | Endpoint override for the xAI provider. |
| `PORT` | No | `8005` | Server port. |

**AI key routing** (`nlp_processor.py` and `translator.py` share the same order):

```
OLLAMA_API_KEY set, or key matches <32 hex>.   → Ollama Cloud   https://ollama.com/v1
key starts with gsk_                            → Groq           https://api.groq.com/openai/v1
anything else                                  → xAI (Grok)     https://api.x.ai/v1
no key at all                                  → rule-based only, ai_verified: false
```

The Ollama key shape is unique to Ollama, so a key pasted into `XAI_API_KEY` still
routes to Ollama. Without any key the grammar checker stays fully functional in
rule-based mode and never claims an AI verification it did not perform.

### Frontend (`frontend/`)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | No | `http://127.0.0.1:8005` | Backend base URL. |

---

## Features

### Authentication

- Signup with **server-enforced password policy**: a lowercase letter and a minimum
  length of 8 are **required**; uppercase, digits and special characters are optional
  and surfaced as a non-blocking strength checklist.
- bcrypt password hashing. Legacy `hashed_` records migrate to bcrypt on the next
  successful login.
- Tokens are HMAC-SHA256 signed, with server-side revocation on logout.
- On page load the frontend **verifies the stored token with `GET /auth/me`** before
  treating you as signed in, so an expired or revoked token fails immediately instead
  of half-working. A backend outage does *not* sign you out.
- User files are written atomically (temp file + `fsync` + rename) and re-read when
  the file changes on disk, so multiple server processes cannot overwrite each other's
  accounts.

### Lessons & Graded Quizzes

- **25 lessons** covering the alphabet through prosody (Chandas).
- Each lesson has an **interactive component** (24 custom components) plus a
  **graded quiz of 7–10 multiple-choice questions**.
- Quizzes are collapsed behind a **Start Quiz** button; questions are numbered and the
  four options render as an aligned **A/B/C/D 2×2 grid**.
- Quizzes are **graded on the server** against the backend's own copy of the questions,
  so answers cannot be spoofed from the browser.
- **Mark as Complete requires a 100% quiz score.**
- Quiz questions are generated from the project's own data files, so every answer key
  is copied verbatim from real entries rather than hand-typed.

### Grammar Checker

A rule-based analyzer with a layered word classifier:

```
Dictionary → Prakriya verb analyzer → Active paradigm table
          → Passive paradigm table → Noun declension rules → Unknown
```

- **Confirmed errors only** are counted. Advisory/meta notices are not shown.
- Corrections are generated for confidently detected errors (missing *pūrṇa virāma*,
  subject–verb agreement, destination case).
- **Uncertain words are surfaced honestly.** A word is "unknown" only when *every*
  layer failed to resolve it. Unknown words are listed at the top of the results with
  the status `Uncertain — Unable to Verify`, the reason, and a spelling/context
  suggestion. They are never reported as errors, and never silently treated as correct.
- Scoring keeps the two apart:

  ```
  confirmed_penalty   = confirmed_errors × 15
  uncertainty_penalty = ceil(15 × unknown_words / total_words)
  score               = max(0, 100 − confirmed_penalty − uncertainty_penalty)
  if any unknown:     score = min(score, 99)
  ```

  A sentence containing an unknown word can therefore never be reported as 100% correct,
  while a fully analysed, error-free sentence still scores 100.

- **It generalizes beyond words it has seen.** The classifier no longer depends on the
  surface spelling being the one stored in the lexicon:

  - **Sandhi-resilient lookup.** A form ending in `ो` / `र्` is retried against the
    dictionary entry ending in `ः`, so unseen `सिंहो` resolves to `सिंहः` and `व्याघ्रो`
    to `व्याघ्रः` — morphologically, with no stem list — instead of falling through to
    *Unknown*.
  - **Anusvāra surface variants.** `ं` and `म्` are treated as the same surface for
    lookup (`गच्छन्ति ↔ गच्छन्त्`, `कर्मन् ↔ कर्म`), tried in Layer 1 before any lower
    layer can claim the word.
  - **Attested stem + paradigm.** A candidate parse must be attested by an analysing
    layer before it is believed — a stem the engine can itself produce is not counted
    as independent evidence (self-confirmation guard).
  - **Genuine ambiguity is reported as ambiguity.** When one stem is offered for two
    numbers by the same source, the number is left blank rather than guessed.
  - **Nominal sentences are legal.** Sanskrit sentences with no finite verb (`अहं
    विद्यार्थी।`) no longer raise a *no verb* error.
  - **Destination case generalises.** The rule derives the required accusative from the
    verb's own paradigm instead of a hardcoded stem list, so it fires for verbs whose
    stems are not special-cased.

  These are covered by `test_generalization.py` (rule-level assertions) and measured on
  the sealed splits in `evaluate_generalization.py` — see
  [Testing & Verification](#testing--verification).

### Translation

- Sanskrit ↔ English using a bundled dictionary and sentence database.
- Word-by-word breakdown with transliteration.

### Games

- **Snake & Ladder** — correct answers climb, incorrect answers send you to a snake.
- **Odd One Out** — identify the Sanskrit word that does not belong in a group.

### Dashboard & Progress

- Dashboard shows lessons completed, level, and XP — all read from real data, with
  honest empty states instead of fabricated zeros.
- Progress page shows streaks, BKT mastery, grammar accuracy, and a **Quiz Performance**
  panel (attempts, average, best, most recent, lessons attempted, questions correct).

---

## How Mastery Works

Mastery is modelled with **Bayesian Knowledge Tracing** per skill.

- Each graded answer produces one BKT observation (`correct` / `incorrect`).
- **Only graded attempts move mastery.** Marking a lesson complete deliberately does
  not — completion is a progress marker, not evidence of learning.
- Grammar-check errors also feed mastery through `skill_mapper.py`, which maps an error
  type to the skill it demonstrates.
- An account with no attempts reports mastery as `0.0` with no attempts recorded, which
  the UI renders as *"Not attempted yet"* rather than a misleading 0%.
- XP awards are **idempotent**, keyed on the underlying event, so refreshing or
  resubmitting cannot inflate your score.
---

## Data & Storage

| File | Tracked in git | Contents |
|---|---|---|
| `backend/data/sanskrit_ai.sqlite3` | No (`*.sqlite3`) | Attempts, mastery, XP, streaks, lesson completions |
| `backend/data/users.json` | No | Accounts and bcrypt password hashes |
| `backend/data/.token_secret` | **Yes — see Security Notes** | Development token signing secret |
| `backend/data/lessons.json` | Yes | Lesson catalog + graded quiz questions |
| `backend/data/sanskrit*.json` | Yes | Grammar/vocabulary data files |
| `backend/data/sanskrit_words.csv` | Yes | Translation dictionary |
| `backend/data/sanskrit_grammar_benchmark_300.json` | Yes | 300-case benchmark dataset |
| `backend/data/generalization_dev.json` | Not yet (new file) | 30 development cases + accepted-nonsense controls |
| `backend/data/generalization_heldout.json` | Not yet (new file) | 38 held-out cases in splits A–D + uncertainty labels |

The SQLite database is the authoritative store for learning data. Per-user
`*_progress.json` files are legacy and still read for compatibility.

---

## API Reference

All routes are served by `backend/main.py`. Interactive docs at `/docs`.

**Auth** — `POST /auth/login` · `POST /auth/signup` · `POST /auth/logout` · `GET /auth/me`

**Lessons** — `GET /lessons` · `GET /lessons/{id}` · `GET /api/lessons/{topic}`
(topics: `greetings`, `numbers`, `self-intro`, `pronouns`, `verbs`, `nouns`, `family`,
`questions`, `time`, `vibhakti`, `sandhi`, `tenses`, `moods`, `pronouns-extended`,
`upasarga`, `voice`, `indeclinables`, `participles`, `reading-composition`, `samasa1`,
`samasa2`, `participles2`, `stri-pratyaya`, `chandas`)

**Progress** — `GET /progress` · `POST /progress/complete` · `POST /progress/quiz` ·
`GET /activities` · `GET /dashboard` · `GET /dashboard/stats` · `GET /streak` ·
`POST /streak/activity` · `GET /recommendation`

**Mastery** — `GET /bkt/summary` · `GET /bkt/mastery` · `POST /lesson/attempt`

**Language** — `POST /grammar/check` · `GET /grammar/history` · `POST /translate` ·
`GET /suggestions` · `GET /api/daily-questions` · `POST /support/chat`

**Games** — `GET /game/start` · `POST /game/turn` · `GET /game/odd/question` ·
`POST /game/odd/answer`

---

## Testing & Verification

Run from the `backend/` directory with your Python interpreter.

| Suite | What it covers |
|---|---|
| `python evaluate_grammar.py` | 51-case grammar classification regression suite |
| `python test_agreement.py` | Subject–verb agreement and voice-preserving corrections |
| `python evaluate_agreement_benchmark.py` | 300-case subject–verb agreement benchmark |
| `python evaluate_generalization.py` | Sealed held-out generalization report (splits A–D + uncertainty). `--baseline` replays the pre-change engine; `--validate-baseline` proves the shim reproduces the recorded baseline. |
| `python test_generalization.py` | 63 rule-level assertions for each generalization fix — positive, negative, boundary and lexical cases |

**Last full run:** the assertion suites report **0 failures** — 51/51
(`evaluate_grammar.py`), 300/300 (`evaluate_agreement_benchmark.py`), agreement 46/46,
generalization rules 63/63, plus the layers, lexicon, AI, auth and quiz verification
suites. `evaluate_generalization.py` reports **33/34** on held-out and therefore exits
`1` by design while any case still fails. `npx tsc --noEmit` and `npx next build` both
exit 0; `npx eslint` is unchanged from the pre-existing baseline.

**Generalization, held-out split only** (34 determinate cases + 4 uncertainty cases),
pre-change engine → current engine:

| Metric | Baseline | Now |
|---|---|---|
| Accuracy | 82.35% | **97.06%** |
| Precision / Recall / F1 | 75.00 / 85.71 / 80.00 | **93.33 / 100.00 / 96.55** |
| False positives (FP rate) | 4 (20.00%) | **1 (5.00%)** |
| False negatives (FN rate) | 2 (14.29%) | **0 (0.00%)** |
| Correction exact-match | 11/13 | **13/13** |
| Uncertainty precision | 44.4% | **80.0%** |

The development split went 23/30 → 30/30 (FP 5 → 0, FN 2 → 0). Dev and held-out are
separate files; nothing was tuned on held-out.

Benchmark labels and expected outcomes must not be edited to improve metrics.

Verification scripts for auth, quiz/mastery wiring and uncertainty handling run against
the live server and are meant to remove the throwaway accounts they create. Two
`zz_audit_*` accounts from earlier runs were left behind and have been kept — see
[CHANGES.md](CHANGES.md).

Quality gates used during development:

```bash
cd frontend
npx tsc --noEmit      # type check
npx next build        # production build
npx eslint .          # lint
```

---

## Deployment (Render + Vercel)

The backend deploys to **Render** and the frontend to **Vercel**.

### Render — Environment

| Key | Value |
|---|---|
| `APP_ENV` | `production` |
| `AUTH_TOKEN_SECRET` | 32 random bytes — **the app will not boot without it** |
| `SQLITE_DB_PATH` | Your disk mount, e.g. `/var/data/sanskrit_ai.sqlite3` |
| `ALLOWED_ORIGINS` | Comma-separated Vercel URLs |
| `OLLAMA_API_KEY` | Optional — Ollama Cloud, preferred provider |
| `XAI_API_KEY` | Optional — Groq or xAI fallback |
| `AI_MODEL` | Optional — model id override |

Generate a secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Render — Disk

Attach a **persistent disk** and point `SQLITE_DB_PATH` at it. Do **not** use a Secret
File for the database: SQLite writes on every request, and Secret Files are read-only
and ephemeral.

### Render — Secret Files

Add `users.json` if you want to carry existing accounts. It mounts at
`/etc/secrets/users.json`, but the app reads `data/users.json`, so copy it in your
start command:

```
cp /etc/secrets/users.json ./data/users.json && python main.py
```

### Vercel — Environment

```
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

### CORS

The backend allows only origins on an explicit allowlist (no wildcard — a wildcard
combined with credentials is a security hole). Vercel serves every deployment and
preview on its own generated URL, so add new ones via `ALLOWED_ORIGINS` on Render and
redeploy. No code change is required.

Prefer testing on your **production domain** rather than a per-deployment URL.

---

## Security Notes

- **Rotate `backend/data/.token_secret`.** It is currently committed to git, which means
  anyone with repository access can forge auth tokens. Setting `AUTH_TOKEN_SECRET` on
  Render protects the deployment, but the leaked secret remains in git history and
  should be replaced. Adding it to `.gitignore` alone does **not** fix this.
- Passwords are bcrypt-hashed; there is no plaintext or reversible fallback.
- `users.json` and the SQLite database are gitignored and must never be committed.
- CORS uses a strict allowlist with `allow_credentials=True`. There is deliberately no
  `allow_origin_regex` and no `*`.
- Quiz answers are validated server-side against the backend's own question set.
- **Odd One Out answers are graded from the server's own catalog.** The echoed
  `correct_index` / `correct_word` from the browser is never trusted; the payload is
  re-matched against `odd_one_out.QUESTIONS` and a payload that matches nothing is
  rejected with 400.
- Signup validates the username (3–50 chars, no leading/trailing or inner whitespace, no
  control characters) and restricts `role` to `student` / `teacher` / `admin`.
- A corrupt or hand-edited `users.json` record degrades to a normal 401 on login rather
  than a 500, and never crashes protected endpoints.
- XP awards are idempotent and cannot be farmed by repetition.

---

## Known Limitations

- **AI mode requires a configured key** (`OLLAMA_API_KEY`, or `XAI_API_KEY` holding a
  Groq/xAI key). Without one — or if the provider rejects the call — the grammar checker
  degrades to rule-based analysis and reports `ai_verified: false` together with the
  provider's own error in `ai_error`; the UI shows *"AI check unavailable"*. It never
  claims verification it did not perform. The AI pass is also **opt-in**: the Grammar
  page toggle defaults to off, so `/grammar/check` receives `use_ai: false` unless the
  learner turns it on.
- **Avagraha (`ऽ`) is not tokenised.** `रामोऽस्ति वीरः।` raises **no** error — nothing
  is wrongly reported — but `ऽस्ति` cannot be parsed, so it is listed as *Uncertain —
  Unable to Verify* and the score is capped at 92. Since a case only counts as correct
  at exactly 100, this is the **single remaining held-out failure** (H-C08, split C,
  dimension `sandhi_avagraha`). The case is deliberately kept in the held-out set and
  labelled in the data as an expected-unsupported construction rather than removed.
  Fixing it means changing the `breakdown` / `word_count` response contract, which is an
  architecture boundary rather than a rule gap.
- **Nonsense input with a matching verb ending is accepted.** `क्लान्ब्रः गच्छति` and
  `रामः ब्लर्फम् गच्छति` score 100 — the engine checks agreement and case, not whether
  the words are real. Measured at 2/2 in the accepted-nonsense control set.
- **The destination-case rule only fires on first person.** Other persons are not yet
  checked.
- **Token revocation is in-memory.** A server restart clears the revocation list, so
  previously logged-out tokens become valid again until they expire.
- **No scheduler.** Streaks are computed from recorded activity days only.
- **The `/admin` page shows honest empty states.** No admin API has been implemented.
- **Testing has been done against the HTTP API and the production build only.** The
  browser UI has not been exercised end-to-end in a real browser session.
- Some words fall outside the analyzers' coverage and are reported as *Uncertain —
  Unable to Verify* rather than being guessed at. This is intentional.
