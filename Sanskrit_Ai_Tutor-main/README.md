# SanskritAI

Intelligent Sanskrit language learning through adaptive, evidence-based practice.

SanskritAI is a full-stack web application: a **Next.js** frontend talking to a **FastAPI**
backend. It teaches Sanskrit through 25 graded lessons, a rule-based grammar checker, a
bilingual dictionary, and two practice games — and it tracks genuine learning progress with
a Bayesian Knowledge Tracing (BKT) mastery model.

> Migrated from an earlier Streamlit prototype to this full-stack architecture.

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
    ├── evaluate_grammar.py    300-case grammar benchmark
    └── test_agreement.py      Subject-verb agreement regression suite
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
| `XAI_API_KEY` | No | — | Enables AI grammar/translation. Without it, rule-based analysis is used. |
| `BASE_URL` | No | `https://api.x.ai/v1` | AI provider endpoint. |
| `PORT` | No | `8005` | Server port. |

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
| `python evaluate_grammar.py` | 300-case grammar classification benchmark |
| `python test_agreement.py` | Subject–verb agreement and voice-preserving corrections |

The grammar benchmark currently reports **0 failures and 0 processing exceptions**.
Benchmark labels and expected outcomes must not be edited to improve metrics.

Additional verification scripts (auth, quiz/mastery wiring, uncertainty handling) are
run against the live server and clean up any throwaway accounts they create.

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
| `XAI_API_KEY` | Optional |

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
- XP awards are idempotent and cannot be farmed by repetition.

---

## Known Limitations

- **AI mode requires a working `XAI_API_KEY`.** Without one (or if the provider
  returns an error) the grammar checker silently degrades to rule-based analysis and
  reports `ai_verified: false` — it never claims verification it did not perform.
- **Token revocation is in-memory.** A server restart clears the revocation list, so
  previously logged-out tokens become valid again until they expire.
- **No scheduler.** Streaks are computed from recorded activity days only.
- **The `/admin` page shows honest empty states.** No admin API has been implemented.
- Some words fall outside the analyzers' coverage and are reported as *Uncertain —
  Unable to Verify* rather than being guessed at. This is intentional.
